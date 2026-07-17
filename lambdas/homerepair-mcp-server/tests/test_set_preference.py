import pytest
from unittest.mock import patch
from tools.set_preference import set_preference


class TestSetPreference:

    def test_successfully_updates_preference(self, mock_conn, mock_cursor):
        mock_cursor.rowcount = 1

        with patch('tools.set_preference.get_connection', return_value=mock_conn):
            result = set_preference(user_id=1, preference='DETAIL')

        assert result == {'message': 'Preference updated successfully', 'preference': 'DETAIL'}
        mock_conn.commit.assert_called_once()

    def test_rejects_invalid_preference(self, mock_conn, mock_cursor):
        with patch('tools.set_preference.get_connection', return_value=mock_conn):
            result = set_preference(user_id=1, preference='VERBOSE')

        assert 'message' in result
        mock_conn.cursor.assert_not_called()
        mock_conn.commit.assert_not_called()

    def test_rolls_back_when_user_not_found(self, mock_conn, mock_cursor):
        mock_cursor.rowcount = 0

        with patch('tools.set_preference.get_connection', return_value=mock_conn):
            result = set_preference(user_id=999, preference='CONCISE')

        assert 'message' in result
        assert '999' in result['message']
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()

    def test_rolls_back_on_db_exception(self, mock_conn, mock_cursor):
        mock_cursor.execute.side_effect = Exception('DB timeout')

        with patch('tools.set_preference.get_connection', return_value=mock_conn):
            result = set_preference(user_id=1, preference='CONCISE')

        assert 'DB timeout' in result['message']
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()
