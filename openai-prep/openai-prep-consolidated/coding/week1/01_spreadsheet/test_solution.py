"""
Tests for spreadsheet. Run: pytest coding/week1/01_spreadsheet/test_solution.py -v

If you wrote your own tests first (good!), compare against these afterward.
"""

import pytest
from solution import Spreadsheet


# --- Basic literal values ---

def test_set_and_get_integer():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 5)
    assert sheet.get_cell("A1") == 5


def test_set_and_get_float():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 3.14)
    assert sheet.get_cell("A1") == 3.14


def test_unset_cell_returns_none():
    sheet = Spreadsheet()
    assert sheet.get_cell("Z99") is None


def test_overwrite_literal():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 5)
    sheet.set_cell("A1", 10)
    assert sheet.get_cell("A1") == 10


# --- Basic formulas ---

def test_simple_formula_addition():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 5)
    sheet.set_cell("B1", 10)
    sheet.set_cell("C1", "=A1+B1")
    assert sheet.get_cell("C1") == 15


def test_simple_formula_subtraction():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 10)
    sheet.set_cell("B1", 3)
    sheet.set_cell("C1", "=A1-B1")
    assert sheet.get_cell("C1") == 7


def test_simple_formula_multiplication():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 4)
    sheet.set_cell("B1", 5)
    sheet.set_cell("C1", "=A1*B1")
    assert sheet.get_cell("C1") == 20


def test_simple_formula_division():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 10)
    sheet.set_cell("B1", 2)
    sheet.set_cell("C1", "=A1/B1")
    assert sheet.get_cell("C1") == 5


def test_formula_with_literal_operand():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 5)
    sheet.set_cell("B1", "=A1+10")
    assert sheet.get_cell("B1") == 15


# --- Propagation ---

def test_change_propagates_to_dependent():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 5)
    sheet.set_cell("B1", 10)
    sheet.set_cell("C1", "=A1+B1")
    assert sheet.get_cell("C1") == 15
    sheet.set_cell("A1", 20)
    assert sheet.get_cell("C1") == 30


def test_chained_propagation():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 5)
    sheet.set_cell("B1", "=A1*2")
    sheet.set_cell("C1", "=B1+1")
    assert sheet.get_cell("C1") == 11
    sheet.set_cell("A1", 10)
    assert sheet.get_cell("B1") == 20
    assert sheet.get_cell("C1") == 21


def test_diamond_dependency():
    """A1 feeds B1 and C1; both feed D1. Update A1, D1 must reflect."""
    sheet = Spreadsheet()
    sheet.set_cell("A1", 10)
    sheet.set_cell("B1", "=A1+1")
    sheet.set_cell("C1", "=A1+2")
    sheet.set_cell("D1", "=B1+C1")
    assert sheet.get_cell("D1") == 23
    sheet.set_cell("A1", 100)
    assert sheet.get_cell("B1") == 101
    assert sheet.get_cell("C1") == 102
    assert sheet.get_cell("D1") == 203


def test_overwrite_formula_with_literal():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 5)
    sheet.set_cell("B1", "=A1+1")
    assert sheet.get_cell("B1") == 6
    sheet.set_cell("B1", 100)
    assert sheet.get_cell("B1") == 100
    sheet.set_cell("A1", 999)
    assert sheet.get_cell("B1") == 100  # no longer depends on A1


def test_overwrite_formula_with_different_formula():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 5)
    sheet.set_cell("B1", 10)
    sheet.set_cell("C1", "=A1+B1")
    sheet.set_cell("C1", "=A1*B1")
    assert sheet.get_cell("C1") == 50


# --- Cycle detection ---

def test_direct_cycle_raises():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 5)
    sheet.set_cell("B1", "=A1")
    with pytest.raises(ValueError):
        sheet.set_cell("A1", "=B1")


def test_self_reference_raises():
    sheet = Spreadsheet()
    with pytest.raises(ValueError):
        sheet.set_cell("A1", "=A1")


def test_indirect_cycle_raises():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 5)
    sheet.set_cell("B1", "=A1+1")
    sheet.set_cell("C1", "=B1+1")
    with pytest.raises(ValueError):
        sheet.set_cell("A1", "=C1+1")


def test_cycle_rejected_state_unchanged():
    """If a cycle is rejected, state must be unchanged."""
    sheet = Spreadsheet()
    sheet.set_cell("A1", 5)
    sheet.set_cell("B1", "=A1+1")
    with pytest.raises(ValueError):
        sheet.set_cell("A1", "=B1")
    assert sheet.get_cell("A1") == 5
    assert sheet.get_cell("B1") == 6


# --- Edge cases ---

def test_division_by_zero():
    sheet = Spreadsheet()
    sheet.set_cell("A1", 10)
    sheet.set_cell("B1", 0)
    with pytest.raises(ZeroDivisionError):
        sheet.set_cell("C1", "=A1/B1")


def test_reference_to_unset_cell():
    """Pick a behavior (0 or raise), be consistent. Adjust this test
    to match your decision."""
    sheet = Spreadsheet()
    sheet.set_cell("A1", "=B1+5")
    result = sheet.get_cell("A1")
    # If unset = 0: result == 5. If unset raises: this test setup
    # would need to be in a pytest.raises block. Either is defensible.
    assert result is None or result == 5 or isinstance(result, (int, float))
