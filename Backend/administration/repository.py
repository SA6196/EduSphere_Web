"""Oracle repository for administrator-managed LMS master data.

These operations deliberately use one explicit Oracle transaction whenever a
business action spans more than one normalized table.  That keeps USER +
STUDENT/INSTRUCTOR creation, offering + instructor assignment, and grading
scheme edits atomic.
"""

from database.connection import oracle_connection, row_to_dict
from database.query import fetch_all, fetch_one
from database.schema import object_name


def list_departments():
    return fetch_all(
        f"""
        SELECT Department_ID, Department_Name
        FROM {object_name('DEPARTMENT')}
        ORDER BY Department_Name
        """
    )


def list_programs():
    return fetch_all(
        f"""
        SELECT
            p.Program_ID,
            p.Program_Name,
            p.Program_Level,
            p.Department_ID,
            d.Department_Name
        FROM {object_name('PROGRAM')} p
        JOIN {object_name('DEPARTMENT')} d
          ON d.Department_ID=p.Department_ID
        ORDER BY d.Department_Name, p.Program_Name, p.Program_Level
        """
    )


def list_students():
    return fetch_all(
        f"""
        SELECT
            s.Student_ID,
            s.Student_Name,
            s.Admission_No,
            s.Batch,
            s.Student_Status,
            p.Program_ID,
            p.Program_Name,
            p.Program_Level,
            d.Department_Name,
            u.Username,
            u.Email,
            u.Phone,
            u.Account_Status
        FROM {object_name('STUDENT')} s
        JOIN {object_name('LMS_USER')} u ON u.User_ID=s.User_ID
        JOIN {object_name('PROGRAM')} p ON p.Program_ID=s.Program_ID
        JOIN {object_name('DEPARTMENT')} d ON d.Department_ID=p.Department_ID
        ORDER BY s.Student_Name, s.Student_ID
        """
    )


def list_instructors():
    return fetch_all(
        f"""
        SELECT
            i.Instructor_ID,
            i.Instructor_Name,
            i.Designation,
            i.Department_ID,
            d.Department_Name,
            u.Username,
            u.Email,
            u.Phone,
            u.Account_Status
        FROM {object_name('INSTRUCTOR')} i
        JOIN {object_name('LMS_USER')} u ON u.User_ID=i.User_ID
        JOIN {object_name('DEPARTMENT')} d ON d.Department_ID=i.Department_ID
        ORDER BY i.Instructor_Name, i.Instructor_ID
        """
    )


def get_program(program_id):
    return fetch_one(
        f"""
        SELECT Program_ID, Program_Name, Program_Level, Department_ID
        FROM {object_name('PROGRAM')}
        WHERE Program_ID=?
        """,
        (program_id,),
    )


def get_department(department_id):
    return fetch_one(
        f"""
        SELECT Department_ID, Department_Name
        FROM {object_name('DEPARTMENT')}
        WHERE Department_ID=?
        """,
        (department_id,),
    )


def get_course(course_id):
    return fetch_one(
        f"""
        SELECT Course_ID, Course_Code, Course_Name
        FROM {object_name('COURSE')}
        WHERE Course_ID=?
        """,
        (course_id,),
    )


def get_semester(semester_id):
    return fetch_one(
        f"""
        SELECT Semester_ID, Semester_Name, Academic_Year,
               Semester_Start_Date, Semester_End_Date
        FROM {object_name('SEMESTER')}
        WHERE Semester_ID=?
        """,
        (semester_id,),
    )


def get_offering_admin(offering_id):
    return fetch_one(
        f"""
        SELECT
            co.Offering_ID,
            co.Course_ID,
            c.Course_Code,
            c.Course_Name,
            co.Semester_ID,
            s.Semester_Name,
            s.Academic_Year,
            co.Section_Code,
            co.Slot_Day,
            co.Start_Time,
            co.End_Time,
            co.Capacity,
            co.Offering_Status
        FROM {object_name('COURSE_OFFERING')} co
        JOIN {object_name('COURSE')} c ON c.Course_ID=co.Course_ID
        JOIN {object_name('SEMESTER')} s ON s.Semester_ID=co.Semester_ID
        WHERE co.Offering_ID=?
        """,
        (offering_id,),
    )


