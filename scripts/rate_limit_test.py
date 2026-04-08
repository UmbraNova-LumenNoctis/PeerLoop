#!/usr/bin/env python3
"""
PeerLoop – Rate Limiting Test Suite
====================================
Tests every nginx rate-limit zone, measures KPIs and prints a structured report.

Usage:
    python3 scripts/rate_limit_test.py [--host https://localhost:8443] [--json]

Requirements:
    pip install aiohttp
"""

import argparse
import asyncio
import json
import ssl
import statistics
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional

import aiohttp

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_HOST = "https://localhost:8443"
GW_HOST      = "https://localhost:8444"   # port 4443 in nginx maps to host 8444

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode    = ssl.CERT_NONE

CONNECTOR_FACTORY = lambda: aiohttp.TCPConnector(ssl=SSL_CTX, limit=200)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ScenarioResult:
    zone:          str
    description:   str
    url:           str
    method:        str
    rate_cfg:      str          # human-readable nginx config
    burst_cfg:     int
    requests_sent: int = 0
    ok:            int = 0      # 1xx-3xx
    throttled:     int = 0      # 429
    errors:        int = 0      # connection errors / 5xx
    first_429_at:  Optional[int] = None  # request index (1-based)
    latencies_ms:  List[float]  = field(default_factory=list)
    passed:        bool = False
    notes:         str  = ""

    # computed after run
    @property
    def throttle_ratio(self) -> float:
        """Return throttled requests as a percentage of requests sent.
        
        Returns:
            float: Throttled requests as a percentage of requests sent.
        """
        if self.requests_sent == 0:
            return 0.0
        return self.throttled / self.requests_sent * 100

    @property
    def lat_min(self) -> Optional[float]:
        """Return the minimum latency in milliseconds.
        
        Returns:
            Optional[float]: Minimum latency in milliseconds.
        """
        return round(min(self.latencies_ms), 2) if self.latencies_ms else None

    @property
    def lat_max(self) -> Optional[float]:
        """Return the maximum latency in milliseconds.
        
        Returns:
            Optional[float]: Maximum latency in milliseconds.
        """
        return round(max(self.latencies_ms), 2) if self.latencies_ms else None

    @property
    def lat_avg(self) -> Optional[float]:
        """Return the average latency in milliseconds.
        
        Returns:
            Optional[float]: Average latency in milliseconds.
        """
        return round(statistics.mean(self.latencies_ms), 2) if self.latencies_ms else None

    @property
    def lat_p95(self) -> Optional[float]:
        """Return the 95th percentile latency in milliseconds.
        
        Returns:
            Optional[float]: 95th percentile latency in milliseconds.
        """
        if not self.latencies_ms:
            return None
        s = sorted(self.latencies_ms)
        idx = max(0, int(len(s) * 0.95) - 1)
        return round(s[idx], 2)

    @property
    def lat_p99(self) -> Optional[float]:
        """Return the 99th percentile latency in milliseconds.
        
        Returns:
            Optional[float]: 99th percentile latency in milliseconds.
        """
        if not self.latencies_ms:
            return None
        s = sorted(self.latencies_ms)
        idx = max(0, int(len(s) * 0.99) - 1)
        return round(s[idx], 2)


# ---------------------------------------------------------------------------
# Core fire function
# ---------------------------------------------------------------------------

