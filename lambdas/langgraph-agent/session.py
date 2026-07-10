import json
import logging
import os
import time
import boto3

logger = logging.getLogger(__name__)

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
        logger.debug('No session state found for sessionId=%s', session_id)
        return None
    logger.debug('Loaded session state for sessionId=%s', session_id)
    return json.loads(item['state'])


def save_session(session_id: str, state: dict):
    serialized = json.dumps(state, default=str)
    _get_table().put_item(Item={
        'sessionId': session_id,
        'state': serialized,
        'ttl': int(time.time()) + _TTL_SECONDS,
    })
    logger.debug('Saved session state for sessionId=%s (%d bytes)', session_id, len(serialized))
