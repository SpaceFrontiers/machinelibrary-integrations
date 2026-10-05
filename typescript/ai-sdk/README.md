# @machinelibrary/ai-sdk

[Machine Library](https://machinelibrary.ai) tools for the
[Vercel AI SDK](https://ai-sdk.dev): citable search across scholarly papers,
books, patents, standards and Wikipedia (or Reddit, Telegram and Discord),
passage search inside a document, and bounded full text. Results carry a
`source_uri` your app can show as a citation.

```bash
npm install @machinelibrary/ai-sdk ai zod
export MACHINELIBRARY_API_KEY=ml_...   # https://machinelibrary.ai/keys
```

```ts
import { generateText, stepCountIs } from 'ai';
import { anthropic } from '@ai-sdk/anthropic';
import { machineLibraryTools } from '@machinelibrary/ai-sdk';

const { text } = await generateText({
  model: anthropic('claude-sonnet-5-5'),
  tools: machineLibraryTools(),
  stopWhen: stepCountIs(8),
  system: 'Answer from Machine Library sources and cite each claim with its source_uri.',
  prompt: 'What limits the cycle life of lithium-metal anodes?',
});
```

| Tool | Use |
| --- | --- |
| `machinelibrary_search` | Find documents; returns passages and `source_uri` |
| `machinelibrary_search_in_document` | Passages supporting a claim inside one document |
| `machinelibrary_fetch_document` | Bounded full text when the body is needed |

`MachineLibrary` is also exported for direct use (`search`, `searchInDocument`,
`fetchDocument`).

Each call is billed to the key's account ([pricing](https://machinelibrary.ai/pricing)).
Retrieved text is evidence to review, not proof that an answer is correct.

MIT license.