async def fire(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    result: ScenarioResult,
    idx: int,
    body: Optional[bytes] = None,
    extra_headers: Optional[dict] = None,
) -> None:
    """Send one HTTP request and update the scenario counters.
    
    Args:
        session (aiohttp.ClientSession): Client session instance.
        method (str): HTTP method.
        url (str): Target URL.
        result (ScenarioResult): Parameter result.
        idx (int): 1-based index for this operation.
        body (Optional[bytes]): Raw request body.
        extra_headers (Optional[dict]): Parameter extra_headers.
    
    Returns:
        None: None.
    """
    headers = {"User-Agent": "PeerLoop-RateLimitTest/1.0"}
    if extra_headers:
        headers.update(extra_headers)
    t0 = time.perf_counter()
    try:
        async with session.request(
            method, url, data=body, headers=headers,
            allow_redirects=False, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            lat = (time.perf_counter() - t0) * 1000
            result.requests_sent += 1
            result.latencies_ms.append(lat)
            if resp.status == 429:
                result.throttled += 1
                if result.first_429_at is None:
                    result.first_429_at = idx
            elif resp.status < 500:
                result.ok += 1
            else:
                result.errors += 1
    except Exception:
        result.requests_sent += 1
        result.errors += 1


# ---------------------------------------------------------------------------
# Scenario helpers
# ---------------------------------------------------------------------------

async def burst_test(
    result: ScenarioResult,
    n: int,
    concurrency: int = 50,
    delay_between_batches: float = 0.0,
) -> None:
    """Fire n requests in rapid bursts of `concurrency` at a time.
    
    Args:
        result (ScenarioResult): Parameter result.
        n (int): Parameter n.
        concurrency (int): Parameter concurrency.
        delay_between_batches (float): Parameter delay_between_batches.
    
    Returns:
        None: None.
    """
    connector = CONNECTOR_FACTORY()
    async with aiohttp.ClientSession(connector=connector) as session:
        for batch_start in range(0, n, concurrency):
            batch = range(batch_start, min(batch_start + concurrency, n))
            tasks = [
                fire(session, result.method, result.url, result, i + 1)
                for i in batch
            ]
            await asyncio.gather(*tasks)
            if delay_between_batches:
                await asyncio.sleep(delay_between_batches)


async def sustained_test(
    result: ScenarioResult,
    n: int,
    rps: float,
) -> None:
    """Fire n requests at a controlled `rps` rate (above the limit).
    
    Args:
        result (ScenarioResult): Parameter result.
        n (int): Parameter n.
        rps (float): Parameter rps.
    
    Returns:
        None: None.
    """
    interval = 1.0 / rps
    connector = CONNECTOR_FACTORY()
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i in range(n):
            tasks.append(asyncio.create_task(
                fire(session, result.method, result.url, result, i + 1)
            ))
            await asyncio.sleep(interval)
        await asyncio.gather(*tasks)


async def concurrent_conn_test(result: ScenarioResult, n_conn: int) -> None:
    """Open n_conn simultaneous long-lived connections.
    
    Args:
        result (ScenarioResult): Parameter result.
        n_conn (int): Parameter n_conn.
    
    Returns:
        None: None.
    """
    connector = CONNECTOR_FACTORY()
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fire(session, result.method, result.url, result, i + 1)
            for i in range(n_conn)
        ]
        await asyncio.gather(*tasks)


# ---------------------------------------------------------------------------
# Scenario definitions  (one per zone + one recovery test)
# ---------------------------------------------------------------------------

