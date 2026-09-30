"""Europe PMC Articles REST API client.

This module only *retrieves and structures* publication records. It never
summarises, ranks by importance, or draws scientific conclusions: that is the
job of the model reading the records. Every record it returns carries its
source identifiers (source/id, PMID, PMCID, DOI) and links so any claim built
on it can be traced back.

API documentation: https://europepmc.org/RestfulWebService
"""

from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import quote, urlencode

import httpx
from pydantic import BaseModel, Field

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_MAX_RESULTS = 5
MAX_RESULTS_LIMIT = 20
MAX_QUERY_LENGTH = 500
SEARCH_ABSTRACT_CHAR_LIMIT = 1500
USER_AGENT = "europepmc-literature-mcp/0.1 (read-only research tool)"

# Europe PMC source codes, see https://europepmc.org/Help#contentsources
KNOWN_SOURCES = {"MED", "PMC", "PPR", "AGR", "CBA", "CTX", "ETH", "HIR", "NBK", "PAT"}

FULL_TEXT_NOT_RETRIEVED = (
    "Full text was NOT retrieved. This record contains bibliographic metadata and the "
    "abstract only. Methods, results, figures, limitations and conflicts of interest that "
    "are not stated in the abstract cannot be verified from this record."
)


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #


class InvalidInputError(ValueError):
    """The caller supplied a query or identifier we will not send upstream."""


class EuropePMCError(RuntimeError):
    """Europe PMC could not be reached or returned something unusable."""


class ArticleNotFoundError(LookupError):
    """A well-formed identifier matched no Europe PMC record."""


# --------------------------------------------------------------------------- #
# Output models (these become the tools' structured output schemas)
# --------------------------------------------------------------------------- #


class FullTextLink(BaseModel):
    url: str
    availability: str | None = Field(None, description="e.g. 'Open access', 'Subscription required'.")
    document_style: str | None = Field(None, description="e.g. 'html', 'pdf', 'doi'.")
    site: str | None = None


class SourceLinks(BaseModel):
    europepmc: str = Field(description="Europe PMC landing page for this record.")
    doi: str | None = None
    pubmed: str | None = None
    pmc: str | None = None
    full_text: list[FullTextLink] = Field(
        default_factory=list, description="Full-text locations reported by Europe PMC (not fetched)."
    )


class ArticleRecord(BaseModel):
    """One Europe PMC record, as reported by Europe PMC. No interpretation added."""

    europepmc_id: str = Field(description="Identifier to pass to get_article, formatted SOURCE:ID (e.g. MED:12345678).")
    source: str = Field(description="Europe PMC source code: MED=PubMed, PMC=PubMed Central, PPR=preprint, etc.")
    id: str
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    title: str | None = None
    authors: str | None = None
    journal: str | None = None
    publication_date: str | None = Field(None, description="First publication date reported by Europe PMC.")
    publication_year: str | None = None
    article_types: list[str] = Field(
        default_factory=list, description="Publication types exactly as listed in Europe PMC metadata."
    )
    review_in_metadata: bool = Field(
        description="True if any listed publication type contains 'review'. Metadata only; not a judgement "
        "about study design. A False value does NOT prove the paper is primary research."
    )
    preprint: bool = Field(description="True if Europe PMC lists this as a preprint (not peer reviewed).")
    open_access: bool | None = None
    cited_by_count: int | None = None
    abstract: str | None = Field(None, description="Abstract text with HTML markup removed. None if Europe PMC has none.")
    abstract_truncated: bool = False
    links: SourceLinks


class SearchResult(BaseModel):
    query: str
    total_hits: int = Field(description="Total records Europe PMC matched (only the first few are returned).")
    returned: int
    results: list[ArticleRecord]
    europepmc_search_url: str = Field(description="Same query on the Europe PMC website, for human checking.")
    note: str


class ArticleResult(BaseModel):
    requested_identifier: str
    article: ArticleRecord
    full_text_retrieved: bool = Field(
        description="Always False in this version: only metadata and abstract are retrieved."
    )
    full_text_note: str
    abstract_available: bool
    other_matching_records: list[str] = Field(
        default_factory=list,
        description="Other Europe PMC records that matched the identifier (e.g. a preprint and its published version).",
    )


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #


def validate_query(query: str) -> str:
    if not isinstance(query, str):
        raise InvalidInputError("The query must be text.")
    cleaned = " ".join(query.split())
    if not cleaned:
        raise InvalidInputError("The query is empty. Provide a question or search terms.")
    if len(cleaned) > MAX_QUERY_LENGTH:
        raise InvalidInputError(
            f"The query is {len(cleaned)} characters; the limit is {MAX_QUERY_LENGTH}. "
            "Use the key search terms rather than a full paragraph."
        )
    return cleaned


def validate_max_results(max_results: int) -> int:
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise InvalidInputError("max_results must be a whole number.")
    if not 1 <= max_results <= MAX_RESULTS_LIMIT:
        raise InvalidInputError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}.")
    return max_results


