"use client";

import { Suspense } from "react";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { logger } from "@/lib/logger";
import MarkdownWithWikilinks from "@/components/MarkdownWithWikilinks";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
import Breadcrumb from "@/components/Breadcrumb";
import { TagPillList } from "@/components/TagPill";

interface Resource {
  id: number;
  title: string;
  content: string;
  content_type?: string;
  url?: string;
  tags: string[];
  created_at: string;
}

function ArticlesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tagFilter = searchParams.get("tag");

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
    // Filter by tag if tag query param is present
    if (tagFilter && !resource.tags.includes(tagFilter)) {
      return false;
    }

    // Filter by search query
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      resource.title.toLowerCase().includes(query) ||
      resource.content.toLowerCase().includes(query) ||
      resource.tags.some((tag) => tag.toLowerCase().includes(query))
    );
  });

  const handleTagClick = (tag: string) => {
    router.push(`/knowledge-base/articles?tag=${encodeURIComponent(tag)}`);
  };

  const clearTagFilter = () => {
    router.push("/knowledge-base/articles");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      {/* AI Panel */}
      <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />

      {/* AI Button */}
      {!aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      {/* Header */}
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="mb-4">
            <Breadcrumb section="articles" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Articles</h1>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Tag Filter Banner */}
        {tagFilter && (
          <div className="mb-6 flex items-center justify-between rounded-lg border border-blue-200 bg-blue-50 p-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-blue-900">Filtering by tag:</span>
              <span className="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-sm font-medium text-blue-800">
                #{tagFilter}
              </span>
            </div>
            <button
              onClick={clearTagFilter}
              className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
            >
              Clear filter
            </button>
          </div>
        )}

        {/* Search Bar */}
        <div className="mb-6">
          <input
            type="text"
            placeholder="Search articles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Articles List */}
        <div className="space-y-4">
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
            filteredResources.map((resource) => {
              // Extract first paragraph or first 200 chars as preview
              const preview = resource.content
                .split("\n\n")[0]
                .replace(/[#*`[\]]/g, "")
                .substring(0, 200);
              const needsTruncation = resource.content.length > 200;

              return (
                <Link
                  key={resource.id}
                  href={`/knowledge-base/articles/${resource.id}`}
                  className="block rounded-lg bg-white p-6 shadow-md transition hover:shadow-lg"
                >
                  <div className="mb-3">
                    <h3 className="mb-2 text-2xl font-semibold text-gray-900 hover:text-blue-600">
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

                  {/* Preview */}
                  <p className="mb-3 overflow-hidden break-words text-gray-700">
                    {preview}
                    {needsTruncation && "..."}
                  </p>

                  {/* Tags */}
                  {resource.tags.length > 0 && (
                    <TagPillList
                      tags={resource.tags}
                      showHash
                      onClick={handleTagClick}
                      className="mt-4"
                    />
                  )}

                  {/* Read more indicator */}
                  <div className="mt-4 text-sm font-medium text-blue-600">Read more →</div>
                </Link>
              );
            })
          )}
        </div>
      </main>
    </div>
  );
}

export default function ArticlesPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
          <header className="border-b border-gray-200 bg-white shadow-sm">
            <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
              <h1 className="text-3xl font-bold text-gray-900">Articles</h1>
            </div>
          </header>
          <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
            <div className="py-12 text-center">
              <p className="text-gray-500">Loading articles...</p>
            </div>
          </main>
        </div>
      }
    >
      <ArticlesContent />
    </Suspense>
  );
}
