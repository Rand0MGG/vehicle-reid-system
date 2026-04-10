from typing import Any, Dict


def success_response(data: Any = None, message: str = "success") -> Dict[str, Any]:
    return {
        "code": 200,
        "message": message,
        "data": data,
    }
