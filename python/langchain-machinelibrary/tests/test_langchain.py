import json

import httpx
import respx

from langchain_machinelibrary import (
    MachineLibraryRetriever,
    MachineLibrarySearch,
    MachineLibrarySearchInDocument,
    machinelibrary_tools,
)

BASE = "https://api.machinelibrary.ai"
HIT = {
    "id": "d1",
    "score": 0.8,
    "snippets": [
        {"field": "content", "text": "Dendrites form above the critical current density."}
    ],
    "document": {
        "title": "Solid-state batteries",
        "uris": ["https://doi.org/10.2/x"],
        "type": "journal-article",
    },
}


@respx.mock
def test_retriever_returns_citable_documents(monkeypatch):
    monkeypatch.setenv("MACHINELIBRARY_API_KEY", "ml_env")
    route = respx.post(f"{BASE}/v2/search/").mock(
        return_value=httpx.Response(200, json={"hits": [HIT]})
    )
    docs = MachineLibraryRetriever(k=3).invoke("dendrites")
    assert docs[0].page_content.startswith("Dendrites form")
    assert docs[0].metadata["source"] == "https://doi.org/10.2/x"
    request = route.calls.last.request
    assert request.headers["X-Api-Key"] == "ml_env"
    assert "(langchain)" in request.headers["User-Agent"]
    assert json.loads(request.content)["limit"] == 3


@respx.mock
async def test_retriever_async(monkeypatch):
    monkeypatch.setenv("MACHINELIBRARY_API_KEY", "ml_env")
    respx.post(f"{BASE}/v2/search/").mock(return_value=httpx.Response(200, json={"hits": [HIT]}))
    docs = await MachineLibraryRetriever().ainvoke("dendrites")
    assert docs[0].metadata["title"] == "Solid-state batteries"


@respx.mock
def test_search_tool_returns_json_with_source_uri():
    respx.post(f"{BASE}/v2/search/").mock(return_value=httpx.Response(200, json={"hits": [HIT]}))
    tool = MachineLibrarySearch(api_key="ml_k")
    result = json.loads(tool.invoke({"query": "dendrites", "limit": 2}))
    assert result[0]["source_uri"] == "https://doi.org/10.2/x"


@respx.mock
def test_search_in_document_tool():
    respx.get(url__startswith=f"{BASE}/v2/documents/by-uri/").mock(
        return_value=httpx.Response(200, json={"hits": [HIT]})
    )
    tool = MachineLibrarySearchInDocument(api_key="ml_k")
    passages = json.loads(tool.invoke({"source_uri": "https://doi.org/10.2/x", "query": "current"}))
    assert passages[0]["text"].startswith("Dendrites")


def test_tool_bundle_exposes_schemas_for_agents():
    tools = machinelibrary_tools(api_key="ml_k")
    assert [t.name for t in tools] == [
        "machinelibrary_search",
        "machinelibrary_search_in_document",
        "machinelibrary_fetch_document",
    ]
    assert "query" in tools[0].args
