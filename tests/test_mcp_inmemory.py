"""MCP integration tests: the SDK's in-memory Client talks to the real server object.

Europe PMC is mocked, so these need no network, but they DO need the pinned MCP SDK
(mcp==2.2.0, see pyproject.toml) and its dependencies properly installed, e.g. via `uv sync`.

If that SDK is not installed the whole module is skipped, unless REQUIRE_MCP=1 is set
(scripts/verify_local.py sets it), in which case the missing SDK is a test failure.

Covers, per tool: normal results, no results, API failure, and input rejection.
"""

from __future__ import annotations

import importlib.metadata
import os

import httpx
import pytest
from conftest import json_response, single_record

PINNED_MCP_VERSION = "2.2.0"


def _installed_mcp_version() -> str | None:
    try:
        return importlib.metadata.version("mcp")
    except importlib.metadata.PackageNotFoundError:
        return None


_installed = _installed_mcp_version()
if _installed != PINNED_MCP_VERSION:
    reason = f"MCP SDK {PINNED_MCP_VERSION} not installed (found: {_installed}); run `uv sync`."
    if os.environ.get("REQUIRE_MCP") == "1":
        pytest.fail(reason, pytrace=False)
    pytest.skip(reason, allow_module_level=True)

from mcp import Client  # noqa: E402

import server  # noqa: E402

pytestmark = [pytest.mark.anyio, pytest.mark.mcp_integration]


@pytest.fixture
def use_europepmc(monkeypatch: pytest.MonkeyPatch, fake_europepmc):
    """Swap the server's Europe PMC client for one backed by a mock handler."""

    def install(handler):
        monkeypatch.setattr(server, "client", fake_europepmc(handler))

    return install


@pytest.fixture
async def client():
    async with Client(server.mcp, raise_exceptions=True) as c:
        yield c


def error_text(result) -> str:
    return " ".join(getattr(c, "text", "") for c in result.content)


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #


async def test_exposes_exactly_two_read_only_tools(client):
    listed = await client.list_tools()
    tools = {t.name: t for t in listed.tools}
    assert set(tools) == {"search_literature", "get_article"}
    for tool in tools.values():
        assert tool.annotations is not None and tool.annotations.read_only_hint is True
    props = tools["search_literature"].input_schema["properties"]
    assert props["max_results"]["minimum"] == 1
    assert props["max_results"]["maximum"] == 20


# --------------------------------------------------------------------------- #
# search_literature
# --------------------------------------------------------------------------- #


async def test_search_normal_results(client, use_europepmc):
    use_europepmc(json_response("search_results.json"))

    result = await client.call_tool("search_literature", {"query": "TCR clonotype persistence", "max_results": 3})

    assert result.is_error is False
    data = result.structured_content
    assert data["total_hits"] == 137 and data["returned"] == 3
    ids = [r["europepmc_id"] for r in data["results"]]
    assert ids == ["MED:99000001", "MED:99000002", "PPR:PPR990003"]
    for rec in data["results"]:
        assert rec["links"]["europepmc"] and rec["doi"]


async def test_search_no_results_is_not_an_error(client, use_europepmc):
    use_europepmc(json_response("no_results.json"))

    result = await client.call_tool("search_literature", {"query": "zzqx nonexistent clonotype"})

    assert result.is_error is False
    assert result.structured_content["results"] == []
    assert "not evidence that no such studies exist" in result.structured_content["note"]


async def test_search_api_failure_is_a_tool_error(client, use_europepmc):
    use_europepmc(lambda r: httpx.Response(503, text="Service Unavailable"))

    result = await client.call_tool("search_literature", {"query": "CAR-T persistence"})

    assert result.is_error is True
    assert result.structured_content is None
    assert "server error (HTTP 503)" in error_text(result)


async def test_search_schema_rejects_out_of_range_limit(client, use_europepmc, requests_seen):
    use_europepmc(json_response("search_results.json"))

    result = await client.call_tool("search_literature", {"query": "T cells", "max_results": 500})

    assert result.is_error is True
    assert requests_seen == []


# --------------------------------------------------------------------------- #
# get_article
# --------------------------------------------------------------------------- #


async def test_get_article_normal_result(client, use_europepmc):
    use_europepmc(single_record(1))

    result = await client.call_tool("get_article", {"identifier": "MED:99000002"})

    assert result.is_error is False
    data = result.structured_content
    assert data["article"]["europepmc_id"] == "MED:99000002"
    assert data["full_text_retrieved"] is False
    assert "Full text was NOT retrieved" in data["full_text_note"]


async def test_get_article_not_found_is_a_tool_error(client, use_europepmc):
    use_europepmc(json_response("no_results.json"))

    result = await client.call_tool("get_article", {"identifier": "PMC0000001"})

    assert result.is_error is True
    assert "No Europe PMC record matched" in error_text(result)


async def test_get_article_api_failure_is_a_tool_error(client, use_europepmc):
    def down(request):
        raise httpx.ConnectError("simulated", request=request)

    use_europepmc(down)
    result = await client.call_tool("get_article", {"identifier": "10.5555/fixture.1"})

    assert result.is_error is True
    assert "Could not connect to Europe PMC" in error_text(result)


async def test_get_article_rejects_free_text(client, use_europepmc, requests_seen):
    use_europepmc(json_response("search_results.json"))

    result = await client.call_tool("get_article", {"identifier": "the CAR-T paper from last year"})

    assert result.is_error is True
    assert "Could not recognise" in error_text(result)
    assert requests_seen == []
