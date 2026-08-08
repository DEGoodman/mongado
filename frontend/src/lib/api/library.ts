/**
 * API client for the Library (curated resource catalog, #294)
 */

import { logger } from "@/lib/logger";
import { getAuthHeaders } from "@/lib/api/client";
import { invalidate, revalidatingFetch } from "@/lib/api/cache";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type LibraryEntryType = "book" | "article" | "video" | "doc" | "paper" | "other";

export const LIBRARY_ENTRY_TYPES: LibraryEntryType[] = [
  "book",
  "article",
  "video",
  "doc",
  "paper",
  "other",
];

export interface LibraryEntry {
  id: string;
  title: string;
  source_url: string;
  author: string;
  type: LibraryEntryType;
  summary: string;
  html_summary?: string; // Pre-rendered HTML from backend (#233)
  tags: string[];
  created_at: number;
  updated_at: number;
}

export interface CreateLibraryEntryRequest {
  title: string;
  source_url?: string;
  author?: string;
  type?: LibraryEntryType;
  summary?: string;
  tags?: string[];
}

export type UpdateLibraryEntryRequest = Partial<CreateLibraryEntryRequest>;

export interface LibraryListResponse {
  entries: LibraryEntry[];
  count: number;
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface ListLibraryOptions {
  type?: LibraryEntryType;
  tag?: string;
  page?: number;
  limit?: number;
}

/**
 * List library entries with optional filters and pagination.
 */
export async function listLibraryEntries(
  options?: ListLibraryOptions
): Promise<LibraryListResponse> {
  const params = new URLSearchParams();
  if (options?.type) params.set("type", options.type);
  if (options?.tag) params.set("tag", options.tag);
  if (options?.page !== undefined) params.set("page", String(options.page));
  if (options?.limit !== undefined) params.set("limit", String(options.limit));

  const url = `${API_URL}/api/library?${params.toString()}`;
  const response = await revalidatingFetch(url, { headers: getAuthHeaders() });

  if (!response.ok) {
    logger.error("Failed to list library entries", { status: response.status });
    throw new Error("Failed to list library entries");
  }

  const data = await response.json();
  logger.info("Library entries listed", { count: data.count, total: data.total });
  return data;
}

/**
 * Fetch every library entry across all pages (for the filterable list view).
 */
export async function listAllLibraryEntries(
  options?: Omit<ListLibraryOptions, "page" | "limit">
): Promise<LibraryEntry[]> {
  const all: LibraryEntry[] = [];
  let page = 1;
  let totalPages = 1;
  do {
    const response = await listLibraryEntries({ ...options, page, limit: 100 });
    all.push(...response.entries);
    totalPages = response.total_pages;
    page += 1;
  } while (page <= totalPages);
  return all;
}

/**
 * Get a single library entry by ID.
 */
export async function getLibraryEntry(entryId: string): Promise<LibraryEntry> {
  const response = await revalidatingFetch(`${API_URL}/api/library/${entryId}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    if (response.status === 404) throw new Error("Library entry not found");
    logger.error("Failed to get library entry", { entryId, status: response.status });
    throw new Error("Failed to get library entry");
  }

  return response.json();
}

/**
 * Create a library entry (requires admin authentication).
 */
export async function createLibraryEntry(
  request: CreateLibraryEntryRequest
): Promise<LibraryEntry> {
  const response = await fetch(`${API_URL}/api/library`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    logger.error("Failed to create library entry", { status: response.status, error });
    throw new Error(error.detail || "Failed to create library entry");
  }

  const entry = await response.json();
  invalidate();
  logger.info("Library entry created", { id: entry.id });
  return entry;
}

/**
 * Update a library entry (requires admin authentication).
 */
export async function updateLibraryEntry(
  entryId: string,
  request: UpdateLibraryEntryRequest
): Promise<LibraryEntry> {
  const response = await fetch(`${API_URL}/api/library/${entryId}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    logger.error("Failed to update library entry", { entryId, status: response.status, error });
    throw new Error(error.detail || "Failed to update library entry");
  }

  const entry = await response.json();
  invalidate();
  logger.info("Library entry updated", { id: entry.id });
  return entry;
}

/**
 * Delete a library entry (requires admin authentication).
 */
export async function deleteLibraryEntry(entryId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/library/${entryId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    logger.error("Failed to delete library entry", { entryId, status: response.status, error });
    throw new Error(error.detail || "Failed to delete library entry");
  }

  invalidate();
  logger.info("Library entry deleted", { id: entryId });
}
