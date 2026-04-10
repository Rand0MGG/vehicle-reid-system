import logging
from typing import Optional

from fastapi import BackgroundTasks

from app.db.session import SessionLocal
from app.models.sys_log_model import SysLog


logger = logging.getLogger(__name__)


def execute_audit_insertion(user_id: Optional[int], operation: str, status: bool) -> None:
    db = SessionLocal()
    try:
        audit_record = SysLog(
            user_id=user_id,
            operation=operation,
            status=status,
        )
        db.add(audit_record)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to insert audit log: user_id=%s, operation=%s", user_id, operation)
    finally:
        db.close()


def get_audit_logger(background_tasks: BackgroundTasks):
    def logger_instance(user_id: Optional[int], operation: str, status: bool = True):
        background_tasks.add_task(execute_audit_insertion, user_id, operation, status)

    return logger_instance
