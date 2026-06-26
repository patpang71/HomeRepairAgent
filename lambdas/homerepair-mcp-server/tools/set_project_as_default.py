from db import get_connection


def set_project_as_default(user_id: int, project_id: int) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Capture existing default so the error message can reference it
            cur.execute("""
                SELECT "ProjectId" FROM userinfo."Project"
                WHERE "UserId" = %s AND "IsDefaultProject" = TRUE
            """, (user_id,))
            row = cur.fetchone()
            original_default_id = row[0] if row else None

            # Unset all defaults for this user
            cur.execute("""
                UPDATE userinfo."Project"
                SET "IsDefaultProject" = FALSE
                WHERE "UserId" = %s
            """, (user_id,))

            # Set the requested project as default
            cur.execute("""
                UPDATE userinfo."Project"
                SET "IsDefaultProject" = TRUE
                WHERE "UserId" = %s AND "ProjectId" = %s
            """, (user_id, project_id))

            if cur.rowcount == 0:
                raise ValueError(
                    f'Project {project_id} not found for user {user_id}. '
                    f'Original default (ProjectId={original_default_id}) has been restored.'
                )

        conn.commit()
        return {'message': 'Default project updated successfully', 'projectId': project_id}

    except Exception as e:
        # Rollback restores the original IsDefaultProject values atomically
        conn.rollback()
        return {'message': str(e)}
