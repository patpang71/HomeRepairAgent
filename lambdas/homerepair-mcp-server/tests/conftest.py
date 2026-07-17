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
    'apple123',    # 1  AppleId
    None,          # 2  GoogleId
    None,          # 3  AvatarUrl
    'p@test.com',  # 4  Email
    'Kai',         # 5  FirstName
    'Tai',         # 6  LastName
    'CONCISE',     # 7  Preference
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
    None,          # 18 ResolutionDetail
    False,         # 19 Resolved
    101,           # 20 ProjectId
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
