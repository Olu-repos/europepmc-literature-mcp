# Local verification results

- Run at: 2026-09-29T17:18:03+01:00
- Host: local Windows PC (Windows 10)
- Mode: full, including live Europe PMC
- Pinned MCP SDK: 2.2.0

| Check | Status |
|---|---|
| environment | PASS |
| unit_tests | PASS |
| mcp_inmemory | PASS |
| mcp_stdio | PASS |
| live_api | PASS |
| live_mcp | PASS |

## environment: PASS

```
Python 3.10.11 on Windows-10-10.0.26200-SP0
Installed: mcp=2.2.0, httpx=0.28.1, pydantic=2.13.5, anyio=4.15.1, pytest=9.1.1, typer=0.27.2
MCP SDK matches pin (2.2.0).
```

## unit_tests: PASS

```
..........................................                               [100%]
42 passed in 0.19s
```

## mcp_inmemory: PASS

```
.........                                                                [100%]
9 passed in 2.55s
```

## mcp_stdio: PASS

```
stdio launch OK; tools listed: ['get_article', 'search_literature']
```

## live_api: PASS

```
Query: (TCR OR "T-cell receptor") AND (clonotype OR "clonal tracking" OR repertoire) AND persistence AND ("adoptive cell" OR "adoptive T-cell" OR "CAR-T" OR TIL) AND NOT PUB_TYPE:review
total_hits=1456 returned=5
- MED:42189877 | PMID 42189877 | DOI 10.1158/1078-0432.ccr-25-4130 | 2026-09-01 | types=['research-article', 'Clinical Trial, Phase I', 'Journal Article'] | review=False | PiggyBac-Engineered Membrane-Bound IL7 TILs Combined with Anti-PD-1 Antibody Demonstrates 
- MED:41267983 | PMID 41267983 | DOI 10.3389/fonc.2025.1693912 | 2025-11-05 | types=['brief-report', 'Journal Article'] | review=False | Serial TIL infusions and PD-1 blockade drive long-term clonal persistence in prostate canc
- MED:42061983 | PMID 42061983 | DOI 10.1136/jitc-2026-014822 | 2026-04-30 | types=['Journal Article', 'Case Reports', 'case-report'] | review=False | First-in-human use of recombinant IL-7 to potentiate antigen-specific T cell therapy: a si
- MED:42618927 | PMID 42618927 | DOI 10.1186/s12967-026-08781-z | 2026-08-11 | types=["Research Support, Non-U.S. Gov't", 'research-article', 'Clinical Trial, Phase I', 'Journal Article'] | review=False | T cell receptor repertoire dynamics and newly identified functional regulators of autologo
- MED:41402893 | PMID 41402893 | DOI 10.1186/s13073-025-01583-w | 2025-12-16 | types=["Research Support, Non-U.S. Gov't", 'research-article', 'Journal Article'] | review=False | Delineation and monitoring of the T cell repertoire of adoptive cell transfer product duri
get_article(MED:42189877): abstract_available=True full_text_retrieved=False other_matches=[]
Live search and get_article returned identifiers, links and the full-text note.
```

## live_mcp: PASS

```
search_literature via MCP: returned=3, total_hits=1456
get_article via MCP: MED:42189877, full_text_retrieved=False
get_article('not an identifier') -> is_error=True
Live Europe PMC reachable through the MCP server.
```