def get_offering_instructors(offering_id):
    return fetch_all(
        f"""
        SELECT
            i.Instructor_ID,
            i.Instructor_Name,
            i.Designation,
            d.Department_Name,
            u.Account_Status
        FROM {object_name('OFFERING_INSTRUCTOR')} oi
        JOIN {object_name('INSTRUCTOR')} i ON i.Instructor_ID=oi.Instructor_ID
        JOIN {object_name('LMS_USER')} u ON u.User_ID=i.User_ID
        JOIN {object_name('DEPARTMENT')} d ON d.Department_ID=i.Department_ID
        WHERE oi.Offering_ID=?
        ORDER BY i.Instructor_Name
        """,
        (offering_id,),
    )


def get_active_instructors_by_ids(instructor_ids):
    if not instructor_ids:
        return []
    markers = ",".join("?" for _ in instructor_ids)
    return fetch_all(
        f"""
        SELECT i.Instructor_ID, i.Instructor_Name, u.Account_Status
        FROM {object_name('INSTRUCTOR')} i
        JOIN {object_name('LMS_USER')} u ON u.User_ID=i.User_ID
        WHERE i.Instructor_ID IN ({markers})
          AND u.Account_Status='ACTIVE'
        """,
        tuple(instructor_ids),
    )


def identity_conflicts(username, email, admission_no=None):
    result = {
        "username": fetch_one(
            f"SELECT User_ID FROM {object_name('LMS_USER')} WHERE UPPER(Username)=UPPER(?)",
            (username,),
        ) is not None,
        "email": fetch_one(
            f"SELECT User_ID FROM {object_name('LMS_USER')} WHERE UPPER(Email)=UPPER(?)",
            (email,),
        ) is not None,
        "admission_no": False,
    }
    if admission_no:
        result["admission_no"] = fetch_one(
            f"SELECT Student_ID FROM {object_name('STUDENT')} WHERE UPPER(Admission_No)=UPPER(?)",
            (admission_no,),
        ) is not None
    return result


def _call_audit(cursor, actor_user_id, activity_type, description):
    cursor.execute(
        f"{{CALL {object_name('PR_LOG_ACTIVITY')}(?,?,?,?)}}",
        (int(actor_user_id), activity_type, description, None),
    )


def create_student_account(actor_user_id, password_hash, data):
    with oracle_connection(commit=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            INSERT INTO {object_name('LMS_USER')}
                (Username, Password_Hash, Email, Phone, Role, Account_Status)
            VALUES (?, ?, ?, ?, 'STUDENT', ?)
            """,
            (
                data["username"], password_hash, data["email"], data.get("phone"),
                data.get("account_status", "ACTIVE"),
            ),
        )
        cursor.execute(
            f"SELECT User_ID FROM {object_name('LMS_USER')} WHERE Username=?",
            (data["username"],),
        )
        user_id = int(cursor.fetchone()[0])

        cursor.execute(
            f"""
            INSERT INTO {object_name('STUDENT')}
                (User_ID, Student_Name, Admission_No, Batch, Program_ID, Student_Status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, data["student_name"], data["admission_no"], data.get("batch"),
                int(data["program_id"]), data.get("student_status", "ACTIVE"),
            ),
        )
        _call_audit(
            cursor,
            actor_user_id if actor_user_id is not None else user_id,
            "STUDENT_ACCOUNT_CREATED" if actor_user_id is not None else "STUDENT_SIGNUP_PENDING",
            f"Student account created: {data['username']} / {data['admission_no']}",
        )

    return fetch_one(
        f"""
        SELECT s.Student_ID, s.Student_Name, s.Admission_No, s.Batch,
               s.Student_Status, p.Program_Name, u.Username, u.Email,
               u.Phone, u.Account_Status
        FROM {object_name('STUDENT')} s
        JOIN {object_name('LMS_USER')} u ON u.User_ID=s.User_ID
        JOIN {object_name('PROGRAM')} p ON p.Program_ID=s.Program_ID
        WHERE u.User_ID=?
        """,
        (user_id,),
    )


