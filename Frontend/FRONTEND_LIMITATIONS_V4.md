# EduSphere Frontend — Remaining Limitations After Cross-Role Cleanup

Date: 27 September 2026

This version incorporates the Student, Instructor and Admin testing pass and fixes the UI/state issues found during those tests.

## Fixed in this pass

- Student/instructor/admin catalog wording is now role-aware.
- Student enrollment-awareness remains enabled; already-enrolled offerings do not invite duplicate enrollment.
- Date-only database values no longer render as midnight timestamps.
- Numeric fields such as quiz Max Attempts are no longer mistaken for timestamps.
- Student attendance and exam tables hide database/audit IDs.
- Instructor assignment/submission and roster tables now prioritize human-readable student/course data.
- Admin semester, roster and upcoming-exam tables hide unnecessary internal IDs.
- Profile pages no longer expose the internal LMS User ID in the primary UI.
- Closed/non-active offering write forms are blocked in the frontend while read/grading views remain available.
- Already-configured assignment/quiz/exam assessment components are removed from creation selectors.
- Generic ODBC/pyodbc/Unicode exception text is sanitized before being shown to users.
- File/resource wording now clearly states that the current API requires a hosted/shared URL; local file selection is not an upload.
- Calendar/chart labels expose full text through native hover titles.
- Assignment submission URLs are shown as human-readable Open submission links.

## Remaining frontend limitations

1. **Real file uploads are not available.**
   The current Django contract stores a URL rather than uploaded file bytes. The frontend can only validate/select a local file as a helper and submit a hosted/shared URL.

2. **No server-restored in-progress quiz answers.**
   Quiz drafts are stored in browser sessionStorage until final submission. Opening the same active attempt on another browser/device cannot restore local draft answers from the backend.

3. **Quiz countdown is client-assisted, not authoritative.**
   The frontend countdown improves UX, but Oracle/Django remain authoritative for duration and close-time enforcement.

4. **No quiz attempt-history endpoint.**
   When maximum attempts are exhausted, the frontend can show a friendly error but cannot automatically list/open prior attempts unless the backend exposes attempt history.

5. **Unexpected pyodbc driver failures still require backend repair.**
   The frontend now hides technical details and shows a safe retryable message, but a driver-level Unicode/exception decoding failure still produces an HTTP 500 until the backend/ODBC path is corrected.

6. **Admin student discovery is roster-derived.**
   The report page builds its student selector by loading offering rosters because there is no dedicated admin student-directory endpoint.

7. **Question-bank quiz discovery requires multiple requests.**
   The frontend scans available offerings/grading components to discover quiz choices instead of consuming a single dedicated quiz-directory endpoint.

8. **Table search/sort/pagination are client-side.**
   This is appropriate for the current course-project dataset but is not optimized for very large LMS datasets.

9. **No real-time synchronization.**
   Updates from another user/browser appear after refresh/reload; there is no WebSocket/SSE channel.

10. **No persistent authoring drafts for most instructor/admin forms.**
    Unsubmitted assignment, announcement, material, quiz, exam or session forms are lost on reload.

11. **No report export workflow yet.**
    Admin reports are readable and searchable but do not currently export CSV/PDF from the frontend.

12. **Accessibility is improved but not formally audited.**
    A dedicated keyboard/screen-reader/WCAG audit is still recommended before production use.

13. **Timezone handling is basic.**
    The frontend renders browser-local date/time values and assumes backend values are appropriate for the deployment timezone.

14. **No formal browser E2E suite yet.**
    Static checks and manual role-based testing have been performed, but Playwright/Cypress coverage is not yet present.
