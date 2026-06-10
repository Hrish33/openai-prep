"""
In-memory SQL-like database, method-call API.

Read problem.md first. Sketch your storage layout, type-check logic, and
select shape BEFORE coding. Specifically decide:
  - How are tables stored?           (recommended: list[dict] per table)
  - How is the schema stored?        (recommended: list of (name, type) tuples)
  - Where does type checking live?   (insert path — fail fast)
  - How does projection respect column order?

Suggested structure (deviate if you have a reason):
  - self.tables:  dict[str, list[dict]]            — table name -> rows
  - self.schemas: dict[str, list[tuple[str, str]]] — table name -> [(col, type), ...]

The `where` argument to select is a Python callable. You don't parse it;
you call it. Predicate composition (AND/OR) is the caller's job.
"""

from typing import Any, Callable, Optional


class Database:
    def __init__(self) -> None:
        # your code here
        raise NotImplementedError

    def create_table(self, name: str, schema: list[tuple[str, str]]) -> None:
        """schema is [(col_name, col_type), ...]. Types: 'INT', 'TEXT'."""
        # your code here
        raise NotImplementedError

    def insert(self, table: str, row: dict[str, Any]) -> None:
        """Row must match the schema exactly (no missing, no extras, types correct)."""
        # your code here
        raise NotImplementedError

    def select(
        self,
        table: str,
        columns: Optional[list[str]] = None,
        where: Optional[Callable[[dict[str, Any]], bool]] = None,
    ) -> list[dict[str, Any]]:
        """columns=None -> all columns (in schema order).
        where=None    -> all rows.
        Projected dicts respect the order in `columns`."""
        # your code here
        raise NotImplementedError
