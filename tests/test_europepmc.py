"""Unit tests for europepmc.py: validation, identifier parsing, record parsing, and the HTTP
client against offline fixtures. These do NOT import the MCP SDK."""

from __future__ import annotations

import httpx
import pytest
from conftest import json_response, load_fixture, single_record

from europepmc import (
    ArticleNotFoundError,
    EuropePMCError,
    InvalidInputError,
    clean_markup,
    identifier_to_query,
    parse_record,
    validate_max_results,
    validate_query,
)


@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        ("12345678", "EXT_ID:12345678 AND SRC:MED"),
        (" 12345678 ", "EXT_ID:12345678 AND SRC:MED"),
        ("MED:12345678", "EXT_ID:12345678 AND SRC:MED"),
        ("med/12345678", "EXT_ID:12345678 AND SRC:MED"),
        ("PMC1234567", "PMCID:PMC1234567"),
        ("pmc1234567", "PMCID:PMC1234567"),
        ("PMC:PMC1234567", "PMCID:PMC1234567"),
        ("PPR123456", "EXT_ID:PPR123456 AND SRC:PPR"),
        ("PPR:PPR123456", "EXT_ID:PPR123456 AND SRC:PPR"),
        ("10.1038/s41586-020-1234-5", 'DOI:"10.1038/s41586-020-1234-5"'),
        ("doi:10.1038/abc.", 'DOI:"10.1038/abc"'),
        ("https://doi.org/10.1126/science.abc123", 'DOI:"10.1126/science.abc123"'),
        ("https://europepmc.org/article/MED/12345678", "EXT_ID:12345678 AND SRC:MED"),
    ],
)
def test_identifier_to_query(identifier, expected):
    assert identifier_to_query(identifier) == expected


@pytest.mark.parametrize("bad", ["", "   ", "some paper about T cells", "XYZ:123", 'MED:1" OR "x'])
def test_identifier_to_query_rejects(bad):
    with pytest.raises(InvalidInputError):
        identifier_to_query(bad)


def test_validate_query_normalises_whitespace():
    assert validate_query("  TCR \n clonotype  ") == "TCR clonotype"


@pytest.mark.parametrize("bad", ["", "   ", "x" * 501])
def test_validate_query_rejects(bad):
    with pytest.raises(InvalidInputError):
        validate_query(bad)


@pytest.mark.parametrize("bad", [0, 21, -1, True, 2.5])
def test_validate_max_results_rejects(bad):
    with pytest.raises(InvalidInputError):
        validate_max_results(bad)


def test_clean_markup():
    assert clean_markup("<h4>Methods</h4>We used <sup>51</sup>Cr &lt;release&gt;.") == "Methods We used 51Cr <release>."
    assert clean_markup("") is None
    assert clean_markup(None) is None


def test_parse_record_handles_missing_optional_fields():
    rec = parse_record({"source": "MED", "id": "1"})
    assert rec.europepmc_id == "MED:1"
    assert rec.title is None and rec.abstract is None and rec.doi is None
    assert rec.article_types == []
    assert rec.review_in_metadata is False
    assert rec.links.europepmc == "https://europepmc.org/article/MED/1"
    assert rec.links.doi is None


def test_parse_record_full_text_links_are_reported_not_fetched():
    raw = load_fixture("search_results.json")["resultList"]["result"][0]
    rec = parse_record(raw)
    assert rec.open_access is True
    assert rec.cited_by_count == 12
    assert rec.links.full_text[0].url == "https://europepmc.org/articles/PMC9900001"
    assert rec.links.full_text[0].availability == "Open access"


