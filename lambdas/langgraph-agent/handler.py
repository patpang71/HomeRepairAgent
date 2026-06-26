import json
import uuid

from graph import get_graph
from session import load_session, save_session


def handler(event, context):
    claims = event['requestContext']['authorizer']['jwt']['claims']
    apple_id = claims['sub']

    body = json.loads(event.get('body') or '{}')
    user_message = body.get('message', '')
    session_id = body.get('sessionId') or str(uuid.uuid4())
    photo_key = body.get('imageKey')

    state = load_session(session_id) or {
        'apple_id': apple_id,
        'session_id': session_id,
        'user_profile': None,
        'current_agent': 'orchestrator',
        'messages': [],
        'project_update_stage': None,
        'pending_project': None,
        'photo_key': None,
        'user_message': '',
        'response': '',
    }

    state['user_message'] = user_message
    if photo_key:
        state['photo_key'] = photo_key

    result = get_graph().invoke(state)

    # Persist everything except the per-invocation input fields
    save_state = {k: v for k, v in result.items() if k != 'user_message'}
    save_session(session_id, save_state)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'response': result['response'],
            'sessionId': session_id,
        }),
    }
