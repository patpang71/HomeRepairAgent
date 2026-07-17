import json
import logging
import os
import uuid

from conversation import save_conversation
from graph import get_graph
from session import load_session, save_session

logging.getLogger().setLevel(os.environ.get('LOG_LEVEL', 'INFO').upper())
logger = logging.getLogger(__name__)


def handler(event, context):
    claims = event['requestContext']['authorizer']['jwt']['claims']
    apple_id = claims['sub']

    body = json.loads(event.get('body') or '{}')
    user_message = body.get('message', '')
    session_id = body.get('sessionId') or str(uuid.uuid4())
    photo_key = body.get('imageKey')

    logger.info(
        'Incoming request sessionId=%s appleId=%s messageLen=%d hasPhoto=%s',
        session_id, apple_id, len(user_message), bool(photo_key),
    )

    existing_state = load_session(session_id)
    logger.info('Session %s: %s', session_id, 'resumed' if existing_state else 'new')

    state = existing_state or {
        'apple_id': apple_id,
        'session_id': session_id,
        'user_profile': None,
        'current_agent': 'initial_verification',
        'messages': [],
        'orchestrator_stage': None,
        'project_update_stage': None,
        'pending_project': None,
        'pending_search_result': None,
        'photo_key': None,
        'user_message': '',
        'response': '',
    }

    state['user_message'] = user_message
    if photo_key:
        state['photo_key'] = photo_key

    logger.info('Invoking graph sessionId=%s currentAgent=%s', session_id, state['current_agent'])
    result = get_graph().invoke(state)
    logger.info('Graph completed sessionId=%s currentAgent=%s', session_id, result.get('current_agent'))

    user_id = (result.get('user_profile') or {}).get('userId')
    if user_id and result.get('messages'):
        try:
            save_conversation(session_id, user_id, result['messages'])
        except Exception:
            logger.exception('Conversation save error sessionId=%s userId=%s', session_id, user_id)

    # Persist everything except the per-invocation input fields
    save_state = {k: v for k, v in result.items() if k != 'user_message'}
    save_session(session_id, save_state)
    logger.info('Responding sessionId=%s responseLen=%d', session_id, len(result['response']))

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'response': result['response'],
            'sessionId': session_id,
        }),
    }
