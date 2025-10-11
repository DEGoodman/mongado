"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { logger } from "@/lib/logger";
import RichTextEditor from "@/components/RichTextEditor";
import RichTextDisplay from "@/components/RichTextDisplay";

interface Resource {
  id: number;
  title: string;
  content: string;  // Markdown content
  content_type?: string;
  url?: string;
  tags: string[];
  created_at: string;
}

export default function KnowledgeBasePage() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    title: "",
    content: "",
    url: "",
    tags: "",
  });

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchResources = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/resources`);
      const data = await response.json();
      setResources(data.resources);
      logger.debug("Fetched resources", { count: data.resources.length });
    } catch (error) {
      logger.error("Error fetching resources", error);
    } finally {
      setIsLoading(false);
    }
  }, [API_URL]);

  useEffect(() => {
    fetchResources();
  }, [fetchResources]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_URL}/api/resources`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: formData.title,
          content: formData.content,
          content_type: "markdown",
          url: formData.url || undefined,
          tags: formData.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
        }),
      });

      if (response.ok) {
        setFormData({ title: "", content: "", url: "", tags: "" });
        setShowForm(false);
        fetchResources();
        logger.info("Resource created successfully");
      }
    } catch (error) {
      logger.error("Error creating resource", error);
    }
  };

  const handleEditorChange = (html: string, markdown: string) => {
    setFormData({ ...formData, content: markdown });
  };

  const handleDelete = async (id: number) => {
    try {
      await fetch(`${API_URL}/api/resources/${id}`, {
        method: "DELETE",
      });
      fetchResources();
      logger.info("Resource deleted", { id });
    } catch (error) {
      logger.error("Error deleting resource", error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <Link href="/" className="text-blue-600 hover:text-blue-800 text-sm">
                ← Home
              </Link>
              <h1 className="text-3xl font-bold text-gray-900">Knowledge Base</h1>
            </div>
            <button
              onClick={() => setShowForm(!showForm)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              {showForm ? "Cancel" : "Add Resource"}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Add Resource Form */}
        {showForm && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Add New Resource</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
                  Title
                </label>
                <input
                  type="text"
                  id="title"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Content
                </label>
                <RichTextEditor
                  content={formData.content}
                  onChange={handleEditorChange}
                  placeholder="Write your content here..."
                />
              </div>
              <div>
                <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-1">
                  URL (optional)
                </label>
                <input
                  type="url"
                  id="url"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label htmlFor="tags" className="block text-sm font-medium text-gray-700 mb-1">
                  Tags (comma-separated)
                </label>
                <input
                  type="text"
                  id="tags"
                  placeholder="e.g. python, tutorial, web"
                  value={formData.tags}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <button
                type="submit"
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Create Resource
              </button>
            </form>
          </div>
        )}

        {/* Resources List */}
        <div className="space-y-6">
          {isLoading ? (
            <div className="text-center py-12">
              <p className="text-gray-500">Loading...</p>
            </div>
          ) : resources.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg shadow-md">
              <p className="text-gray-500 mb-2">No resources yet</p>
              <p className="text-gray-400 text-sm">Click "Add Resource" to create your first entry</p>
            </div>
          ) : (
            resources.map((resource) => (
              <div key={resource.id} className="bg-white rounded-lg shadow-md p-6">
                <div className="flex justify-between items-start mb-3">
                  <h3 className="text-xl font-semibold text-gray-900">{resource.title}</h3>
                  <button
                    onClick={() => handleDelete(resource.id)}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Delete
                  </button>
                </div>
                {resource.content_type === "markdown" || resource.content_type === undefined ? (
                  <RichTextDisplay markdown={resource.content} />
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
                  <div className="flex flex-wrap gap-2 mt-3">
                    {resource.tags.map((tag, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded-full"
                      >
                        {tag}
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
