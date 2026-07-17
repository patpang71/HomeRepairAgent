import pytest
from unittest.mock import patch
from tools.update_resolution import update_resolution


class TestUpdateResolution:

    def test_successfully_updates_resolution(self, mock_conn, mock_cursor):
        mock_cursor.rowcount = 1

        with patch('tools.update_resolution.get_connection', return_value=mock_conn):
            result = update_resolution(
                project_id=101,
                resolution_detail='Replaced the pressure relief valve to stop the leak.',
                resolved=True,
            )

        assert result == {'message': 'Resolution updated successfully', 'resolved': True}
        mock_conn.commit.assert_called_once()

    def test_rolls_back_when_project_not_found(self, mock_conn, mock_cursor):
        mock_cursor.rowcount = 0

        with patch('tools.update_resolution.get_connection', return_value=mock_conn):
            result = update_resolution(project_id=999, resolution_detail='detail', resolved=False)

        assert 'message' in result
        assert '999' in result['message']
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()

    def test_rolls_back_on_db_exception(self, mock_conn, mock_cursor):
        mock_cursor.execute.side_effect = Exception('DB timeout')

        with patch('tools.update_resolution.get_connection', return_value=mock_conn):
            result = update_resolution(project_id=101, resolution_detail='detail', resolved=False)

        assert 'DB timeout' in result['message']
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()
