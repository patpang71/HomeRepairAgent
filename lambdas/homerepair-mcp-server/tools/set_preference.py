import logging

from db import get_connection

logger = logging.getLogger(__name__)

VALID_PREFERENCES = ('CONCISE', 'DETAIL')


def set_preference(user_id: int, preference: str) -> dict:
    if preference not in VALID_PREFERENCES:
        logger.warning('set_preference: invalid preference=%r userId=%s', preference, user_id)
        return {'message': f'preference must be one of {VALID_PREFERENCES}'}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE userinfo."User"
                SET "Preference" = %s
                WHERE "UserId" = %s
            """, (preference, user_id))

            if cur.rowcount == 0:
                raise ValueError(f'User {user_id} not found')

        conn.commit()
        logger.info('set_preference: userId=%s preference=%s', user_id, preference)
        return {'message': 'Preference updated successfully', 'preference': preference}

    except Exception as e:
        conn.rollback()
        logger.exception('set_preference failed userId=%s preference=%s', user_id, preference)
        return {'message': str(e)}
