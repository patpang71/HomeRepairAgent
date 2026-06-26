import sys
from unittest.mock import MagicMock

# Stub psycopg2 before any Lambda module is imported — unit tests mock
# get_connection directly so the real driver is never needed locally.
sys.modules['psycopg2'] = MagicMock()
sys.modules['psycopg2.extras'] = MagicMock()

import pytest


# Column order matches the SELECT in get_user_profile.py
SAMPLE_ROW = (
    1,             # 0  UserId
    'patpang',     # 1  Username
    'apple123',    # 2  AppleId
    None,          # 3  GoogleId
    None,          # 4  AvatarUrl
    'p@test.com',  # 5  Email
    'Kai',         # 6  FirstName
    'Tai',         # 7  LastName
    True,          # 8  IsDefaultProject
    True,          # 9  IsActive
    'My House',    # 10 ProjectName
    'MISC',        # 11 JobType
    'Home repairs',# 12 Description
    '123 Main St', # 13 StreetAddress
    None,          # 14 StreetAddress2
    'Union City',  # 15 City
    'CA',          # 16 State
    '94587',       # 17 ZipCode
    101,           # 18 ProjectId
)


@pytest.fixture
def mock_cursor():
    cursor = MagicMock()
    cursor.rowcount = 1
    return cursor


@pytest.fixture
def mock_conn(mock_cursor):
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = mock_cursor
    conn.cursor.return_value.__exit__.return_value = False
    return conn
