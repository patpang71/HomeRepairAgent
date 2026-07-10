import logging

from db import get_connection

logger = logging.getLogger(__name__)


def add_project(
    user_id: int,
    zip_code: str,
    is_default_project: bool = False,
    project_name: str = '',
    job_type: str = '',
    description: str = None,
    street_address: str = None,
    street_address2: str = None,
    city: str = None,
    state: str = None,
) -> dict:
    if not zip_code:
        logger.warning('add_project called without zipCode userId=%s', user_id)
        return {'message': 'zipCode is required'}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO userinfo."Project"
                    ("UserId", "IsDefaultProject", "IsActive", "ProjectName", "JobType",
                     "Description", "StreetAddress", "StreetAddress2", "City", "State", "ZipCode")
                VALUES (%s, %s, TRUE, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING "ProjectId"
            """, (
                user_id, is_default_project, project_name, job_type,
                description, street_address, street_address2, city, state, zip_code,
            ))
            project_id = cur.fetchone()[0]
        conn.commit()
        logger.info('add_project: created projectId=%s for userId=%s', project_id, user_id)
        return {'message': 'Project added successfully', 'projectId': project_id}

    except Exception as e:
        conn.rollback()
        logger.exception('add_project failed userId=%s', user_id)
        return {'message': str(e)}
