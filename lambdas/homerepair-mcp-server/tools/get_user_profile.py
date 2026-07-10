import logging

from db import get_connection

logger = logging.getLogger(__name__)


def get_user_profile(apple_id: str = None, google_id: str = None) -> dict:
    if not apple_id and not google_id:
        logger.warning('get_user_profile called without appleId or googleId')
        return {'message': 'Either appleId or googleId is required'}

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            if apple_id:
                where = 'u."AppleId" = %s'
                param = apple_id
            else:
                where = 'u."GoogleId" = %s'
                param = google_id

            cur.execute(f"""
                SELECT
                    u."UserId", u."Username", u."AppleId", u."GoogleId", u."AvatarUrl",
                    u."Email", u."FirstName", u."LastName",
                    p."IsDefaultProject", p."IsActive", p."ProjectName", p."JobType",
                    p."Description", p."StreetAddress", p."StreetAddress2",
                    p."City", p."State", p."ZipCode", p."ProjectId"
                FROM userinfo."User" u
                JOIN userinfo."Project" p ON u."UserId" = p."UserId"
                WHERE {where}
            """, (param,))

            rows = cur.fetchall()

        if not rows:
            logger.info('get_user_profile: no user found for %s=%s', 'appleId' if apple_id else 'googleId', param)
            return {'message': 'User not found'}

        first = rows[0]
        result = {
            'userId':    first[0],
            'userName':  first[1],
            'appleId':   first[2] or '',
            'googleId':  first[3] or '',
            'avatarUrl': first[4] or '',
            'email':     first[5],
            'firstName': first[6] or '',
            'lastName':  first[7] or '',
            'projects':  [],
        }

        for row in rows:
            result['projects'].append({
                'isDefaultProject': str(row[8]).lower(),
                'isActive':         str(row[9]).lower(),
                'projectName':      row[10] or '',
                'jobType':          row[11] or '',
                'description':      row[12] or '',
                'streetAddress':    row[13] or '',
                'streetAddress2':   row[14] or '',
                'city':             row[15] or '',
                'state':            row[16] or '',
                'zipCode':          row[17] or '',
                'projectId':        row[18],
            })

        logger.info('get_user_profile: found userId=%s with %d project(s)', result['userId'], len(result['projects']))
        return result

    except Exception as e:
        logger.exception('get_user_profile failed')
        return {'message': str(e)}
