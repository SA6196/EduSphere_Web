"""
EduSphere LMS
Startup Validation

Commit 3.6

Checks:
- Oracle connectivity
- Schema accessibility
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "edusphere.settings"
)

import django
django.setup()

from django.conf import settings
from database.connection import oracle_connection


def check_environment():

    print("EduSphere startup validation")
    print("----------------------------")

    print(
        "Schema:",
        settings.ORACLE_SCHEMA
    )


def check_database():

    try:

        with oracle_connection() as conn:

            cursor = conn.cursor()

            cursor.execute(
                "SELECT 1 FROM DUAL"
            )

            result = cursor.fetchone()[0]


        if result == 1:

            print(
                "Oracle connection: OK"
            )

        else:

            raise RuntimeError(
                "Oracle ping failed"
            )


    except Exception as e:

        print(
            "Oracle connection: FAILED"
        )

        raise e



if __name__ == "__main__":

    

    check_environment()

    check_database()

    print(
        "Startup validation completed"
    )
