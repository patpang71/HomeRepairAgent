import pytest
from unittest.mock import patch
from tools.add_user import add_user


class TestAddUser:

    def test_returns_error_when_email_missing(self):
        result = add_user(email='', apple_id='apple123', first_name='John', last_name='Doe')
        assert result == {'message': 'email is required'}

    def test_returns_error_when_email_none(self):
        result = add_user(email=None, apple_id='apple123', first_name='John', last_name='Doe')
        assert result == {'message': 'email is required'}

    def test_successfully_inserts_user_when_email_not_found(self, mock_conn, mock_cursor):
        # First fetchone (existence check) -> no row found; second (RETURNING) -> new UserId
        mock_cursor.fetchone.side_effect = [None, (42,)]

        with patch('tools.add_user.get_connection', return_value=mock_conn):
            result = add_user(
                email='new@test.com',
                apple_id='apple123',
                first_name='John',
                last_name='Doe',
            )

        assert result == {'message': 'User added successfully', 'userId': 42}
        mock_conn.commit.assert_called_once()

    def test_insert_uses_correct_parameters(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.side_effect = [None, (7,)]

        with patch('tools.add_user.get_connection', return_value=mock_conn):
            add_user(
                email='new@test.com',
                apple_id='apple123',
                first_name='John',
                last_name='Doe',
            )

        insert_call = mock_cursor.execute.call_args_list[1]
        params = insert_call[0][1]
        assert params == ('apple123', 'new@test.com', 'John', 'Doe')

    def test_returns_error_when_email_already_exists(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = (1,)

        with patch('tools.add_user.get_connection', return_value=mock_conn):
            result = add_user(
                email='existing@test.com',
                apple_id='apple123',
                first_name='John',
                last_name='Doe',
            )

        assert result == {'message': 'Email existing@test.com is already existed'}
        mock_conn.commit.assert_not_called()
        assert mock_cursor.execute.call_count == 1  # only the existence check ran

    def test_rolls_back_and_returns_error_on_exception(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.side_effect = [None]  # existence check finds no row
        mock_cursor.execute.side_effect = [None, Exception('boom')]  # INSERT fails

        with patch('tools.add_user.get_connection', return_value=mock_conn):
            result = add_user(
                email='new@test.com',
                apple_id='apple123',
                first_name='John',
                last_name='Doe',
            )

        assert 'message' in result
        assert 'boom' in result['message']
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()
