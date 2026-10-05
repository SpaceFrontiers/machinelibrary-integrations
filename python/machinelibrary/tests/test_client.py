import httpx
import pytest
import respx

from machinelibrary import (
    AsyncMachineLibrary,
    AuthenticationError,
    InsufficientCreditError,
    MachineLibrary,
)
from machinelibrary.client import normalize_uri

BASE = "https://api.machinelibrary.ai"
HIT = {
    "id": "d1",
    "score": 0.9,
    "snippets": [
        {"field": "content", "text": "  "},
        {"field": "content", "text": "Off-target edits were rare."},
    ],
    "document": {
        "title": "CRISPR in vivo",
        "uris": ["doi://10.1/abc", "https://doi.org/10.1/abc"],
        "authors": [{"given": "Ana", "family": "Rivera"}, "Li Chen"],
        "issued_at": 1704067200,
        "type": "journal-article",
        "abstract": "We assess off-target editing.",
    },
}


@respx.mock
def test_search_sends_bounded_request_and_returns_citable_hits():
    route = respx.post(f"{BASE}/v2/search/").mock(
        return_value=httpx.Response(200, json={"hits": [HIT]})
    )
    with MachineLibrary(api_key="ml_test", integration="langchain") as ml:
        hits = ml.search("crispr", limit=3, issued_after=1_600_000_000)
    sent = route.calls.last.request
    assert sent.headers["X-Api-Key"] == "ml_test"
    assert sent.headers["User-Agent"].endswith("(langchain)")
    assert b'"index_names":["documents"]' in sent.content.replace(b" ", b"")
    assert hits[0].source_uri == "https://doi.org/10.1/abc"
    assert hits[0].snippet == "Off-target edits were rare."
    assert hits[0].authors == ["Ana Rivera", "Li Chen"]
    assert hits[0].issued_date == "2024-01-01"


@respx.mock
def test_errors_are_typed():
    respx.post(f"{BASE}/v2/search/").mock(
        side_effect=[
            httpx.Response(401, json={"detail": "Unauthorized"}),
            httpx.Response(402, json={"detail": "Insufficient balance"}),
        ]
    )
    ml = MachineLibrary(api_key="bad")
    with pytest.raises(AuthenticationError):
        ml.search("x")
    with pytest.raises(InsufficientCreditError):
        ml.search("x")


def test_missing_key_names_the_environment_variable(monkeypatch):
    monkeypatch.delenv("MACHINELIBRARY_API_KEY", raising=False)
    with pytest.raises(AuthenticationError, match="MACHINELIBRARY_API_KEY"):
        MachineLibrary()


def test_invalid_arguments_are_rejected_before_any_request():
    ml = MachineLibrary(api_key="k")
    with pytest.raises(ValueError, match="limit"):
        ml.search("x", limit=0)
    with pytest.raises(ValueError, match="query"):
        ml.search("  ")
    with pytest.raises(ValueError, match="index"):
        ml.search("x", index="web")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://doi.org/10.1038/Nature14539", "doi://10.1038/nature14539"),
        ("doi:10.1/X", "doi://10.1/x"),
        ("pmid:123", "pubmed://123"),
        ("arXiv:2101.00001", "arxiv://2101.00001"),
        ("isbn:978-0", "isbn://978-0"),
        ("https://en.wikipedia.org/wiki/X", "https://en.wikipedia.org/wiki/X"),
    ],
)
def test_normalize_uri(raw, expected):
    assert normalize_uri(raw) == expected


@respx.mock
def test_fetch_and_search_in_document_use_the_encoded_canonical_uri():
    path = f"{BASE}/v2/documents/by-uri/doi%3A%2F%2F10.1%2Fabc"
    respx.get(path, params={"text_filter": "rates"}).mock(
        return_value=httpx.Response(200, json={"hits": [HIT]})
    )
    respx.get(path).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "d1",
                "uris": HIT["document"]["uris"],
                "document": {**HIT["document"], "content": "Body", "content_truncated": True},
            },
        )
    )
    ml = MachineLibrary(api_key="k")
    passages = ml.search_in_document("https://doi.org/10.1/ABC", "rates")
    assert [p.text for p in passages] == ["Off-target edits were rare."]
    doc = ml.fetch_document("doi:10.1/abc")
    assert doc is not None and doc.content == "Body" and doc.content_truncated


@respx.mock
def test_unknown_document_is_none():
    respx.get(url__startswith=f"{BASE}/v2/documents/by-uri/").mock(return_value=httpx.Response(404))
    assert MachineLibrary(api_key="k").fetch_document("doi:10.1/missing") is None


@respx.mock
async def test_async_client_matches_sync():
    respx.post(f"{BASE}/v2/search/").mock(return_value=httpx.Response(200, json={"hits": [HIT]}))
    async with AsyncMachineLibrary(api_key="k") as ml:
        hits = await ml.search("crispr")
    assert hits[0].title == "CRISPR in vivo"
