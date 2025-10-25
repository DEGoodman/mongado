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
import SettingsDropdown from "@/components/SettingsDropdown";
import AISuggestionsPanel from "@/components/AISuggestionsPanel";
import { useSettings } from "@/hooks/useSettings";

export default function NewNotePage() {
  const router = useRouter();
  const { settings } = useSettings();
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
  const [showAtomicityWarning, setShowAtomicityWarning] = useState(false);
  const [atomicityIssues, setAtomicityIssues] = useState<string[]>([]);
  const [showFirstPersonReminder, setShowFirstPersonReminder] = useState(true);

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

  // Check if note appears non-atomic (covers multiple topics)
  const checkAtomicity = (text: string): string[] => {
    const issues: string[] = [];

    // Count top-level bullet points (lines starting with - or *)
    const bulletPoints = text.split("\n").filter((line) => /^[-*]\s/.test(line.trim()));
    if (bulletPoints.length > 5) {
      issues.push(`${bulletPoints.length} bullet points - might cover multiple concepts`);
    }

    // Count H2/H3 headings (## or ###)
    const headings = text.split("\n").filter((line) => /^#{2,3}\s/.test(line.trim()));
    if (headings.length > 3) {
      issues.push(`${headings.length} section headings - consider splitting by topic`);
    }

    // Check for "and" in title suggesting multiple topics
    if (title && (title.includes(" and ") || title.includes(" & "))) {
      issues.push('Title contains "and" - might be combining multiple ideas');
    }

    return issues;
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
      setSavedNoteId(note.id);

      // Check atomicity and show warning if issues detected
      const issues = checkAtomicity(content);
      if (issues.length > 0) {
        setAtomicityIssues(issues);
        setShowAtomicityWarning(true);
      } else {
        // Show AI suggestions modal instead of immediately redirecting
        setShowPostSaveSuggestions(true);
      }
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

  const handleContinueToSuggestions = () => {
    setShowAtomicityWarning(false);
    setShowPostSaveSuggestions(true);
  };

  const handleKeepAsIs = () => {
    setShowAtomicityWarning(false);
    setShowPostSaveSuggestions(true);
  };

  const handleCancel = () => {
    if (content.trim() && !confirm("Discard unsaved changes?")) {
      return;
    }
    router.push("/knowledge-base/notes");
  };

  const handleAddTag = (tag: string) => {
    // Add tag if not already present
    const currentTags = tags
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t);

    if (!currentTags.includes(tag)) {
      const newTags = [...currentTags, tag].join(", ");
      setTags(newTags);
      logger.info("Tag added from AI suggestion", { tag });
    }
  };

  const handleInsertLink = (noteId: string) => {
    // Insert wikilink at the end of content
    const wikilink = `[[${noteId}]]`;
    const newContent = content.trim() + `\n\n${wikilink}`;
    setContent(newContent);
    logger.info("Link inserted from AI suggestion", { noteId });
  };

  return (
    <div className="container mx-auto max-w-4xl px-4 py-8">
      {/* AI Panel */}
      <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />

      {/* AI Button */}
      {!aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      {/* Header */}
      <div className="mb-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex gap-4">
            <Link href="/knowledge-base" className="text-sm text-blue-600 hover:underline">
              ← Knowledge Base
            </Link>
            <Link href="/knowledge-base/notes" className="text-sm text-blue-600 hover:underline">
              All notes
            </Link>
          </div>
          <SettingsDropdown />
        </div>
        <h1 className="mb-2 text-3xl font-bold text-gray-900">Create New Note</h1>
        <p className="text-gray-600">Add a new note to your Zettelkasten knowledge base</p>
      </div>

      {/* Authentication status banner */}
      <AuthStatusBanner mode="auto" />

      {/* First-Person Voice Reminder */}
      {showFirstPersonReminder && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h4 className="mb-1 text-sm font-semibold text-blue-900">
                💭 Zettelkasten Tip: Write in first person
              </h4>
              <p className="mb-2 text-sm text-blue-800">
                Capture YOUR understanding, not objective facts. This makes notes more memorable and
                personal.
              </p>
              <div className="text-xs text-blue-700">
                <span className="font-medium">❌ Avoid:</span> &quot;DORA metrics measure deployment
                performance&quot;
                <br />
                <span className="font-medium">✓ Better:</span> &quot;I use DORA metrics to identify
                bottlenecks in my team&apos;s pipeline&quot;
              </div>
            </div>
            <button
              onClick={() => setShowFirstPersonReminder(false)}
              className="ml-4 text-blue-400 hover:text-blue-600"
              aria-label="Dismiss"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* Form */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Editor Column */}
        <div className="space-y-4 lg:col-span-2">
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
              placeholder="What's the ONE idea this note captures?"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              ✓ Good: &quot;Psychological safety enables early problem detection&quot; | ✗ Bad:
              &quot;Team Culture Concepts&quot;
            </p>
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
            <div className="mb-2 flex items-start justify-between">
              <label className="block text-sm font-medium text-gray-700">Content *</label>
              <div className="text-right text-xs text-gray-500">
                <span
                  className={
                    content.length >= 300 && content.length <= 500 ? "font-medium text-green-600" : ""
                  }
                >
                  {content.length} chars
                </span>
                {content.length > 0 && content.length < 300 && (
                  <span className="ml-2 text-gray-400">• Brief - good for atomic notes</span>
                )}
                {content.length >= 300 && content.length <= 500 && (
                  <span className="ml-2 text-green-600">• ✓ Good length for atomic note</span>
                )}
                {content.length > 500 && content.length <= 1000 && (
                  <span className="ml-2 text-yellow-600">• Getting long - single idea?</span>
                )}
                {content.length > 1000 && (
                  <span className="ml-2 text-orange-600">
                    • Consider splitting into multiple notes
                  </span>
                )}
              </div>
            </div>
            <NoteEditor
              content={content}
              onChange={setContent}
              allNotes={allNotes}
              placeholder="Capture ONE idea. Use [[note-id]] to connect related concepts..."
              onNoteClick={(noteId) => {
                // Open note in new tab
                window.open(`/knowledge-base/notes/${noteId}`, "_blank");
              }}
            />
            <p className="mt-2 text-xs text-gray-500">
              💡 Tip: Atomic notes are easier to link and reuse. If you&apos;re listing multiple
              concepts, consider creating separate notes.
            </p>
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

        {/* AI Suggestions Panel */}
        {settings.aiMode !== "off" && (
          <div className="lg:col-span-1">
            <AISuggestionsPanel
              noteId="new-note-temp-id"
              mode={settings.aiMode}
              content={content}
              onAddTag={handleAddTag}
              onInsertLink={handleInsertLink}
            />
          </div>
        )}
      </div>

      {/* Atomicity Warning Modal */}
      {showAtomicityWarning && atomicityIssues.length > 0 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h3 className="mb-3 text-lg font-semibold text-gray-900">
              📋 Note might cover multiple topics
            </h3>
            <p className="mb-4 text-gray-700">
              This note shows signs of covering more than one concept:
            </p>
            <ul className="mb-6 list-inside list-disc space-y-1 text-sm text-gray-700">
              {atomicityIssues.map((issue, index) => (
                <li key={index}>{issue}</li>
              ))}
            </ul>
            <div className="mb-4 rounded-lg bg-blue-50 p-3 text-sm text-gray-700">
              <p className="font-medium">💡 Zettelkasten tip:</p>
              <p className="mt-1">
                Atomic notes (one idea each) are easier to link and reuse. Consider splitting this
                into separate notes.
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleKeepAsIs}
                className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-700"
              >
                Keep As-Is
              </button>
              <button
                onClick={() => {
                  setShowAtomicityWarning(false);
                  if (savedNoteId) {
                    router.push(`/knowledge-base/notes/${savedNoteId}`);
                  }
                }}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition hover:bg-gray-50"
              >
                Edit Note
              </button>
            </div>
          </div>
        </div>
      )}

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
