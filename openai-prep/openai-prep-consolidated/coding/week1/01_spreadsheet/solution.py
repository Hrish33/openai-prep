"""
Spreadsheet with formula dependencies.

Read 00_prereqs.md, then problem.md. Sketch your data structures
before coding.

Suggested structure (you don't have to follow this — design what makes
sense to you):
  - dict of cell_id -> raw value (literal or formula string)
  - dict of cell_id -> evaluated value (cache)
  - dependency graph: cell -> set of cells it depends on (forward edges)
  - reverse graph: cell -> set of cells that depend on it (for propagation)
"""

from typing import Union, Optional

CellValue = Union[int, float, str]  # str is reserved for formulas starting with "="


class Spreadsheet:
    def __init__(self) -> None:
        # your code here
        raise NotImplementedError

    def set_cell(self, cell_id: str, value: CellValue) -> None:
        # your code here
        raise NotImplementedError

    def get_cell(self, cell_id: str) -> Optional[Union[int, float]]:
        # your code here
        raise NotImplementedError
