"""
EduSphere LMS

Course Material Repository Layer

Commit 7
"""

from database.query import (
    fetch_all,
    fetch_one,
    execute,
)

from database.schema import object_name



def create_material(
    offering_id,
    uploaded_by_user_id,
    title,
    material_type,
    material_url,
):

    execute(
        f"""
        INSERT INTO {object_name("COURSE_MATERIAL")}
        (
            OFFERING_ID,
            UPLOADED_BY_USER_ID,
            MATERIAL_TITLE,
            MATERIAL_TYPE,
            MATERIAL_URL
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
            offering_id,
            uploaded_by_user_id,
            title,
            material_type,
            material_url,
        )
    )


def get_materials(offering_id):

    return fetch_all(
        f"""
        SELECT
            MATERIAL_ID,
            OFFERING_ID,
            UPLOADED_BY_USER_ID,
            MATERIAL_TITLE,
            MATERIAL_TYPE,
            MATERIAL_URL,
            UPLOADED_AT
        FROM {object_name("COURSE_MATERIAL")}
        WHERE OFFERING_ID=?
        ORDER BY UPLOADED_AT DESC
        """,
        (
            offering_id,
        )
    )


def get_material(material_id):

    return fetch_one(
        f"""
        SELECT
            MATERIAL_ID,
            OFFERING_ID,
            UPLOADED_BY_USER_ID,
            MATERIAL_TITLE,
            MATERIAL_TYPE,
            MATERIAL_URL,
            UPLOADED_AT
        FROM {object_name("COURSE_MATERIAL")}
        WHERE MATERIAL_ID=?
        """,
        (
            material_id,
        )
    )