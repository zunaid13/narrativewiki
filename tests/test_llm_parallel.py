"""`llm/parallel.py` — the stage-level "run a few calls at once" helper (2026-09-23).

The only promises callers depend on: same results, same order, and a real speed-up. Each is
pinned here, because a silent reordering would scramble claim order across characters and a
silent serialization would quietly give back the wall-clock win it exists for.
"""

from __future__ import annotations

import threading
import time

import pytest

from narrativewiki.llm.parallel import map_calls, workers_for


def test_results_keep_input_order_even_when_calls_finish_out_of_order():
    def slow_for_early_items(n: int) -> int:
        time.sleep(0.05 if n < 3 else 0.0)  # the first items finish LAST
        return n * 10

    assert map_calls(slow_for_early_items, list(range(6)), workers=6) == [0, 10, 20, 30, 40, 50]


def test_progress_callback_sees_items_in_order():
    seen: list[tuple[int, int]] = []
    map_calls(lambda n: n, [5, 6, 7], workers=3, on_result=lambda i, item, r: seen.append((i, item)))
    assert seen == [(0, 5), (1, 6), (2, 7)]


def test_single_worker_creates_no_threads():
    """A local Ollama profile declares concurrency 1 and must behave exactly as the old loop."""
    main = threading.get_ident()
    threads = map_calls(lambda _: threading.get_ident(), [1, 2, 3], workers=1)
    assert threads == [main, main, main]


def test_calls_really_do_overlap():
    """Eight 0.1s calls take ~0.1s at width 8, not ~0.8s -- the whole point of the module."""
    started = time.perf_counter()
    map_calls(lambda _: time.sleep(0.1), list(range(8)), workers=8)
    assert time.perf_counter() - started < 0.4


def test_an_exception_propagates_like_a_serial_loop():
    def boom(n: int) -> int:
        if n == 2:
            raise RuntimeError("model said no")
        return n

    with pytest.raises(RuntimeError, match="model said no"):
        map_calls(boom, [1, 2, 3], workers=3)


def test_workers_for_reads_the_routed_profile_and_never_guesses():
    class Profile:
        concurrency = 8

    class Client:
        def profile_for(self, stage):
            return Profile()

    class ClientWithoutProfiles:
        def profile_for(self, stage):
            raise KeyError(stage)

    assert workers_for(Client(), "claim_extract") == 8
    assert workers_for(Client(), "claim_extract", cap=4) == 4
    assert workers_for(ClientWithoutProfiles(), "claim_extract") == 1


def test_a_failure_cancels_the_calls_still_queued():
    """[33] During a Vertex 429 outage the first failed call used to let every queued call run
    its own retry ladder anyway (`with ThreadPoolExecutor` waits for all submitted work)."""
    import threading
    import time as _t
    started = []
    lock = threading.Lock()

    def fn(i):
        with lock:
            started.append(i)
        if i == 0:
            raise RuntimeError("429")
        _t.sleep(0.05)
        return i

    import pytest
    with pytest.raises(RuntimeError):
        map_calls(fn, list(range(50)), workers=2)
    assert len(started) < 10, f"{len(started)} calls started after the first failure"
