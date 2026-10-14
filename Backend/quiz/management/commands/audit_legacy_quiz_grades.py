"""Audit old quiz attempts using the immutable EduSphere 37-table schema.

This command is read-only unless --sync-existing is specified. Missing
QUIZ_GRADING rows must be investigated manually: answer keys may have changed
since those attempts were submitted and cannot safely be reconstructed by a
bulk automatic migration.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from database.query import fetch_all
from database.schema import object_name
from database.connection import atomic_oracle
from quiz.auto_grader import (
    load_recorder_user_id,
    lock_quiz_enrollment,
    synchronize_quiz_component_mark,
)

VALID_STATUSES = {"AUTO_GRADED", "REVIEWED", "RELEASED"}


def _num(value):
    return Decimal(str(value)) if value is not None else None


def get_legacy_audit_rows():
    # One row per submitted quiz attempt. A missing grading header is flagged,
    # not silently assumed to have zero marks.
    return fetch_all(f"""
        SELECT qa.ATTEMPT_ID, qa.ATTEMPT_NO, qa.QUIZ_ID, qa.STUDENT_ID,
               q.COMPONENT_ID, ac.MAX_MARKS AS COMPONENT_MAX_MARKS,
               gs.OFFERING_ID, e.ENROLLMENT_ID, sm.MARKS_OBTAINED,
               qg.GRADING_ID, qg.GRADING_STATUS, qg.FINAL_MARKS,
               qg.MAX_MARKS AS QUIZ_MAX_MARKS,
               (SELECT SUM(qq.QUESTION_MARKS)
                  FROM {object_name('QUIZ_QUESTION')} qq
                 WHERE qq.QUIZ_ID=qa.QUIZ_ID) AS CURRENT_QUESTION_TOTAL
          FROM {object_name('QUIZ_ATTEMPT')} qa
          JOIN {object_name('QUIZ')} q ON q.QUIZ_ID=qa.QUIZ_ID
          JOIN {object_name('ASSESSMENT_COMPONENT')} ac ON ac.COMPONENT_ID=q.COMPONENT_ID
          JOIN {object_name('GRADING_SCHEME')} gs ON gs.SCHEME_ID=ac.SCHEME_ID
          JOIN {object_name('ENROLLMENT')} e
            ON e.STUDENT_ID=qa.STUDENT_ID AND e.OFFERING_ID=gs.OFFERING_ID
          LEFT JOIN {object_name('QUIZ_GRADING')} qg ON qg.ATTEMPT_ID=qa.ATTEMPT_ID
          LEFT JOIN {object_name('STUDENT_MARK')} sm
            ON sm.ENROLLMENT_ID=e.ENROLLMENT_ID AND sm.COMPONENT_ID=q.COMPONENT_ID
         WHERE qa.SUBMITTED_AT IS NOT NULL
         ORDER BY qa.QUIZ_ID, qa.STUDENT_ID, qa.ATTEMPT_NO
    """)


@atomic_oracle
def _sync_one(group, best):
    # Do not touch QUIZ_GRADING records themselves; only the component mark.
    lock_quiz_enrollment(int(group['enrollment_id']))
    recorder = load_recorder_user_id(
        int(group['quiz_id']), int(group['offering_id']),
        best.get('reviewed_by_user_id'),
    )
    if recorder is None:
        raise ValueError('No authorized instructor available to record the component mark.')
    return synchronize_quiz_component_mark(
        int(group['component_id']), int(group['enrollment_id']),
        int(group['quiz_id']), int(group['student_id']), int(recorder),
    )


class Command(BaseCommand):
    help = 'Audit existing/historical quiz grades. Read-only by default; --sync-existing reconciles only already-graded attempts.'

    def add_arguments(self, parser):
        parser.add_argument('--sync-existing', action='store_true',
                            help='Update STUDENT_MARK to the highest existing finalized QUIZ_GRADING score (does not regrade missing attempts).')

    def handle(self, *args, **options):
        rows = get_legacy_audit_rows()
        groups = {}
        missing = []
        invalid = []
        inconsistent_max = []
        for row in rows:
            key = (int(row['quiz_id']), int(row['student_id']))
            group = groups.setdefault(key, {'context': row, 'eligible': []})
            status = row.get('grading_status')
            if row.get('grading_id') is None:
                missing.append(row['attempt_id'])
            elif status not in VALID_STATUSES:
                invalid.append((row['attempt_id'], status))
            else:
                group['eligible'].append(row)
                if (_num(row['quiz_max_marks']) is not None and
                        _num(row['component_max_marks']) != _num(row['quiz_max_marks'])):
                    inconsistent_max.append((row['attempt_id'], row['quiz_max_marks'], row['component_max_marks']))

        self.stdout.write(f'Submitted attempts: {len(rows)}; quiz/student groups: {len(groups)}')
        self.stdout.write(f'No QUIZ_GRADING record: {len(missing)} | attempt IDs: {missing[:50]}')
        self.stdout.write(f'Unrecognized grading status: {len(invalid)} | details: {invalid[:30]}')
        self.stdout.write(f'Quiz maximum vs assessment maximum mismatch: {len(inconsistent_max)} | (attempt, quiz, component): {inconsistent_max[:30]}')

        needs_sync = []
        for group in groups.values():
            if not group['eligible']:
                continue
            best = max(group['eligible'], key=lambda r: (
                _num(r['final_marks']) if r['final_marks'] is not None else Decimal('-1'),
                int(r['attempt_no']), int(r['attempt_id']),
            ))
            # A null grade cannot be used as a best-attempt mark.
            if best['final_marks'] is None:
                continue
            current = group['context'].get('marks_obtained')
            if current is None or _num(current) != _num(best['final_marks']):
                needs_sync.append((group['context'], best, current))
        self.stdout.write(f'Best-attempt component marks needing reconciliation: {len(needs_sync)}')
        for group, best, current in needs_sync[:50]:
            self.stdout.write(f"Quiz {group['quiz_id']}, student {group['student_id']}: "
                              f"recorded={current}, best={best['final_marks']} (attempt {best['attempt_id']})")

        if not options['sync_existing']:
            self.stdout.write(self.style.WARNING('READ-ONLY. Run --sync-existing only after backing up your database and reviewing this output.'))
            self.stdout.write('Missing grading rows require historical review; no automatic regrading is performed.')
            return

        self.stdout.write(self.style.WARNING('Synchronizing existing *graded* attempts only.'))
        synced = 0
        failed = []
        for group, best, _ in needs_sync:
            try:
                _sync_one(group, best)
                synced += 1
            except Exception as exc:
                failed.append((group['quiz_id'], group['student_id'], str(exc)))
        self.stdout.write(f'Synchronized: {synced}; failures: {len(failed)}')
        for quiz_id, student_id, error in failed:
            self.stderr.write(f'Quiz {quiz_id} / student {student_id}: {error}')
        if failed:
            raise CommandError('Some marks were not synchronized. See individual failures above.')
