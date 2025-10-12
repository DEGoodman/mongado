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
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-4">
            <Link href="/knowledge-base" className="text-blue-600 hover:text-blue-800 text-sm">
              ← Knowledge Base
            </Link>
            <h1 className="text-3xl font-bold text-gray-900">Articles</h1>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Bar */}
        <div className="mb-6">
          <input
            type="text"
            placeholder="Search articles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Articles List */}
        <div className="space-y-6">
          {isLoading ? (
            <div className="text-center py-12">
              <p className="text-gray-500">Loading articles...</p>
            </div>
          ) : filteredResources.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg shadow-md">
              <p className="text-gray-500 mb-2">
                {searchQuery ? "No articles match your search" : "No articles yet"}
              </p>
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="text-blue-600 hover:underline text-sm"
                >
                  Clear search
                </button>
              )}
            </div>
          ) : (
            filteredResources.map((resource) => (
              <div key={resource.id} className="bg-white rounded-lg shadow-md p-6">
                <div className="mb-3">
                  <h3 className="text-2xl font-semibold text-gray-900 mb-2">
                    {resource.title}
                  </h3>
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
                  <p className="text-gray-700 mb-3">{resource.content}</p>
                )}

                {resource.url && (
                  <a
                    href={resource.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline text-sm mb-3 block"
                  >
                    {resource.url}
                  </a>
                )}

                {resource.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-4">
                    {resource.tags.map((tag, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded-full"
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
