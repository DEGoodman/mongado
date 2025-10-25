"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import NoteEditor from "@/components/NoteEditor";
import MarkdownWithWikilinks from "@/components/MarkdownWithWikilinks";
import { AuthStatusIndicator } from "@/components/AuthStatusBanner";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
import AISuggestionsPanel from "@/components/AISuggestionsPanel";
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

export default function NoteDetailPage() {
  const params = useParams();
  const router = useRouter();
  const noteId = params.id as string;
  const { settings } = useSettings();

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

  const handleSave = async () => {
    if (!editContent.trim()) {
      setError("Content cannot be empty");
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
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update note";
      setError(message);
      logger.error("Failed to update note", err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
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

      {/* Auth status indicator at top */}
      <AuthStatusIndicator />

      <div className="container mx-auto max-w-6xl px-4 py-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Main content */}
          <div className="lg:col-span-2">
            {/* Header */}
            <div className="mb-6">
              <div className="mb-4 flex gap-4">
                <Link href="/knowledge-base" className="text-sm text-blue-600 hover:underline">
                  ← Knowledge Base
                </Link>
                <Link
                  href="/knowledge-base/notes"
                  className="text-sm text-blue-600 hover:underline"
                >
                  All notes
                </Link>
              </div>

              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="mb-2 flex items-center gap-2">
                    <code className="rounded bg-blue-50 px-2 py-1 font-mono text-sm text-blue-600">
                      {note.id}
                    </code>
                    {note.is_ephemeral && (
                      <span className="rounded bg-yellow-100 px-2 py-1 text-xs text-yellow-800">
                        ephemeral
                      </span>
                    )}
                  </div>

                  <h1 className="mb-2 text-3xl font-bold text-gray-900">
                    {note.title || "Untitled Note"}
                  </h1>

                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    <span>{formatNoteDate(note.created_at)}</span>
                    <span>by {note.author}</span>
                    {note.updated_at !== note.created_at && (
                      <span>edited {formatNoteDate(note.updated_at)}</span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                {!isEditing && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => setIsEditing(true)}
                      className="rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
                    >
                      Edit
                    </button>
                    <button
                      onClick={handleDelete}
                      className="rounded-lg border border-red-300 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Error message */}
            {error && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
                <p className="text-red-600">{error}</p>
              </div>
            )}

            {/* Content */}
            {isEditing ? (
              <div className="grid gap-6 lg:grid-cols-3">
                {/* Editor Column */}
                <div className="space-y-4 lg:col-span-2">
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

                  <div className="flex gap-3">
                    <button
                      onClick={handleSave}
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
                  </div>
                </div>

                {/* AI Suggestions Panel */}
                {settings.aiSuggestionsEnabled && (
                  <div className="lg:col-span-1">
                    <AISuggestionsPanel
                      noteId={noteId}
                      onAddTag={handleAddTag}
                      onInsertLink={handleInsertLink}
                    />
                  </div>
                )}
              </div>
            ) : (
              <div>
                {/* Tags */}
                {note.tags.length > 0 && (
                  <div className="mb-4 flex gap-2">
                    {note.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-700"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}

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
    </div>
  );
}
