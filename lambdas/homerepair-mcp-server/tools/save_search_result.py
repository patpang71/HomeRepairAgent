import logging

from db import get_connection

logger = logging.getLogger(__name__)


def save_search_result(project_id: int, search_question: str, search_result: str) -> dict:
    if not project_id:
        logger.warning('save_search_result called without projectId')
        return {'message': 'projectId is required'}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO userinfo."SearchResult"
                    ("ProjectId", "SearchQuestion", "SearchResult")
                VALUES (%s, %s, %s)
                RETURNING "SearchResultId"
            """, (project_id, search_question, search_result))
            search_result_id = cur.fetchone()[0]
        conn.commit()
        logger.info('save_search_result: created searchResultId=%s projectId=%s', search_result_id, project_id)
        return {'message': 'Search result saved successfully', 'searchResultId': search_result_id}

    except Exception as e:
        conn.rollback()
        logger.exception('save_search_result failed projectId=%s', project_id)
        return {'message': str(e)}
