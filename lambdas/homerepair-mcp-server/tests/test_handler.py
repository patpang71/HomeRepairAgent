import json
import pytest
from unittest.mock import patch, MagicMock
import handler


class TestToolsList:

    def test_returns_all_three_tools(self):
        result = handler.handler({'method': 'tools/list'}, None)
        tool_names = [t['name'] for t in result['tools']]
        assert 'get_user_profile' in tool_names
        assert 'add_project' in tool_names
        assert 'set_project_as_default' in tool_names

    def test_each_tool_has_required_fields(self):
        result = handler.handler({'method': 'tools/list'}, None)
        for tool in result['tools']:
            assert 'name' in tool
            assert 'description' in tool
            assert 'inputSchema' in tool

    def test_add_project_requires_userid_and_zipcode(self):
        result = handler.handler({'method': 'tools/list'}, None)
        add_project_tool = next(t for t in result['tools'] if t['name'] == 'add_project')
        assert 'userId' in add_project_tool['inputSchema']['required']
        assert 'zipCode' in add_project_tool['inputSchema']['required']


class TestToolsCall:

    def test_routes_to_get_user_profile(self):
        expected = {'userName': 'patpang', 'projects': []}
        with patch('handler.get_user_profile', return_value=expected) as mock_fn:
            result = handler.handler({
                'method': 'tools/call',
                'params': {'name': 'get_user_profile', 'arguments': {'appleId': 'apple123'}},
            }, None)

        mock_fn.assert_called_once_with(apple_id='apple123', google_id=None)
        content = json.loads(result['content'][0]['text'])
        assert content['userName'] == 'patpang'

    def test_routes_to_add_project(self):
        expected = {'message': 'Project added successfully', 'projectId': 42}
        with patch('handler.add_project', return_value=expected) as mock_fn:
            result = handler.handler({
                'method': 'tools/call',
                'params': {
                    'name': 'add_project',
                    'arguments': {'userId': 1, 'zipCode': '94587', 'projectName': 'My House'},
                },
            }, None)

        mock_fn.assert_called_once_with(
            user_id=1,
            zip_code='94587',
            is_default_project=False,
            project_name='My House',
            job_type='',
            description=None,
            street_address=None,
            street_address2=None,
            city=None,
            state=None,
        )
        content = json.loads(result['content'][0]['text'])
        assert content['projectId'] == 42

    def test_routes_to_set_project_as_default(self):
        expected = {'message': 'Default project updated successfully', 'projectId': 10}
        with patch('handler.set_project_as_default', return_value=expected) as mock_fn:
            result = handler.handler({
                'method': 'tools/call',
                'params': {
                    'name': 'set_project_as_default',
                    'arguments': {'userId': 1, 'projectId': 10},
                },
            }, None)

        mock_fn.assert_called_once_with(user_id=1, project_id=10)
        content = json.loads(result['content'][0]['text'])
        assert content['projectId'] == 10

    def test_response_wrapped_in_content_array(self):
        with patch('handler.get_user_profile', return_value={'userName': 'x', 'projects': []}):
            result = handler.handler({
                'method': 'tools/call',
                'params': {'name': 'get_user_profile', 'arguments': {'appleId': 'x'}},
            }, None)

        assert 'content' in result
        assert result['content'][0]['type'] == 'text'
        assert isinstance(result['content'][0]['text'], str)

    def test_returns_error_for_unknown_tool(self):
        result = handler.handler({
            'method': 'tools/call',
            'params': {'name': 'nonexistent_tool', 'arguments': {}},
        }, None)
        content = json.loads(result['content'][0]['text'])
        assert 'message' in content
        assert 'nonexistent_tool' in content['message']

    def test_returns_error_for_unknown_method(self):
        result = handler.handler({'method': 'bad/method'}, None)
        assert 'message' in result
        assert 'bad/method' in result['message']
