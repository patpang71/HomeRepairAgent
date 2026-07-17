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
                    u."UserId", u."AppleId", u."GoogleId", u."AvatarUrl",
                    u."Email", u."FirstName", u."LastName", u."Preference",
                    p."IsDefaultProject", p."IsActive", p."ProjectName", p."JobType",
                    p."Description", p."StreetAddress", p."StreetAddress2",
                    p."City", p."State", p."ZipCode", p."ResolutionDetail",
                    p."Resolved", p."ProjectId"
                FROM userinfo."User" u
                JOIN userinfo."Project" p ON u."UserId" = p."UserId"
                WHERE {where}
            """, (param,))

            rows = cur.fetchall()

            if not rows:
                logger.info('get_user_profile: no user found for %s=%s', 'appleId' if apple_id else 'googleId', param)
                return {'message': 'User not found'}

            project_ids = [row[20] for row in rows]
            search_result_ids_by_project = {pid: [] for pid in project_ids}
            cur.execute(
                'SELECT "ProjectId", "SearchResultId" FROM userinfo."SearchResult" '
                'WHERE "ProjectId" = ANY(%s) ORDER BY "SearchResultId"',
                (project_ids,),
            )
            for project_id, search_result_id in cur.fetchall():
                search_result_ids_by_project.setdefault(project_id, []).append(search_result_id)

        first = rows[0]
        result = {
            'userId':     first[0],
            'appleId':    first[1] or '',
            'googleId':   first[2] or '',
            'avatarUrl':  first[3] or '',
            'email':      first[4],
            'firstName':  first[5] or '',
            'lastName':   first[6] or '',
            'preference': first[7] or 'CONCISE',
            'projects':   [],
        }

        for row in rows:
            project_id = row[20]
            result['projects'].append({
                'isDefaultProject':  str(row[8]).lower(),
                'isActive':          str(row[9]).lower(),
                'projectName':       row[10] or '',
                'jobType':           row[11] or '',
                'description':       row[12] or '',
                'streetAddress':     row[13] or '',
                'streetAddress2':    row[14] or '',
                'city':              row[15] or '',
                'state':             row[16] or '',
                'zipCode':           row[17] or '',
                'resolutionDetail':  row[18] or '',
                'resolved':          str(row[19]).lower(),
                'projectId':         project_id,
                'searchResultIds':   search_result_ids_by_project.get(project_id, []),
            })

        logger.info('get_user_profile: found userId=%s with %d project(s)', result['userId'], len(result['projects']))
        return result

    except Exception as e:
        logger.exception('get_user_profile failed')
        return {'message': str(e)}
