import { describe, expect, it, vi } from 'vitest';

import { MachineLibrary, machineLibraryTools, normalizeUri } from '../src/index.js';

const HIT = {
  id: 'd1',
  score: 0.7,
  snippets: [{ field: 'content', text: 'Base editors reduce indels.' }],
  document: { title: 'Base editing', uris: ['doi://10.4/z', 'https://doi.org/10.4/z'], issued_at: 1704067200 },
};

const ok = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });

describe('MachineLibrary client', () => {
  it('searches with the key and returns citable hits', async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok({ hits: [HIT] }));
    const hits = await new MachineLibrary({ apiKey: 'ml_k', fetch: fetchMock }).search('base editing', { limit: 3 });
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe('https://api.machinelibrary.ai/v2/search/');
    expect((init.headers as Record<string, string>)['X-Api-Key']).toBe('ml_k');
    expect(JSON.parse(init.body)).toMatchObject({ limit: 3, index_names: ['documents'] });
    expect(hits[0]).toMatchObject({ source_uri: 'https://doi.org/10.4/z', issued_date: '2024-01-01' });
  });

  it('treats an unknown document as null and other errors as exceptions', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response('', { status: 404 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'Insufficient balance' }), { status: 402 }));
    const ml = new MachineLibrary({ apiKey: 'ml_k', fetch: fetchMock });
    expect(await ml.fetchDocument('doi:10.4/none')).toBeNull();
    await expect(ml.search('x')).rejects.toThrow('402');
  });

  it('requires an API key', () => {
    const saved = process.env.MACHINELIBRARY_API_KEY;
    delete process.env.MACHINELIBRARY_API_KEY;
    expect(() => new MachineLibrary()).toThrow('MACHINELIBRARY_API_KEY');
    if (saved) process.env.MACHINELIBRARY_API_KEY = saved;
  });

  it('normalizes identifiers', () => {
    expect(normalizeUri('https://doi.org/10.1038/Nature14539')).toBe('doi://10.1038/nature14539');
    expect(normalizeUri('pmid:123')).toBe('pubmed://123');
  });
});

describe('AI SDK tools', () => {
  it('exposes three tools whose search returns source_uri', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => ok({ hits: [HIT] }));
    const tools = machineLibraryTools({ apiKey: 'ml_k', fetch: fetchMock });
    expect(Object.keys(tools)).toEqual([
      'machinelibrary_search',
      'machinelibrary_search_in_document',
      'machinelibrary_fetch_document',
    ]);
    const result = await tools.machinelibrary_search.execute!(
      { query: 'base editing', limit: 2, index: 'documents' },
      { toolCallId: 't1', messages: [] } as never,
    );
    expect((result as { source_uri: string }[])[0]!.source_uri).toBe('https://doi.org/10.4/z');
    const passages = await tools.machinelibrary_search_in_document.execute!(
      { source_uri: 'doi:10.4/z', query: 'indels' },
      { toolCallId: 't2', messages: [] } as never,
    );
    expect(passages).toEqual([{ text: 'Base editors reduce indels.', field: 'content' }]);
    expect(String(fetchMock.mock.calls[1]![0])).toContain('/v2/documents/by-uri/doi%3A%2F%2F10.4%2Fz?text_filter=indels');
  });
});
