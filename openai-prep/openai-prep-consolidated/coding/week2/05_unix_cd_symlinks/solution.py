"""
Unix-style `cd` with symbolic link resolution.

Read 00_prereqs.md, then problem.md. Sketch on paper before coding:
  - The 5 path-normalization rules (split, empty, '.', '..', regular)
  - WHERE you resolve symlinks (at each component push? at the end?)
  - WHERE the cycle-detection visited set lives (per-call? per-component? on self?)
  - HOW you keep cwd unchanged when a cycle is detected mid-walk

Suggested structure (deviate if you have a reason):
  - self._cwd:      str                       — always absolute, starts "/"
  - self._symlinks: dict[str, str]            — link path -> target path

The walker that turns a path string into a normalized stack of components
gets called in TWO places: for the user's command, and recursively for
each symlink target. Write it once.
"""


class Shell:
    def __init__(self) -> None:
        self.sym_link = {}
        self.cwd = "/"

    def register_symlink(self, link_path: str, target: str) -> None:
        """Register `link_path` as a symlink to `target`. Both are absolute."""
        # your code here
        self.sym_link[link_path] = target

    def cd(self, command: str) -> str:
        """Resolve `command` from current cwd, update cwd, return new cwd.

        Raises ValueError on symlink cycle (cwd unchanged in that case).
        """
        if command.startswith("/"):
            stack = []
        else:
            stack = [p for p in self.cwd.split("/") if p]

        for ele in command.split("/"):
            if ele == '.' or ele == '':
                continue
            if ele == '..':
                if stack:
                    stack.pop()
            else:
                stack.append(ele)
            stack = self.resolve(stack, set())

        self.cwd = "/" + "/".join(stack) if stack else "/"
        return self.cwd

    def resolve(self, stack, visited) -> list:
        curr = "/" + "/".join(stack)
        if curr not in self.sym_link :
            return stack
        if curr in visited:
            raise ValueError('cycle')
        visited.add(curr)
        target = self.sym_link[curr]

        new_stack = []
        for ele in target.split("/"):
            if ele == '.' or ele == '':
                continue
            if ele == '..' :
                new_stack.pop()
            else:
                new_stack.append(ele)
            new_stack = self.resolve(new_stack, visited)

        return new_stack


    def pwd(self) -> str:
        """Return the current working directory (always absolute)."""
        # your code here
        return self.cwd