def create_instructor_account(actor_user_id, password_hash, data):
    with oracle_connection(commit=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            INSERT INTO {object_name('LMS_USER')}
                (Username, Password_Hash, Email, Phone, Role, Account_Status)
            VALUES (?, ?, ?, ?, 'INSTRUCTOR', ?)
            """,
            (
                data["username"], password_hash, data["email"], data.get("phone"),
                data.get("account_status", "ACTIVE"),
            ),
        )
        cursor.execute(
            f"SELECT User_ID FROM {object_name('LMS_USER')} WHERE Username=?",
            (data["username"],),
        )
        user_id = int(cursor.fetchone()[0])

        cursor.execute(
            f"""
            INSERT INTO {object_name('INSTRUCTOR')}
                (User_ID, Instructor_Name, Designation, Department_ID)
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id, data["instructor_name"], data.get("designation"),
                int(data["department_id"]),
            ),
        )
        _call_audit(
            cursor,
            actor_user_id,
            "INSTRUCTOR_ACCOUNT_CREATED",
            f"Instructor account created: {data['username']}",
        )

    return fetch_one(
        f"""
        SELECT i.Instructor_ID, i.Instructor_Name, i.Designation,
               d.Department_Name, u.Username, u.Email, u.Phone, u.Account_Status
        FROM {object_name('INSTRUCTOR')} i
        JOIN {object_name('LMS_USER')} u ON u.User_ID=i.User_ID
        JOIN {object_name('DEPARTMENT')} d ON d.Department_ID=i.Department_ID
        WHERE u.User_ID=?
        """,
        (user_id,),
    )


def create_offering(actor_user_id, data, instructor_ids):
    with oracle_connection(commit=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            INSERT INTO {object_name('COURSE_OFFERING')}
                (Course_ID, Semester_ID, Section_Code, Slot_Day,
                 Start_Time, End_Time, Capacity, Offering_Status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(data["course_id"]), int(data["semester_id"]), data["section_code"],
                data.get("slot_day"), data.get("start_time"), data.get("end_time"),
                int(data["capacity"]), data["offering_status"],
            ),
        )
        # The combination is unique for non-null timetable fields. Ordering by
        # identity also makes this deterministic when optional slot fields are null.
        cursor.execute(
            f"""
            SELECT Offering_ID
            FROM {object_name('COURSE_OFFERING')}
            WHERE Course_ID=? AND Semester_ID=? AND Section_Code=?
            ORDER BY Offering_ID DESC
            FETCH FIRST 1 ROW ONLY
            """,
            (int(data["course_id"]), int(data["semester_id"]), data["section_code"]),
        )
        offering_id = int(cursor.fetchone()[0])

        for instructor_id in instructor_ids:
            cursor.execute(
                f"""
                INSERT INTO {object_name('OFFERING_INSTRUCTOR')}
                    (Offering_ID, Instructor_ID)
                VALUES (?, ?)
                """,
                (offering_id, int(instructor_id)),
            )

        _call_audit(
            cursor,
            actor_user_id,
            "OFFERING_CREATED",
            f"Offering {offering_id} created with {len(instructor_ids)} instructor assignment(s)",
        )

    return get_offering_admin(offering_id)


def replace_offering_instructors(actor_user_id, offering_id, instructor_ids):
    with oracle_connection(commit=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"DELETE FROM {object_name('OFFERING_INSTRUCTOR')} WHERE Offering_ID=?",
            (offering_id,),
        )
        for instructor_id in instructor_ids:
            cursor.execute(
                f"""
                INSERT INTO {object_name('OFFERING_INSTRUCTOR')}
                    (Offering_ID, Instructor_ID)
                VALUES (?, ?)
                """,
                (offering_id, int(instructor_id)),
            )
        _call_audit(
            cursor,
            actor_user_id,
            "OFFERING_INSTRUCTORS_UPDATED",
            f"Offering {offering_id} instructor assignments replaced; count={len(instructor_ids)}",
        )
    return get_offering_instructors(offering_id)


