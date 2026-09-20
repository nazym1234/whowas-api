from __future__ import annotations

import time
from collections import Counter


class Metrics:
    def __init__(self) -> None:
        self.started_at = time.monotonic()
        self.counters: Counter[str] = Counter()
        self.request_duration_sum = 0.0

    def increment(self, name: str, amount: int = 1) -> None:
        self.counters[name] += amount

    def observe_request(self, duration: float) -> None:
        self.counters["requests_total"] += 1
        self.request_duration_sum += duration

    def render(self) -> str:
        lines = [
            "# HELP whowas_requests_total Total HTTP requests.",
            "# TYPE whowas_requests_total counter",
            f"whowas_requests_total {self.counters['requests_total']}",
            "# HELP whowas_request_duration_seconds_sum Total request duration.",
            "# TYPE whowas_request_duration_seconds_sum counter",
            f"whowas_request_duration_seconds_sum {self.request_duration_sum:.6f}",
        ]
        for name in (
            "wikidata_requests_total",
            "wikipedia_requests_total",
            "upstream_errors_total",
            "cache_hits_total",
            "cache_misses_total",
            "rate_limited_total",
        ):
            metric = f"whowas_{name}"
            lines.extend(
                [
                    f"# TYPE {metric} counter",
                    f"{metric} {self.counters[name]}",
                ]
            )
        return "\n".join(lines) + "\n"


metrics = Metrics()
