import json
import logging
import os

import boto3
import psycopg2

logger = logging.getLogger(__name__)

_connection = None
_secret = None


def _get_secret() -> dict:
    global _secret
    if _secret is None:
        client = boto3.client('secretsmanager')
        response = client.get_secret_value(SecretId=os.environ['DB_SECRET_ARN'])
        _secret = json.loads(response['SecretString'])
    return _secret


def _get_connection():
    global _connection
    try:
        if _connection is not None and not _connection.closed:
            with _connection.cursor() as cur:
                cur.execute('SELECT 1')
            return _connection
    except Exception:
        logger.info('DB connection stale or unavailable, reconnecting')

    secret = _get_secret()
    logger.info('Opening DB connection to %s/%s', secret['host'], secret['dbname'])
    _connection = psycopg2.connect(
        host=secret['host'],
        port=int(secret.get('port', 5432)),
        database=secret['dbname'],
        user=secret['username'],
        password=secret['password'],
        sslmode='require',
        connect_timeout=10,
    )
    return _connection


def save_conversation(session_id: str, user_id: int, messages: list):
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(
            'SELECT "ConversationId" FROM userinfo."Conversation" WHERE "SessionId" = %s',
            (session_id,),
        )
        row = cur.fetchone()

        if row is None:
            cur.execute(
                'INSERT INTO userinfo."Conversation" ("UserId", "SessionId") VALUES (%s, %s) RETURNING "ConversationId"',
                (user_id, session_id),
            )
            conversation_id = cur.fetchone()[0]
            saved_count = 0
            logger.info('Created conversation=%s sessionId=%s userId=%s', conversation_id, session_id, user_id)
        else:
            conversation_id = row[0]
            cur.execute(
                'SELECT COUNT(*) FROM userinfo."Message" WHERE "ConversationId" = %s',
                (conversation_id,),
            )
            saved_count = cur.fetchone()[0]

        new_messages = messages[saved_count:]
        for msg in new_messages:
            cur.execute(
                'INSERT INTO userinfo."Message" ("ConversationId", "Role", "Content") VALUES (%s, %s, %s)',
                (conversation_id, msg['role'], msg['content']),
            )

    conn.commit()
    logger.info('Saved %d new message(s) to conversation=%s', len(new_messages), conversation_id)
