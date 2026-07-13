import json
import logging
import os

from tools.add_project import add_project
from tools.add_user import add_user
from tools.get_user_profile import get_user_profile
from tools.set_project_as_default import set_project_as_default

logging.getLogger().setLevel(os.environ.get('LOG_LEVEL', 'INFO').upper())
logger = logging.getLogger(__name__)

TOOLS = [
    {
        'name': 'get_user_profile',
        'description': 'Get user profile and all associated projects by Apple ID or Google ID.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'appleId':  {'type': 'string', 'description': 'Apple ID of the user'},
                'googleId': {'type': 'string', 'description': 'Google ID of the user'},
            },
        },
    },
    {
        'name': 'add_project',
        'description': 'Add a new home repair project for a user.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'userId':           {'type': 'integer'},
                'isDefaultProject': {'type': 'boolean'},
                'projectName':      {'type': 'string'},
                'jobType':          {'type': 'string'},
                'description':      {'type': 'string'},
                'streetAddress':    {'type': 'string'},
                'streetAddress2':   {'type': 'string'},
                'city':             {'type': 'string'},
                'state':            {'type': 'string'},
                'zipCode':          {'type': 'string', 'description': 'Required'},
            },
            'required': ['userId', 'zipCode'],
        },
    },
    {
        'name': 'add_user',
        'description': 'Create a new user account if one does not already exist for the given email.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'email':     {'type': 'string', 'description': 'Required. Also used as the username.'},
                'appleId':   {'type': 'string', 'description': 'Apple ID of the user'},
                'firstName': {'type': 'string'},
                'lastName':  {'type': 'string'},
            },
            'required': ['email', 'appleId', 'firstName', 'lastName'],
        },
    },
    {
        'name': 'set_project_as_default',
        'description': 'Set a specific project as the default for a user, clearing the previous default.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'userId':    {'type': 'integer'},
                'projectId': {'type': 'integer'},
            },
            'required': ['userId', 'projectId'],
        },
    },
]


def handler(event, context):
    method = event.get('method')
    logger.info('Incoming MCP request method=%s', method)

    if method == 'tools/list':
        return {'tools': TOOLS}

    if method == 'tools/call':
        params = event.get('params', {})
        tool_name = params.get('name')
        args = params.get('arguments', {})
        logger.info('tools/call name=%s args=%s', tool_name, args)

        if tool_name == 'get_user_profile':
            result = get_user_profile(
                apple_id=args.get('appleId'),
                google_id=args.get('googleId'),
            )

        elif tool_name == 'add_project':
            result = add_project(
                user_id=args['userId'],
                zip_code=args['zipCode'],
                is_default_project=args.get('isDefaultProject', False),
                project_name=args.get('projectName', ''),
                job_type=args.get('jobType', ''),
                description=args.get('description'),
                street_address=args.get('streetAddress'),
                street_address2=args.get('streetAddress2'),
                city=args.get('city'),
                state=args.get('state'),
            )

        elif tool_name == 'add_user':
            result = add_user(
                email=args['email'],
                apple_id=args['appleId'],
                first_name=args['firstName'],
                last_name=args['lastName'],
            )

        elif tool_name == 'set_project_as_default':
            result = set_project_as_default(
                user_id=args['userId'],
                project_id=args['projectId'],
            )

        else:
            logger.warning('Unknown tool requested: %s', tool_name)
            result = {'message': f'Unknown tool: {tool_name}'}

        logger.info('tools/call name=%s result=%s', tool_name, result)
        return {'content': [{'type': 'text', 'text': json.dumps(result)}]}

    logger.warning('Unknown MCP method: %s', method)
    return {'message': f'Unknown method: {method}'}
