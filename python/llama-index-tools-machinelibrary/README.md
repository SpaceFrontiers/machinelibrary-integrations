# llama-index-tools-machinelibrary

[Machine Library](https://machinelibrary.ai) tools for LlamaIndex agents: citable
search across scholarly papers, books, patents, standards and Wikipedia (or
Reddit, Telegram and Discord), passage search inside a document, and bounded
full text. Each result's `source_uri` is the link to cite.

```bash
pip install llama-index-tools-machinelibrary
export MACHINELIBRARY_API_KEY=ml_...   # https://machinelibrary.ai/keys
```

```python
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.tools.machinelibrary import MachineLibraryToolSpec

agent = FunctionAgent(
    tools=MachineLibraryToolSpec().to_tool_list(),
    llm=llm,  # any function-calling LLM
    system_prompt="Answer from Machine Library sources and cite each claim's source_uri.",
)
response = await agent.run("What evidence links GLP-1 agonists to reduced dementia risk?")
```

Requests are billed per call to the key's account
([pricing](https://machinelibrary.ai/pricing)). Retrieved text is evidence to
review, not proof that an answer is correct.