def grading_scheme_admin(offering_id):
    scheme = fetch_one(
        f"""
        SELECT Scheme_ID, Offering_ID, Scheme_Name
        FROM {object_name('GRADING_SCHEME')}
        WHERE Offering_ID=?
        """,
        (offering_id,),
    )
    components = []
    if scheme:
        components = fetch_all(
            f"""
            SELECT
                ac.Component_ID,
                ac.Component_Name,
                ac.Component_Type,
                ac.Weight_Percentage,
                ac.Max_Marks,
                CASE
                    WHEN EXISTS (SELECT 1 FROM {object_name('ASSIGNMENT')} a WHERE a.Component_ID=ac.Component_ID) THEN 'Y'
                    WHEN EXISTS (SELECT 1 FROM {object_name('QUIZ')} q WHERE q.Component_ID=ac.Component_ID) THEN 'Y'
                    WHEN EXISTS (SELECT 1 FROM {object_name('EXAM')} e WHERE e.Component_ID=ac.Component_ID) THEN 'Y'
                    ELSE 'N'
                END AS Configured
            FROM {object_name('ASSESSMENT_COMPONENT')} ac
            WHERE ac.Scheme_ID=?
            ORDER BY ac.Component_ID
            """,
            (scheme["scheme_id"],),
        )
    return {"scheme": scheme, "components": components}


def published_grade_count(offering_id):
    row = fetch_one(
        f"""
        SELECT COUNT(*) AS CNT
        FROM {object_name('COURSE_GRADE')} cg
        JOIN {object_name('ENROLLMENT')} e ON e.Enrollment_ID=cg.Enrollment_ID
        WHERE e.Offering_ID=?
        """,
        (offering_id,),
    )
    return int(row["cnt"]) if row else 0


def save_grading_scheme(actor_user_id, offering_id, scheme_name, components):
    """Create/update one offering grading scheme atomically.

    Existing components are first set to zero weight inside the transaction.
    Oracle readers outside this transaction keep seeing the old committed
    version, while the component-weight trigger never observes a total > 100
    during the replacement.  All existing components must be supplied by the
    service layer, so nothing is silently deleted.
    """
    with oracle_connection(commit=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT Scheme_ID FROM {object_name('GRADING_SCHEME')} WHERE Offering_ID=?",
            (offering_id,),
        )
        row = cursor.fetchone()
        if row:
            scheme_id = int(row[0])
            cursor.execute(
                f"UPDATE {object_name('GRADING_SCHEME')} SET Scheme_Name=? WHERE Scheme_ID=?",
                (scheme_name, scheme_id),
            )
            cursor.execute(
                f"UPDATE {object_name('ASSESSMENT_COMPONENT')} SET Weight_Percentage=0 WHERE Scheme_ID=?",
                (scheme_id,),
            )
        else:
            cursor.execute(
                f"""
                INSERT INTO {object_name('GRADING_SCHEME')} (Offering_ID, Scheme_Name)
                VALUES (?, ?)
                """,
                (offering_id, scheme_name),
            )
            cursor.execute(
                f"SELECT Scheme_ID FROM {object_name('GRADING_SCHEME')} WHERE Offering_ID=?",
                (offering_id,),
            )
            scheme_id = int(cursor.fetchone()[0])

        for component in components:
            component_id = component.get("component_id")
            if component_id:
                cursor.execute(
                    f"""
                    UPDATE {object_name('ASSESSMENT_COMPONENT')}
                    SET Component_Name=?, Component_Type=?, Weight_Percentage=?, Max_Marks=?
                    WHERE Component_ID=? AND Scheme_ID=?
                    """,
                    (
                        component["component_name"], component["component_type"],
                        component["weight_percentage"], component["max_marks"],
                        int(component_id), scheme_id,
                    ),
                )
            else:
                cursor.execute(
                    f"""
                    INSERT INTO {object_name('ASSESSMENT_COMPONENT')}
                        (Scheme_ID, Component_Name, Component_Type, Weight_Percentage, Max_Marks)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        scheme_id, component["component_name"], component["component_type"],
                        component["weight_percentage"], component["max_marks"],
                    ),
                )

        _call_audit(
            cursor,
            actor_user_id,
            "GRADING_SCHEME_UPDATED",
            f"Grading scheme {scheme_id} updated for offering {offering_id}; components={len(components)}",
        )

    return grading_scheme_admin(offering_id)
