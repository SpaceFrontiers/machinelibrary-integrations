"""Sync and async clients for the Machine Library REST API.

Authentication: an API key from https://machinelibrary.ai/keys, passed as
`api_key` or the `MACHINELIBRARY_API_KEY` environment variable. Searches and
document reads are billed per request to that account.
"""

from __future__ import annotations

import os
from typing import Any, Literal
from urllib.parse import quote

import httpx

from machinelibrary.models import Document, Passage, SearchHit

__version__ = "0.1.0"
DEFAULT_BASE_URL = "https://api.machinelibrary.ai"
DEFAULT_TIMEOUT = 60.0
MAX_LIMIT = 50

Index = Literal["documents", "social"]


class MachineLibraryError(Exception):
    """An API error, with the HTTP status and the server's detail message."""

    def __init__(self, status: int, detail: str):
        super().__init__(f"Machine Library API error {status}: {detail}")
        self.status = status
        self.detail = detail


class AuthenticationError(MachineLibraryError):
    """The API key is missing, invalid or revoked."""


class InsufficientCreditError(MachineLibraryError):
    """The account balance cannot cover the request; top up at /payments."""


def normalize_uri(uri: str) -> str:
    """Accept DOI/PMID/arXiv/ISBN shorthands and doi.org links as document URIs."""
    value = uri.strip()
    lowered = value.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi://"):
        if lowered.startswith(prefix):
            return f"doi://{value[len(prefix) :].lower()}"
    shorthands = {
        "doi:": "doi://",
        "pmid:": "pubmed://",
        "pubmed:": "pubmed://",
        "arxiv:": "arxiv://",
        "isbn:": "isbn://",
    }
    for prefix, scheme in shorthands.items():
        if lowered.startswith(prefix):
            rest = value[len(prefix) :].lstrip("/").strip()
            return scheme + (rest.lower() if scheme in ("doi://", "arxiv://") else rest)
    return value


def _api_key(api_key: str | None) -> str:
    key = api_key or os.environ.get("MACHINELIBRARY_API_KEY")
    if not key:
        raise AuthenticationError(
            401,
            "no API key: pass api_key or set MACHINELIBRARY_API_KEY "
            "(create one at https://machinelibrary.ai/keys)",
        )
    return key


def _headers(api_key: str | None, integration: str | None) -> dict[str, str]:
    agent = f"machinelibrary-python/{__version__}"
    if integration:
        agent += f" ({integration})"
    return {"X-Api-Key": _api_key(api_key), "User-Agent": agent, "Accept": "application/json"}


def _search_body(
    query: str,
    limit: int,
    index: Index,
    document_types: list[str] | None,
    issued_after: int | None,
    issued_before: int | None,
) -> dict[str, Any]:
    if not query.strip():
        raise ValueError("query must not be empty")
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    if index not in ("documents", "social"):
        raise ValueError("index must be 'documents' or 'social'")
    body: dict[str, Any] = {"query": query, "limit": limit, "index_names": [index]}
    if document_types:
        body["filter_types"] = document_types
    if issued_after is not None:
        body["filter_issued_after"] = issued_after
    if issued_before is not None:
        body["filter_issued_before"] = issued_before
    return body


def _raise_for(response: httpx.Response) -> None:
    if response.is_success:
        return
    try:
        detail = str(response.json().get("detail") or response.text)
    except ValueError:
        detail = response.text
    if response.status_code == 401:
        raise AuthenticationError(401, detail)
    if response.status_code == 402:
        raise InsufficientCreditError(402, detail)
    raise MachineLibraryError(response.status_code, detail)


def _hits(payload: dict[str, Any]) -> list[SearchHit]:
    return [SearchHit.from_api(hit) for hit in payload.get("hits") or []]


def _passages(payload: dict[str, Any]) -> list[Passage]:
    passages: list[Passage] = []
    for hit in payload.get("hits") or []:
        for snippet in hit.get("snippets") or []:
            text = str(snippet.get("text") or "").strip()
            if text:
                passages.append(
                    Passage(
                        text=text,
                        field=str(snippet.get("field") or "content"),
                        score=snippet.get("score"),
                    )
                )
    return passages


def _document_path(uri: str) -> str:
    return f"/v2/documents/by-uri/{quote(normalize_uri(uri), safe='')}"


class MachineLibrary:
    """Synchronous client.

    Args:
        api_key: Machine Library API key; defaults to `MACHINELIBRARY_API_KEY`.
        base_url: API origin.
        timeout: Request timeout in seconds.
        integration: Short name added to the User-Agent (for example "langchain").
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        integration: str | None = None,
        http_client: httpx.Client | None = None,
    ):
        self._client = http_client or httpx.Client(
            base_url=base_url, timeout=timeout, headers=_headers(api_key, integration)
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        index: Index = "documents",
        document_types: list[str] | None = None,
        issued_after: int | None = None,
        issued_before: int | None = None,
    ) -> list[SearchHit]:
        """Search papers, books, patents, standards and Wikipedia (`documents`) or
        Reddit, Telegram and Discord (`social`). Dates are Unix seconds."""
        body = _search_body(query, limit, index, document_types, issued_after, issued_before)
        response = self._client.post("/v2/search/", json=body)
        _raise_for(response)
        return _hits(response.json())

    def fetch_document(self, uri: str, *, max_tokens: int | None = None) -> Document | None:
        """Bounded full text and metadata for one document, or None if unknown."""
        params = {"max_tokens": max_tokens} if max_tokens else None
        response = self._client.get(_document_path(uri), params=params)
        if response.status_code == 404:
            return None
        _raise_for(response)
        return Document.from_api(response.json())

    def search_in_document(self, uri: str, query: str) -> list[Passage]:
        """The passages inside one document that best match `query`."""
        if not query.strip():
            raise ValueError("query must not be empty")
        response = self._client.get(_document_path(uri), params={"text_filter": query})
        if response.status_code == 404:
            return []
        _raise_for(response)
        return _passages(response.json())

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> MachineLibrary:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class AsyncMachineLibrary:
    """Asynchronous client with the same methods as `MachineLibrary`."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        integration: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ):
        self._client = http_client or httpx.AsyncClient(
            base_url=base_url, timeout=timeout, headers=_headers(api_key, integration)
        )

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        index: Index = "documents",
        document_types: list[str] | None = None,
        issued_after: int | None = None,
        issued_before: int | None = None,
    ) -> list[SearchHit]:
        body = _search_body(query, limit, index, document_types, issued_after, issued_before)
        response = await self._client.post("/v2/search/", json=body)
        _raise_for(response)
        return _hits(response.json())

    async def fetch_document(self, uri: str, *, max_tokens: int | None = None) -> Document | None:
        params = {"max_tokens": max_tokens} if max_tokens else None
        response = await self._client.get(_document_path(uri), params=params)
        if response.status_code == 404:
            return None
        _raise_for(response)
        return Document.from_api(response.json())

    async def search_in_document(self, uri: str, query: str) -> list[Passage]:
        if not query.strip():
            raise ValueError("query must not be empty")
        response = await self._client.get(_document_path(uri), params={"text_filter": query})
        if response.status_code == 404:
            return []
        _raise_for(response)
        return _passages(response.json())

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncMachineLibrary:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
