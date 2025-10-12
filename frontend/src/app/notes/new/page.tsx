"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import NoteEditor from "@/components/NoteEditor";
import AuthStatusBanner from "@/components/AuthStatusBanner";
import { createNote, listNotes, Note } from "@/lib/api/notes";
import { logger } from "@/lib/logger";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";

export default function NewNotePage() {
  const router = useRouter();
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("");
  const [tags, setTags] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [allNotes, setAllNotes] = useState<Note[]>([]);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);

  // Load all notes for autocomplete
  useEffect(() => {
    async function fetchNotes() {
      try {
        const response = await listNotes();
        setAllNotes(response.notes);
      } catch (err) {
        logger.error("Failed to load notes for autocomplete", err);
      }
    }

    fetchNotes();
  }, []);

  const handleSave = async () => {
    if (!content.trim()) {
      setError("Content cannot be empty");
      return;
    }

    try {
      setSaving(true);
      setError(null);

      const tagArray = tags
        .split(",")
        .map((t) => t.trim())
        .filter((t) => t);

      const note = await createNote({
        content,
        title: title.trim() || undefined,
        tags: tagArray.length > 0 ? tagArray : undefined,
      });

      logger.info("Note created successfully", { id: note.id });
      router.push(`/notes/${note.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create note";
      setError(message);
      logger.error("Failed to create note", err);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (content.trim() && !confirm("Discard unsaved changes?")) {
      return;
    }
    router.push("/notes");
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* AI Panel */}
      <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />

      {/* AI Button */}
      {!aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      {/* Header */}
      <div className="mb-6">
        <div className="flex gap-4 mb-4">
          <Link href="/" className="text-blue-600 hover:underline text-sm">
            ← Home
          </Link>
          <Link href="/notes" className="text-blue-600 hover:underline text-sm">
            All notes
          </Link>
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Create New Note</h1>
        <p className="text-gray-600">
          Add a new note to your Zettelkasten knowledge base
        </p>
      </div>

      {/* Authentication status banner */}
      <AuthStatusBanner mode="auto" />

      {/* Error message */}
      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* Form */}
      <div className="space-y-4">
        {/* Title (optional) */}
        <div>
          <label
            htmlFor="title"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Title (optional)
          </label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Give your note a title..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Tags (optional) */}
        <div>
          <label htmlFor="tags" className="block text-sm font-medium text-gray-700 mb-1">
            Tags (optional)
          </label>
          <input
            id="tags"
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="Comma-separated tags (e.g., idea, research, todo)"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Content */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Content *
          </label>
          <NoteEditor
            content={content}
            onChange={setContent}
            allNotes={allNotes}
            onNoteClick={(noteId) => {
              // Open note in new tab
              window.open(`/notes/${noteId}`, "_blank");
            }}
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-4">
          <button
            onClick={handleSave}
            disabled={saving || !content.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {saving ? "Saving..." : "Save Note"}
          </button>
          <button
            onClick={handleCancel}
            disabled={saving}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
