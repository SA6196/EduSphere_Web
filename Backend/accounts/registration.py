"""Student self-signup: inactive until administrator verifies identity."""
from django.contrib.auth.hashers import make_password
from core.exceptions import ValidationError, BusinessRuleError, NotFoundError
from database.query import fetch_all, execute, fetch_one
from database.schema import object_name
from administration.services import _email, _required, _positive_int, _ensure_unique_identity
from administration.repository import get_program, create_student_account


def public_programs():
    return fetch_all(f"SELECT PROGRAM_ID, PROGRAM_NAME, PROGRAM_LEVEL FROM {object_name('PROGRAM')} ORDER BY PROGRAM_NAME")


def register_student(data):
    if not isinstance(data,dict): raise ValidationError("Invalid signup payload.")
    username=str(_required(data,'username')).strip()
    if len(username) > 50 or len(username) < 4: raise ValidationError("Username must contain 4–50 characters.")
    password=str(_required(data,'password'))
    if len(password)<10 or len(password)>128: raise ValidationError("Password must be 10–128 characters.")
    email=_email(_required(data,'email'))
    name=str(_required(data,'student_name'))
    admission=str(_required(data,'admission_no'))
    if len(admission)>30 or len(name)>120: raise ValidationError("Student details exceed allowed length.")
    program_id=_positive_int(_required(data,'program_id'),'program_id')
    if not get_program(program_id): raise NotFoundError("Program not found.")
    _ensure_unique_identity(username,email,admission)
    record={
        'username':username,'email':email,'student_name':name,'admission_no':admission,
        'program_id':program_id,'phone':str(data.get('phone') or '').strip() or None,
        'batch':str(data.get('batch') or '').strip() or None,
        'account_status':'INACTIVE','student_status':'INACTIVE',
    }
    create_student_account(None,make_password(password),record)
    return {'message':'Registration received. An administrator must verify the student and activate the account before login.'}


def activate_student(student_id, actor_user_id):
    sid=_positive_int(student_id,'student_id')
    record=fetch_one(
        f"SELECT s.USER_ID, u.ACCOUNT_STATUS FROM {object_name('STUDENT')} s "
        f"JOIN {object_name('LMS_USER')} u ON u.USER_ID=s.USER_ID WHERE s.STUDENT_ID=?",
        (sid,),
    )
    if not record: raise NotFoundError('Student not found.')
    if record['account_status']!='INACTIVE': raise BusinessRuleError('Only inactive accounts can be activated.')
    from database.connection import oracle_transaction
    from core.audit import log_activity
    with oracle_transaction():
        execute(f"UPDATE {object_name('STUDENT')} SET STUDENT_STATUS='ACTIVE' WHERE STUDENT_ID=?",(sid,))
        execute(f"UPDATE {object_name('LMS_USER')} SET ACCOUNT_STATUS='ACTIVE' WHERE USER_ID=?",(int(record['user_id']),))
        log_activity(actor_user_id,'STUDENT_ACCOUNT_ACTIVATED',f'Student {sid} approved for access')
    return {'message':'Student account activated after identity verification.'}
