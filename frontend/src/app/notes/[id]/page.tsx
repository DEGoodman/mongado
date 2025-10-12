"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import NoteEditor from "@/components/NoteEditor";
import { AuthStatusIndicator } from "@/components/AuthStatusBanner";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
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

export default function NoteDetailPage() {
  const params = useParams();
  const router = useRouter();
  const noteId = params.id as string;

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
    if (
      !confirm(
        "Are you sure you want to delete this note? This action cannot be undone."
      )
    ) {
      return;
    }

    try {
      await deleteNote(noteId);
      logger.info("Note deleted successfully", { id: noteId });
      router.push("/notes");
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

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-64 bg-gray-200 rounded mb-4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error && !note) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h2 className="text-red-800 font-semibold mb-2">Error</h2>
          <p className="text-red-600">{error}</p>
          <Link
            href="/notes"
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

      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2">
          {/* Header */}
          <div className="mb-6">
            <Link
              href="/notes"
              className="text-blue-600 hover:underline text-sm mb-4 inline-block"
            >
              ← Back to all notes
            </Link>

            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <code className="text-sm font-mono text-blue-600 bg-blue-50 px-2 py-1 rounded">
                    {note.id}
                  </code>
                  {note.is_ephemeral && (
                    <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                      ephemeral
                    </span>
                  )}
                </div>

                <h1 className="text-3xl font-bold text-gray-900 mb-2">
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
                    className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Edit
                  </button>
                  <button
                    onClick={handleDelete}
                    className="px-4 py-2 text-sm text-red-600 border border-red-300 rounded-lg hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-600">{error}</p>
            </div>
          )}

          {/* Content */}
          {isEditing ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Title (optional)
                </label>
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tags (optional)
                </label>
                <input
                  type="text"
                  value={editTags}
                  onChange={(e) => setEditTags(e.target.value)}
                  placeholder="Comma-separated tags"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Content *
                </label>
                <NoteEditor
                  content={editContent}
                  onChange={setEditContent}
                  allNotes={allNotes}
                  onNoteClick={(id) => window.open(`/notes/${id}`, "_blank")}
                />
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleSave}
                  disabled={saving || !editContent.trim()}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save Changes"}
                </button>
                <button
                  onClick={handleCancelEdit}
                  disabled={saving}
                  className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div>
              {/* Tags */}
              {note.tags.length > 0 && (
                <div className="flex gap-2 mb-4">
                  {note.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {/* Content display with wikilinks highlighted */}
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <div className="whitespace-pre-wrap font-sans text-gray-800 leading-relaxed">
                  {note.content.split(/(\[\[[a-z0-9-]+\]\])/g).map((part, i) => {
                    const match = part.match(/\[\[([a-z0-9-]+)\]\]/);
                    if (match) {
                      return (
                        <Link
                          key={i}
                          href={`/notes/${match[1]}`}
                          className="text-blue-600 hover:underline font-mono bg-blue-50 px-1 rounded"
                        >
                          {part}
                        </Link>
                      );
                    }
                    return <span key={i}>{part}</span>;
                  })}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar - Links and Backlinks */}
        <div className="space-y-6">
          {/* Outbound Links */}
          {outboundLinks.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <h3 className="font-semibold text-gray-900 mb-3">
                Links ({outboundLinks.length})
              </h3>
              <div className="space-y-2">
                {outboundLinks.map((link) => (
                  <Link
                    key={link.id}
                    href={`/notes/${link.id}`}
                    className="block p-2 hover:bg-gray-50 rounded"
                  >
                    <code className="text-sm text-blue-600">{link.id}</code>
                    {link.title && (
                      <div className="text-sm text-gray-700">{link.title}</div>
                    )}
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Backlinks */}
          {backlinks.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <h3 className="font-semibold text-gray-900 mb-3">
                Backlinks ({backlinks.length})
              </h3>
              <div className="space-y-2">
                {backlinks.map((backlink) => (
                  <Link
                    key={backlink.id}
                    href={`/notes/${backlink.id}`}
                    className="block p-2 hover:bg-gray-50 rounded"
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
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
              <p className="text-sm text-gray-600">
                No links yet. Use <code className="bg-gray-200 px-1 rounded">[[note-id]]</code> to connect notes
              </p>
            </div>
          )}
        </div>
      </div>
      </div>
    </div>
  );
}
