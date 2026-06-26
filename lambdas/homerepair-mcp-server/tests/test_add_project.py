import pytest
from unittest.mock import patch
from tools.add_project import add_project


class TestAddProject:

    def test_returns_error_when_zipcode_missing(self):
        result = add_project(user_id=1, zip_code='')
        assert result == {'message': 'zipCode is required'}

    def test_returns_error_when_zipcode_none(self):
        result = add_project(user_id=1, zip_code=None)
        assert result == {'message': 'zipCode is required'}

    def test_successfully_inserts_project(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = (42,)

        with patch('tools.add_project.get_connection', return_value=mock_conn):
            result = add_project(
                user_id=1,
                zip_code='94587',
                project_name='My House',
                job_type='MISC',
                street_address='123 Main St',
                city='Union City',
                state='CA',
            )

        assert result['message'] == 'Project added successfully'
        assert result['projectId'] == 42
        mock_conn.commit.assert_called_once()

    def test_insert_uses_correct_parameters(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = (10,)

        with patch('tools.add_project.get_connection', return_value=mock_conn):
            add_project(
                user_id=5,
                zip_code='94587',
                is_default_project=True,
                project_name='Kitchen Reno',
                job_type='ELECTRICAL',
                description='Fix wiring',
                street_address='456 Oak Ave',
                street_address2='Unit 2',
                city='Fremont',
                state='CA',
            )

        call_args = mock_cursor.execute.call_args_list[0]
        params = call_args[0][1]
        assert params[0] == 5        # user_id
        assert params[1] is True     # is_default_project
        assert params[2] == 'Kitchen Reno'
        assert params[3] == 'ELECTRICAL'
        assert params[9] == '94587'  # zip_code (last param)

    def test_is_default_project_defaults_to_false(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = (1,)

        with patch('tools.add_project.get_connection', return_value=mock_conn):
            add_project(user_id=1, zip_code='94587')

        params = mock_cursor.execute.call_args_list[0][0][1]
        assert params[1] is False

    def test_rolls_back_and_returns_error_on_exception(self, mock_conn, mock_cursor):
        mock_cursor.execute.side_effect = Exception('Unique constraint violation')

        with patch('tools.add_project.get_connection', return_value=mock_conn):
            result = add_project(user_id=1, zip_code='94587')

        assert 'message' in result
        assert 'Unique constraint violation' in result['message']
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()
