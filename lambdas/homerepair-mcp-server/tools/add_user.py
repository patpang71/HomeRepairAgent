import logging

from db import get_connection

logger = logging.getLogger(__name__)


def add_user(email: str, apple_id: str, first_name: str, last_name: str) -> dict:
    if not email:
        logger.warning('add_user called without email')
        return {'message': 'email is required'}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT "UserId" FROM userinfo."User" WHERE "Email" = %s',
                (email,),
            )
            if cur.fetchone() is not None:
                logger.error('add_user: email already exists email=%s', email)
                return {'message': f'Email {email} is already existed'}

            cur.execute("""
                INSERT INTO userinfo."User"
                    ("Username", "AppleId", "GoogleId", "AvatarUrl", "Email", "FirstName", "LastName")
                VALUES (%s, %s, '', '', %s, %s, %s)
                RETURNING "UserId"
            """, (email, apple_id, email, first_name, last_name))
            user_id = cur.fetchone()[0]
        conn.commit()
        logger.info('add_user: created userId=%s email=%s', user_id, email)
        return {'message': 'User added successfully', 'userId': user_id}

    except Exception as e:
        conn.rollback()
        logger.exception('add_user failed email=%s', email)
        return {'message': str(e)}
