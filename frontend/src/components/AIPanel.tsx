"use client";

import { useState, useRef, useEffect } from "react";
import { logger } from "@/lib/logger";
import styles from "./AIPanel.module.scss";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const IS_DEVELOPMENT = process.env.NODE_ENV === "development";

type AIMode = "chat" | "search";

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
}

export default function AIPanel({ isOpen, onClose }: AIPanelProps) {
  const [mode, setMode] = useState<AIMode>("search"); // Default to Search (faster)
  const [hasGPU, setHasGPU] = useState<boolean | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [forceCpuMode, setForceCpuMode] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const warmupStartedRef = useRef(false);

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
      if (mode === "chat") {
        // Chat mode - Q&A with hybrid KB + general knowledge
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
          sources: results.map((r: any) => ({
            id: r.id,
            type: r.type,
            title: r.title,
            content: r.content,
            score: r.score,
          })),
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

  const handleModeChange = (newMode: AIMode) => {
    setMode(newMode);
    // Clear messages when switching modes for clarity
    setMessages([]);
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
        {/* Mode Switcher - Search first (faster) */}
        <div className={styles.modeSwitcher}>
          <button
            onClick={() => handleModeChange("search")}
            className={`${styles.modeButton} ${mode === "search" ? styles.active : styles.inactive}`}
          >
            🔍 Search
          </button>
          <button
            onClick={() => handleModeChange("chat")}
            className={`${styles.modeButton} ${mode === "chat" ? styles.active : styles.inactive}`}
          >
            💬 Chat
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className={styles.messagesContainer} style={{ WebkitOverflowScrolling: "touch" }}>
        {messages.length === 0 && (
          <div className={styles.emptyState}>
            {mode === "chat" ? (
              <>
                <p className={styles.emptyTitle}>💬 Conversational Q&A</p>
                <p className={styles.emptyDescription}>
                  Ask questions like &quot;What is systems thinking?&quot; I&apos;ll search your
                  knowledge base and provide answers with context. For finding related content, use
                  the Search tab.
                </p>
                {hasGPU === false && (
                  <div className={styles.performanceNotice}>
                    <p className={styles.noticeTitle}>⚠️ Performance Notice</p>
                    <p className={styles.noticeDescription}>
                      This feature is under active development and currently running on CPU-only
                      infrastructure. Response times may be 60-120 seconds. For faster results, use
                      the Search tab.
                    </p>
                  </div>
                )}
              </>
            ) : (
              <>
                <p className={styles.emptyTitle}>🔍 AI Semantic Search</p>
                <p className={styles.emptyDescription}>
                  Find conceptually related content using AI embeddings. Discovers connections even
                  without exact keyword matches. Fast with pre-computed embeddings. For keyword
                  search, use the main search box.
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
                              {source.type === "article"
                                ? "📚"
                                : source.type === "note"
                                  ? "🔗"
                                  : "📄"}{" "}
                              {source.title || `Document ${source.id}`}
                            </span>
                            {source.score && (
                              <span className={styles.sourceScore}>{source.score.toFixed(3)}</span>
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
            Clear {mode === "chat" ? "conversation" : "results"}
          </button>
        )}
        <form onSubmit={handleSubmit} className={styles.inputForm}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={mode === "chat" ? "Ask a question..." : "Search query..."}
            className={styles.input}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()} className={styles.submitButton}>
            {loading ? "..." : mode === "chat" ? "Send" : "Search"}
          </button>
        </form>
      </div>
    </div>
  );
}
