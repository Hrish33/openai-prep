"""
Tests for Unix `cd` with symlink resolution.
Run: pytest coding/week2/05_unix_cd_symlinks/test_solution.py -v

If you wrote your own tests first (good!), compare against these afterward.
"""

import pytest
from solution import Shell


# --- pwd / starting state ---

def test_initial_cwd_is_root():
    shell = Shell()
    assert shell.pwd() == "/"


def test_pwd_does_not_mutate():
    shell = Shell()
    shell.pwd()
    shell.pwd()
    assert shell.pwd() == "/"


# --- Absolute paths ---

def test_cd_absolute_simple():
    shell = Shell()
    assert shell.cd("/home/user") == "/home/user"
    assert shell.pwd() == "/home/user"


def test_cd_to_root():
    shell = Shell()
    shell.cd("/home/user")
    assert shell.cd("/") == "/"
    assert shell.pwd() == "/"


def test_cd_absolute_resets():
    """Absolute path discards current cwd."""
    shell = Shell()
    shell.cd("/a/b/c")
    assert shell.cd("/x/y") == "/x/y"


# --- Relative paths ---

def test_cd_relative_simple():
    shell = Shell()
    shell.cd("/home")
    assert shell.cd("user") == "/home/user"


def test_cd_relative_extends():
    shell = Shell()
    shell.cd("/a")
    shell.cd("b")
    shell.cd("c")
    assert shell.pwd() == "/a/b/c"


# --- Dots: . and .. ---

def test_dot_is_noop():
    shell = Shell()
    shell.cd("/a/b")
    assert shell.cd(".") == "/a/b"


def test_dotdot_goes_up_one():
    shell = Shell()
    shell.cd("/a/b/c")
    assert shell.cd("..") == "/a/b"


def test_dotdot_at_root_stays_at_root():
    shell = Shell()
    assert shell.cd("..") == "/"
    assert shell.cd("/../../..") == "/"


def test_dots_mixed_in_path():
    shell = Shell()
    assert shell.cd("/a/b/./c/../d") == "/a/b/d"


def test_dotdot_relative():
    shell = Shell()
    shell.cd("/a/b/c")
    assert shell.cd("../../x") == "/a/x"


# --- Redundant slashes ---

def test_multiple_slashes_collapse():
    shell = Shell()
    assert shell.cd("/a//b///c") == "/a/b/c"


def test_trailing_slash_stripped():
    shell = Shell()
    assert shell.cd("/a/b/") == "/a/b"


# --- Symlinks ---

def test_symlink_basic():
    shell = Shell()
    shell.register_symlink("/usr/local", "/usr")
    assert shell.cd("/usr/local") == "/usr"


def test_symlink_resolved_mid_path():
    """The symlink is in the middle of the cd input — resolution must happen
    when /usr/local lands on the stack, before /bin gets pushed."""
    shell = Shell()
    shell.register_symlink("/usr/local", "/usr")
    assert shell.cd("/usr/local/bin") == "/usr/bin"


def test_symlink_target_has_dotdot():
    shell = Shell()
    shell.register_symlink("/a/b", "/x/y/..")
    assert shell.cd("/a/b/c") == "/x/c"


def test_chained_symlinks():
    shell = Shell()
    shell.register_symlink("/a", "/b")
    shell.register_symlink("/b", "/c")
    assert shell.cd("/a/file") == "/c/file"


def test_symlink_to_root():
    shell = Shell()
    shell.register_symlink("/home/back", "/")
    assert shell.cd("/home/back") == "/"
    assert shell.cd("/home/back/etc") == "/etc"


def test_reregister_symlink_replaces_target():
    shell = Shell()
    shell.register_symlink("/link", "/a")
    shell.register_symlink("/link", "/b")
    assert shell.cd("/link") == "/b"


# --- Cycle detection ---

def test_self_loop_symlink_raises():
    shell = Shell()
    shell.register_symlink("/loop", "/loop")
    with pytest.raises(ValueError):
        shell.cd("/loop")


def test_two_link_cycle_raises():
    shell = Shell()
    shell.register_symlink("/a", "/b")
    shell.register_symlink("/b", "/a")
    with pytest.raises(ValueError):
        shell.cd("/a")


def test_three_link_cycle_raises():
    shell = Shell()
    shell.register_symlink("/a", "/b")
    shell.register_symlink("/b", "/c")
    shell.register_symlink("/c", "/a")
    with pytest.raises(ValueError):
        shell.cd("/a")


def test_cycle_leaves_cwd_unchanged():
    shell = Shell()
    shell.cd("/safe/place")
    shell.register_symlink("/loop", "/loop")
    with pytest.raises(ValueError):
        shell.cd("/loop")
    assert shell.pwd() == "/safe/place"


def test_two_separate_cd_calls_both_touch_same_symlink():
    """Visited set is scoped per-call. The same symlink can be safely
    traversed in two different cd calls."""
    shell = Shell()
    shell.register_symlink("/usr/local", "/usr")
    shell.cd("/usr/local/bin")
    assert shell.pwd() == "/usr/bin"
    shell.cd("/")
    shell.cd("/usr/local/share")
    assert shell.pwd() == "/usr/share"


# --- Edge cases ---

def test_empty_command_is_noop():
    """Defensible behavior: empty command leaves cwd unchanged.
    (Adjust this test if you chose "raise" instead — both are defensible.)"""
    shell = Shell()
    shell.cd("/a/b")
    result = shell.cd("")
    assert result == "/a/b"
    assert shell.pwd() == "/a/b"


def test_cd_returns_new_cwd():
    """cd's return value matches pwd after the call."""
    shell = Shell()
    new_cwd = shell.cd("/a/b/c")
    assert new_cwd == shell.pwd()


def test_long_chain_no_cycle_resolves():
    """Defensive: a long but non-cyclic chain should resolve without false-positive."""
    shell = Shell()
    shell.register_symlink("/a", "/b")
    shell.register_symlink("/b", "/c")
    shell.register_symlink("/c", "/d")
    shell.register_symlink("/d", "/e")
    assert shell.cd("/a") == "/e"
