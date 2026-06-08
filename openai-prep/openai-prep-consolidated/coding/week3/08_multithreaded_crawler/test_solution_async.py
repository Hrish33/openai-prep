"""
Tests for the asyncio variant of the crawler. Run:
  pytest coding/week3/08_multithreaded_crawler/test_solution_async.py -v

Mirrors test_solution.py but with an async parser and async test functions.
Uses pytest-asyncio. If not installed:  pip install pytest-asyncio

The latency test at the bottom verifies REAL concurrency — a serial
implementation will pass correctness but blow the wall-clock budget.
"""

import asyncio
import time
import pytest
from solution_async import AsyncCrawler


# ---- Async test double ----

class MockAsyncHtmlParser:
    """
    Static link graph + simulated async I/O latency. Tracks call counts
    so we can assert "no URL fetched more than once" across coroutines.
    """

    def __init__(self, graph: dict[str, list[str]], latency: float = 0.0):
        self._graph = graph
        self._latency = latency
        self._calls: list[str] = []
        self._lock = asyncio.Lock()

    async def get_urls(self, url: str) -> list[str]:
        if self._latency:
            await asyncio.sleep(self._latency)   # ← genuine async suspension
        async with self._lock:
            self._calls.append(url)
        return list(self._graph.get(url, []))

    @property
    def call_count(self) -> dict[str, int]:
        # No await needed for the snapshot; tests read this after crawl returns.
        counts: dict[str, int] = {}
        for u in self._calls:
            counts[u] = counts.get(u, 0) + 1
        return counts


# ---- Basic correctness ----

@pytest.mark.asyncio
async def test_single_page_no_links():
    parser = MockAsyncHtmlParser({"http://a.com/x": []})
    result = await AsyncCrawler(num_workers=2).crawl("http://a.com/x", parser)
    assert set(result) == {"http://a.com/x"}


@pytest.mark.asyncio
async def test_two_pages_linear():
    parser = MockAsyncHtmlParser({
        "http://a.com/1": ["http://a.com/2"],
        "http://a.com/2": [],
    })
    result = await AsyncCrawler(num_workers=2).crawl("http://a.com/1", parser)
    assert set(result) == {"http://a.com/1", "http://a.com/2"}


@pytest.mark.asyncio
async def test_cycle_handled():
    parser = MockAsyncHtmlParser({
        "http://a.com/1": ["http://a.com/2"],
        "http://a.com/2": ["http://a.com/1"],   # cycle back
    })
    result = await AsyncCrawler(num_workers=2).crawl("http://a.com/1", parser)
    assert set(result) == {"http://a.com/1", "http://a.com/2"}


@pytest.mark.asyncio
async def test_self_loop():
    parser = MockAsyncHtmlParser({
        "http://a.com/1": ["http://a.com/1", "http://a.com/2"],
        "http://a.com/2": [],
    })
    result = await AsyncCrawler(num_workers=2).crawl("http://a.com/1", parser)
    assert set(result) == {"http://a.com/1", "http://a.com/2"}


# ---- Same-host filter ----

@pytest.mark.asyncio
async def test_other_host_excluded():
    parser = MockAsyncHtmlParser({
        "http://a.com/x": ["http://a.com/y", "http://b.com/z"],
        "http://a.com/y": [],
        "http://b.com/z": ["http://b.com/w"],   # must NOT be crawled
        "http://b.com/w": [],
    })
    result = await AsyncCrawler(num_workers=2).crawl("http://a.com/x", parser)
    assert set(result) == {"http://a.com/x", "http://a.com/y"}


@pytest.mark.asyncio
async def test_port_and_subdomain_treated_as_different_host():
    """Strict hostname match — subdomains and ports are different hosts."""
    parser = MockAsyncHtmlParser({
        "http://a.com/x":       ["http://www.a.com/y", "http://a.com:8080/z"],
        "http://www.a.com/y":   [],
        "http://a.com:8080/z":  [],
    })
    result = await AsyncCrawler(num_workers=2).crawl("http://a.com/x", parser)
    assert set(result) == {"http://a.com/x"}


# ---- Dedup under concurrency ----

@pytest.mark.asyncio
async def test_no_url_fetched_twice():
    """The visited-set guard must prevent duplicate fetches across coroutines."""
    parser = MockAsyncHtmlParser({
        "http://a.com/1": ["http://a.com/2", "http://a.com/3"],
        "http://a.com/2": ["http://a.com/4", "http://a.com/3"],
        "http://a.com/3": ["http://a.com/4"],
        "http://a.com/4": [],
    }, latency=0.01)

    await AsyncCrawler(num_workers=4).crawl("http://a.com/1", parser)
    for url, count in parser.call_count.items():
        assert count == 1, f"{url} fetched {count} times"


@pytest.mark.asyncio
async def test_diamond_graph_correct():
    parser = MockAsyncHtmlParser({
        "http://a.com/top":    ["http://a.com/left", "http://a.com/right"],
        "http://a.com/left":   ["http://a.com/bottom"],
        "http://a.com/right":  ["http://a.com/bottom"],
        "http://a.com/bottom": [],
    })
    result = await AsyncCrawler(num_workers=4).crawl("http://a.com/top", parser)
    assert set(result) == {
        "http://a.com/top",
        "http://a.com/left",
        "http://a.com/right",
        "http://a.com/bottom",
    }


# ---- Concurrency is real (the speedup test) ----

@pytest.mark.asyncio
async def test_concurrent_fetches_real_speedup():
    """
    8 URLs, 100ms latency each. Serial would take ~800ms; with 8 workers
    awaiting in parallel, should take ~100ms plus scheduling slop.
    """
    parser = MockAsyncHtmlParser({
        "http://a.com/0": [f"http://a.com/{i}" for i in range(1, 8)],
        **{f"http://a.com/{i}": [] for i in range(1, 8)},
    }, latency=0.1)

    start = time.perf_counter()
    result = await AsyncCrawler(num_workers=8).crawl("http://a.com/0", parser)
    elapsed = time.perf_counter() - start

    assert set(result) == {f"http://a.com/{i}" for i in range(8)}
    assert elapsed < 0.4, (
        f"Crawl took {elapsed:.2f}s — looks serial. "
        "Workers should await get_urls concurrently."
    )


# ---- Termination ----

@pytest.mark.asyncio
async def test_terminates_on_empty_graph():
    """Empty graph — the start URL itself is the only result. Must not hang."""
    parser = MockAsyncHtmlParser({"http://a.com/start": []})
    result = await asyncio.wait_for(
        AsyncCrawler(num_workers=4).crawl("http://a.com/start", parser),
        timeout=2.0,
    )
    assert result == ["http://a.com/start"]


@pytest.mark.asyncio
async def test_terminates_on_isolated_url():
    """URL is referenced but parser doesn't know it — should return cleanly."""
    parser = MockAsyncHtmlParser({})
    result = await asyncio.wait_for(
        AsyncCrawler(num_workers=4).crawl("http://a.com/ghost", parser),
        timeout=2.0,
    )
    assert result == ["http://a.com/ghost"]
