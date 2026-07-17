import logging

from db import get_connection

logger = logging.getLogger(__name__)


def update_resolution(project_id: int, resolution_detail: str, resolved: bool) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE userinfo."Project"
                SET "ResolutionDetail" = %s, "Resolved" = %s
                WHERE "ProjectId" = %s
            """, (resolution_detail, resolved, project_id))

            if cur.rowcount == 0:
                raise ValueError(f'Project {project_id} not found')

        conn.commit()
        logger.info('update_resolution: projectId=%s resolved=%s', project_id, resolved)
        return {'message': 'Resolution updated successfully', 'resolved': resolved}

    except Exception as e:
        conn.rollback()
        logger.exception('update_resolution failed projectId=%s', project_id)
        return {'message': str(e)}
