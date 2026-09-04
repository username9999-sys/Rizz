"""Performance indexes

Revision ID: 002_indexes
Revises: 001_initial
Create Date: 2026-09-04

Adds indexes that the auth and posts query patterns need. These are
NOT recreations of indexes that 001_initial already created — they
are NEW indexes identified by reviewing actual query patterns:

  - /api/auth/login   : WHERE username = ?         (covered by ix_users_username)
  - /api/auth/login   : WHERE email = ?            (covered by ix_users_email)
  - /api/auth/me      : WHERE id = ?               (PK)
  - /api/posts (list) : ORDER BY created_at DESC   (NEEDS ix_posts_created_at)
  - /api/posts (list) : WHERE user_id = ? ORDER BY created_at DESC
                                              (NEEDS ix_posts_user_created)
  - /api/posts (user) : WHERE user_id = ? AND status = 'published'
                                              (NEEDS ix_posts_user_status_pub)
  - Audit logs        : WHERE user_id = ? ORDER BY created_at DESC
                                              (NEEDS ix_audit_user_created)
  - Token revocations : WHERE jti = ?              (PK)
  - Sessions (refresh): WHERE expires_at < now()  (NEEDS ix_sessions_expires)

These are added with `CREATE INDEX CONCURRENTLY` style to avoid
locking writes during deployment. For SQLite (local dev), the
CONCURRENTLY keyword is not supported, so the migration uses
plain CREATE INDEX which is fast on small dev databases.
"""

from alembic import op

revision = "002_indexes"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    concurrently_sql = "" if is_sqlite else "CONCURRENTLY"

    # Posts: list ordering & filtering
    op.execute(f"CREATE INDEX {concurrently_sql} IF NOT EXISTS ix_posts_created_at "
               f"ON posts (created_at DESC)")
    op.execute(f"CREATE INDEX {concurrently_sql} IF NOT EXISTS ix_posts_user_created "
               f"ON posts (user_id, created_at DESC)")
    op.execute(f"CREATE INDEX {concurrently_sql} IF NOT EXISTS ix_posts_user_status_pub "
               f"ON posts (user_id, status, created_at DESC) "
               f"WHERE status = 'published'")
    op.execute(f"CREATE INDEX {concurrently_sql} IF NOT EXISTS ix_posts_status_published_at "
               f"ON posts (published_at DESC) "
               f"WHERE status = 'published'")

    # Posts: full-text search on title+content (if Postgres)
    if not is_sqlite:
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_posts_fts "
            "ON posts USING gin(to_tsvector('english', title || ' ' || content))"
        )

    # Users: case-insensitive email lookup
    if not is_sqlite:
        op.execute("CREATE INDEX IF NOT EXISTS ix_users_email_lower "
                   "ON users (LOWER(email))")
        op.execute("CREATE INDEX IF NOT EXISTS ix_users_username_lower "
                   "ON users (LOWER(username))")

    # Users: last_login for "active users" reports
    op.execute(f"CREATE INDEX {concurrently_sql} IF NOT EXISTS ix_users_last_login "
               f"ON users (last_login_at DESC NULLS LAST)")

    # Sessions / refresh tokens: expiry sweep
    op.execute(f"CREATE INDEX {concurrently_sql} IF NOT EXISTS ix_sessions_expires "
               f"ON sessions (expires_at) WHERE revoked_at IS NULL")

    # Audit logs: per-user timeline
    op.execute(f"CREATE INDEX {concurrently_sql} IF NOT EXISTS ix_audit_user_created "
               f"ON audit_logs (user_id, created_at DESC)")
    op.execute(f"CREATE INDEX {concurrently_sql} IF NOT EXISTS ix_audit_created "
               f"ON audit_logs (created_at DESC)")

    # Comments: per-post listing
    op.execute(f"CREATE INDEX {concurrently_sql} IF NOT EXISTS ix_comments_post_created "
               f"ON comments (post_id, created_at DESC)")
    op.execute(f"CREATE INDEX {concurrently_sql} IF NOT EXISTS ix_comments_user "
               f"ON comments (user_id)")

    # Tags + post_tags
    op.execute(f"CREATE INDEX {concurrently_sql} IF NOT EXISTS ix_post_tags_post "
               f"ON post_tags (post_id)")
    op.execute(f"CREATE INDEX {concurrently_sql} IF NOT EXISTS ix_post_tags_tag "
               f"ON post_tags (tag_id)")

    # Analyze to update planner statistics (Postgres only)
    if not is_sqlite:
        op.execute("ANALYZE posts")
        op.execute("ANALYZE users")
        op.execute("ANALYZE audit_logs")
        op.execute("ANALYZE sessions")
        op.execute("ANALYZE comments")


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    concurrently_sql = "" if is_sqlite else "CONCURRENTLY"

    op.execute(f"DROP INDEX {concurrently_sql} IF EXISTS ix_comments_user")
    op.execute(f"DROP INDEX {concurrently_sql} IF EXISTS ix_comments_post_created")
    op.execute(f"DROP INDEX {concurrently_sql} IF EXISTS ix_audit_created")
    op.execute(f"DROP INDEX {concurrently_sql} IF EXISTS ix_audit_user_created")
    op.execute(f"DROP INDEX {concurrently_sql} IF EXISTS ix_sessions_expires")
    op.execute(f"DROP INDEX {concurrently_sql} IF EXISTS ix_users_last_login")
    op.execute(f"DROP INDEX {concurrently_sql} IF EXISTS ix_post_tags_tag")
    op.execute(f"DROP INDEX {concurrently_sql} IF EXISTS ix_post_tags_post")
    op.execute(f"DROP INDEX {concurrently_sql} IF EXISTS ix_posts_status_published_at")
    if not is_sqlite:
        op.execute("DROP INDEX IF EXISTS ix_posts_fts")
        op.execute("DROP INDEX IF EXISTS ix_users_username_lower")
        op.execute("DROP INDEX IF EXISTS ix_users_email_lower")
    op.execute(f"DROP INDEX {concurrently_sql} IF EXISTS ix_posts_user_status_pub")
    op.execute(f"DROP INDEX {concurrently_sql} IF EXISTS ix_posts_user_created")
    op.execute(f"DROP INDEX {concurrently_sql} IF EXISTS ix_posts_created_at")
