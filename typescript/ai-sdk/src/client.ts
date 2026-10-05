/** Minimal fetch client for the Machine Library REST API. */

export const DEFAULT_BASE_URL = 'https://api.machinelibrary.ai';
export const VERSION = '0.1.0';

export interface MachineLibraryOptions {
  /** API key from https://machinelibrary.ai/keys; defaults to MACHINELIBRARY_API_KEY. */
  apiKey?: string;
  baseURL?: string;
  fetch?: typeof fetch;
}

export interface SearchHit {
  title: string;
  source_uri: string;
  score: number;
  snippet?: string;
  abstract?: string;
  authors: string[];
  issued_date?: string;
  document_type?: string;
}

export interface Passage {
  text: string;
  field: string;
}

export interface FetchedDocument {
  title: string;
  source_uri: string;
  content?: string;
  content_truncated: boolean;
  abstract?: string;
  authors: string[];
  issued_date?: string;
}

export class MachineLibraryError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(`Machine Library API error ${status}: ${detail}`);
    this.name = 'MachineLibraryError';
  }
}

type Json = Record<string, unknown>;

const SNIPPET_LIMIT = 900;
const ABSTRACT_LIMIT = 2_000;

export function canonicalUri(uris: string[]): string {
  return (
    uris.find(u => u.includes('doi.org/')) ??
    uris.find(u => u.startsWith('http://') || u.startsWith('https://')) ??
    uris[0] ??
    ''
  );
}

export function normalizeUri(uri: string): string {
  const value = uri.trim();
  const lower = value.toLowerCase();
  for (const prefix of ['https://doi.org/', 'http://doi.org/', 'doi://']) {
    if (lower.startsWith(prefix)) return `doi://${value.slice(prefix.length).toLowerCase()}`;
  }
  const shorthands: [string, string, boolean][] = [
    ['doi:', 'doi://', true],
    ['pmid:', 'pubmed://', false],
    ['pubmed:', 'pubmed://', false],
    ['arxiv:', 'arxiv://', true],
    ['isbn:', 'isbn://', false],
  ];
  for (const [prefix, scheme, lowerRest] of shorthands) {
    if (lower.startsWith(prefix)) {
      const rest = value.slice(prefix.length).replace(/^\/+/, '').trim();
      return scheme + (lowerRest ? rest.toLowerCase() : rest);
    }
  }
  return value;
}

const clip = (text: string, limit: number) =>
  text.length <= limit ? text : `${text.slice(0, limit).trimEnd()}…`;

function authors(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map(a => {
      if (typeof a === 'string') return a.trim();
      if (a && typeof a === 'object') {
        const o = a as Json;
        const name = String(o.name ?? '').trim();
        return name || [o.given, o.family].filter(Boolean).map(String).join(' ').trim();
      }
      return '';
    })
    .filter(Boolean);
}

function date(issuedAt: unknown): string | undefined {
  const seconds = Number(issuedAt);
  if (issuedAt == null || !Number.isFinite(seconds)) return undefined;
  return new Date(seconds * 1000).toISOString().slice(0, 10);
}

function toHit(hit: Json): SearchHit {
  const doc = (hit.document ?? {}) as Json;
  const uris = Array.isArray(doc.uris) ? doc.uris.map(String) : [];
  const snippets = Array.isArray(hit.snippets) ? (hit.snippets as Json[]) : [];
  const snippet = snippets.map(s => String(s.text ?? '').trim()).find(Boolean);
  const abstract = String(doc.abstract ?? '').trim();
  return {
    title: String(doc.title ?? 'Untitled'),
    source_uri: canonicalUri(uris),
    score: Number(hit.score ?? 0),
    snippet: snippet ? clip(snippet, SNIPPET_LIMIT) : undefined,
    abstract: abstract ? clip(abstract, ABSTRACT_LIMIT) : undefined,
    authors: authors(doc.authors),
    issued_date: date(doc.issued_at),
    document_type: typeof doc.type === 'string' ? doc.type : undefined,
  };
}

export class MachineLibrary {
  private readonly apiKey: string;
  private readonly baseURL: string;
  private readonly fetchImpl: typeof fetch;

  constructor(options: MachineLibraryOptions = {}) {
    const key =
      options.apiKey ??
      (typeof process === 'undefined' ? undefined : process.env.MACHINELIBRARY_API_KEY);
    if (!key) {
      throw new MachineLibraryError(
        401,
        'no API key: pass apiKey or set MACHINELIBRARY_API_KEY (https://machinelibrary.ai/keys)',
      );
    }
    this.apiKey = key;
    this.baseURL = (options.baseURL ?? DEFAULT_BASE_URL).replace(/\/+$/, '');
    this.fetchImpl = options.fetch ?? fetch;
  }

  private async request(path: string, init: RequestInit = {}): Promise<Json | null> {
    const response = await this.fetchImpl(`${this.baseURL}${path}`, {
      ...init,
      headers: {
        'X-Api-Key': this.apiKey,
        'Content-Type': 'application/json',
        Accept: 'application/json',
        // Node sends it; browsers ignore it. The gateway logs it for attribution.
        'User-Agent': `machinelibrary-ai-sdk/${VERSION}`,
        ...init.headers,
      },
    });
    if (response.status === 404 && path.startsWith('/v2/documents/')) return null;
    if (!response.ok) {
      let detail = await response.text();
      try {
        detail = String((JSON.parse(detail) as Json).detail ?? detail);
      } catch {
        // Plain-text error body.
      }
      throw new MachineLibraryError(response.status, detail);
    }
    return (await response.json()) as Json;
  }

  async search(query: string, options: { limit?: number; index?: 'documents' | 'social' } = {}) {
    const body = { query, limit: options.limit ?? 10, index_names: [options.index ?? 'documents'] };
    const data = await this.request('/v2/search/', { method: 'POST', body: JSON.stringify(body) });
    return ((data?.hits ?? []) as Json[]).map(toHit);
  }

  async searchInDocument(uri: string, query: string): Promise<Passage[]> {
    const params = new URLSearchParams({ text_filter: query });
    const data = await this.request(
      `/v2/documents/by-uri/${encodeURIComponent(normalizeUri(uri))}?${params}`,
    );
    const passages: Passage[] = [];
    for (const hit of (data?.hits ?? []) as Json[]) {
      for (const s of (Array.isArray(hit.snippets) ? hit.snippets : []) as Json[]) {
        const text = String(s.text ?? '').trim();
        if (text) passages.push({ text, field: String(s.field ?? 'content') });
      }
    }
    return passages;
  }

  async fetchDocument(uri: string, maxChars = 40_000): Promise<FetchedDocument | null> {
    const data = await this.request(`/v2/documents/by-uri/${encodeURIComponent(normalizeUri(uri))}`);
    if (!data) return null;
    const doc = (data.document ?? {}) as Json;
    const uris = (Array.isArray(data.uris) ? data.uris : (doc.uris ?? [])) as string[];
    const content = typeof doc.content === 'string' ? doc.content : undefined;
    const abstract = String(doc.abstract ?? '').trim();
    return {
      title: String(doc.title ?? 'Untitled'),
      source_uri: canonicalUri(uris.map(String)),
      content: content?.slice(0, maxChars),
      content_truncated: Boolean(doc.content_truncated) || (content?.length ?? 0) > maxChars,
      abstract: abstract || undefined,
      authors: authors(doc.authors),
      issued_date: date(doc.issued_at),
    };
  }
}
