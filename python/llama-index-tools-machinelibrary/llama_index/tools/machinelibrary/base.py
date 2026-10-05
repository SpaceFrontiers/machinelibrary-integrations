"""Machine Library tool spec: citable search for LlamaIndex agents."""

from __future__ import annotations

from llama_index.core.schema import Document
from llama_index.core.tools.tool_spec.base import BaseToolSpec

from machinelibrary import MachineLibrary, SearchHit

MAX_CONTENT_CHARS = 40_000


def _hit_document(hit: SearchHit) -> Document:
    metadata = {
        "source_uri": hit.source_uri,
        "title": hit.title,
        "authors": ", ".join(hit.authors),
        "issued_date": hit.issued_date,
        "document_type": hit.document_type,
    }
    return Document(text=hit.text, metadata={k: v for k, v in metadata.items() if v})


class MachineLibraryToolSpec(BaseToolSpec):
    """Search scholarly papers, books, patents, standards and Wikipedia, and read
    evidence inside them. Every result carries a `source_uri` to cite.

    Reads the API key from `api_key` or `MACHINELIBRARY_API_KEY`
    (create one at https://machinelibrary.ai/keys).
    """

    spec_functions = ["search", "search_in_document", "fetch_document"]  # noqa: RUF012 (BaseToolSpec API)

    def __init__(self, api_key: str | None = None) -> None:
        self._client = MachineLibrary(api_key, integration="llama-index")

    def search(self, query: str, limit: int = 10, social: bool = False) -> list[Document]:
        """Search scholarly papers, books, patents, standards and Wikipedia.

        Args:
            query: What to look for, in natural language or keywords.
            limit: Number of documents to return (1-50).
            social: Search Reddit, Telegram and Discord instead.

        Returns matching passages; cite metadata `source_uri` and pass it to the
        other tools. Do not invent sources.
        """
        index = "social" if social else "documents"
        return [_hit_document(hit) for hit in self._client.search(query, limit=limit, index=index)]

    def search_in_document(self, source_uri: str, query: str) -> list[Document]:
        """Find up to five passages inside one document that match a claim or topic.

        Args:
            source_uri: A `source_uri` from a search result, or a DOI.
            query: The claim or topic to find evidence for.

        An empty list means the document has no matching passage.
        """
        return [
            Document(text=p.text, metadata={"source_uri": source_uri, "field": p.field})
            for p in self._client.search_in_document(source_uri, query)
        ]

    def fetch_document(self, source_uri: str) -> list[Document]:
        """Read the bounded full text of one document by its `source_uri`.

        Args:
            source_uri: A `source_uri` from a search result, or a DOI.

        Prefer search_in_document when you only need specific evidence.
        """
        doc = self._client.fetch_document(source_uri)
        if doc is None:
            return []
        text = doc.content or doc.abstract or ""
        truncated = doc.content_truncated or len(text) > MAX_CONTENT_CHARS
        metadata = {
            "source_uri": doc.source_uri,
            "title": doc.title,
            "authors": ", ".join(doc.authors),
            "issued_date": doc.issued_date,
            "content_truncated": truncated,
        }
        return [
            Document(
                text=text[:MAX_CONTENT_CHARS], metadata={k: v for k, v in metadata.items() if v}
            )
        ]
