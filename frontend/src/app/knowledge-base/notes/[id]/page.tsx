"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import NoteEditor from "@/components/NoteEditor";
import MarkdownWithWikilinks from "@/components/MarkdownWithWikilinks";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
import AISuggestionsPanel from "@/components/AISuggestionsPanel";
import PostSaveAISuggestions from "@/components/PostSaveAISuggestions";
import SettingsDropdown from "@/components/SettingsDropdown";
import Breadcrumb from "@/components/Breadcrumb";
import Badge from "@/components/Badge";
import { TagPillList } from "@/components/TagPill";
import {
  getNote,
  updateNote,
  deleteNote,
  getBacklinks,
  getOutboundLinks,
  listNotes,
  Note,
  formatNoteDate,
} from "@/lib/api/notes";
import { logger } from "@/lib/logger";
import { useSettings } from "@/hooks/useSettings";
import { isAuthenticated } from "@/lib/api/client";
import { config } from "@/lib/config";

export default function NoteDetailPage() {
  const params = useParams();
  const router = useRouter();
  const noteId = params.id as string;
  const { settings } = useSettings();

  // Check if AI features should be available
  // AI is available if: user is authenticated OR unauthenticated AI is allowed
  const aiAvailable = isAuthenticated() || config.allowUnauthenticatedAI;

  const [note, setNote] = useState<Note | null>(null);
  const [backlinks, setBacklinks] = useState<Note[]>([]);
  const [outboundLinks, setOutboundLinks] = useState<Note[]>([]);
  const [allNotes, setAllNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit state
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [editTitle, setEditTitle] = useState("");
  const [editTags, setEditTags] = useState("");
  const [saving, setSaving] = useState(false);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [showZeroLinksWarning, setShowZeroLinksWarning] = useState(false);
  const [showPostSaveSuggestions, setShowPostSaveSuggestions] = useState(false);
  const [aiSuggestionsOpen, setAiSuggestionsOpen] = useState(false);
  const [aiPrewarming, setAiPrewarming] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);

        // Fetch note, backlinks, outbound links, and all notes in parallel
        const [noteData, backlinksData, outboundData, allNotesData] = await Promise.all([
          getNote(noteId),
          getBacklinks(noteId),
          getOutboundLinks(noteId),
          listNotes(),
        ]);

        setNote(noteData);
        setBacklinks(backlinksData.backlinks);
        setOutboundLinks(outboundData.links);
        setAllNotes(allNotesData.notes);

        // Initialize edit state
        setEditContent(noteData.content);
        setEditTitle(noteData.title || "");
        setEditTags(noteData.tags.join(", "));

        logger.info("Note loaded", {
          id: noteData.id,
          backlinks: backlinksData.count,
          outbound: outboundData.count,
        });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load note";
        setError(message);
        logger.error("Failed to load note", err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [noteId]);

  // Pre-warm Ollama (lightweight) when entering edit mode
  useEffect(() => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    async function prewarmOllama() {
      if (!isEditing || settings.aiMode === "off" || aiPrewarming) {
        return;
      }

      setAiPrewarming(true);
      logger.info("Pre-warming Ollama model for edit mode");

      try {
        // Just warm up the model (lightweight) - don't generate suggestions yet
        const response = await fetch(`${API_URL}/api/ollama/warmup`, {
          method: "POST",
        });

        if (response.ok) {
          logger.info("Ollama model pre-warmed successfully");
        }
      } catch (err) {
        logger.error("Failed to pre-warm Ollama", err);
        // Don't block - warmup will happen on first suggestion request
      } finally {
        setAiPrewarming(false);
      }
    }

    prewarmOllama();
    // Only depend on isEditing and aiMode - don't re-run on content changes
  }, [isEditing, settings.aiMode, aiPrewarming]);

  // Check if content has wikilinks
  const hasWikilinks = (text: string): boolean => {
    return /\[\[[a-z0-9-]+\]\]/i.test(text);
  };

  const handleSave = async (forceSave = false) => {
    // Check authentication before saving
    if (!isAuthenticated()) {
      setError("You must be logged in to save notes. Changes you make will not be persisted.");
      logger.warn("Unauthenticated user attempted to save note");
      return;
    }

    if (!editContent.trim()) {
      setError("Content cannot be empty");
      return;
    }

    // Check for zero wikilinks and show warning (unless forcing save)
    if (!forceSave && !hasWikilinks(editContent)) {
      setShowZeroLinksWarning(true);
      return;
    }

    try {
      setSaving(true);
      setError(null);

      const tagArray = editTags
        .split(",")
        .map((t) => t.trim())
        .filter((t) => t);

      const updatedNote = await updateNote(noteId, {
        content: editContent,
        title: editTitle.trim() || undefined,
        tags: tagArray.length > 0 ? tagArray : undefined,
      });

      setNote(updatedNote);
      setIsEditing(false);
      logger.info("Note updated successfully", { id: noteId });

      // Refresh backlinks and outbound links
      const [backlinksData, outboundData] = await Promise.all([
        getBacklinks(noteId),
        getOutboundLinks(noteId),
      ]);
      setBacklinks(backlinksData.backlinks);
      setOutboundLinks(outboundData.links);

      // Show AI suggestions modal after save
      setShowPostSaveSuggestions(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update note";
      setError(message);
      logger.error("Failed to update note", err);
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
    if (!note) return;

    // Check authentication before saving
    if (!isAuthenticated()) {
      setError("You must be logged in to save notes. Changes you make will not be persisted.");
      logger.warn("Unauthenticated user attempted to insert link");
      return;
    }

    try {
      // Add the wikilink to the end of the content
      const updatedContent = note.content.trim() + `\n\n[[${linkNoteId}]]`;

      // Update the note
      const updatedNote = await updateNote(noteId, {
        content: updatedContent,
        title: note.title || undefined,
        tags: note.tags,
      });

      setNote(updatedNote);
      setEditContent(updatedContent);

      // Refresh links
      const [backlinksData, outboundData] = await Promise.all([
        getBacklinks(noteId),
        getOutboundLinks(noteId),
      ]);
      setBacklinks(backlinksData.backlinks);
      setOutboundLinks(outboundData.links);

      logger.info("Inserted link from post-save suggestion", { linkNoteId });
    } catch (err) {
      logger.error("Failed to insert link from suggestion", err);
    }
  };

  const handleCloseSuggestions = () => {
    setShowPostSaveSuggestions(false);
  };

  const handleDelete = async () => {
    // Check authentication before deleting
    if (!isAuthenticated()) {
      setError("You must be logged in to delete notes.");
      logger.warn("Unauthenticated user attempted to delete note");
      return;
    }

    if (!confirm("Are you sure you want to delete this note? This action cannot be undone.")) {
      return;
    }

    try {
      await deleteNote(noteId);
      logger.info("Note deleted successfully", { id: noteId });
      router.push("/knowledge-base/notes");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to delete note";
      setError(message);
      logger.error("Failed to delete note", err);
    }
  };

  const handleCancelEdit = () => {
    if (note) {
      setEditContent(note.content);
      setEditTitle(note.title || "");
      setEditTags(note.tags.join(", "));
    }
    setIsEditing(false);
    setError(null);
  };

  const handleAddTag = (tag: string) => {
    // Add tag if not already present
    const currentTags = editTags
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t);

    if (!currentTags.includes(tag)) {
      const newTags = [...currentTags, tag].join(", ");
      setEditTags(newTags);
      logger.info("Tag added from AI suggestion", { tag });
    }
  };

  const handleInsertLink = (noteId: string) => {
    // Insert wikilink at the end of content
    const wikilink = `[[${noteId}]]`;
    const newContent = editContent.trim() + `\n\n${wikilink}`;
    setEditContent(newContent);
    logger.info("Link inserted from AI suggestion", { noteId });
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="animate-pulse">
          <div className="mb-4 h-8 w-1/3 rounded bg-gray-200"></div>
          <div className="mb-4 h-64 rounded bg-gray-200"></div>
          <div className="h-32 rounded bg-gray-200"></div>
        </div>
      </div>
    );
  }

  if (error && !note) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <h2 className="mb-2 font-semibold text-red-800">Error</h2>
          <p className="text-red-600">{error}</p>
          <Link
            href="/knowledge-base/notes"
            className="mt-4 inline-block text-blue-600 hover:underline"
          >
            ← Back to notes
          </Link>
        </div>
      </div>
    );
  }

  if (!note) return null;

  return (
    <div>
      {/* AI Panel */}
      <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />

      {/* AI Button */}
      {!aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      <div className="container mx-auto max-w-6xl px-4 py-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Main content */}
          <div className="lg:col-span-2">
            {/* Header */}
            <div className="mb-6 rounded-lg border border-gray-200 bg-gray-50 p-6">
              {/* Breadcrumb and Settings */}
              <div className="mb-6 flex items-center justify-between">
                <Breadcrumb section="notes" />
                <SettingsDropdown />
              </div>

              {/* Note ID - shown only in edit mode or as subtle metadata */}
              {isEditing && (
                <div className="mb-4">
                  <span className="text-xs text-gray-400">
                    ID: <code className="font-mono">{note.id}</code>
                  </span>
                </div>
              )}

              {/* Content Type Badge */}
              <div className="mb-4">
                <Badge type="note" />
              </div>

              {/* Title and Actions */}
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <h1 className="mb-4 text-2xl font-bold text-gray-900 sm:text-3xl lg:text-4xl">
                    {note.title || "Untitled Note"}
                  </h1>

                  {/* Metadata */}
                  <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500">
                    <span className="flex items-center gap-2">
                      <span aria-hidden="true">📝</span>
                      <span>
                        Created{" "}
                        <time dateTime={String(note.created_at)}>
                          {formatNoteDate(note.created_at)}
                        </time>
                      </span>
                    </span>
                    <span>by {note.author}</span>
                    {note.updated_at !== note.created_at && (
                      <span>
                        Edited{" "}
                        <time dateTime={String(note.updated_at)}>
                          {formatNoteDate(note.updated_at)}
                        </time>
                      </span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                {!isEditing && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => setIsEditing(true)}
                      className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm hover:bg-gray-50"
                    >
                      Edit
                    </button>
                    <button
                      onClick={handleDelete}
                      className="rounded-lg border border-red-300 bg-white px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>

              {/* Tags */}
              {note.tags.length > 0 && !isEditing && (
                <div className="mt-4">
                  <TagPillList tags={note.tags} />
                </div>
              )}
            </div>

            {/* Error message */}
            {error && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
                <p className="text-red-600">{error}</p>
              </div>
            )}

            {/* Content */}
            {isEditing ? (
              <div
                className={`grid gap-6 ${aiSuggestionsOpen ? "lg:grid-cols-3" : "lg:grid-cols-1"}`}
              >
                {/* Editor Column */}
                <div
                  className={`space-y-4 ${aiSuggestionsOpen ? "lg:col-span-2" : "lg:col-span-1"}`}
                >
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Title (optional)
                    </label>
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2"
                    />
                  </div>

                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Tags (optional)
                    </label>
                    <input
                      type="text"
                      value={editTags}
                      onChange={(e) => setEditTags(e.target.value)}
                      placeholder="Comma-separated tags"
                      className="w-full rounded-lg border border-gray-300 px-3 py-2"
                    />
                  </div>

                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Content *
                    </label>
                    <NoteEditor
                      content={editContent}
                      onChange={setEditContent}
                      allNotes={allNotes}
                      onNoteClick={(id) => window.open(`/knowledge-base/notes/${id}`, "_blank")}
                    />
                  </div>

                  <div className="flex flex-wrap gap-3">
                    <button
                      onClick={() => handleSave()}
                      disabled={saving || !editContent.trim()}
                      className="rounded-lg bg-blue-600 px-6 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      {saving ? "Saving..." : "Save Changes"}
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      disabled={saving}
                      className="rounded-lg border border-gray-300 px-6 py-2 text-gray-700 hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                    {settings.aiMode !== "off" && aiAvailable && (
                      <button
                        onClick={() => setAiSuggestionsOpen(!aiSuggestionsOpen)}
                        className="rounded-lg border border-blue-600 bg-blue-50 px-6 py-2 text-blue-700 hover:bg-blue-100"
                      >
                        {aiSuggestionsOpen ? "Hide AI Suggestions" : "✨ Get AI Suggestions"}
                      </button>
                    )}
                  </div>
                </div>

                {/* AI Suggestions Panel */}
                {settings.aiMode !== "off" && aiAvailable && aiSuggestionsOpen && (
                  <div className="lg:col-span-1">
                    <AISuggestionsPanel
                      noteId={noteId}
                      mode={settings.aiMode}
                      content={editContent}
                      isOpen={aiSuggestionsOpen}
                      onClose={() => setAiSuggestionsOpen(false)}
                      onAddTag={handleAddTag}
                      onInsertLink={handleInsertLink}
                    />
                  </div>
                )}
              </div>
            ) : (
              <div>
                {/* Content display with markdown and wikilinks */}
                <div className="rounded-lg border border-gray-200 bg-white p-6">
                  <MarkdownWithWikilinks content={note.content} />
                </div>
              </div>
            )}
          </div>

          {/* Sidebar - Links and Backlinks */}
          <div className="space-y-6">
            {/* Outbound Links */}
            {outboundLinks.length > 0 && (
              <div className="rounded-lg border border-gray-200 bg-white p-4">
                <h3 className="mb-3 font-semibold text-gray-900">Links ({outboundLinks.length})</h3>
                <div className="space-y-2">
                  {outboundLinks.map((link) => (
                    <Link
                      key={link.id}
                      href={`/knowledge-base/notes/${link.id}`}
                      className="block rounded p-2 hover:bg-gray-50"
                    >
                      <code className="text-sm text-blue-600">{link.id}</code>
                      {link.title && <div className="text-sm text-gray-700">{link.title}</div>}
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Backlinks */}
            {backlinks.length > 0 && (
              <div className="rounded-lg border border-gray-200 bg-white p-4">
                <h3 className="mb-3 font-semibold text-gray-900">Backlinks ({backlinks.length})</h3>
                <div className="space-y-2">
                  {backlinks.map((backlink) => (
                    <Link
                      key={backlink.id}
                      href={`/knowledge-base/notes/${backlink.id}`}
                      className="block rounded p-2 hover:bg-gray-50"
                    >
                      <code className="text-sm text-blue-600">{backlink.id}</code>
                      {backlink.title && (
                        <div className="text-sm text-gray-700">{backlink.title}</div>
                      )}
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* No links message */}
            {outboundLinks.length === 0 && backlinks.length === 0 && (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center">
                <p className="text-sm text-gray-600">
                  No links yet. Use <code className="rounded bg-gray-200 px-1">[[note-id]]</code> to
                  connect notes
                </p>
              </div>
            )}
          </div>
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
      <PostSaveAISuggestions
        noteId={noteId}
        isOpen={showPostSaveSuggestions}
        onClose={handleCloseSuggestions}
        onInsertLink={handleInsertLinkFromSuggestion}
      />
    </div>
  );
}
