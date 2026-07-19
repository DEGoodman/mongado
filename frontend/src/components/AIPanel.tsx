"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  MagnifyingGlass,
  ChatCircle,
  Sparkle,
  Warning,
  Tag,
  LinkSimple,
} from "@phosphor-icons/react";
import { logger } from "@/lib/logger";
import type { AiMode } from "@/lib/settings";
import Toast from "@/components/Toast";
import {
  streamAISuggestions,
  isStreamingSupported,
  type TagSuggestion,
  type LinkSuggestion,
  type StreamPhase,
} from "@/lib/aiSuggestionsStream";
import styles from "./AIPanel.module.scss";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const IS_DEVELOPMENT = process.env.NODE_ENV === "development";
const SUGGEST_DEBOUNCE_MS = 5000; // real-time mode: refetch after typing pauses

export type PanelTab = "search" | "ask" | "suggest";

/** Note context that enables the Suggest tab (requires a saved note) */
export interface SuggestContext {
  noteId: string;
  aiMode: AiMode;
  /** Current editor content, if editing — used for outdated detection and real-time refresh */
  content?: string;
  onAddTag?: (tag: string) => void;
  onInsertLink: (noteId: string) => void;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{
    id: number | string;
    type?: "article" | "note";
    title: string;
    content: string;
    score?: number;
  }>;
}

interface AIPanelProps {
  isOpen: boolean;
  onClose: () => void;
  /** Tab to show; applied whenever this prop changes (pages set it when opening) */
  defaultTab?: PanelTab;
  /** Enables the Suggest tab for a saved note */
  suggest?: SuggestContext;
}

