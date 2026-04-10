import logging

from sqlalchemy import inspect, text

from app.core.security import get_password_hash
from app.db.session import SessionLocal, engine
from app.models.user import User


logger = logging.getLogger(__name__)


def _ensure_user_builtin_column() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    if "sys_user" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("sys_user")}
    with engine.begin() as connection:
        if "is_builtin" not in columns:
            logger.info("Adding sys_user.is_builtin compatibility column")
            connection.execute(
                text(
                    """
                    ALTER TABLE sys_user
                    ADD COLUMN is_builtin TINYINT(1) NOT NULL DEFAULT 0
                    """
                )
            )

        connection.execute(text("UPDATE sys_user SET is_builtin = 1 WHERE username = 'admin'"))

        builtin_count = connection.execute(
            text("SELECT COUNT(*) FROM sys_user WHERE is_builtin = 1")
        ).scalar() or 0
        if builtin_count == 0:
            connection.execute(
                text(
                    """
                    UPDATE sys_user
                    SET is_builtin = 1
                    WHERE id = (
                        SELECT min_id
                        FROM (
                            SELECT MIN(id) AS min_id
                            FROM sys_user
                            WHERE role = 'admin'
                        ) AS builtin_admin
                    )
                    """
                )
            )


def _hash_builtin_plaintext_passwords() -> None:
    session = SessionLocal()

    try:
        builtin_users = session.query(User).filter(User.is_builtin.is_(True)).all()
        updated = False

        for user in builtin_users:
            if not user.password.startswith("$2"):
                logger.info("Hashing plaintext password for builtin user '%s'", user.username)
                user.password = get_password_hash(user.password)
                updated = True

        if updated:
            session.commit()
    except Exception:
        session.rollback()
        logger.exception("Failed to normalize builtin user passwords during startup migration")
        raise
    finally:
        session.close()


def run_startup_migrations() -> None:
    _ensure_user_builtin_column()
    _hash_builtin_plaintext_passwords()
