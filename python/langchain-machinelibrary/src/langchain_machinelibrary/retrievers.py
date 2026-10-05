"""A retriever that returns citable passages as LangChain documents."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from machinelibrary import SearchHit
from pydantic import SecretStr

from langchain_machinelibrary._clients import async_client, sync_client


def _to_document(hit: SearchHit) -> Document:
    metadata: dict[str, Any] = {
        "source": hit.source_uri,
        "title": hit.title,
        "score": hit.score,
        "authors": hit.authors,
        "issued_date": hit.issued_date,
        "document_type": hit.document_type,
        "uris": hit.uris,
    }
    return Document(page_content=hit.text, metadata={k: v for k, v in metadata.items() if v})


class MachineLibraryRetriever(BaseRetriever):
    """Search Machine Library and return the best matching passage per document.

    `metadata["source"]` is the canonical URI to cite. Reads the API key from
    `api_key` or `MACHINELIBRARY_API_KEY`.

    Example:
        retriever = MachineLibraryRetriever(k=5)
        docs = retriever.invoke("perovskite solar cell stability")
    """

    api_key: SecretStr | None = None
    k: int = 10
    index: Literal["documents", "social"] = "documents"
    document_types: list[str] | None = None
    issued_after: int | None = None
    issued_before: int | None = None

    def _search_kwargs(self) -> dict[str, Any]:
        return {
            "limit": self.k,
            "index": self.index,
            "document_types": self.document_types,
            "issued_after": self.issued_after,
            "issued_before": self.issued_before,
        }

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        with sync_client(self.api_key) as client:
            return [_to_document(hit) for hit in client.search(query, **self._search_kwargs())]

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun
    ) -> list[Document]:
        async with async_client(self.api_key) as client:
            hits = await client.search(query, **self._search_kwargs())
        return [_to_document(hit) for hit in hits]
