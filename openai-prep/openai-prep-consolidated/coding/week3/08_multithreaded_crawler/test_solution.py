"""
Tests for multithreaded crawler. Run:
  pytest coding/week3/08_multithreaded_crawler/test_solution.py -v

These tests use a MockHtmlParser with simulated latency so a correct
solution exhibits real concurrency. A serial solution will pass
correctness tests but FAIL the speedup test at the bottom.
"""

import threading
import time
import pytest
from solution import Crawler


# ---- Test double ----

class MockHtmlParser:
    """
    Static link graph + simulated per-request latency. Tracks call counts
    so we can assert "no URL fetched more than once" across threads.
    """

    def __init__(self, graph: dict[str, list[str]], latency: float = 0.0):
        self._graph = graph
        self._latency = latency
        self._calls: list[str] = []
        self._lock = threading.Lock()

    def get_urls(self, url: str) -> list[str]:
        if self._latency:
            time.sleep(self._latency)
        with self._lock:
            self._calls.append(url)
        return list(self._graph.get(url, []))

    @property
    def call_count(self) -> dict[str, int]:
        with self._lock:
            counts: dict[str, int] = {}
            for u in self._calls:
                counts[u] = counts.get(u, 0) + 1
            return counts


# ---- Basic correctness ----

def test_single_page_no_links():
    parser = MockHtmlParser({"http://a.com/x": []})
    result = Crawler(num_workers=2).crawl("http://a.com/x", parser)
    assert set(result) == {"http://a.com/x"}


def test_two_pages_linear():
    parser = MockHtmlParser({
        "http://a.com/1": ["http://a.com/2"],
        "http://a.com/2": [],
    })
    result = Crawler(num_workers=2).crawl("http://a.com/1", parser)
    assert set(result) == {"http://a.com/1", "http://a.com/2"}


def test_branching_graph():
    parser = MockHtmlParser({
        "http://a.com/root": ["http://a.com/x", "http://a.com/y", "http://a.com/z"],
        "http://a.com/x": [],
        "http://a.com/y": [],
        "http://a.com/z": [],
    })
    result = Crawler(num_workers=4).crawl("http://a.com/root", parser)
    assert set(result) == {
        "http://a.com/root",
        "http://a.com/x",
        "http://a.com/y",
        "http://a.com/z",
    }


# ---- Dedup / cycles ----

def test_self_link_visited_once():
    parser = MockHtmlParser({
        "http://a.com/x": ["http://a.com/x"],
    })
    result = Crawler(num_workers=4).crawl("http://a.com/x", parser)
    assert set(result) == {"http://a.com/x"}
    assert parser.call_count["http://a.com/x"] == 1


def test_two_node_cycle():
    parser = MockHtmlParser({
        "http://a.com/1": ["http://a.com/2"],
        "http://a.com/2": ["http://a.com/1"],
    })
    result = Crawler(num_workers=4).crawl("http://a.com/1", parser)
    assert set(result) == {"http://a.com/1", "http://a.com/2"}
    assert parser.call_count["http://a.com/1"] == 1
    assert parser.call_count["http://a.com/2"] == 1


def test_duplicate_links_on_one_page():
    parser = MockHtmlParser({
        "http://a.com/root": [
            "http://a.com/x",
            "http://a.com/x",
            "http://a.com/x",
        ],
        "http://a.com/x": [],
    })
    result = Crawler(num_workers=4).crawl("http://a.com/root", parser)
    assert set(result) == {"http://a.com/root", "http://a.com/x"}
    assert parser.call_count["http://a.com/x"] == 1


def test_diamond_dedups():
    parser = MockHtmlParser({
        "http://a.com/A": ["http://a.com/B", "http://a.com/C"],
        "http://a.com/B": ["http://a.com/D"],
        "http://a.com/C": ["http://a.com/D"],
        "http://a.com/D": [],
    })
    result = Crawler(num_workers=4).crawl("http://a.com/A", parser)
    assert set(result) == {
        "http://a.com/A", "http://a.com/B",
        "http://a.com/C", "http://a.com/D",
    }
    assert parser.call_count["http://a.com/D"] == 1


# ---- Same-host filter ----

