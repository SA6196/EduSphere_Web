"""
EduSphere LMS

Standard API Responses

Commit 5.6
"""


from rest_framework.response import Response

from core.pagination import paginate



def success_response(
    data=None,
    message=None,
    status_code=200
):

    return Response(
        {
            "success": True,
            "message": message,
            "data": data,
        },
        status=status_code,
    )



def error_response(
    message,
    error_code=None,
    status_code=400
):

    return Response(
        {
            "success": False,
            "message": message,
            "error_code": error_code,
        },
        status=status_code,
    )



def paginated_response(
    rows,
    page=1,
    page_size=10,
    message=None
):

    return success_response(
        data=paginate(
            rows,
            page,
            page_size,
        ),
        message=message,
    )