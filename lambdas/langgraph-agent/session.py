import json
import os
import time
import boto3

TABLE_NAME = os.environ['SESSION_TABLE_NAME']
_TTL_SECONDS = 86400  # 24 hours

_table = None


def _get_table():
    global _table
    if _table is None:
        _table = boto3.resource('dynamodb').Table(TABLE_NAME)
    return _table


def load_session(session_id: str) -> dict | None:
    response = _get_table().get_item(Key={'sessionId': session_id})
    item = response.get('Item')
    if not item:
        return None
    return json.loads(item['state'])


def save_session(session_id: str, state: dict):
    _get_table().put_item(Item={
        'sessionId': session_id,
        'state': json.dumps(state, default=str),
        'ttl': int(time.time()) + _TTL_SECONDS,
    })
