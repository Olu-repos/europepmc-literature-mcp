"""Shared test helpers. No test touches the network: Europe PMC is replaced by httpx.MockTransport.

The JSON fixtures are SYNTHETIC. Their identifiers (PMID 990000xx, DOI prefix 10.5555)
are deliberately fake so they can never be mistaken for real papers.

This file must not import the MCP SDK: the unit tests in test_europepmc.py run without it.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from europepmc import EuropePMCClient  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def json_response(name: str, status: int = 200) -> Callable[[httpx.Request], httpx.Response]:
    return lambda request: httpx.Response(status, json=load_fixture(name))


def single_record(index: int) -> Callable[[httpx.Request], httpx.Response]:
    """Respond with one record from search_results.json, as Europe PMC does for an ID lookup."""

    def handler(request: httpx.Request) -> httpx.Response:
        data = load_fixture("search_results.json")
        data["resultList"]["result"] = [data["resultList"]["result"][index]]
        data["hitCount"] = 1
        return httpx.Response(200, json=data)

    return handler


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def requests_seen() -> list[httpx.Request]:
    return []


@pytest.fixture
def fake_europepmc(requests_seen: list[httpx.Request]):
    """Factory: handler (Request -> Response, or raise) -> EuropePMCClient backed by it."""

    def build(handler: Callable[[httpx.Request], httpx.Response]) -> EuropePMCClient:
        def recording(request: httpx.Request) -> httpx.Response:
            requests_seen.append(request)
            return handler(request)

        return EuropePMCClient(transport=httpx.MockTransport(recording), timeout=2.0)

    return build
