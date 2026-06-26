import pytest
from unittest.mock import patch, call
from tools.set_project_as_default import set_project_as_default


class TestSetProjectAsDefault:

    def test_successfully_sets_default_project(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = (5,)  # existing default
        mock_cursor.rowcount = 1                  # UPDATE affected a row

        with patch('tools.set_project_as_default.get_connection', return_value=mock_conn):
            result = set_project_as_default(user_id=1, project_id=10)

        assert result == {'message': 'Default project updated successfully', 'projectId': 10}
        mock_conn.commit.assert_called_once()

    def test_executes_three_sql_statements_in_order(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = (5,)
        mock_cursor.rowcount = 1

        with patch('tools.set_project_as_default.get_connection', return_value=mock_conn):
            set_project_as_default(user_id=1, project_id=10)

        assert mock_cursor.execute.call_count == 3
        # First call: SELECT current default
        first_sql = mock_cursor.execute.call_args_list[0][0][0]
        assert 'SELECT' in first_sql
        assert 'IsDefaultProject' in first_sql
        # Second call: UPDATE all to FALSE
        second_sql = mock_cursor.execute.call_args_list[1][0][0]
        assert 'FALSE' in second_sql
        # Third call: UPDATE target to TRUE
        third_sql = mock_cursor.execute.call_args_list[2][0][0]
        assert 'TRUE' in third_sql

    def test_handles_no_existing_default(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = None  # no current default
        mock_cursor.rowcount = 1

        with patch('tools.set_project_as_default.get_connection', return_value=mock_conn):
            result = set_project_as_default(user_id=1, project_id=10)

        assert result['message'] == 'Default project updated successfully'

    def test_rolls_back_when_project_not_found(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = (5,)
        mock_cursor.rowcount = 0  # target project does not exist

        with patch('tools.set_project_as_default.get_connection', return_value=mock_conn):
            result = set_project_as_default(user_id=1, project_id=999)

        assert 'message' in result
        assert '999' in result['message']
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()

    def test_rolls_back_on_db_exception(self, mock_conn, mock_cursor):
        mock_cursor.execute.side_effect = Exception('DB timeout')

        with patch('tools.set_project_as_default.get_connection', return_value=mock_conn):
            result = set_project_as_default(user_id=1, project_id=10)

        assert 'DB timeout' in result['message']
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()
