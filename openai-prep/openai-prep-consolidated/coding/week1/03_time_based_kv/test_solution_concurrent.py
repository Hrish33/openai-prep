"""
Tests for the thread-safe variant.
Run: pytest coding/week1/03_time_based_kv/test_solution_concurrent.py -v

Concurrency tests are inherently probabilistic — race conditions don't
always reproduce. These tests use high enough iteration counts to make
silent corruption *very* likely to surface, but they're not a proof of
correctness. Reviewers should understand this.
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from solution_concurrent import TimeMap


# --- Base correctness still holds (single-threaded) ---

def test_base_single_threaded_still_works():
    tm = TimeMap()
    tm.set("foo", "bar", 1)
    tm.set("foo", "baz", 4)
    print(tm.times, tm.values)
    assert tm.get("foo", 1) == "bar"
    assert tm.get("foo", 4) == "baz"
    assert tm.get("foo", 5) == "baz"
    assert tm.get("foo", 0) == ""


# --- Concurrent writers to the same key (no exceptionsmy con, no torn state) ---

def test_concurrent_writers_same_key_no_exceptions():
    """1000 writes from 8 threads. No exceptions raised, and the final
    history has exactly 1000 entries."""
    tm = TimeMap()
    N_WRITES = 1000

    def writer(start: int):
        for i in range(start, start + N_WRITES // 8):
            tm.set("k", f"v{i}", i)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(writer, range(0, N_WRITES, N_WRITES // 8)))

    # The final read should see SOME value at every timestamp written.
    # If the lock didn't work, some writes would be lost or duplicated.
    seen = {tm.get("k", t) for t in range(N_WRITES)}
    # All 1000 writes should be visible — no losses.
    assert seen == {f"v{i}" for i in range(N_WRITES)}


# --- Concurrent readers + writers (no torn reads) ---

def test_concurrent_reader_writer_no_torn_reads():
    """One thread writes, another reads. Readers must never see a
    corrupted value (a partial decode of two records, e.g.).

    With parallel arrays, a torn read = times array advanced but values
    array didn't, so values[index] is from the WRONG record. We don't
    have a direct way to detect that without inspecting internals, so
    we assert a weaker property: every read returns either "" or one
    of the values we actually wrote."""
    tm = TimeMap()
    N = 5000
    valid_values = {f"v{i}" for i in range(N)} | {""}

    def writer():
        for i in range(N):
            tm.set("k", f"v{i}", i)

    def reader():
        for _ in range(N):
            v = tm.get("k", N // 2)
            assert v in valid_values, f"torn read: {v!r}"

    t1 = threading.Thread(target=writer)
    t2 = threading.Thread(target=reader)
    t1.start(); t2.start()
    t1.join(); t2.join()


# --- Concurrent operations on DIFFERENT keys (global lock means they serialize) ---

def test_concurrent_writes_different_keys():
    """Writes to different keys should all succeed. The global lock means
    they don't run in parallel, but they should all complete correctly.
    (Per-key lock striping would let these run in parallel — the natural
    next rung up.)"""
    tm = TimeMap()

    def writer(key: str):
        for i in range(100):
            tm.set(key, f"{key}_v{i}", i)

    with ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(writer, [f"key_{i}" for i in range(10)]))

    for k in range(10):
        key = f"key_{k}"
        assert tm.get(key, 99) == f"{key}_v99"
        assert tm.get(key, 50) == f"{key}_v50"


# --- Stress: many concurrent set + get, just verify no exceptions ---

def test_stress_no_exceptions():
    """Hammer the codec with mixed set/get from many threads. The bar
    is just: no exceptions raised, no deadlocks. (If you ran this
    without a lock, you'd get TypeError or IndexError from torn reads
    on the parallel arrays.)"""
    tm = TimeMap()

    def worker(tid: int):
        for i in range(500):
            if i % 2 == 0:
                tm.set(f"k{tid}", f"v{i}", i)
            else:
                tm.get(f"k{tid}", i)

    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(worker, range(16)))
