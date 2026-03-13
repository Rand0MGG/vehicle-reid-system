from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional # <--- 引入 Optional

class AuditLogItem(BaseModel):
    id: int
    user_id: Optional[int] = None # <--- 修改这里：允许为空，默认值为 None
    operation: str
    status: bool
    exec_time: datetime

    class Config:
        from_attributes = True # 注意：如果你用的是 Pydantic v2，orm_mode 已经改名为 from_attributes 了

class AuditLogData(BaseModel):
    total: int
    items: List[AuditLogItem]

class AuditLogResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: AuditLogData