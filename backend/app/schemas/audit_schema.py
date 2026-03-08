from pydantic import BaseModel
from datetime import datetime
from typing import List

class AuditLogItem(BaseModel):
    id: int
    user_id: int
    operation: str
    status: bool
    exec_time: datetime

    class Config:
        orm_mode = True

class AuditLogData(BaseModel):
    total: int
    items: List[AuditLogItem]

class AuditLogResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: AuditLogData