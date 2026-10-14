"""
EduSphere LMS

Assignment Repository Layer

Commit 6

Handles:
- Assignment queries
- Assignment creation
- Submission handling
"""

from database.query import (
    fetch_one,
    fetch_all,
    execute,
)

from database.schema import object_name



# -------------------------------------------------
# Component / Ownership Helpers
# -------------------------------------------------

def get_component(component_id):

    return fetch_one(
        f"""
        SELECT
            ac.COMPONENT_ID,
            ac.COMPONENT_TYPE,
            ac.COMPONENT_NAME,
            ac.MAX_MARKS,
            gs.OFFERING_ID

        FROM {object_name("ASSESSMENT_COMPONENT")} ac

        JOIN {object_name("GRADING_SCHEME")} gs
          ON gs.SCHEME_ID = ac.SCHEME_ID

        WHERE ac.COMPONENT_ID = ?
        """,
        (
            component_id,
        )
    )



def get_component_offering(component_id):

    row = fetch_one(
        f"""
        SELECT
            gs.OFFERING_ID

        FROM {object_name("ASSESSMENT_COMPONENT")} ac

        JOIN {object_name("GRADING_SCHEME")} gs
          ON gs.SCHEME_ID = ac.SCHEME_ID

        WHERE ac.COMPONENT_ID = ?
        """,
        (
            component_id,
        )
    )

    return row["offering_id"] if row else None



# -------------------------------------------------
# Assignment CRUD
# -------------------------------------------------

def create_assignment(
    component_id,
    title,
    description,
    due_date,
    allow_resubmission,
):

    execute(
        f"""
        INSERT INTO {object_name("ASSIGNMENT")}
        (
            COMPONENT_ID,
            ASSIGNMENT_TITLE,
            ASSIGNMENT_DESCRIPTION,
            DUE_DATE,
            ALLOW_RESUBMISSION
        )

        VALUES
        (
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """,
        (
            component_id,
            title,
            description,
            due_date,
            allow_resubmission,
        )
    )



def get_assignments(
    component_id,
):

    return fetch_all(
        f"""
        SELECT

            ASSIGNMENT_ID,
            COMPONENT_ID,
            ASSIGNMENT_TITLE,
            ASSIGNMENT_DESCRIPTION,
            DUE_DATE,
            ALLOW_RESUBMISSION

        FROM {object_name("ASSIGNMENT")}

        WHERE COMPONENT_ID = ?

        ORDER BY ASSIGNMENT_ID

        """,
        (
            component_id,
        )
    )



def get_assignment(
    assignment_id,
):

    return fetch_one(
        f"""
        SELECT

            ASSIGNMENT_ID,
            COMPONENT_ID,
            ASSIGNMENT_TITLE,
            ASSIGNMENT_DESCRIPTION,
            DUE_DATE,
            ALLOW_RESUBMISSION

        FROM {object_name("ASSIGNMENT")}

        WHERE ASSIGNMENT_ID = ?

        """,
        (
            assignment_id,
        )
    )



# -------------------------------------------------
# Submission Handling
# -------------------------------------------------

def get_latest_submission_version(
    assignment_id,
    student_id,
):

    row = fetch_one(
        f"""
        SELECT
            MAX(SUBMISSION_VERSION)
            AS VERSION

        FROM {object_name("ASSIGNMENT_SUBMISSION")}

        WHERE ASSIGNMENT_ID = ?

        AND STUDENT_ID = ?

        """,
        (
            assignment_id,
            student_id,
        )
    )


    if not row or row["version"] is None:
        return 0


    return row["version"]



def create_submission(
    assignment_id,
    student_id,
    file_url,
    version,
):

    execute(
        f"""
        INSERT INTO {object_name("ASSIGNMENT_SUBMISSION")}
        (
            ASSIGNMENT_ID,
            STUDENT_ID,
            SUBMISSION_VERSION,
            FILE_URL
        )

        VALUES
        (
            ?,
            ?,
            ?,
            ?
        )
        """,
        (
            assignment_id,
            student_id,
            version,
            file_url,
        )
    )



def get_student_submissions(
    assignment_id,
    student_id,
):

    return fetch_all(
        f"""
        SELECT

            SUBMISSION_ID,
            ASSIGNMENT_ID,
            STUDENT_ID,
            SUBMISSION_VERSION,
            SUBMITTED_AT,
            FILE_URL,
            SUBMISSION_STATUS,
            FEEDBACK

        FROM {object_name("ASSIGNMENT_SUBMISSION")}

        WHERE ASSIGNMENT_ID = ?

        AND STUDENT_ID = ?

        ORDER BY SUBMISSION_VERSION DESC

        """,
        (
            assignment_id,
            student_id,
        )
    )
    
    
def instructor_owns_offering(
    instructor_id,
    offering_id
):

    row = fetch_one(
        f"""
        SELECT
            OFFERING_INSTRUCTOR_ID

        FROM {object_name("OFFERING_INSTRUCTOR")}

        WHERE OFFERING_ID = ?

        AND INSTRUCTOR_ID = ?

        """,
        (
            offering_id,
            instructor_id,
        )
    )

    return row is not None

def assignment_exists_for_component(component_id):

    row = fetch_one(
        f"""
        SELECT
            ASSIGNMENT_ID
        FROM {object_name("ASSIGNMENT")}
        WHERE COMPONENT_ID = ?
        """,
        (component_id,)
    )

    return row is not None    

def get_assignment_submissions(
    assignment_id,
):
    return fetch_all(
        f"""
        SELECT
            SUBMISSION_ID,
            ASSIGNMENT_ID,
            STUDENT_ID,
            SUBMISSION_VERSION,
            SUBMITTED_AT,
            FILE_URL,
            SUBMISSION_STATUS,
            FEEDBACK
        FROM {object_name("ASSIGNMENT_SUBMISSION")}
        WHERE ASSIGNMENT_ID = ?
        ORDER BY STUDENT_ID, SUBMISSION_VERSION DESC
        """,
        (
            assignment_id,
        )
    )