_DOI_RE = re.compile(r"^(?:doi:\s*|https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/\S+)$", re.IGNORECASE)
_PMCID_RE = re.compile(r"^PMC\d+$", re.IGNORECASE)
_PMID_RE = re.compile(r"^\d{1,9}$")
_PPR_RE = re.compile(r"^PPR\d+$", re.IGNORECASE)
_SOURCE_ID_RE = re.compile(r"^([A-Za-z]{3})\s*[:/]\s*(\S+)$")
_EPMC_URL_RE = re.compile(r"^https?://(?:www\.)?europepmc\.org/(?:article|abstract)/([A-Za-z]{3})/([^/?#\s]+)", re.I)


def identifier_to_query(identifier: str) -> str:
    """Translate a user-facing identifier into a Europe PMC search query.

    Accepted: PMID (12345678), PMCID (PMC1234567), DOI (10.x/y, doi:..., https://doi.org/...),
    SOURCE:ID (MED:12345678, PPR:PPR123456), or a europepmc.org article URL.
    """
    if not isinstance(identifier, str) or not identifier.strip():
        raise InvalidInputError("The identifier is empty.")
    ident = identifier.strip()

    if m := _EPMC_URL_RE.match(ident):
        ident = f"{m.group(1)}:{m.group(2)}"

    if m := _DOI_RE.match(ident):
        doi = m.group(1).rstrip(".,;")
        return f'DOI:"{doi}"'
    if _PMCID_RE.match(ident):
        return f"PMCID:{ident.upper()}"
    if _PMID_RE.match(ident):
        return f"EXT_ID:{ident} AND SRC:MED"
    if _PPR_RE.match(ident):
        return f"EXT_ID:{ident.upper()} AND SRC:PPR"
    if m := _SOURCE_ID_RE.match(ident):
        source, ext_id = m.group(1).upper(), m.group(2)
        if source not in KNOWN_SOURCES:
            raise InvalidInputError(
                f"Unknown Europe PMC source {source!r}. Known sources: {', '.join(sorted(KNOWN_SOURCES))}."
            )
        if source == "PMC":
            return f"PMCID:{ext_id.upper()}"
        if not re.fullmatch(r"[A-Za-z0-9._-]+", ext_id):
            raise InvalidInputError(f"Identifier part {ext_id!r} contains unexpected characters.")
        return f"EXT_ID:{ext_id} AND SRC:{source}"

    raise InvalidInputError(
        f"Could not recognise {identifier!r} as an article identifier. Use a PMID (e.g. 12345678), "
        "PMCID (PMC1234567), DOI (10.1000/xyz), or the europepmc_id from search_literature (e.g. MED:12345678)."
    )


# --------------------------------------------------------------------------- #
# Record parsing
# --------------------------------------------------------------------------- #

_BLOCK_TAGS = re.compile(r"</?(?:h\d|p|br|div|li|ul|ol|sec|title)[^>]*>", re.IGNORECASE)
_ANY_TAG = re.compile(r"<[^>]+>")


def clean_markup(text: str | None) -> str | None:
    if not text:
        return None
    text = _BLOCK_TAGS.sub(" ", text)
    text = _ANY_TAG.sub("", text)
    text = html.unescape(text)
    text = " ".join(text.split())
    return text or None


def _publication_date(raw: dict[str, Any]) -> str | None:
    journal_info = raw.get("journalInfo") or {}
    return (
        raw.get("firstPublicationDate")
        or raw.get("electronicPublicationDate")
        or journal_info.get("printPublicationDate")
        or raw.get("pubYear")
    )


def parse_record(raw: dict[str, Any], *, truncate_abstract: int | None = None) -> ArticleRecord:
    source = str(raw.get("source") or "").upper()
    rec_id = str(raw.get("id") or "")
    if not source or not rec_id:
        raise EuropePMCError("Europe PMC returned a record without a source or id.")

    pub_types_raw = (raw.get("pubTypeList") or {}).get("pubType") or []
    if isinstance(pub_types_raw, str):
        pub_types_raw = [pub_types_raw]
    article_types = [str(t) for t in pub_types_raw]
    lowered = [t.lower() for t in article_types]

    journal = ((raw.get("journalInfo") or {}).get("journal") or {}).get("title")
    if not journal:
        journal = (raw.get("bookOrReportDetails") or {}).get("publisher") or raw.get("journalTitle")

    abstract = clean_markup(raw.get("abstractText"))
    truncated = False
    if abstract and truncate_abstract and len(abstract) > truncate_abstract:
        abstract = abstract[:truncate_abstract].rsplit(" ", 1)[0] + " …"
        truncated = True

    pmid = raw.get("pmid")
    pmcid = raw.get("pmcid")
    doi = raw.get("doi")

    full_text = [
        FullTextLink(
            url=u["url"],
            availability=u.get("availability"),
            document_style=u.get("documentStyle"),
            site=u.get("site"),
        )
        for u in ((raw.get("fullTextUrlList") or {}).get("fullTextUrl") or [])
        if isinstance(u, dict) and u.get("url")
    ]

    oa = raw.get("isOpenAccess")
    cited = raw.get("citedByCount")

    return ArticleRecord(
        europepmc_id=f"{source}:{rec_id}",
        source=source,
        id=rec_id,
        pmid=pmid,
        pmcid=pmcid,
        doi=doi,
        title=clean_markup(raw.get("title")),
        authors=raw.get("authorString"),
        journal=journal,
        publication_date=_publication_date(raw),
        publication_year=raw.get("pubYear"),
        article_types=article_types,
        review_in_metadata=any("review" in t for t in lowered),
        preprint=source == "PPR" or any("preprint" in t for t in lowered),
        open_access=None if oa is None else str(oa).upper() == "Y",
        cited_by_count=int(cited) if isinstance(cited, (int, str)) and str(cited).isdigit() else None,
        abstract=abstract,
        abstract_truncated=truncated,
        links=SourceLinks(
            europepmc=f"https://europepmc.org/article/{source}/{quote(rec_id)}",
            doi=f"https://doi.org/{doi}" if doi else None,
            pubmed=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
            pmc=f"https://europepmc.org/article/PMC/{pmcid}" if pmcid else None,
            full_text=full_text,
        ),
    )


