/**
 * API client for content inspiration endpoints
 */

import { logger } from "@/lib/logger";
import { getAuthHeaders } from "@/lib/api/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Kinds of suggestion the knowledge base can produce.
 *
 * Note length is deliberately absent: a short atomic note is correct, not a
 * defect, so suggestions describe structural problems instead (see #259).
 */
export type SuggestionType =
  | "orphan" // no links in or out - unreachable in the graph
  | "duplicate" // same idea captured twice - merge
  | "connection" // related but unlinked - add a wikilink
  | "hub" // cluster of related notes with no index
  | "promote" // heavily referenced - could be a full article
  | "split" // long enough to hold several ideas
  | "article"; // many notes on a topic, no article covering it

export interface Suggestion {
  type: SuggestionType;
  title: string;
  description: string;
  related_notes: string[];
  action_text: string;
}

export interface InspireResponse {
  suggestions: Suggestion[];
  generated_at: number;
  has_llm: boolean;
  cached: boolean;
}

export interface OrphanNote {
  note_id: string;
  title: string;
  content_length: number;
  tags: string[];
}

export interface OversizedNote {
  note_id: string;
  title: string;
  content_length: number;
}

export interface PromotableNote {
  note_id: string;
  title: string;
  backlink_count: number;
  content_length: number;
}

export interface UncoveredTopic {
  tag: string;
  note_count: number;
  note_ids: string[];
  titles: string[];
}

export interface GapsResponse {
  orphans: OrphanNote[];
  oversized: OversizedNote[];
  promotable: PromotableNote[];
  uncovered_topics: UncoveredTopic[];
  count: number;
}

export interface NotePair {
  note_a_id: string;
  note_a_title: string;
  note_b_id: string;
  note_b_title: string;
  similarity: number;
  title_overlap: number;
  kind: "duplicate" | "connection";
}

export interface HubOpportunity {
  note_ids: string[];
  titles: string[];
  size: number;
}

export interface ConnectionsResponse {
  connections: NotePair[];
  duplicates: NotePair[];
  hubs: HubOpportunity[];
  count: number;
  similarity_threshold: number;
}

/**
 * Get headers for API requests
 */
function getHeaders(): HeadersInit {
  return getAuthHeaders();
}

interface SuggestionOptions {
  /** Rotate to a different slice of the candidate pool */
  refresh?: boolean;
  /** Return templated wording immediately, without waiting on the LLM */
  skipLlm?: boolean;
}

/**
 * Get content suggestions.
 *
 * With `skipLlm` the backend returns the same suggestions phrased from
 * templates, which lets the page paint immediately and swap in the
 * LLM-phrased versions when they arrive.
 */
export async function getSuggestions(
  limit: number = 5,
  options: SuggestionOptions = {}
): Promise<InspireResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (options.refresh) params.set("refresh", "true");
  if (options.skipLlm) params.set("skip_llm", "true");

  const response = await fetch(`${API_URL}/api/inspire/suggestions?${params.toString()}`, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    logger.error("Failed to get suggestions", { status: response.status });
    throw new Error("Failed to get suggestions");
  }

  const data = await response.json();
  logger.info("Suggestions retrieved", {
    count: data.suggestions.length,
    hasLlm: data.has_llm,
    cached: data.cached,
  });
  return data;
}

/**
 * Get structural gaps: orphaned, oversized, promotable notes and uncovered topics
 */
export async function getKnowledgeGaps(limit: number = 10): Promise<GapsResponse> {
  const params = new URLSearchParams({ limit: String(limit) });

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
 * Get connection opportunities: unlinked similar notes, duplicates, and hub clusters
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