def test_other_host_links_skipped():
    parser = MockHtmlParser({
        "http://news.yahoo.com/topics": [
            "http://news.yahoo.com/news",
            "http://sports.yahoo.com/scores",
            "http://other.com/anything",
        ],
        "http://news.yahoo.com/news": [],
        "http://sports.yahoo.com/scores": ["http://sports.yahoo.com/more"],
        "http://sports.yahoo.com/more": [],
        "http://other.com/anything": [],
    })
    result = Crawler(num_workers=4).crawl(
        "http://news.yahoo.com/topics", parser
    )
    assert set(result) == {
        "http://news.yahoo.com/topics",
        "http://news.yahoo.com/news",
    }
    assert "http://sports.yahoo.com/scores" not in parser.call_count
    assert "http://other.com/anything" not in parser.call_count


def test_start_url_with_no_path():
    parser = MockHtmlParser({
        "http://a.com": ["http://a.com/x"],
        "http://a.com/x": [],
    })
    result = Crawler(num_workers=2).crawl("http://a.com", parser)
    assert set(result) == {"http://a.com", "http://a.com/x"}


# ---- Termination ----

def test_terminates_with_empty_graph():
    """No links anywhere. Crawl must return, not hang."""
    parser = MockHtmlParser({"http://a.com/x": []})
    # If this hangs, pytest's per-test timeout (if configured) catches it.
    # Otherwise this test will simply not return — which IS a failure signal.
    result = Crawler(num_workers=8).crawl("http://a.com/x", parser)
    assert set(result) == {"http://a.com/x"}


def test_terminates_with_pure_cycle():
    parser = MockHtmlParser({
        "http://a.com/1": ["http://a.com/2", "http://a.com/3"],
        "http://a.com/2": ["http://a.com/1"],
        "http://a.com/3": ["http://a.com/1"],
    })
    result = Crawler(num_workers=4).crawl("http://a.com/1", parser)
    assert set(result) == {
        "http://a.com/1", "http://a.com/2", "http://a.com/3",
    }


def test_returns_list_type():
    parser = MockHtmlParser({"http://a.com/x": []})
    result = Crawler(num_workers=2).crawl("http://a.com/x", parser)
    assert isinstance(result, list)


# ---- Concurrency (the real test) ----

def test_no_url_visited_more_than_once_under_concurrency():
    """
    Wide fan-out + latency. Races on the visited set show up here.
    """
    children = [f"http://a.com/c{i}" for i in range(50)]
    graph: dict[str, list[str]] = {"http://a.com/root": list(children)}
    for c in children:
        graph[c] = list(children)  # every child links to every child
    parser = MockHtmlParser(graph, latency=0.01)

    result = Crawler(num_workers=8).crawl("http://a.com/root", parser)

    assert set(result) == {"http://a.com/root", *children}
    for url, count in parser.call_count.items():
        assert count == 1, f"{url} fetched {count} times — visited-set race"


def test_actually_uses_threads_for_speedup():
    """
    With 10 pages at 50ms each, serial = 500ms. With 5 workers, expect <=200ms.
    Gives a healthy margin for thread overhead. A serial solution will
    take ~500ms and fail. Marked slow so you can skip in fast loops.
    """
    pages = [f"http://a.com/p{i}" for i in range(10)]
    graph: dict[str, list[str]] = {"http://a.com/root": list(pages)}
    for p in pages:
        graph[p] = []
    parser = MockHtmlParser(graph, latency=0.05)

    crawler = Crawler(num_workers=5)
    start = time.perf_counter()
    result = crawler.crawl("http://a.com/root", parser)
    elapsed = time.perf_counter() - start

    assert len(set(result)) == 11
    assert elapsed < 0.25, (
        f"Crawl took {elapsed:.2f}s with 5 workers on 10 pages of 50ms — "
        f"looks serial, not concurrent."
    )


def test_independent_crawlers_dont_share_state():
    """Two Crawler instances run independently."""
    parser1 = MockHtmlParser({"http://a.com/x": []})
    parser2 = MockHtmlParser({"http://b.com/y": []})

    r1 = Crawler(num_workers=2).crawl("http://a.com/x", parser1)
    r2 = Crawler(num_workers=2).crawl("http://b.com/y", parser2)

    assert set(r1) == {"http://a.com/x"}
    assert set(r2) == {"http://b.com/y"}