# --------------------------------------------------------------------------- #
# HTTP client
# --------------------------------------------------------------------------- #


class EuropePMCClient:
    """Thin async client for the Europe PMC search endpoint.

    `transport` exists so tests can inject `httpx.MockTransport` without network access.
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    async def _search_raw(self, query: str, page_size: int) -> dict[str, Any]:
        params = {"query": query, "format": "json", "resultType": "core", "pageSize": str(page_size)}
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, transport=self.transport, headers={"User-Agent": USER_AGENT}
            ) as client:
                response = await client.get(f"{self.base_url}/search", params=params)
        except httpx.TimeoutException as exc:
            raise EuropePMCError(
                f"Europe PMC did not respond within {self.timeout:g} seconds. Try again, or narrow the query."
            ) from exc
        except httpx.RequestError as exc:
            raise EuropePMCError(f"Could not connect to Europe PMC ({type(exc).__name__}).") from exc

        if response.status_code >= 500:
            raise EuropePMCError(
                f"Europe PMC returned a server error (HTTP {response.status_code}). The service may be down; try again later."
            )
        if response.status_code == 429:
            raise EuropePMCError("Europe PMC is rate-limiting requests (HTTP 429). Wait before retrying.")
        if response.status_code >= 400:
            raise EuropePMCError(
                f"Europe PMC rejected the request (HTTP {response.status_code}). Check the query syntax, "
                "e.g. balanced quotes and parentheses."
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise EuropePMCError("Europe PMC returned a response that was not valid JSON.") from exc
        if not isinstance(data, dict):
            raise EuropePMCError("Europe PMC returned an unexpected response shape.")
        if data.get("errMsg"):
            raise EuropePMCError(f"Europe PMC reported an error: {data['errMsg']}")
        return data

    @staticmethod
    def _records(data: dict[str, Any]) -> list[dict[str, Any]]:
        results = (data.get("resultList") or {}).get("result") or []
        return [r for r in results if isinstance(r, dict)]

    async def search(self, query: str, max_results: int = DEFAULT_MAX_RESULTS) -> SearchResult:
        query = validate_query(query)
        max_results = validate_max_results(max_results)
        data = await self._search_raw(query, max_results)

        records = [
            parse_record(r, truncate_abstract=SEARCH_ABSTRACT_CHAR_LIMIT) for r in self._records(data)[:max_results]
        ]
        try:
            total = int(data.get("hitCount") or 0)
        except (TypeError, ValueError):
            total = len(records)

        if not records:
            note = (
                "No Europe PMC records matched this query. Absence of results is not evidence that no "
                "such studies exist; try synonyms, fewer terms, or field searches such as TITLE:\"...\"."
            )
        else:
            note = (
                f"Showing {len(records)} of {total} matches in Europe PMC relevance order. Abstracts over "
                f"{SEARCH_ABSTRACT_CHAR_LIMIT} characters are truncated; call get_article with europepmc_id "
                "for the full abstract. Records are unverified source data, not conclusions."
            )
        return SearchResult(
            query=query,
            total_hits=total,
            returned=len(records),
            results=records,
            europepmc_search_url="https://europepmc.org/search?" + urlencode({"query": query}),
            note=note,
        )

    async def get_article(self, identifier: str) -> ArticleResult:
        query = identifier_to_query(identifier)
        data = await self._search_raw(query, 5)
        raw_records = self._records(data)
        if not raw_records:
            raise ArticleNotFoundError(
                f"No Europe PMC record matched {identifier!r}. Check the identifier, or use search_literature "
                "and pass the europepmc_id it returns."
            )
        article = parse_record(raw_records[0])
        others = [f"{r.get('source')}:{r.get('id')}" for r in raw_records[1:] if r.get("source") and r.get("id")]
        abstract_available = bool(article.abstract)
        note = FULL_TEXT_NOT_RETRIEVED
        if not abstract_available:
            note += " Europe PMC holds no abstract for this record, so only its bibliographic metadata is available."
        return ArticleResult(
            requested_identifier=identifier,
            article=article,
            full_text_retrieved=False,
            full_text_note=note,
            abstract_available=abstract_available,
            other_matching_records=others,
        )
