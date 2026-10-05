"""Agent tools: search, read, and find evidence inside one document.

Each tool returns compact JSON so the model can cite `source_uri` exactly.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Literal

from langchain_core.tools import BaseTool, BaseToolkit
from pydantic import BaseModel, Field, SecretStr

from langchain_machinelibrary._clients import async_client, sync_client

MAX_CONTENT_CHARS = 40_000


class SearchInput(BaseModel):
    query: str = Field(description="What to look for, in natural language or keywords.")
    limit: int = Field(default=10, ge=1, le=50, description="Number of documents to return.")
    index: Literal["documents", "social"] = Field(
        default="documents",
        description="'documents': papers, books, patents, standards, Wikipedia. "
        "'social': Reddit, Telegram, Discord.",
    )


class FetchInput(BaseModel):
    source_uri: str = Field(description="A `source_uri` copied from a search result, or a DOI.")


class SearchInDocumentInput(BaseModel):
    source_uri: str = Field(description="A `source_uri` copied from a search result, or a DOI.")
    query: str = Field(description="The claim or topic to find passages for inside this document.")


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


class MachineLibrarySearch(BaseTool):
    name: str = "machinelibrary_search"
    description: str = (
        "Search scholarly papers, books, patents, standards and Wikipedia (or Reddit, Telegram "
        "and Discord with index='social'). Returns titles, matching passages and a `source_uri` "
        "to cite and to pass to the other Machine Library tools. Do not invent sources."
    )
    args_schema: type[BaseModel] = SearchInput
    api_key: SecretStr | None = None

    def _run(self, query: str, limit: int = 10, index: str = "documents") -> str:
        with sync_client(self.api_key) as client:
            hits = client.search(query, limit=limit, index=index)  # type: ignore[arg-type]
        return _json([asdict(hit) for hit in hits])

    async def _arun(self, query: str, limit: int = 10, index: str = "documents") -> str:
        async with async_client(self.api_key) as client:
            hits = await client.search(query, limit=limit, index=index)  # type: ignore[arg-type]
        return _json([asdict(hit) for hit in hits])


class MachineLibraryFetchDocument(BaseTool):
    name: str = "machinelibrary_fetch_document"
    description: str = (
        "Read the bounded full text and metadata of one document by its `source_uri`. Use only "
        "when you need the body; prefer machinelibrary_search_in_document for specific evidence."
    )
    args_schema: type[BaseModel] = FetchInput
    api_key: SecretStr | None = None

    @staticmethod
    def _format(doc: object | None) -> str:
        if doc is None:
            return _json({"error": "document not found"})
        data = asdict(doc)  # type: ignore[arg-type]
        content = data.get("content") or ""
        if len(content) > MAX_CONTENT_CHARS:
            data["content"] = content[:MAX_CONTENT_CHARS]
            data["content_truncated"] = True
        return _json(data)

    def _run(self, source_uri: str) -> str:
        with sync_client(self.api_key) as client:
            return self._format(client.fetch_document(source_uri))

    async def _arun(self, source_uri: str) -> str:
        async with async_client(self.api_key) as client:
            return self._format(await client.fetch_document(source_uri))


class MachineLibrarySearchInDocument(BaseTool):
    name: str = "machinelibrary_search_in_document"
    description: str = (
        "Find up to five passages inside one document (by `source_uri`) that match a claim or "
        "topic. Quote these passages when citing; an empty list means no supporting passage."
    )
    args_schema: type[BaseModel] = SearchInDocumentInput
    api_key: SecretStr | None = None

    def _run(self, source_uri: str, query: str) -> str:
        with sync_client(self.api_key) as client:
            passages = client.search_in_document(source_uri, query)
        return _json([asdict(p) for p in passages])

    async def _arun(self, source_uri: str, query: str) -> str:
        async with async_client(self.api_key) as client:
            passages = await client.search_in_document(source_uri, query)
        return _json([asdict(p) for p in passages])


class MachineLibraryToolkit(BaseToolkit):
    """Search, find evidence inside a document, and read full text.

    Example:
        tools = MachineLibraryToolkit().get_tools()
    """

    api_key: SecretStr | None = None

    def get_tools(self) -> list[BaseTool]:
        return [
            MachineLibrarySearch(api_key=self.api_key),
            MachineLibrarySearchInDocument(api_key=self.api_key),
            MachineLibraryFetchDocument(api_key=self.api_key),
        ]


def machinelibrary_tools(api_key: str | None = None) -> list[BaseTool]:
    """All three tools, ready for `create_agent(model, tools=...)`."""
    return MachineLibraryToolkit(api_key=SecretStr(api_key) if api_key else None).get_tools()
