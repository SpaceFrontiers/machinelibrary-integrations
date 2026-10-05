import httpx
import respx

from llama_index.tools.machinelibrary import MachineLibraryToolSpec

BASE = "https://api.machinelibrary.ai"
HIT = {
    "id": "d1",
    "score": 0.8,
    "snippets": [{"field": "abstract", "text": "Graphene oxide membranes sieve ions."}],
    "document": {
        "title": "Ion sieving",
        "uris": ["https://doi.org/10.3/y"],
        "authors": ["A. Geim"],
    },
}


@respx.mock
def test_search_returns_documents_with_source_uri():
    route = respx.post(f"{BASE}/v2/search/").mock(
        return_value=httpx.Response(200, json={"hits": [HIT]})
    )
    docs = MachineLibraryToolSpec(api_key="ml_k").search("ion sieving", limit=2)
    assert docs[0].metadata["source_uri"] == "https://doi.org/10.3/y"
    assert docs[0].text.startswith("Graphene")
    assert "(llama-index)" in route.calls.last.request.headers["User-Agent"]


def test_tools_have_names_and_descriptions():
    tools = MachineLibraryToolSpec(api_key="ml_k").to_tool_list()
    names = [t.metadata.name for t in tools]
    assert names == ["search", "search_in_document", "fetch_document"]
    assert "source_uri" in tools[1].metadata.description


@respx.mock
def test_fetch_missing_document_is_empty():
    respx.get(url__startswith=f"{BASE}/v2/documents/by-uri/").mock(return_value=httpx.Response(404))
    assert MachineLibraryToolSpec(api_key="ml_k").fetch_document("doi:10.3/none") == []
