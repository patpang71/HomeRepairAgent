import pytest
from unittest.mock import patch
from tools.save_search_result import save_search_result


class TestSaveSearchResult:

    def test_returns_error_when_project_id_missing(self):
        result = save_search_result(project_id=None, search_question='q', search_result='r')
        assert result == {'message': 'projectId is required'}

    def test_successfully_inserts_search_result(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = (7,)

        with patch('tools.save_search_result.get_connection', return_value=mock_conn):
            result = save_search_result(
                project_id=101,
                search_question='Why is my water heater leaking?',
                search_result='Check the pressure relief valve.',
            )

        assert result == {'message': 'Search result saved successfully', 'searchResultId': 7}
        mock_conn.commit.assert_called_once()

    def test_insert_uses_correct_parameters(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = (7,)

        with patch('tools.save_search_result.get_connection', return_value=mock_conn):
            save_search_result(
                project_id=101,
                search_question='Why is my water heater leaking?',
                search_result='Check the pressure relief valve.',
            )

        insert_call = mock_cursor.execute.call_args_list[0]
        params = insert_call[0][1]
        assert params == (101, 'Why is my water heater leaking?', 'Check the pressure relief valve.')

    def test_rolls_back_and_returns_error_on_exception(self, mock_conn, mock_cursor):
        mock_cursor.execute.side_effect = Exception('boom')

        with patch('tools.save_search_result.get_connection', return_value=mock_conn):
            result = save_search_result(project_id=101, search_question='q', search_result='r')

        assert 'message' in result
        assert 'boom' in result['message']
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()
