import pytest
from unittest.mock import patch
from tools.get_user_profile import get_user_profile
from tests.conftest import SAMPLE_ROW


class TestGetUserProfile:

    def test_returns_error_when_no_id_provided(self):
        result = get_user_profile()
        assert result == {'message': 'Either appleId or googleId is required'}

    def test_returns_profile_by_apple_id(self, mock_conn, mock_cursor):
        mock_cursor.fetchall.side_effect = [[SAMPLE_ROW], []]

        with patch('tools.get_user_profile.get_connection', return_value=mock_conn):
            result = get_user_profile(apple_id='apple123')

        assert result['userId'] == 1
        assert result['appleId'] == 'apple123'
        assert result['googleId'] == ''
        assert result['email'] == 'p@test.com'
        assert result['firstName'] == 'Kai'
        assert result['lastName'] == 'Tai'
        assert result['preference'] == 'CONCISE'
        assert len(result['projects']) == 1

    def test_returns_profile_by_google_id(self, mock_conn, mock_cursor):
        google_row = SAMPLE_ROW[:1] + (None, 'google456') + SAMPLE_ROW[3:]
        mock_cursor.fetchall.side_effect = [[google_row], []]

        with patch('tools.get_user_profile.get_connection', return_value=mock_conn):
            result = get_user_profile(google_id='google456')

        assert result['googleId'] == 'google456'
        assert result['appleId'] == ''

    def test_project_fields_are_mapped_correctly(self, mock_conn, mock_cursor):
        mock_cursor.fetchall.side_effect = [[SAMPLE_ROW], []]

        with patch('tools.get_user_profile.get_connection', return_value=mock_conn):
            result = get_user_profile(apple_id='apple123')

        project = result['projects'][0]
        assert project['projectId'] == 101
        assert project['isDefaultProject'] == 'true'
        assert project['isActive'] == 'true'
        assert project['projectName'] == 'My House'
        assert project['jobType'] == 'MISC'
        assert project['streetAddress'] == '123 Main St'
        assert project['streetAddress2'] == ''
        assert project['city'] == 'Union City'
        assert project['state'] == 'CA'
        assert project['zipCode'] == '94587'
        assert project['resolutionDetail'] == ''
        assert project['resolved'] == 'false'
        assert project['searchResultIds'] == []

    def test_returns_multiple_projects_for_same_user(self, mock_conn, mock_cursor):
        second_row = SAMPLE_ROW[:10] + ('Second House', 'PLUMBING') + SAMPLE_ROW[12:20] + (102,)
        mock_cursor.fetchall.side_effect = [[SAMPLE_ROW, second_row], []]

        with patch('tools.get_user_profile.get_connection', return_value=mock_conn):
            result = get_user_profile(apple_id='apple123')

        assert len(result['projects']) == 2
        assert result['projects'][0]['projectName'] == 'My House'
        assert result['projects'][1]['projectName'] == 'Second House'

    def test_includes_search_result_ids_for_project(self, mock_conn, mock_cursor):
        mock_cursor.fetchall.side_effect = [[SAMPLE_ROW], [(101, 5001), (101, 5002)]]

        with patch('tools.get_user_profile.get_connection', return_value=mock_conn):
            result = get_user_profile(apple_id='apple123')

        assert result['projects'][0]['searchResultIds'] == [5001, 5002]

    def test_returns_error_when_user_not_found(self, mock_conn, mock_cursor):
        mock_cursor.fetchall.return_value = []

        with patch('tools.get_user_profile.get_connection', return_value=mock_conn):
            result = get_user_profile(apple_id='unknown')

        assert result == {'message': 'User not found'}

    def test_returns_error_on_db_exception(self, mock_conn):
        mock_conn.cursor.side_effect = Exception('DB connection lost')

        with patch('tools.get_user_profile.get_connection', return_value=mock_conn):
            result = get_user_profile(apple_id='apple123')

        assert 'message' in result
        assert 'DB connection lost' in result['message']
