"use client";

import { useState, useRef, useEffect } from "react";
import { logger } from "@/lib/logger";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  const [mode, setMode] = useState<AIMode>("chat");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const warmupStartedRef = useRef(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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
        const timeoutId = setTimeout(() => controller.abort(), 90000); // 90 second timeout

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
            "Request timed out after 90 seconds. The AI model may be overloaded or the server may need more resources.";
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

  // Warm up Ollama when AI Panel opens (not on page load)
  useEffect(() => {
    if (!isOpen) return;

    // Prevent duplicate warmups
    if (warmupStartedRef.current) {
      return;
    }
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

    // Fire and forget - don't block UI
    warmupOllama();
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed right-0 top-0 z-50 flex h-screen w-96 flex-col border-l border-gray-200 bg-white shadow-lg">
      {/* Header */}
      <div className="border-b border-gray-200 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">AI Assistant</h2>
          <button
            onClick={onClose}
            className="text-gray-400 transition hover:text-gray-600"
            aria-label="Close AI panel"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
        {/* Mode Switcher */}
        <div className="flex gap-2">
          <button
            onClick={() => handleModeChange("chat")}
            className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition ${
              mode === "chat"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            💬 Chat
          </button>
          <button
            onClick={() => handleModeChange("search")}
            className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition ${
              mode === "search"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            🔍 Search
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="mt-8 text-center text-gray-500">
            {mode === "chat" ? (
              <>
                <p className="text-sm font-medium">💬 Conversational Q&A</p>
                <p className="mt-2 text-xs">
                  Ask questions like &quot;What is systems thinking?&quot; I&apos;ll search your
                  knowledge base and provide answers with context. For finding related content, use
                  the Search tab.
                </p>
              </>
            ) : (
              <>
                <p className="text-sm font-medium">🔍 AI Semantic Search</p>
                <p className="mt-2 text-xs">
                  Find conceptually related content using AI embeddings. Discovers connections even
                  without exact keyword matches. Takes 15-30 seconds. For faster keyword search, use
                  the main search box.
                </p>
              </>
            )}
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-lg p-3 ${
                message.role === "user" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-900"
              }`}
            >
              <p className="whitespace-pre-wrap text-sm">{message.content}</p>

              {/* Sources */}
              {message.sources && message.sources.length > 0 && (
                <div className="mt-3 space-y-2">
                  {message.sources.map((source, idx) => {
                    const resourcePath =
                      source.type === "article"
                        ? `/knowledge-base/articles/${source.id}`
                        : source.type === "note"
                          ? `/knowledge-base/notes/${source.id}`
                          : null;

                    return (
                      <div
                        key={`${source.id}-${idx}`}
                        className="rounded border border-gray-200 bg-white p-2"
                      >
                        <div className="mb-1 flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-medium text-blue-600">
                              {source.type === "article"
                                ? "📚"
                                : source.type === "note"
                                  ? "🔗"
                                  : "📄"}{" "}
                              {source.title || `Document ${source.id}`}
                            </span>
                            {source.score && (
                              <span className="text-xs text-gray-400">
                                {source.score.toFixed(3)}
                              </span>
                            )}
                          </div>
                          {resourcePath && (
                            <a
                              href={resourcePath}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-blue-600 hover:underline"
                            >
                              View →
                            </a>
                          )}
                        </div>
                        <div className="line-clamp-2 text-xs text-gray-600">{source.content}</div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="rounded-lg bg-gray-100 p-3">
              <div className="flex gap-1">
                <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400"></div>
                <div
                  className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                  style={{ animationDelay: "0.1s" }}
                ></div>
                <div
                  className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                  style={{ animationDelay: "0.2s" }}
                ></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        {messages.length > 0 && (
          <button onClick={handleClear} className="mb-2 text-xs text-gray-500 hover:text-gray-700">
            Clear {mode === "chat" ? "conversation" : "results"}
          </button>
        )}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={mode === "chat" ? "Ask a question..." : "Search query..."}
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "..." : mode === "chat" ? "Send" : "Search"}
          </button>
        </form>
      </div>
    </div>
  );
}
