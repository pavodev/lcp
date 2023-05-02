from typing import Any, Dict, Tuple

from .ddl_gen import generate_ddl


async def pg_create(template: Dict[Any, Any]) -> Tuple[str, str, Dict[Any, Any]]:
    # TODO: this function should also return the mapping file at some point
    (
        create_ddl,
        constraints_ddl,
        prep_seg_create,
        prep_seg_inserts,
        mapping,
    ) = generate_ddl(template)

    return create_ddl, constraints_ddl, prep_seg_create, prep_seg_inserts, mapping
