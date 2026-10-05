"""Result types. Every result carries `source_uri`, the canonical link to cite."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

SNIPPET_LIMIT = 900
ABSTRACT_LIMIT = 2_000


def canonical_uri(uris: list[str]) -> str:
    """Prefer a doi.org link, then any web link, then the first scheme URI."""
    for uri in uris:
        if "doi.org/" in uri:
            return uri
    for uri in uris:
        if uri.startswith(("http://", "https://")):
            return uri
    return uris[0] if uris else ""


def _authors(raw: list[Any]) -> list[str]:
    names: list[str] = []
    for author in raw:
        if isinstance(author, str):
            name = author.strip()
        elif isinstance(author, dict):
            name = str(author.get("name") or "").strip() or " ".join(
                part
                for part in (
                    str(author.get("given") or "").strip(),
                    str(author.get("family") or "").strip(),
                )
                if part
            )
        else:
            name = ""
        if name:
            names.append(name)
    return names


def _date(issued_at: Any) -> str | None:
    if issued_at is None:
        return None
    try:
        return datetime.fromtimestamp(int(issued_at), tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _clip(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


@dataclass(frozen=True)
class SearchHit:
    """One search result. Cite `source_uri`; pass it to `fetch_document`."""

    title: str
    source_uri: str
    score: float
    snippet: str | None = None
    abstract: str | None = None
    authors: list[str] = field(default_factory=list)
    issued_date: str | None = None
    document_type: str | None = None
    uris: list[str] = field(default_factory=list)

    @classmethod
    def from_api(cls, hit: dict[str, Any]) -> SearchHit:
        doc = hit.get("document") or {}
        uris = [str(uri) for uri in doc.get("uris") or []]
        snippet = next(
            (str(s["text"]) for s in hit.get("snippets") or [] if str(s.get("text") or "").strip()),
            None,
        )
        abstract = str(doc.get("abstract") or "")
        return cls(
            title=str(doc.get("title") or "Untitled"),
            source_uri=canonical_uri(uris),
            score=float(hit.get("score") or 0.0),
            snippet=_clip(snippet, SNIPPET_LIMIT) if snippet else None,
            abstract=_clip(abstract, ABSTRACT_LIMIT) if abstract.strip() else None,
            authors=_authors(doc.get("authors") or []),
            issued_date=_date(doc.get("issued_at")),
            document_type=doc.get("type"),
            uris=uris,
        )

    @property
    def text(self) -> str:
        """The best available text: the matching passage, else the abstract."""
        return self.snippet or self.abstract or self.title


@dataclass(frozen=True)
class Passage:
    """A passage found inside one document by `search_in_document`."""

    text: str
    field: str
    score: float | None = None


@dataclass(frozen=True)
class Document:
    """A fetched document. `content` is bounded; check `content_truncated`."""

    title: str
    source_uri: str
    content: str | None
    content_truncated: bool
    abstract: str | None = None
    authors: list[str] = field(default_factory=list)
    issued_date: str | None = None
    document_type: str | None = None
    uris: list[str] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Document:
        doc = data.get("document") or {}
        uris = [str(uri) for uri in data.get("uris") or doc.get("uris") or []]
        abstract = str(doc.get("abstract") or "").strip()
        return cls(
            title=str(doc.get("title") or "Untitled"),
            source_uri=canonical_uri(uris),
            content=doc.get("content") or None,
            content_truncated=bool(doc.get("content_truncated")),
            abstract=abstract or None,
            authors=_authors(doc.get("authors") or []),
            issued_date=_date(doc.get("issued_at")),
            document_type=doc.get("type"),
            uris=uris,
        )
