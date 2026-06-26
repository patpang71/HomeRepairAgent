import json
import os

import boto3
import psycopg2

_connection = None
_secret = None


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
        pass

    secret = _get_secret()
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
