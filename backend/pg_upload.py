from typing import Any, Dict, Tuple


async def pg_create(template: Dict[Any, Any]) -> Tuple[str, str]:
    create_ddl = ""
    constraints_ddl = ""
    return create_ddl, constraints_ddl
