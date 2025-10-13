"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { logger } from "@/lib/logger";
import RichTextDisplay from "@/components/RichTextDisplay";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";

interface Resource {
  id: number;
  title: string;
  content: string;
  content_type?: string;
  url?: string;
  tags: string[];
  created_at: string;
}

export default function ArticlesPage() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchResources = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/resources`);
      const data = await response.json();
      setResources(data.resources);
      logger.debug("Fetched articles", { count: data.resources.length });
    } catch (error) {
      logger.error("Error fetching articles", error);
    } finally {
      setIsLoading(false);
    }
  }, [API_URL]);

  useEffect(() => {
    fetchResources();
  }, [fetchResources]);

  const filteredResources = resources.filter((resource) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      resource.title.toLowerCase().includes(query) ||
      resource.content.toLowerCase().includes(query) ||
      resource.tags.some((tag) => tag.toLowerCase().includes(query))
    );
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      {/* AI Panel */}
      <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />

      {/* AI Button */}
      {!aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      {/* Header */}
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center gap-4">
            <Link href="/knowledge-base" className="text-sm text-blue-600 hover:text-blue-800">
              ← Knowledge Base
            </Link>
            <h1 className="text-3xl font-bold text-gray-900">Articles</h1>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Search Bar */}
        <div className="mb-6">
          <input
            type="text"
            placeholder="Search articles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
        </div>

        {/* Articles List */}
        <div className="space-y-6">
          {isLoading ? (
            <div className="py-12 text-center">
              <p className="text-gray-500">Loading articles...</p>
            </div>
          ) : filteredResources.length === 0 ? (
            <div className="rounded-lg bg-white py-12 text-center shadow-md">
              <p className="mb-2 text-gray-500">
                {searchQuery ? "No articles match your search" : "No articles yet"}
              </p>
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="text-sm text-blue-600 hover:underline"
                >
                  Clear search
                </button>
              )}
            </div>
          ) : (
            filteredResources.map((resource) => (
              <div key={resource.id} className="rounded-lg bg-white p-6 shadow-md">
                <div className="mb-3">
                  <h3 className="mb-2 text-2xl font-semibold text-gray-900">{resource.title}</h3>
                  <div className="text-sm text-gray-500">
                    {new Date(resource.created_at).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </div>
                </div>

                {resource.content_type === "markdown" || resource.content_type === undefined ? (
                  <div className="prose prose-blue max-w-none">
                    <RichTextDisplay markdown={resource.content} />
                  </div>
                ) : (
                  <p className="mb-3 text-gray-700">{resource.content}</p>
                )}

                {resource.url && (
                  <a
                    href={resource.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mb-3 block text-sm text-blue-600 hover:underline"
                  >
                    {resource.url}
                  </a>
                )}

                {resource.tags.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {resource.tags.map((tag, index) => (
                      <span
                        key={index}
                        className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-700"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
