"""
EduSphere LMS

Pagination Utilities

Commit 5.2
"""

import math


DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100



def paginate(
    rows,
    page=1,
    page_size=DEFAULT_PAGE_SIZE
):

    try:
        page = int(page)
    except:
        page = 1


    try:
        page_size = int(page_size)
    except:
        page_size = DEFAULT_PAGE_SIZE


    if page < 1:
        page = 1


    if page_size < 1:
        page_size = DEFAULT_PAGE_SIZE


    if page_size > MAX_PAGE_SIZE:
        page_size = MAX_PAGE_SIZE


    total_records = len(rows)

    total_pages = (
        math.ceil(
            total_records / page_size
        )
        if total_records
        else 1
    )


    start = (
        page - 1
    ) * page_size


    end = start + page_size


    return {
        "results": rows[start:end],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_records": total_records,
            "total_pages": total_pages,
        },
    }
