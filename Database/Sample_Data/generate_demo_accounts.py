"""Generate an Oracle DML script for demo accounts using fresh Django PBKDF2 hashes.

No passwords are stored in the handoff ZIP. Run on the recipient's own computer.
Requires only Python 3.10+.
"""
import argparse
import base64
import getpass
import hashlib
import secrets
import string
from pathlib import Path

ROLES = (
    ('DEMO_ADMIN', 'ADMIN', 920001, 'demo.admin@example.invalid'),
    ('DEMO_INSTRUCTOR_A', 'INSTRUCTOR', 920002, 'demo.instructor.a@example.invalid'),
    ('DEMO_INSTRUCTOR_B', 'INSTRUCTOR', 920003, 'demo.instructor.b@example.invalid'),
    ('DEMO_STUDENT_A', 'STUDENT', 920004, 'demo.student.a@example.invalid'),
    ('DEMO_STUDENT_B', 'STUDENT', 920005, 'demo.student.b@example.invalid'),
)
ITERATIONS = 720000


def django_hash(password: str) -> str:
    alphabet = string.ascii_letters + string.digits
    salt = ''.join(secrets.choice(alphabet) for _ in range(22))
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('ascii'), ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt}${base64.b64encode(digest).decode("ascii").strip()}'


def generate(path: Path) -> None:
    if path.exists():
        raise SystemExit(f'Not overwriting existing file: {path} (move it away first).')
    print('Set five strong, distinct DEMO passwords. They are never printed or saved in plaintext.')
    hashes = {}
    passwords_seen = set()
    for username, role, user_id, email in ROLES:
        while True:
            pwd = getpass.getpass(f'Password for {username}: ')
            repeat = getpass.getpass('Repeat password: ')
            if len(pwd) < 10:
                print('Use at least 10 characters.'); continue
            if pwd != repeat:
                print('Passwords do not match.'); continue
            if pwd in passwords_seen:
                print('Use different passwords for each account.'); continue
            hashes[username] = django_hash(pwd)
            passwords_seen.add(pwd)
            break
    lines = [
        '-- AUTO-GENERATED DEMO LOGIN DML. Contains only password hashes, not plaintext passwords.',
        '-- Do not send this generated SQL file to other people.',
        'SET DEFINE OFF',
        'SET SERVEROUTPUT ON',
        'WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK',
        'DECLARE',
        '  v_count NUMBER;',
        'BEGIN',
        "  IF USER <> 'EDUSPHERE_OWNER' OR SYS_CONTEXT('USERENV','CON_NAME') <> 'XEPDB1' THEN",
        "    RAISE_APPLICATION_ERROR(-20997, 'STOP: only EDUSPHERE_OWNER in XEPDB1.');",
        '  END IF;',
        '  SELECT COUNT(*) INTO v_count FROM PROGRAM WHERE PROGRAM_ID = 910001;',
        "  IF v_count <> 1 THEN RAISE_APPLICATION_ERROR(-20998,'Run 01_sample_catalog.sql first.'); END IF;",
        "  SELECT COUNT(*) INTO v_count FROM LMS_USER WHERE Username='DEMO_ADMIN';",
        "  IF v_count <> 0 THEN RAISE_APPLICATION_ERROR(-20999,'Demo accounts already installed.'); END IF;",
        'END;',
        '/',
    ]
    for username, role, uid, email in ROLES:
        lines += [
            'INSERT INTO LMS_USER (User_ID,Username,Password_Hash,Email,Role,Account_Status)',
            f"VALUES ({uid},'{username}','{hashes[username]}','{email}','{role}','ACTIVE');",
        ]
    lines += [
        "INSERT INTO ADMIN (Admin_ID,User_ID,Admin_Name) VALUES (920001,920001,'Demo Administrator');",
        "INSERT INTO INSTRUCTOR (Instructor_ID,User_ID,Instructor_Name,Designation,Department_ID) VALUES (920001,920002,'Dr. Ananya Rao','Assistant Professor',910001);",
        "INSERT INTO INSTRUCTOR (Instructor_ID,User_ID,Instructor_Name,Designation,Department_ID) VALUES (920002,920003,'Dr. Dev Mehta','Associate Professor',910001);",
        "INSERT INTO STUDENT (Student_ID,User_ID,Student_Name,Admission_No,Batch,Program_ID,Student_Status) VALUES (920001,920004,'Aarav Patel','DEMO26CS001','2026',910001,'ACTIVE');",
        "INSERT INTO STUDENT (Student_ID,User_ID,Student_Name,Admission_No,Batch,Program_ID,Student_Status) VALUES (920002,920005,'Maya Singh','DEMO26CS002','2026',910001,'ACTIVE');",
        'COMMIT;',
        "PROMPT PASS: DEMO_ADMIN, two instructors and two students created. Passwords were set locally.",
    ]
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    try:
        path.chmod(0o600)
    except OSError:
        pass
    print(f'Generated {path}. Run it while connected as EDUSPHERE_OWNER. Do not share this generated file.')


def main():
    parser = argparse.ArgumentParser(description='Create Django-compatible Oracle DML for demo login accounts.')
    parser.add_argument('--output', default='02_accounts.generated.sql')
    args=parser.parse_args()
    generate(Path(args.output).resolve())

if __name__=='__main__':
    main()
