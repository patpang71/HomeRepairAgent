import json
import logging
import os

from tools.add_project import add_project
from tools.add_user import add_user
from tools.get_user_profile import get_user_profile
from tools.save_search_result import save_search_result
from tools.set_preference import set_preference
from tools.set_project_as_default import set_project_as_default
from tools.update_resolution import update_resolution

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
                'email':     {'type': 'string', 'description': 'Required. Unique identifier for the user.'},
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
    {
        'name': 'set_preference',
        'description': 'Set a user\'s search result preference — CONCISE (top 2 results) or DETAIL (full results).',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'userId':     {'type': 'integer'},
                'preference': {'type': 'string', 'enum': ['CONCISE', 'DETAIL']},
            },
            'required': ['userId', 'preference'],
        },
    },
    {
        'name': 'save_search_result',
        'description': 'Save a Tavily search question and result against a project.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'projectId':      {'type': 'integer'},
                'searchQuestion': {'type': 'string'},
                'searchResult':   {'type': 'string'},
            },
            'required': ['projectId', 'searchQuestion', 'searchResult'],
        },
    },
    {
        'name': 'update_resolution',
        'description': 'Update a project\'s resolution summary and resolved status.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'projectId':         {'type': 'integer'},
                'resolutionDetail':  {'type': 'string'},
                'resolved':          {'type': 'boolean'},
            },
            'required': ['projectId', 'resolutionDetail', 'resolved'],
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

        elif tool_name == 'set_preference':
            result = set_preference(
                user_id=args['userId'],
                preference=args['preference'],
            )

        elif tool_name == 'save_search_result':
            result = save_search_result(
                project_id=args['projectId'],
                search_question=args['searchQuestion'],
                search_result=args['searchResult'],
            )

        elif tool_name == 'update_resolution':
            result = update_resolution(
                project_id=args['projectId'],
                resolution_detail=args['resolutionDetail'],
                resolved=args['resolved'],
            )

        else:
            logger.warning('Unknown tool requested: %s', tool_name)
            result = {'message': f'Unknown tool: {tool_name}'}

        logger.info('tools/call name=%s result=%s', tool_name, result)
        return {'content': [{'type': 'text', 'text': json.dumps(result)}]}

    logger.warning('Unknown MCP method: %s', method)
    return {'message': f'Unknown method: {method}'}
