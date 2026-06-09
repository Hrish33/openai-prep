"""
In-memory SQL database.

Read 00_prereqs.md, then problem.md. Sketch your token types, AST classes,
and the execute() dispatch BEFORE coding. Specifically decide:
  - What stages does execute() go through?  (tokenize -> parse -> execute)
  - What's the shape of your AST?            (CreateTable, Insert, Select)
  - Where do errors come from at each stage?

Suggested structure (you don't have to follow this — design what makes
sense to you):
  - Tokenizer: str -> list[Token]
  - Parser: list[Token] -> AST node (Create | Insert | Select)
  - Executor: AST node + Database state -> result (None or list[dict])
  - Database holds {table_name -> rows} and {table_name -> column schema}

DO NOT use eval() or exec() to evaluate WHERE. The whole point of this
problem is implementing the SQL pipeline yourself.
"""

from typing import Any, Optional


class Database:
    def __init__(self) -> None:
        # your code here
        raise NotImplementedError

    def execute(self, sql: str) -> Optional[list[dict[str, Any]]]:
        # your code here
        raise NotImplementedError
