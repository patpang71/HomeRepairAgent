import json
import logging
import os

import boto3
import psycopg2

logger = logging.getLogger(__name__)

_connection = None
_secret = None
_logging_cursor_class = None


def _get_logging_cursor_class():
    # Built lazily (not at import time) since psycopg2.extensions.cursor is a
    # C extension type only meaningful once the real driver is loaded.
    global _logging_cursor_class
    if _logging_cursor_class is None:
        class _LoggingCursor(psycopg2.extensions.cursor):
            def execute(self, query, vars=None):
                try:
                    logger.info('SQL: %s', self.mogrify(query, vars).decode('utf-8', errors='replace'))
                except Exception:
                    logger.info('SQL: %s vars=%s', query, vars)
                return super().execute(query, vars)

        _logging_cursor_class = _LoggingCursor
    return _logging_cursor_class


def _get_secret() -> dict:
    global _secret
    if _secret is None:
        client = boto3.client('secretsmanager')
        response = client.get_secret_value(SecretId=os.environ['DB_SECRET_ARN'])
        _secret = json.loads(response['SecretString'])
    return _secret


def get_connection():
    """Return a live psycopg2 connection, reusing across warm Lambda invocations."""
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
        cursor_factory=_get_logging_cursor_class(),
    )
    return _connection