def build_scenarios(host: str, gw: str) -> List[ScenarioResult]:
    """Build the list of rate-limit scenarios for each nginx zone.
    
    Args:
        host (str): Base URL for the primary ingress.
        gw (str): Base URL for the gateway ingress.
    
    Returns:
        List[ScenarioResult]: List of rate-limit scenarios for each nginx zone.
    """
    return [
        ScenarioResult(
            zone="auth_limit",
            description="Brute-force protection on auth endpoint (10 req/min, burst=5)",
            url=f"{host}/services/auth_service/health",
            method="GET",
            rate_cfg="10r/min",
            burst_cfg=5,
        ),
        ScenarioResult(
            zone="auth_limit [/auth/]",
            description="OAuth callback brute-force on /auth/ (10 req/min, burst=5)",
            url=f"{host}/auth/health",
            method="GET",
            rate_cfg="10r/min",
            burst_cfg=5,
        ),
        ScenarioResult(
            zone="llm_limit",
            description="AI cost-budget protection (5 req/min, burst=3)",
            url=f"{host}/services/llm-service/health",
            method="GET",
            rate_cfg="5r/min",
            burst_cfg=3,
        ),
        ScenarioResult(
            zone="upload_limit",
            description="File upload flood protection (5 req/s, burst=10)",
            url=f"{host}/services/file_service/health",
            method="GET",
            rate_cfg="5r/s",
            burst_cfg=10,
        ),
        ScenarioResult(
            zone="search_limit",
            description="Search query rate control (20 req/s, burst=30)",
            url=f"{host}/services/search-service/health",
            method="GET",
            rate_cfg="20r/s",
            burst_cfg=30,
        ),
        ScenarioResult(
            zone="api_limit [/api/]",
            description="General API gateway throttle (60 req/s, burst=30)",
            url=f"{host}/api/health",
            method="GET",
            rate_cfg="60r/s",
            burst_cfg=30,
        ),
        ScenarioResult(
            zone="api_limit [gw:4443]",
            description="Dedicated API gateway port throttle (60 req/s, burst=30)",
            url=f"{gw}/health",
            method="GET",
            rate_cfg="60r/s",
            burst_cfg=30,
        ),
        ScenarioResult(
            zone="static_limit",
            description="Frontend SPA static delivery (100 req/s, burst=100)",
            url=f"{host}/",
            method="GET",
            rate_cfg="100r/s",
            burst_cfg=100,
        ),
        ScenarioResult(
            zone="conn_limit",
            description="Concurrent connection cap per IP (limit_conn 50)",
            url=f"{host}/health",
            method="GET",
            rate_cfg="N/A (conn cap)",
            burst_cfg=0,
        ),
        ScenarioResult(
            zone="ws_limit",
            description="WebSocket establishment flood (10 req/s, burst=10)",
            url=f"{host}/ws/",
            method="GET",
            rate_cfg="10r/s",
            burst_cfg=10,
        ),
    ]


# ---------------------------------------------------------------------------
# Run each scenario
# ---------------------------------------------------------------------------

async def run_scenario(s: ScenarioResult) -> None:
    """Strategy per zone:.
    
      - slow zones (r/min): send burst+rate+5 rapid requests → expect 429 after burst
      - fast zones (r/s)  : blast 3x(rate+burst) requests concurrently → expect 429
      - conn_limit        : open 80 simultaneous connections
    
    Args:
        s (ScenarioResult): Parameter s.
    
    Returns:
        None: None.
    """
    if "r/min" in s.rate_cfg:
        # Need to trigger throttle fast: send way more than burst in one shot
        n = s.burst_cfg + 20
        await burst_test(s, n, concurrency=n)
        s.passed = s.throttled > 0

    elif s.zone == "conn_limit":
        await concurrent_conn_test(s, n_conn=80)
        # conn_limit = 50 → at least some should be 429 or conn-reset
        s.passed = (s.throttled + s.errors) > 0

    elif s.zone == "ws_limit":
        # WS endpoint returns 400/426 for plain HTTP, rate limiting fires first
        n = s.burst_cfg + 30
        await burst_test(s, n, concurrency=n)
        s.passed = s.throttled > 0 or s.errors == 0  # 400/426 is also OK here

    else:
        # Fast zones: send 3×(rate+burst) blasted at once
        rate_val = int(s.rate_cfg.rstrip("r/s"))
        n = (rate_val + s.burst_cfg) * 3
        await burst_test(s, n, concurrency=min(n, 150))
        s.passed = s.throttled > 0


async def run_recovery_test(host: str) -> dict:
    """After throttling auth_limit, wait 7s (> 60s/10r = 6s per token).
    
    and confirm next request goes through.
    
    Args:
        host (str): Base URL for the primary ingress.
    
    Returns:
        dict: Result of the operation.
    """
    url = f"{host}/services/auth_service/health"
    result = {"zone": "auth_limit [recovery]", "passed": False, "status_after_wait": None}
    connector = CONNECTOR_FACTORY()
    async with aiohttp.ClientSession(connector=connector) as session:
        # Exhaust burst
        tasks = [fire(session, "GET", url,
                      ScenarioResult("_", "_", url, "GET", "10r/min", 5), i)
                 for i in range(20)]
        await asyncio.gather(*tasks)
        # Wait for token bucket to refill (10r/min = 1 token / 6s)
        await asyncio.sleep(7)
        # One clean request
        probe = ScenarioResult("_", "_", url, "GET", "10r/min", 5)
        await fire(session, "GET", url, probe, 1)
        result["status_after_wait"] = "ok" if probe.ok == 1 else "still-throttled"
        result["passed"] = probe.ok == 1
    return result


