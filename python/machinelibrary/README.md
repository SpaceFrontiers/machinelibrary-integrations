# machinelibrary

Python client for [Machine Library](https://machinelibrary.ai): search full text
across scholarly papers, books, patents, standards and Wikipedia (plus Reddit,
Telegram and Discord), read bounded full text, and find passages inside long
documents. Every result carries a canonical `source_uri` to cite.

Built for AI agents and RAG pipelines. Framework adapters:
[`langchain-machinelibrary`](https://pypi.org/project/langchain-machinelibrary/),
[`llama-index-tools-machinelibrary`](https://pypi.org/project/llama-index-tools-machinelibrary/).
Prefer MCP? Connect `https://mcp.machinelibrary.ai` — see
[machinelibrary.ai/mcp](https://machinelibrary.ai/mcp).

## Install

```bash
pip install machinelibrary
export MACHINELIBRARY_API_KEY=ml_...   # https://machinelibrary.ai/keys
```

## Use

```python
from machinelibrary import MachineLibrary

ml = MachineLibrary()
hits = ml.search("solid-state battery dendrite growth", limit=5)
for hit in hits:
    print(hit.title, hit.source_uri)
    print("  ", hit.text)

# Find the passages that support a claim, without downloading the whole text.
for passage in ml.search_in_document(hits[0].source_uri, "critical current density"):
    print(passage.text)

# Bounded full text (check `content_truncated`).
doc = ml.fetch_document("doi:10.1038/nature14539", max_tokens=8000)
```

`AsyncMachineLibrary` has the same methods as coroutines.

`search(index="social")` searches Reddit, Telegram and Discord. Dates for
`issued_after` / `issued_before` are Unix seconds. Identifiers accept DOIs
(`doi:…`, `https://doi.org/…`), `pmid:`, `arxiv:` and `isbn:` shorthands.

## Billing and limits

Searches and document reads are charged per request to the account that owns
the key; see [pricing](https://machinelibrary.ai/pricing). `InsufficientCreditError`
means the balance needs a [top-up](https://machinelibrary.ai/payments).
Results are evidence to review, not proof that a claim is correct, and coverage
is not exhaustive.

## License

MIT
