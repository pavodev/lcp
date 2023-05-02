from typing import Any, Dict, Tuple

from .ddl_gen import generate_ddl


async def pg_create(template: Dict[Any, Any]) -> Dict[str, Any]:
    # TODO: this function should also return the mapping file at some point
    return generate_ddl(template)
