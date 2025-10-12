"use client";

import { useState, useRef, useEffect } from "react";
import { logger } from "@/lib/logger";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{
    id: number;
    title: string;
    content: string;
  }>;
}

interface AIPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AIPanel({ isOpen, onClose }: AIPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"search" | "ask">("ask");
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
      if (mode === "search") {
        // Semantic search mode
        const response = await fetch(`${API_URL}/api/search`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: userMessage.content,
            top_k: 5,
          }),
        });

        if (!response.ok) {
          throw new Error(`Search failed: ${response.statusText}`);
        }

        const data = await response.json();
        const results = data.results || [];

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content:
            results.length > 0
              ? `Found ${results.length} relevant documents:`
              : "No results found for your search.",
          sources: results,
        };

        setMessages((prev) => [...prev, assistantMessage]);
        logger.info("Search completed", { query: userMessage.content, count: results.length });
      } else {
        // Q&A mode
        const response = await fetch(`${API_URL}/api/ask`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: userMessage.content,
          }),
        });

        if (!response.ok) {
          throw new Error(`Q&A failed: ${response.statusText}`);
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
      }
    } catch (err) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content:
          err instanceof Error
            ? `Error: ${err.message}`
            : "Failed to process request. Make sure Ollama is running.",
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

  if (!isOpen) return null;

  return (
    <div className="fixed right-0 top-0 h-screen w-96 bg-white border-l border-gray-200 shadow-lg flex flex-col z-50">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-gray-900">AI Assistant</h2>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setMode("ask")}
              className={`px-2 py-1 text-xs rounded ${
                mode === "ask"
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Q&A
            </button>
            <button
              onClick={() => setMode("search")}
              className={`px-2 py-1 text-xs rounded ${
                mode === "search"
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Search
            </button>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition"
          aria-label="Close AI panel"
        >
          <svg
            className="w-5 h-5"
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

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <p className="text-sm">
              {mode === "ask"
                ? "Ask questions about your knowledge base"
                : "Search for relevant documents"}
            </p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-lg p-3 ${
                message.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-900"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>

              {/* Sources */}
              {message.sources && message.sources.length > 0 && (
                <div className="mt-3 space-y-2">
                  {message.sources.map((source) => (
                    <div
                      key={source.id}
                      className="bg-white rounded border border-gray-200 p-2"
                    >
                      <div className="text-xs font-medium text-blue-600 mb-1">
                        {source.title || `Document ${source.id}`}
                      </div>
                      <div className="text-xs text-gray-600 line-clamp-2">
                        {source.content}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.1s" }}
                ></div>
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
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
          <button
            onClick={handleClear}
            className="text-xs text-gray-500 hover:text-gray-700 mb-2"
          >
            Clear conversation
          </button>
        )}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              mode === "ask" ? "Ask a question..." : "Search knowledge base..."
            }
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition text-sm"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