export default function AIPanel({ isOpen, onClose, defaultTab, suggest }: AIPanelProps) {
  const [tab, setTab] = useState<PanelTab>(defaultTab ?? "search");
  const [hasGPU, setHasGPU] = useState<boolean | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [forceCpuMode, setForceCpuMode] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const warmupStartedRef = useRef(false);

  // Apply defaultTab whenever the page changes it (e.g. "AI Suggestions" button)
  useEffect(() => {
    if (defaultTab) {
      setTab(defaultTab);
    }
  }, [defaultTab]);

  // Fall back off the Suggest tab if context disappears (e.g. leaving edit mode)
  useEffect(() => {
    if (!suggest && tab === "suggest") {
      setTab("search");
    }
  }, [suggest, tab]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load force CPU mode from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("ai-force-cpu-mode");
    if (stored !== null) {
      setForceCpuMode(stored === "true");
    }
  }, []);

  // Save force CPU mode to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("ai-force-cpu-mode", String(forceCpuMode));
  }, [forceCpuMode]);

  // Close settings dropdown when clicking outside
  useEffect(() => {
    if (!showSettings) return;

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest(".settings-dropdown")) {
        setShowSettings(false);
      }
    };

    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, [showSettings]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      if (tab === "ask") {
        // Ask mode - Q&A with hybrid KB + general knowledge
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 second timeout (CPU can be slow)

        const response = await fetch(`${API_URL}/api/ask`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: userMessage.content,
          }),
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`Request failed: ${response.statusText}`);
        }

        const data = await response.json();

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: data.answer,
          sources: data.sources || [],
        };

        setMessages((prev) => [...prev, assistantMessage]);
        logger.info("Question answered", { question: userMessage.content });
      } else {
        // Search mode - Semantic search
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 90000); // 90 second timeout

        const response = await fetch(`${API_URL}/api/search`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: userMessage.content,
            semantic: true,
            limit: 10,
          }),
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`Search failed: ${response.statusText}`);
        }

        const data = await response.json();
        const results = data.results || [];

        const resultText =
          results.length > 0
            ? `Found ${results.length} result${results.length !== 1 ? "s" : ""}:`
            : "No results found.";

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: resultText,
          sources: results.map(
            (r: {
              id: number | string;
              type?: "article" | "note";
              title: string;
              content: string;
              score?: number;
            }) => ({
              id: r.id,
              type: r.type,
              title: r.title,
              content: r.content,
              score: r.score,
            })
          ),
        };

        setMessages((prev) => [...prev, assistantMessage]);
        logger.info("Semantic search completed", {
          query: userMessage.content,
          resultCount: results.length,
        });
      }
    } catch (err) {
      let errorContent = "Failed to process request. Make sure Ollama is running.";

      if (err instanceof Error) {
        if (err.name === "AbortError") {
          errorContent =
            "Request timed out after 120 seconds. The AI model may be overloaded or CPU inference is too slow. Try a shorter question or use Search mode.";
        } else if (err.message.includes("Failed to fetch")) {
          errorContent = "Network error: Could not connect to the API server.";
        } else {
          errorContent = `Error: ${err.message}`;
        }
      }

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: errorContent,
      };
      setMessages((prev) => [...prev, errorMessage]);
      logger.error("AI request failed", err);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
  };

  const handleTabChange = (newTab: PanelTab) => {
    setTab(newTab);
    // Clear messages when switching between search and ask for clarity
    if (newTab !== "suggest") {
      setMessages([]);
    }
  };

  // Check GPU status and warm up Ollama when AI Panel opens
  useEffect(() => {
    if (!isOpen) return;

    // Check GPU status
    const checkGPU = async () => {
      try {
        // If force CPU mode is enabled, always report no GPU
        if (forceCpuMode) {
          setHasGPU(false);
          logger.info("Force CPU mode enabled - simulating CPU-only environment");
          return;
        }

        const response = await fetch(`${API_URL}/api/ollama/gpu-status`);
        if (response.ok) {
          const data = await response.json();
          setHasGPU(data.has_gpu);
          logger.info("GPU status checked", { has_gpu: data.has_gpu });
        }
      } catch (err) {
        logger.warn("Failed to check GPU status", err);
        setHasGPU(false); // Assume no GPU on error
      }
    };

    // Prevent duplicate warmups
    if (!warmupStartedRef.current) {
      warmupStartedRef.current = true;

      const warmupOllama = async () => {
        try {
          logger.info("Starting Ollama warmup (AI Assistant opened)");
          const response = await fetch(`${API_URL}/api/ollama/warmup`, {
            method: "POST",
          });

          if (response.ok) {
            const data = await response.json();
            logger.info("Ollama warmup completed", { duration: data.duration_seconds });
          } else {
            logger.warn("Ollama warmup failed", { status: response.status });
          }
        } catch (err) {
          // Silently fail - warmup is optional optimization
          logger.debug("Ollama warmup error (non-critical)", err);
        }
      };

      // Fire both in parallel
      checkGPU();
      warmupOllama();
    } else {
      // Just check GPU if warmup already done
      checkGPU();
    }
  }, [isOpen, forceCpuMode]);

  if (!isOpen) return null;

  const suggestActive = tab === "suggest" && suggest !== undefined;

  return (
    <div className={styles.panel}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerTop}>
          <h2 className={styles.title}>AI Assistant</h2>
          <div className={styles.headerActions}>
            {/* Settings Dropdown - Only in Development */}
            {IS_DEVELOPMENT && (
              <div className={styles.settingsDropdown}>
                <button
                  onClick={() => setShowSettings(!showSettings)}
                  className={styles.settingsButton}
                  aria-label="Settings"
                >
                  <svg
                    className={styles.settingsIcon}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                  </svg>
                </button>
                {showSettings && (
                  <div className={styles.settingsPanel}>
                    <div className={styles.settingsTitle}>Developer Settings</div>
                    <label className={styles.settingsOption}>
                      <span className={styles.label}>Force CPU Mode</span>
                      <input
                        type="checkbox"
                        checked={forceCpuMode}
                        onChange={(e) => setForceCpuMode(e.target.checked)}
                        className={styles.checkbox}
                      />
                    </label>
                    <p className={styles.settingsDescription}>
                      Simulates CPU-only environment for testing production performance on
                      GPU-enabled machines.
                    </p>
                  </div>
                )}
              </div>
            )}
            <button onClick={onClose} className={styles.closeButton} aria-label="Close AI panel">
              <svg
                className={styles.closeIcon}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>
        {/* Tab Switcher - Search first (faster) */}
        <div className={styles.modeSwitcher}>
          <button
            onClick={() => handleTabChange("search")}
            className={`${styles.modeButton} ${tab === "search" ? styles.active : styles.inactive}`}
          >
            <MagnifyingGlass size={14} aria-hidden="true" /> Search
          </button>
          <button
            onClick={() => handleTabChange("ask")}
            className={`${styles.modeButton} ${tab === "ask" ? styles.active : styles.inactive}`}
          >
            <ChatCircle size={14} aria-hidden="true" /> Ask
          </button>
          {suggest && (
            <button
              onClick={() => handleTabChange("suggest")}
              className={`${styles.modeButton} ${tab === "suggest" ? styles.active : styles.inactive}`}
            >
              <Sparkle size={14} aria-hidden="true" /> Suggest
            </button>
          )}
        </div>
      </div>

      {/* Suggest view - kept mounted while panel is open so results survive tab switches */}
      {suggest && (
        <div hidden={!suggestActive} className={styles.suggestContainer}>
          <SuggestView context={suggest} active={suggestActive} />
        </div>
      )}

      {/* Search / Ask view */}
      <div hidden={suggestActive} className={styles.chatContainer}>
        <div className={styles.messagesContainer} style={{ WebkitOverflowScrolling: "touch" }}>
          {messages.length === 0 && (
            <div className={styles.emptyState}>
              {tab === "ask" ? (
                <>
                  <p className={styles.emptyTitle}>Conversational Q&A</p>
                  <p className={styles.emptyDescription}>
                    Ask questions like &quot;What is systems thinking?&quot; I&apos;ll search your
                    knowledge base and provide answers with context. For finding related content,
                    use the Search tab.
                  </p>
                  {hasGPU === false && (
                    <div className={styles.performanceNotice}>
                      <p className={styles.noticeTitle}>
                        <Warning size={14} aria-hidden="true" /> Performance Notice
                      </p>
                      <p className={styles.noticeDescription}>
                        This feature is under active development and currently running on CPU-only
                        infrastructure. Response times may be 60-120 seconds. For faster results,
                        use the Search tab.
                      </p>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <p className={styles.emptyTitle}>AI Semantic Search</p>
                  <p className={styles.emptyDescription}>
                    Find conceptually related content using AI embeddings. Discovers connections
                    even without exact keyword matches. Fast with pre-computed embeddings. For
                    keyword search, use the main search box.
                  </p>
                </>
              )}
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`${styles.messageWrapper} ${message.role === "user" ? styles.user : styles.assistant}`}
            >
              <div
                className={`${styles.message} ${message.role === "user" ? styles.userMessage : styles.assistantMessage}`}
              >
                <p className={styles.messageContent}>{message.content}</p>

                {/* Sources */}
                {message.sources && message.sources.length > 0 && (
                  <div className={styles.sources}>
                    {message.sources.map((source, idx) => {
                      const resourcePath =
                        source.type === "article"
                          ? `/knowledge-base/articles/${source.id}`
                          : source.type === "note"
                            ? `/knowledge-base/notes/${source.id}`
                            : null;

                      return (
                        <div key={`${source.id}-${idx}`} className={styles.sourceCard}>
                          <div className={styles.sourceHeader}>
                            <div className={styles.sourceInfo}>
                              <span className={styles.sourceTitle}>
                                <span className={styles.sourceType} data-type={source.type}>
                                  {source.type === "article"
                                    ? "ART"
                                    : source.type === "note"
                                      ? "NOTE"
                                      : "REF"}
                                </span>{" "}
                                {source.title || `Document ${source.id}`}
                              </span>
                              {source.score && (
                                <span className={styles.sourceScore}>
                                  {source.score.toFixed(3)}
                                </span>
                              )}
                            </div>
                            {resourcePath && (
                              <a
                                href={resourcePath}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={styles.sourceLink}
                              >
                                View →
                              </a>
                            )}
                          </div>
                          <div className={styles.sourceContent}>{source.content}</div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className={styles.loadingWrapper}>
              <div className={styles.loadingBubble}>
                <div className={styles.loadingDots}>
                  <div className={styles.loadingDot}></div>
                  <div className={styles.loadingDot}></div>
                  <div className={styles.loadingDot}></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} className={styles.messagesEnd} />
        </div>

        {/* Input */}
        <div className={styles.inputArea}>
          {messages.length > 0 && (
            <button onClick={handleClear} className={styles.clearButton}>
              Clear {tab === "ask" ? "conversation" : "results"}
            </button>
          )}
          <form onSubmit={handleSubmit} className={styles.inputForm}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={tab === "ask" ? "Ask a question..." : "Search query..."}
              className={styles.input}
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className={styles.submitButton}
            >
              {loading ? "..." : tab === "ask" ? "Send" : "Search"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

// ===== Suggest tab =====

interface CachedSuggestions {
  tags: TagSuggestion[];
  links: LinkSuggestion[];
  contentHash: string;
}

// Simple hash function for content
function hashContent(content: string): string {
  let hash = 0;
  for (let i = 0; i < content.length; i++) {
    const char = content.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return hash.toString(36);
}

function SuggestView({ context, active }: { context: SuggestContext; active: boolean }) {
  const { noteId, aiMode, content, onAddTag, onInsertLink } = context;

  const [tagSuggestions, setTagSuggestions] = useState<TagSuggestion[]>([]);
  const [linkSuggestions, setLinkSuggestions] = useState<LinkSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState<string>("");
  const [streamPhase, setStreamPhase] = useState<StreamPhase>("idle");
  const [tokenCount, setTokenCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [cachedData, setCachedData] = useState<CachedSuggestions | null>(null);
  const [isOutdated, setIsOutdated] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);
  const streamCleanupRef = useRef<(() => void) | null>(null);
  const tagsRef = useRef<TagSuggestion[]>([]);
  const linksRef = useRef<LinkSuggestion[]>([]);

  // Check if current content matches cached content
  useEffect(() => {
    if (cachedData && content) {
      const currentHash = hashContent(content);
      setIsOutdated(currentHash !== cachedData.contentHash);
    }
  }, [content, cachedData]);

  // Streaming fetch using SSE
  const fetchSuggestionsStreaming = useCallback(() => {
    // Clean up any existing stream
    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }

    setLoading(true);
    setError(null);
    setTagSuggestions([]);
    setLinkSuggestions([]);
    tagsRef.current = [];
    linksRef.current = [];
    setStreamPhase("idle");
    setTokenCount(0);
    setLoadingStatus("Connecting to AI service...");

    const cleanup = streamAISuggestions(noteId, {
      onProgress: (phase) => {
        setStreamPhase(phase);
        setTokenCount(0); // Reset token count when phase changes
        if (phase === "tags") {
          setLoadingStatus("Generating tag suggestions...");
        } else if (phase === "links") {
          setLoadingStatus("Finding related notes...");
        }
      },
      onGenerating: (_phase, tokens) => {
        setTokenCount(tokens);
      },
      onTag: (tag) => {
        tagsRef.current = [...tagsRef.current, tag];
        setTagSuggestions(tagsRef.current);
      },
      onLink: (link) => {
        linksRef.current = [...linksRef.current, link];
        setLinkSuggestions(linksRef.current);
      },
      onComplete: () => {
        setLoading(false);
        setLoadingStatus("");
        setStreamPhase("complete");

        // Cache the results (against current content when editing, else note id marker)
        setCachedData({
          tags: tagsRef.current,
          links: linksRef.current,
          contentHash: content ? hashContent(content) : "saved",
        });
        setIsOutdated(false);

        logger.info("AI suggestions streaming complete");

        // Show toast notification for automatic mode
        if (aiMode === "real-time") {
          setShowToast(true);
        }
      },
      onError: (message) => {
        setError(message);
        setLoading(false);
        setLoadingStatus("");
        setStreamPhase("error");
        logger.error("AI suggestions streaming failed", { message });
      },
    });

    streamCleanupRef.current = cleanup;
  }, [noteId, content, aiMode]);

  // Non-streaming fallback fetch
  const fetchSuggestionsFallback = useCallback(async () => {
    setLoading(true);
    setError(null);
    setLoadingStatus("Generating AI suggestions... typically takes 10-15 seconds");

    try {
      // Fetch tags first
      setLoadingStatus("Finding relevant tags...");
      const tagsResponse = await fetch(`${API_URL}/api/notes/${noteId}/suggest-tags`, {
        method: "POST",
      });

      if (!tagsResponse.ok) {
        throw new Error("Failed to fetch tag suggestions");
      }

      const tagsData = await tagsResponse.json();
      setTagSuggestions(tagsData.suggestions || []);
      setLoadingStatus("Analyzing related notes...");

      // Then fetch links
      const linksResponse = await fetch(`${API_URL}/api/notes/${noteId}/suggest-links`, {
        method: "POST",
      });

      if (!linksResponse.ok) {
        throw new Error("Failed to fetch link suggestions");
      }

      const linksData = await linksResponse.json();
      setLinkSuggestions(linksData.suggestions || []);

      setCachedData({
        tags: tagsData.suggestions || [],
        links: linksData.suggestions || [],
        contentHash: content ? hashContent(content) : "saved",
      });
      setIsOutdated(false);

      logger.info("AI suggestions fetched", {
        tags: tagsData.count,
        links: linksData.count,
      });

      // Show toast notification for automatic mode
      if (aiMode === "real-time") {
        setShowToast(true);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load suggestions";
      setError(message);
      logger.error("Failed to fetch AI suggestions", err);
    } finally {
      setLoading(false);
      setLoadingStatus("");
    }
  }, [noteId, content, aiMode]);

  // Main fetch function - uses streaming if available
  const fetchSuggestions = useCallback(() => {
    if (isStreamingSupported()) {
      fetchSuggestionsStreaming();
    } else {
      fetchSuggestionsFallback();
    }
  }, [fetchSuggestionsStreaming, fetchSuggestionsFallback]);

  // Cleanup stream on unmount
  useEffect(() => {
    return () => {
      if (streamCleanupRef.current) {
        streamCleanupRef.current();
      }
    };
  }, []);

  // Auto-fetch when the tab becomes active and nothing is cached yet.
  // Outdated results are refreshed explicitly (Refresh button) or by the
  // real-time debounce below - never on every keystroke.
  useEffect(() => {
    if (active && !loading && !error && !cachedData) {
      fetchSuggestions();
    }
  }, [active, loading, error, cachedData, fetchSuggestions]);

  // Real-time mode: auto-refresh suggestions when content changes (debounced)
  useEffect(() => {
    if (aiMode !== "real-time" || !content || !active) {
      return;
    }

    // Clear existing timer
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    // Set new timer to fetch suggestions after debounce period
    debounceTimer.current = setTimeout(() => {
      // Only fetch if content is non-empty
      if (content.trim().length > 10) {
        fetchSuggestions();
      }
    }, SUGGEST_DEBOUNCE_MS);

    // Cleanup timer on unmount or when dependencies change
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [aiMode, content, fetchSuggestions, active]);

  const hasAnySuggestions = tagSuggestions.length + linkSuggestions.length > 0;

  return (
    <div className={styles.suggestView}>
      {/* Status row */}
      <div className={styles.suggestStatusRow}>
        {aiMode === "real-time" && (
          <div className={styles.modeIndicator}>
            {loading && <div className={styles.autoIndicatorDot}></div>}
            <span className={styles.autoIndicatorLabel}>Automatic mode</span>
          </div>
        )}
        {isOutdated && !loading && (
          <button
            onClick={fetchSuggestions}
            className={styles.refreshButton}
            title="Content has changed - refresh suggestions"
          >
            🔄 Refresh
          </button>
        )}
      </div>

      {/* Streaming Progress Indicator */}
      {loading && (
        <div className={styles.streamingProgress}>
          <div className={styles.suggestLoadingContent}>
            <div className={styles.spinner}></div>
            <div className={styles.progressText}>
              <span className={styles.progressStatus}>
                {loadingStatus}
                {tokenCount > 0 && ` (${tokenCount} tokens)`}
              </span>
              <span className={styles.progressCounts}>
                {tagSuggestions.length > 0 && `${tagSuggestions.length} tags`}
                {tagSuggestions.length > 0 && streamPhase === "links" && ", "}
                {streamPhase === "links" && `${linkSuggestions.length} links`}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className={styles.errorBanner}>
          {error}
          <button onClick={fetchSuggestions} className={styles.retryButton}>
            Retry
          </button>
        </div>
      )}

      {/* Empty State - a completed fetch yielded nothing */}
      {!loading && !hasAnySuggestions && !error && cachedData !== null && (
        <div className={styles.emptyState}>
          <p className={styles.emptyTitle}>No suggestions found.</p>
          <p className={styles.emptyDescription}>This note might be exploring a new topic!</p>
        </div>
      )}

      {/* Outdated Warning */}
      {isOutdated && !loading && hasAnySuggestions && (
        <div className={styles.outdatedBanner}>
          <Warning size={14} aria-hidden="true" /> Suggestions may be outdated - content has changed
          since generation.
        </div>
      )}

      {/* Tag Suggestions - show progressively during streaming */}
      {tagSuggestions.length > 0 && (
        <div className={styles.suggestionsSection}>
          <h4 className={styles.sectionTitle}>
            <Tag size={14} aria-hidden="true" /> Suggested Tags
          </h4>
          <div className={styles.suggestionsList}>
            {tagSuggestions.map((suggestion, index) => (
              <div key={index} className={`${styles.suggestionCard} ${styles.fadeIn}`}>
                <div className={styles.suggestionHeader}>
                  <span className={styles.suggestionTitle}>{suggestion.tag}</span>
                  {onAddTag && (
                    <button
                      onClick={() => {
                        onAddTag(suggestion.tag);
                        // Remove from current suggestions (optimistic UI)
                        tagsRef.current = tagsRef.current.filter((_, i) => i !== index);
                        setTagSuggestions(tagsRef.current);
                      }}
                      className={styles.suggestionAction}
                    >
                      Add
                    </button>
                  )}
                </div>
                <p className={styles.suggestionReason}>{suggestion.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Link Suggestions - show progressively during streaming */}
      {linkSuggestions.length > 0 && (
        <div className={styles.suggestionsSection}>
          <h4 className={styles.sectionTitle}>
            <LinkSimple size={14} aria-hidden="true" /> Suggested Links
          </h4>
          <div className={styles.suggestionsList}>
            {linkSuggestions.map((suggestion, index) => (
              <div key={index} className={`${styles.suggestionCard} ${styles.fadeIn}`}>
                <div className={styles.suggestionHeader}>
                  <div className={styles.suggestionMeta}>
                    <div className={styles.suggestionSubtitle}>{suggestion.title}</div>
                    <code className={styles.suggestionNoteId}>{suggestion.note_id}</code>
                  </div>
                  <button
                    onClick={() => {
                      onInsertLink(suggestion.note_id);
                      // Remove from current suggestions (optimistic UI)
                      linksRef.current = linksRef.current.filter((_, i) => i !== index);
                      setLinkSuggestions(linksRef.current);
                    }}
                    className={styles.suggestionAction}
                  >
                    Insert
                  </button>
                </div>
                <p className={styles.suggestionReason}>{suggestion.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Toast for automatic mode */}
      <Toast
        message="AI suggestions ready"
        isVisible={showToast}
        onClose={() => setShowToast(false)}
        duration={4000}
      />
    </div>
  );
}