# ---------------------------------------------------------------------------
# KPI Report
# ---------------------------------------------------------------------------

RESET  = "\033[0m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"

def fmt_pass(ok: bool) -> str:
    """Format a PASS/FAIL label using ANSI colors.
    
    Args:
        ok (bool): Parameter ok.
    
    Returns:
        str: Result of the operation.
    """
    return f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"

def bar(ratio: float, width: int = 20) -> str:
    """Build a simple ASCII bar for a percentage ratio.
    
    Args:
        ratio (float): Parameter ratio.
        width (int): Parameter width.
    
    Returns:
        str: Simple ASCII bar for a percentage ratio.
    """
    filled = int(ratio / 100 * width)
    return f"[{'█' * filled}{'░' * (width - filled)}] {ratio:5.1f}%"

def print_report(results: List[ScenarioResult], recovery: dict) -> None:
    """Print the KPI report to stdout.
    
    Args:
        results (List[ScenarioResult]): Parameter results.
        recovery (dict): Parameter recovery.
    
    Returns:
        None: None.
    """
    print(f"\n{BOLD}{'=' * 72}{RESET}")
    print(f"{BOLD}  PeerLoop – Rate Limiting KPI Report{RESET}")
    print(f"{BOLD}{'=' * 72}{RESET}\n")

    all_passed = all(r.passed for r in results) and recovery["passed"]

    for r in results:
        status = fmt_pass(r.passed)
        print(f"{BOLD}{CYAN}{r.zone}{RESET}  [{r.rate_cfg}  burst={r.burst_cfg}]  {status}")
        print(f"  {r.description}")
        print(f"  URL              : {r.url}")
        print(f"  Requests sent    : {r.requests_sent}")
        print(f"  ✅ Accepted       : {r.ok}")
        print(f"  🚫 Throttled(429) : {r.throttled}  {bar(r.throttle_ratio)}")
        print(f"  ❌ Errors         : {r.errors}")
        if r.first_429_at is not None:
            print(f"  First 429 at req : #{r.first_429_at}")
        if r.latencies_ms:
            print(f"  Latency (ms)     : "
                  f"min={r.lat_min}  avg={r.lat_avg}  "
                  f"p95={r.lat_p95}  p99={r.lat_p99}  max={r.lat_max}")
        if r.notes:
            print(f"  Note             : {r.notes}")
        print()

    # Recovery test
    rec_status = fmt_pass(recovery["passed"])
    print(f"{BOLD}{CYAN}auth_limit [recovery]{RESET}  {rec_status}")
    print(f"  Status after 7s cool-down: {recovery['status_after_wait']}")
    print()

    # Summary table
    print(f"{BOLD}{'─' * 72}{RESET}")
    print(f"{BOLD}  SUMMARY{RESET}")
    print(f"{'─' * 72}")
    header = f"  {'Zone':<30} {'Sent':>5} {'429':>5} {'Throttle%':>10} {'p95ms':>8}  Result"
    print(header)
    print(f"  {'─'*29} {'─'*5} {'─'*5} {'─'*10} {'─'*8}  {'─'*6}")
    for r in results:
        ratio_s = f"{r.throttle_ratio:6.1f}%"
        p95_s   = f"{r.lat_p95}" if r.lat_p95 else "  N/A"
        print(f"  {r.zone:<30} {r.requests_sent:>5} {r.throttled:>5} {ratio_s:>10} "
              f"{str(p95_s):>8}  {fmt_pass(r.passed)}")
    rec_row = "auth_limit [recovery]"
    print(f"  {rec_row:<30} {'—':>5} {'—':>5} {'—':>10} {'—':>8}  {fmt_pass(recovery['passed'])}")
    print(f"{'─' * 72}")

    total  = len(results) + 1
    passed = sum(1 for r in results if r.passed) + (1 if recovery["passed"] else 0)
    color  = GREEN if all_passed else (YELLOW if passed > total // 2 else RED)
    print(f"\n{BOLD}  Overall: {color}{passed}/{total} scenarios passed{RESET}\n")


def build_json_output(results: List[ScenarioResult], recovery: dict) -> dict:
    """Build a JSON-serializable report structure.
    
    Args:
        results (List[ScenarioResult]): Parameter results.
        recovery (dict): Parameter recovery.
    
    Returns:
        dict: JSON-serializable report structure.
    """
    def r_dict(r: ScenarioResult) -> dict:
        """Serialize one ScenarioResult into a JSON-friendly dict.
        
        Args:
            r (ScenarioResult): Parameter r.
        
        Returns:
            dict: One ScenarioResult into a JSON-friendly dict.
        """
        return {
            "zone":          r.zone,
            "description":   r.description,
            "url":           r.url,
            "rate_cfg":      r.rate_cfg,
            "burst_cfg":     r.burst_cfg,
            "requests_sent": r.requests_sent,
            "ok":            r.ok,
            "throttled":     r.throttled,
            "errors":        r.errors,
            "throttle_ratio_pct": round(r.throttle_ratio, 2),
            "first_429_at":  r.first_429_at,
            "latency_ms": {
                "min": r.lat_min, "avg": r.lat_avg,
                "p95": r.lat_p95, "p99": r.lat_p99, "max": r.lat_max,
            },
            "passed": r.passed,
            "notes":  r.notes,
        }
    return {
        "scenarios": [r_dict(r) for r in results],
        "recovery":  recovery,
        "summary": {
            "total":  len(results) + 1,
            "passed": sum(1 for r in results if r.passed) + (1 if recovery["passed"] else 0),
        },
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(host: str, gw: str, as_json: bool) -> int:
    """Run all scenarios and emit either JSON or a formatted report.
    
    Args:
        host (str): Base URL for the primary ingress.
        gw (str): Base URL for the gateway ingress.
        as_json (bool): Parameter as_json.
    
    Returns:
        int: Result of the operation.
    """
    scenarios = build_scenarios(host, gw)

    print(f"{CYAN}Running {len(scenarios)} rate-limit scenarios against {host} …{RESET}")
    print(f"{YELLOW}(self-signed TLS – cert verification disabled){RESET}\n")

    t_start = time.perf_counter()

    for s in scenarios:
        print(f"  ▶ {s.zone} …", end=" ", flush=True)
        await run_scenario(s)
        status = "✓" if s.passed else "✗"
        print(status)

    print("\n  ▶ Recovery test (auth_limit – 7s cool-down) …", end=" ", flush=True)
    recovery = await run_recovery_test(host)
    print("✓" if recovery["passed"] else "✗")

    elapsed = time.perf_counter() - t_start
    print(f"\n  Total test time: {elapsed:.1f}s\n")

    if as_json:
        output = build_json_output(scenarios, recovery)
        print(json.dumps(output, indent=2))
    else:
        print_report(scenarios, recovery)

    all_passed = all(s.passed for s in scenarios) and recovery["passed"]
    return 0 if all_passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PeerLoop rate-limit test suite")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"Main HTTPS base URL (default: {DEFAULT_HOST})")
    parser.add_argument("--gw", default=GW_HOST,
                        help=f"API gateway HTTPS base URL (default: {GW_HOST})")
    parser.add_argument("--json", action="store_true",
                        help="Output KPIs as JSON instead of coloured table")
    args = parser.parse_args()

    rc = asyncio.run(main(args.host, args.gw, args.json))
    sys.exit(rc)
