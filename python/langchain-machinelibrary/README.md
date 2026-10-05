# langchain-machinelibrary

[Machine Library](https://machinelibrary.ai) for LangChain: a retriever and agent
tools for citable search across scholarly papers, books, patents, standards and
Wikipedia (plus Reddit, Telegram and Discord). Results carry a canonical
`source_uri`, so answers can cite sources a reader can open and check.

## Install

```bash
pip install langchain-machinelibrary
export MACHINELIBRARY_API_KEY=ml_...   # https://machinelibrary.ai/keys
```

## Retriever (RAG)

```python
from langchain_machinelibrary import MachineLibraryRetriever

retriever = MachineLibraryRetriever(k=5)
for doc in retriever.invoke("perovskite solar cell stability under humidity"):
    print(doc.metadata["title"], doc.metadata["source"])
    print(doc.page_content)
```

## Agent tools

```python
from langchain.agents import create_agent
from langchain_machinelibrary import MachineLibraryToolkit

agent = create_agent(
    "anthropic:claude-sonnet-5-5",
    tools=MachineLibraryToolkit().get_tools(),
    system_prompt="Answer from Machine Library sources and cite each claim's source_uri.",
)
agent.invoke({"messages": [{"role": "user", "content": "What limits lithium-metal anodes?"}]})
```

| Tool | Use |
| --- | --- |
| `machinelibrary_search` | Find documents; returns passages and `source_uri` |
| `machinelibrary_search_in_document` | Find passages supporting a claim inside one document |
| `machinelibrary_fetch_document` | Read bounded full text when the body is needed |

## Billing and limits

Each search or read is charged to the key's account; see
[pricing](https://machinelibrary.ai/pricing). Retrieved text is evidence to
review, not proof that a generated answer is correct. Coverage is broad but not
exhaustive.
