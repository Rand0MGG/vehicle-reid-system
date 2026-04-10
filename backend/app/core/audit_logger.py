from fastapi import BackgroundTasks
from typing import Optional

from app.db.session import SessionLocal
from app.models.sys_log_model import SysLog


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
        raise
    finally:
        db.close()


def get_audit_logger(background_tasks: BackgroundTasks):
    def logger_instance(user_id: Optional[int], operation: str, status: bool = True):
        background_tasks.add_task(execute_audit_insertion, user_id, operation, status)

    return logger_instance
