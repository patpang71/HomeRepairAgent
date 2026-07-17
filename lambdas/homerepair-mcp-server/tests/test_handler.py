import json
import pytest
from unittest.mock import patch, MagicMock
import handler


class TestToolsList:

    def test_returns_all_tools(self):
        result = handler.handler({'method': 'tools/list'}, None)
        tool_names = [t['name'] for t in result['tools']]
        assert 'get_user_profile' in tool_names
        assert 'add_project' in tool_names
        assert 'set_project_as_default' in tool_names
        assert 'set_preference' in tool_names
        assert 'save_search_result' in tool_names
        assert 'update_resolution' in tool_names

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
        expected = {'preference': 'CONCISE', 'projects': []}
        with patch('handler.get_user_profile', return_value=expected) as mock_fn:
            result = handler.handler({
                'method': 'tools/call',
                'params': {'name': 'get_user_profile', 'arguments': {'appleId': 'apple123'}},
            }, None)

        mock_fn.assert_called_once_with(apple_id='apple123', google_id=None)
        content = json.loads(result['content'][0]['text'])
        assert content['preference'] == 'CONCISE'

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

    def test_routes_to_set_preference(self):
        expected = {'message': 'Preference updated successfully', 'preference': 'DETAIL'}
        with patch('handler.set_preference', return_value=expected) as mock_fn:
            result = handler.handler({
                'method': 'tools/call',
                'params': {
                    'name': 'set_preference',
                    'arguments': {'userId': 1, 'preference': 'DETAIL'},
                },
            }, None)

        mock_fn.assert_called_once_with(user_id=1, preference='DETAIL')
        content = json.loads(result['content'][0]['text'])
        assert content['preference'] == 'DETAIL'

    def test_routes_to_save_search_result(self):
        expected = {'message': 'Search result saved successfully', 'searchResultId': 55}
        with patch('handler.save_search_result', return_value=expected) as mock_fn:
            result = handler.handler({
                'method': 'tools/call',
                'params': {
                    'name': 'save_search_result',
                    'arguments': {'projectId': 101, 'searchQuestion': 'q', 'searchResult': 'r'},
                },
            }, None)

        mock_fn.assert_called_once_with(project_id=101, search_question='q', search_result='r')
        content = json.loads(result['content'][0]['text'])
        assert content['searchResultId'] == 55

    def test_routes_to_update_resolution(self):
        expected = {'message': 'Resolution updated successfully', 'resolved': True}
        with patch('handler.update_resolution', return_value=expected) as mock_fn:
            result = handler.handler({
                'method': 'tools/call',
                'params': {
                    'name': 'update_resolution',
                    'arguments': {'projectId': 101, 'resolutionDetail': 'summary', 'resolved': True},
                },
            }, None)

        mock_fn.assert_called_once_with(project_id=101, resolution_detail='summary', resolved=True)
        content = json.loads(result['content'][0]['text'])
        assert content['resolved'] is True

    def test_response_wrapped_in_content_array(self):
        with patch('handler.get_user_profile', return_value={'preference': 'CONCISE', 'projects': []}):
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
