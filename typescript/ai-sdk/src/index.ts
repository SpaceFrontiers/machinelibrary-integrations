/**
 * Machine Library tools for the Vercel AI SDK.
 *
 *   import { machineLibraryTools } from '@machinelibrary/ai-sdk';
 *   const result = await generateText({ model, tools: machineLibraryTools(), prompt });
 */

import { tool } from 'ai';
import { z } from 'zod';

import { MachineLibrary, type MachineLibraryOptions } from './client.js';

export * from './client.js';

export function machineLibraryTools(options: MachineLibraryOptions = {}) {
  const client = new MachineLibrary(options);
  return {
    machinelibrary_search: tool({
      description:
        'Search scholarly papers, books, patents, standards and Wikipedia (or Reddit, Telegram ' +
        "and Discord with index 'social'). Returns passages and a source_uri to cite and to pass " +
        'to the other Machine Library tools. Do not invent sources.',
      inputSchema: z.object({
        query: z.string().min(1).describe('What to look for.'),
        limit: z.number().int().min(1).max(50).default(10).describe('Number of documents.'),
        index: z.enum(['documents', 'social']).default('documents'),
      }),
      execute: async ({ query, limit, index }) => client.search(query, { limit, index }),
    }),
    machinelibrary_search_in_document: tool({
      description:
        'Find up to five passages inside one document (by source_uri) that match a claim or ' +
        'topic. Quote them when citing; an empty list means no supporting passage.',
      inputSchema: z.object({
        source_uri: z.string().min(1).describe('A source_uri from a search result, or a DOI.'),
        query: z.string().min(1).describe('The claim or topic to find evidence for.'),
      }),
      execute: async ({ source_uri, query }) => client.searchInDocument(source_uri, query),
    }),
    machinelibrary_fetch_document: tool({
      description:
        'Read the bounded full text of one document by source_uri. Prefer ' +
        'machinelibrary_search_in_document when you only need specific evidence.',
      inputSchema: z.object({
        source_uri: z.string().min(1).describe('A source_uri from a search result, or a DOI.'),
      }),
      execute: async ({ source_uri }) =>
        (await client.fetchDocument(source_uri)) ?? { error: 'document not found' },
    }),
  };
}
