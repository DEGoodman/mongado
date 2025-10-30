/**
 * API client for Zettelkasten notes endpoints
 */

import { logger } from "@/lib/logger";
import { getAuthHeaders as getBaseAuthHeaders } from "@/lib/api/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Note {
  id: string;
  title: string | null;
  content: string;
  author: string;
  is_ephemeral: boolean;
  tags: string[];
  created_at: number | string;
  updated_at: number | string;
  links: string[];
  session_id?: string;
}

export interface CreateNoteRequest {
  content: string;
  title?: string;
  tags?: string[];
}

export interface UpdateNoteRequest {
  content: string;
  title?: string;
  tags?: string[];
}

export interface NotesListResponse {
  notes: Note[];
  count: number;
}

export interface BacklinksResponse {
  backlinks: Note[];
  count: number;
}

export interface OutboundLinksResponse {
  links: Note[];
  count: number;
}

/**
 * Get headers with authentication and session ID
 * This now uses the shared getAuthHeaders which includes Authorization header
 */
function getHeaders(): HeadersInit {
  return getBaseAuthHeaders();
}

/**
 * Create a new note (requires admin authentication)
 */
export async function createNote(request: CreateNoteRequest): Promise<Note> {
  const response = await fetch(`${API_URL}/api/notes`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    logger.error("Failed to create note", { status: response.status, error });
    throw new Error(error.detail || "Failed to create note");
  }

  const note = await response.json();
  logger.info("Note created", { id: note.id });
  return note;
}

/**
 * List all notes
 */
export async function listNotes(): Promise<NotesListResponse> {
  const response = await fetch(`${API_URL}/api/notes`, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    logger.error("Failed to list notes", { status: response.status });
    throw new Error("Failed to list notes");
  }

  const data = await response.json();
  logger.info("Notes listed", { count: data.count });
  return data;
}

/**
 * Get a specific note by ID
 */
export async function getNote(noteId: string): Promise<Note> {
  const response = await fetch(`${API_URL}/api/notes/${noteId}`, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Note not found");
    }
    logger.error("Failed to get note", { noteId, status: response.status });
    throw new Error("Failed to get note");
  }

  const note = await response.json();
  logger.info("Note retrieved", { id: note.id });
  return note;
}

/**
 * Get a random note for serendipitous discovery
 */
export async function getRandomNote(): Promise<Note> {
  const response = await fetch(`${API_URL}/api/notes/random`, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("No notes available");
    }
    logger.error("Failed to get random note", { status: response.status });
    throw new Error("Failed to get random note");
  }

  const note = await response.json();
  logger.info("Random note retrieved", { id: note.id });
  return note;
}

/**
 * Update a note
 */
export async function updateNote(noteId: string, request: UpdateNoteRequest): Promise<Note> {
  const response = await fetch(`${API_URL}/api/notes/${noteId}`, {
    method: "PUT",
    headers: getHeaders(),
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    logger.error("Failed to update note", { noteId, status: response.status, error });
    throw new Error(error.detail || "Failed to update note");
  }

  const note = await response.json();
  logger.info("Note updated", { id: note.id });
  return note;
}

/**
 * Delete a note
 */
export async function deleteNote(noteId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/notes/${noteId}`, {
    method: "DELETE",
    headers: getHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    logger.error("Failed to delete note", { noteId, status: response.status, error });
    throw new Error(error.detail || "Failed to delete note");
  }

  logger.info("Note deleted", { id: noteId });
}

/**
 * Get notes that link to this note (backlinks)
 */
export async function getBacklinks(noteId: string): Promise<BacklinksResponse> {
  const response = await fetch(`${API_URL}/api/notes/${noteId}/backlinks`, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    logger.error("Failed to get backlinks", { noteId, status: response.status });
    throw new Error("Failed to get backlinks");
  }

  const data = await response.json();
  logger.info("Backlinks retrieved", { noteId, count: data.count });
  return data;
}

/**
 * Get notes this note links to (outbound links)
 */
export async function getOutboundLinks(noteId: string): Promise<OutboundLinksResponse> {
  const response = await fetch(`${API_URL}/api/notes/${noteId}/links`, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    logger.error("Failed to get outbound links", { noteId, status: response.status });
    throw new Error("Failed to get outbound links");
  }

  const data = await response.json();
  logger.info("Outbound links retrieved", { noteId, count: data.count });
  return data;
}

/**
 * Extract wikilinks from markdown content
 */
export function extractWikilinks(content: string): string[] {
  const pattern = /\[\[([a-z0-9-]+)\]\]/g;
  const matches = content.matchAll(pattern);
  return Array.from(matches, (m) => m[1]);
}

/**
 * Format date for display
 */
export function formatNoteDate(timestamp: number | string): string {
  const date = typeof timestamp === "number" ? new Date(timestamp * 1000) : new Date(timestamp);

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}
