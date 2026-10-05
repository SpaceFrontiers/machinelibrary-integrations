# Machine Library integrations

Framework integrations for [Machine Library](https://machinelibrary.ai):
citable search across scholarly papers, books, patents, standards and
Wikipedia (plus Reddit, Telegram and Discord), passage search inside long
documents, and bounded full text. Every result carries a canonical
`source_uri` to cite.

| Package | Ecosystem | Path |
| --- | --- | --- |
| [`machinelibrary`](https://pypi.org/project/machinelibrary/) | Python client (sync and async) | [`python/machinelibrary`](python/machinelibrary) |
| [`langchain-machinelibrary`](https://pypi.org/project/langchain-machinelibrary/) | LangChain retriever and tools | [`python/langchain-machinelibrary`](python/langchain-machinelibrary) |
| [`llama-index-tools-machinelibrary`](https://pypi.org/project/llama-index-tools-machinelibrary/) | LlamaIndex tool spec | [`python/llama-index-tools-machinelibrary`](python/llama-index-tools-machinelibrary) |
| `@machinelibrary/ai-sdk` | Vercel AI SDK tools | [`typescript/ai-sdk`](typescript/ai-sdk) |

All packages read an API key from `MACHINELIBRARY_API_KEY`
([create one](https://machinelibrary.ai/keys)). Requests are billed per call
([pricing](https://machinelibrary.ai/pricing)).

Prefer MCP? Connect `https://mcp.machinelibrary.ai` from Claude, ChatGPT,
Claude Code, Codex or Cursor — see [machinelibrary.ai/mcp](https://machinelibrary.ai/mcp)
and [SpaceFrontiers/mcp](https://github.com/SpaceFrontiers/mcp).

## Development

```bash
uv venv && uv pip install -e python/machinelibrary -e python/langchain-machinelibrary \
  -e python/llama-index-tools-machinelibrary pytest pytest-asyncio respx ruff langchain
pytest python
cd typescript/ai-sdk && npm install && npm test
```
