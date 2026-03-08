from fastapi import BackgroundTasks, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.sys_log_model import SysLog

def execute_audit_insertion(db: Session, user_id: int, operation: str, status: bool):
    audit_record = SysLog(
        user_id=user_id,
        operation=operation,
        status=status
    )
    db.add(audit_record)
    db.commit()

def get_audit_logger(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    def logger_instance(user_id: int, operation: str, status: bool = True):
        background_tasks.add_task(execute_audit_insertion, db, user_id, operation, status)
    return logger_instance