# --------------------------------------------------------------------------- #
# API client against offline fixtures (httpx.MockTransport; no MCP SDK needed)
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_client_search_normal_results(fake_europepmc, requests_seen):
    result = await fake_europepmc(json_response("search_results.json")).search("TCR clonotype persistence", 3)

    assert result.total_hits == 137 and result.returned == 3
    primary, review, preprint = result.results
    for rec in result.results:
        assert rec.europepmc_id and rec.links.europepmc.startswith("https://europepmc.org/article/")
        assert rec.doi and rec.links.doi == f"https://doi.org/{rec.doi}"
    assert primary.europepmc_id == "MED:99000001"
    assert primary.pmid == "99000001" and primary.pmcid == "PMC9900001"
    assert primary.links.pubmed == "https://pubmed.ncbi.nlm.nih.gov/99000001/"
    assert primary.publication_date == "2024-03-01"
    assert primary.article_types == ["research-article", "Journal Article"]
    assert primary.review_in_metadata is False
    assert "<i>" not in primary.abstract and "&amp;" not in primary.abstract
    assert "persistence correlated with response" in primary.abstract
    assert review.review_in_metadata is True and review.abstract_truncated is True
    assert preprint.preprint is True and preprint.abstract is None

    sent = requests_seen[0]
    assert sent.url.path.endswith("/search")
    assert sent.url.params["pageSize"] == "3"
    assert sent.url.params["resultType"] == "core"
    assert sent.url.params["format"] == "json"


@pytest.mark.anyio
async def test_client_search_no_results(fake_europepmc):
    result = await fake_europepmc(json_response("no_results.json")).search("zzqx nonexistent", 5)
    assert result.total_hits == 0 and result.results == []
    assert "not evidence that no such studies exist" in result.note


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("handler", "expected"),
    [
        (lambda r: httpx.Response(503, text="Service Unavailable"), "server error (HTTP 503)"),
        (lambda r: httpx.Response(429), "rate-limiting"),
        (lambda r: httpx.Response(400, text="bad"), "rejected the request (HTTP 400)"),
        (lambda r: httpx.Response(200, text="<html>not json</html>"), "not valid JSON"),
        (lambda r: httpx.Response(200, json={"errMsg": "syntax error"}), "reported an error"),
    ],
    ids=["http-503", "http-429", "http-400", "bad-json", "errMsg"],
)
async def test_client_api_failures(fake_europepmc, handler, expected):
    with pytest.raises(EuropePMCError, match=expected.replace("(", r"\(").replace(")", r"\)")):
        await fake_europepmc(handler).search("CAR-T persistence", 5)


@pytest.mark.anyio
async def test_client_timeout_and_connection_error(fake_europepmc):
    def timeout(request):
        raise httpx.ReadTimeout("simulated", request=request)

    def down(request):
        raise httpx.ConnectError("simulated", request=request)

    with pytest.raises(EuropePMCError, match="did not respond within"):
        await fake_europepmc(timeout).search("x", 1)
    with pytest.raises(EuropePMCError, match="Could not connect"):
        await fake_europepmc(down).get_article("10.5555/fixture.1")


@pytest.mark.anyio
async def test_client_validation_happens_before_any_request(fake_europepmc, requests_seen):
    client = fake_europepmc(json_response("search_results.json"))
    for call in (client.search("   ", 5), client.search("ok", 500), client.get_article("the CAR-T paper")):
        with pytest.raises(InvalidInputError):
            await call
    assert requests_seen == []


@pytest.mark.anyio
async def test_client_get_article_full_abstract_and_note(fake_europepmc, requests_seen):
    result = await fake_europepmc(single_record(1)).get_article("99000002")
    assert requests_seen[0].url.params["query"] == "EXT_ID:99000002 AND SRC:MED"
    assert result.article.europepmc_id == "MED:99000002"
    assert result.article.abstract_truncated is False and len(result.article.abstract) > 1500
    assert result.full_text_retrieved is False
    assert "Full text was NOT retrieved" in result.full_text_note
    assert result.abstract_available is True


@pytest.mark.anyio
async def test_client_get_article_without_abstract(fake_europepmc):
    result = await fake_europepmc(single_record(2)).get_article("PPR:PPR990003")
    assert result.abstract_available is False
    assert "no abstract" in result.full_text_note


@pytest.mark.anyio
async def test_client_get_article_not_found(fake_europepmc):
    with pytest.raises(ArticleNotFoundError, match="No Europe PMC record matched"):
        await fake_europepmc(json_response("no_results.json")).get_article("PMC0000001")
