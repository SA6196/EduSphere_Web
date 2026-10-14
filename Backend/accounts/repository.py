from database.connection import fetch_one, execute, call_procedure_no_out
from database.schema import object_name


USER_COLUMNS = """
    User_ID,
    Username,
    Password_Hash,
    Email,
    Phone,
    Role,
    Account_Status,
    Last_Login
"""


def get_user_by_username(username: str):
    table = object_name("LMS_USER")
    return fetch_one(
        f"""
        SELECT {USER_COLUMNS}
        FROM {table}
        WHERE Username = ?
        """,
        (username,),
    )


def get_user_by_id(user_id: int):
    table = object_name("LMS_USER")
    return fetch_one(
        f"""
        SELECT {USER_COLUMNS}
        FROM {table}
        WHERE User_ID = ?
        """,
        (user_id,),
    )


def update_last_login(user_id: int):
    table = object_name("LMS_USER")
    execute(
        f"""
        UPDATE {table}
        SET Last_Login = SYSTIMESTAMP
        WHERE User_ID = ?
        """,
        (user_id,),
    )


def set_password_hash(user_id: int, password_hash: str):
    table = object_name("LMS_USER")
    execute(
        f"""
        UPDATE {table}
        SET Password_Hash = ?
        WHERE User_ID = ?
        """,
        (password_hash, user_id),
    )


def log_activity(user_id: int, activity_type: str, description=None, ip_address=None):
    proc = object_name("PR_LOG_ACTIVITY")
    call_procedure_no_out(
        proc,
        (user_id, activity_type, description, ip_address),
    )



def get_student_id_by_user_id(user_id: int):
    student_t = object_name("STUDENT")
    row = fetch_one(
        f"""
        SELECT Student_ID
        FROM {student_t}
        WHERE User_ID = ?
        """,
        (user_id,),
    )
    return row["student_id"] if row else None


def get_instructor_id_by_user_id(user_id: int):
    instructor_t = object_name("INSTRUCTOR")
    row = fetch_one(
        f"""
        SELECT Instructor_ID
        FROM {instructor_t}
        WHERE User_ID = ?
        """,
        (user_id,),
    )
    return row["instructor_id"] if row else None
