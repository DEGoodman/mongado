"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import NoteEditor from "@/components/NoteEditor";
import AuthStatusBanner from "@/components/AuthStatusBanner";
import { createNote, listNotes, updateNote, getNote, Note } from "@/lib/api/notes";
import { logger } from "@/lib/logger";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
import PostSaveAISuggestions from "@/components/PostSaveAISuggestions";

export default function NewNotePage() {
  const router = useRouter();
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("");
  const [tags, setTags] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [allNotes, setAllNotes] = useState<Note[]>([]);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [showZeroLinksWarning, setShowZeroLinksWarning] = useState(false);
  const [pendingNote, setPendingNote] = useState<{
    content: string;
    title?: string;
    tags: string[];
  } | null>(null);
  const [showPostSaveSuggestions, setShowPostSaveSuggestions] = useState(false);
  const [savedNoteId, setSavedNoteId] = useState<string | null>(null);

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

  // Check if content has wikilinks
  const hasWikilinks = (text: string): boolean => {
    return /\[\[[a-z0-9-]+\]\]/i.test(text);
  };

  const handleSave = async (forceSave = false) => {
    if (!content.trim()) {
      setError("Content cannot be empty");
      return;
    }

    const tagArray = tags
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t);

    // Check for zero wikilinks and show warning (unless forcing save)
    if (!forceSave && !hasWikilinks(content)) {
      setPendingNote({
        content,
        title: title.trim() || undefined,
        tags: tagArray,
      });
      setShowZeroLinksWarning(true);
      return;
    }

    try {
      setSaving(true);
      setError(null);

      const note = await createNote({
        content,
        title: title.trim() || undefined,
        tags: tagArray.length > 0 ? tagArray : undefined,
      });

      logger.info("Note created successfully", { id: note.id });

      // Show AI suggestions modal instead of immediately redirecting
      setSavedNoteId(note.id);
      setShowPostSaveSuggestions(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create note";
      setError(message);
      logger.error("Failed to create note", err);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAnyway = async () => {
    setShowZeroLinksWarning(false);
    await handleSave(true);
  };

  const handleGetAISuggestions = () => {
    setShowZeroLinksWarning(false);
    setAiPanelOpen(true);
  };

  const handleInsertLinkFromSuggestion = async (linkNoteId: string) => {
    if (!savedNoteId) return;

    try {
      // Fetch the current note
      const currentNote = await getNote(savedNoteId);

      // Add the wikilink to the end of the content
      const updatedContent = currentNote.content.trim() + `\n\n[[${linkNoteId}]]`;

      // Update the note
      await updateNote(savedNoteId, {
        content: updatedContent,
        title: currentNote.title || undefined,
        tags: currentNote.tags,
      });

      logger.info("Inserted link from post-save suggestion", { linkNoteId });
    } catch (err) {
      logger.error("Failed to insert link from suggestion", err);
    }
  };

  const handleCloseSuggestions = () => {
    setShowPostSaveSuggestions(false);
    if (savedNoteId) {
      router.push(`/knowledge-base/notes/${savedNoteId}`);
    }
  };

  const handleCancel = () => {
    if (content.trim() && !confirm("Discard unsaved changes?")) {
      return;
    }
    router.push("/knowledge-base/notes");
  };

  return (
    <div className="container mx-auto max-w-4xl px-4 py-8">
      {/* AI Panel */}
      <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />

      {/* AI Button */}
      {!aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      {/* Header */}
      <div className="mb-6">
        <div className="mb-4 flex gap-4">
          <Link href="/knowledge-base" className="text-sm text-blue-600 hover:underline">
            ← Knowledge Base
          </Link>
          <Link href="/knowledge-base/notes" className="text-sm text-blue-600 hover:underline">
            All notes
          </Link>
        </div>
        <h1 className="mb-2 text-3xl font-bold text-gray-900">Create New Note</h1>
        <p className="text-gray-600">Add a new note to your Zettelkasten knowledge base</p>
      </div>

      {/* Authentication status banner */}
      <AuthStatusBanner mode="auto" />

      {/* Error message */}
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* Form */}
      <div className="space-y-4">
        {/* Title (optional) */}
        <div>
          <label htmlFor="title" className="mb-1 block text-sm font-medium text-gray-700">
            Title (optional)
          </label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Give your note a title..."
            className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Tags (optional) */}
        <div>
          <label htmlFor="tags" className="mb-1 block text-sm font-medium text-gray-700">
            Tags (optional)
          </label>
          <input
            id="tags"
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="Comma-separated tags (e.g., idea, research, todo)"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Content */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Content *</label>
          <NoteEditor
            content={content}
            onChange={setContent}
            allNotes={allNotes}
            onNoteClick={(noteId) => {
              // Open note in new tab
              window.open(`/knowledge-base/notes/${noteId}`, "_blank");
            }}
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-4">
          <button
            onClick={() => handleSave()}
            disabled={saving || !content.trim()}
            className="rounded-lg bg-blue-600 px-6 py-2 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Note"}
          </button>
          <button
            onClick={handleCancel}
            disabled={saving}
            className="rounded-lg border border-gray-300 px-6 py-2 text-gray-700 transition hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </div>

      {/* Zero Links Warning Modal */}
      {showZeroLinksWarning && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h3 className="mb-3 text-lg font-semibold text-gray-900">💡 No connections found</h3>
            <p className="mb-4 text-gray-700">
              This note has no connections to other notes. Zettelkasten works best when ideas link
              together.
            </p>
            <p className="mb-4 text-sm text-gray-600">Consider:</p>
            <ul className="mb-6 list-inside list-disc space-y-1 text-sm text-gray-600">
              <li>What concepts does this relate to?</li>
              <li>What led to this idea?</li>
              <li>Where might you apply this?</li>
            </ul>
            <div className="flex gap-3">
              <button
                onClick={handleGetAISuggestions}
                className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-700"
              >
                Get AI Link Suggestions
              </button>
              <button
                onClick={handleSaveAnyway}
                disabled={saving}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition hover:bg-gray-50 disabled:opacity-50"
              >
                Save Anyway
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Post-Save AI Suggestions Modal */}
      {savedNoteId && (
        <PostSaveAISuggestions
          noteId={savedNoteId}
          isOpen={showPostSaveSuggestions}
          onClose={handleCloseSuggestions}
          onInsertLink={handleInsertLinkFromSuggestion}
        />
      )}
    </div>
  );
}
