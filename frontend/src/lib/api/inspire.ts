/**
 * API client for content inspiration endpoints
 */

import { logger } from "@/lib/logger";
import { getAuthHeaders } from "@/lib/api/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Suggestion {
  type: "gap" | "connection";
  title: string;
  description: string;
  related_notes: string[];
  action_text: string;
}

export interface InspireResponse {
  suggestions: Suggestion[];
  generated_at: number;
  has_llm: boolean;
}

export interface GapNote {
  note_id: string;
  title: string;
  content_length: number;
  link_count: number;
  backlink_count: number;
  is_short: boolean;
  has_few_links: boolean;
}

export interface GapsResponse {
  gaps: GapNote[];
  count: number;
  min_content_length: number;
  max_links: number;
}

export interface ConnectionOpportunity {
  note_a_id: string;
  note_a_title: string;
  note_b_id: string;
  note_b_title: string;
  similarity: number;
}

export interface ConnectionsResponse {
  connections: ConnectionOpportunity[];
  count: number;
  similarity_threshold: number;
}

/**
 * Get headers for API requests
 */
function getHeaders(): HeadersInit {
  return getAuthHeaders();
}

/**
 * Get AI-powered content suggestions
 */
export async function getSuggestions(limit: number = 5): Promise<InspireResponse> {
  const response = await fetch(`${API_URL}/api/inspire/suggestions?limit=${limit}`, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    logger.error("Failed to get suggestions", { status: response.status });
    throw new Error("Failed to get suggestions");
  }

  const data = await response.json();
  logger.info("Suggestions retrieved", { count: data.suggestions.length, hasLlm: data.has_llm });
  return data;
}

/**
 * Get knowledge gaps (underdeveloped topics)
 */
export async function getKnowledgeGaps(
  minContentLength: number = 500,
  maxLinks: number = 1,
  limit: number = 10
): Promise<GapsResponse> {
  const params = new URLSearchParams({
    min_content_length: String(minContentLength),
    max_links: String(maxLinks),
    limit: String(limit),
  });

  const response = await fetch(`${API_URL}/api/inspire/gaps?${params.toString()}`, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    logger.error("Failed to get knowledge gaps", { status: response.status });
    throw new Error("Failed to get knowledge gaps");
  }

  const data = await response.json();
  logger.info("Knowledge gaps retrieved", { count: data.count });
  return data;
}

/**
 * Get connection opportunities (unlinked similar notes)
 */
export async function getConnectionOpportunities(
  similarityThreshold: number = 0.7,
  limit: number = 10
): Promise<ConnectionsResponse> {
  const params = new URLSearchParams({
    similarity_threshold: String(similarityThreshold),
    limit: String(limit),
  });

  const response = await fetch(`${API_URL}/api/inspire/connections?${params.toString()}`, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    logger.error("Failed to get connection opportunities", { status: response.status });
    throw new Error("Failed to get connection opportunities");
  }

  const data = await response.json();
  logger.info("Connection opportunities retrieved", { count: data.count });
  return data;
}
