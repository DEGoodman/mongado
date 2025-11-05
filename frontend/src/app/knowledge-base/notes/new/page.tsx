"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import NoteEditor from "@/components/NoteEditor";
import { createNote, listNotes, updateNote, getNote, Note } from "@/lib/api/notes";
import { logger } from "@/lib/logger";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
import PostSaveAISuggestions from "@/components/PostSaveAISuggestions";
import SettingsDropdown from "@/components/SettingsDropdown";
import AISuggestionsPanel from "@/components/AISuggestionsPanel";
import { useSettings } from "@/hooks/useSettings";
import { isAuthenticated } from "@/lib/api/client";
import { config } from "@/lib/config";
import styles from "./page.module.scss";

export default function NewNotePage() {
  const router = useRouter();
  const { settings } = useSettings();

  // Check if AI features should be available
  // AI is available if: user is authenticated OR unauthenticated AI is allowed
  const aiAvailable = isAuthenticated() || config.allowUnauthenticatedAI;

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
  const [aiSuggestionsOpen, setAiSuggestionsOpen] = useState(false);

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
    // Check authentication before saving
    if (!isAuthenticated()) {
      setError("You must be logged in to create notes. Changes you make will not be persisted.");
      logger.warn("Unauthenticated user attempted to create note");
      return;
    }

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

    // Check authentication before saving
    if (!isAuthenticated()) {
      setError("You must be logged in to save notes. Changes you make will not be persisted.");
      logger.warn("Unauthenticated user attempted to insert link");
      return;
    }

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
    <div className={styles.container}>
      {/* AI Panel */}
      <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />

      {/* AI Button */}
      {!aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      <div className={styles.main}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerTop}>
            <div className={styles.breadcrumbs}>
              <Link href="/knowledge-base" className={styles.breadcrumbLink}>
                ← Knowledge Base
              </Link>
              <Link href="/knowledge-base/notes" className={styles.breadcrumbLink}>
                All notes
              </Link>
            </div>
            <SettingsDropdown />
          </div>
          <h1 className={styles.title}>Create New Note</h1>
          <p className={styles.subtitle}>Add a new note to your Zettelkasten knowledge base</p>
        </div>

        {/* First-Person Voice Reminder */}
        {showFirstPersonReminder && (
          <div className={styles.tipBox}>
            <div className={styles.tipHeader}>
              <div>
                <h4 className={styles.tipTitle}>💭 Zettelkasten Tip: Write in first person</h4>
                <p className={styles.tipContent}>
                  Capture YOUR understanding, not objective facts. This makes notes more memorable
                  and personal.
                </p>
                <div className={styles.tipExamples}>
                  <span className="font-medium">❌ Avoid:</span> &quot;DORA metrics measure
                  deployment performance&quot;
                  <br />
                  <span className="font-medium">✓ Better:</span> &quot;I use DORA metrics to
                  identify bottlenecks in my team&apos;s pipeline&quot;
                </div>
              </div>
              <button
                onClick={() => setShowFirstPersonReminder(false)}
                className={styles.dismissButton}
                aria-label="Dismiss"
              >
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
          <div className={styles.errorBox}>
            <p className={styles.errorMessage}>{error}</p>
          </div>
        )}

        {/* Form */}
        <div
          className={
            aiSuggestionsOpen ? styles.editorGrid + " " + styles.withSidebar : styles.editorGrid
          }
        >
          {/* Editor Column */}
          <div className={styles.editorColumn}>
            {/* Title (optional) */}
            <div>
              <label htmlFor="title" className={styles.formLabel}>
                Title (optional)
              </label>
              <input
                id="title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="What's the ONE idea this note captures?"
                className={styles.formInput}
              />
              <p className={styles.formHint}>
                ✓ Good: &quot;Psychological safety enables early problem detection&quot; | ✗ Bad:
                &quot;Team Culture Concepts&quot;
              </p>
            </div>

            {/* Tags (optional) */}
            <div>
              <label htmlFor="tags" className={styles.formLabel}>
                Tags (optional)
              </label>
              <input
                id="tags"
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="Comma-separated tags (e.g., idea, research, todo)"
                className={styles.formInput}
              />
            </div>

            {/* Content */}
            <div>
              <div className={styles.charCountWrapper}>
                <label className={styles.formLabel}>Content *</label>
                <div className={styles.charCount}>
                  <span
                    className={
                      content.length >= 300 && content.length <= 500
                        ? styles.count + " " + styles.good
                        : styles.count
                    }
                  >
                    {content.length} chars
                  </span>
                  {content.length > 0 && content.length < 300 && (
                    <span className={styles.hint}>• Brief - good for atomic notes</span>
                  )}
                  {content.length >= 300 && content.length <= 500 && (
                    <span className={styles.hint + " " + styles.good}>
                      • ✓ Good length for atomic note
                    </span>
                  )}
                  {content.length > 500 && content.length <= 1000 && (
                    <span className={styles.hint + " " + styles.warning}>
                      • Getting long - single idea?
                    </span>
                  )}
                  {content.length > 1000 && (
                    <span className={styles.hint + " " + styles.error}>
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
              <p className={styles.formHint}>
                💡 Tip: Atomic notes are easier to link and reuse. If you&apos;re listing multiple
                concepts, consider creating separate notes.
              </p>
            </div>

            {/* Actions */}
            <div className={styles.actions}>
              <button
                onClick={() => handleSave()}
                disabled={saving || !content.trim()}
                className={`${styles.button} ${styles.saveButton}`}
              >
                {saving ? "Saving..." : "Save Note"}
              </button>
              <button
                onClick={handleCancel}
                disabled={saving}
                className={`${styles.button} ${styles.cancelButton}`}
              >
                Cancel
              </button>
              {settings.aiMode !== "off" && aiAvailable && (
                <button
                  onClick={() => setAiSuggestionsOpen(!aiSuggestionsOpen)}
                  className={`${styles.button} ${styles.aiButton}`}
                >
                  {aiSuggestionsOpen ? "Hide AI Suggestions" : "✨ Get AI Suggestions"}
                </button>
              )}
            </div>
          </div>

          {/* AI Suggestions Panel */}
          {settings.aiMode !== "off" && aiAvailable && aiSuggestionsOpen && (
            <AISuggestionsPanel
              noteId="new-note-temp-id"
              mode={settings.aiMode}
              content={content}
              isOpen={aiSuggestionsOpen}
              onClose={() => setAiSuggestionsOpen(false)}
              onAddTag={handleAddTag}
              onInsertLink={handleInsertLink}
            />
          )}
        </div>
      </div>

      {/* Atomicity Warning Modal */}
      {showAtomicityWarning && atomicityIssues.length > 0 && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <h3 className={styles.modalTitle}>📋 Note might cover multiple topics</h3>
            <p className={styles.modalText}>
              This note shows signs of covering more than one concept:
            </p>
            <ul className={styles.modalList}>
              {atomicityIssues.map((issue, index) => (
                <li key={index}>{issue}</li>
              ))}
            </ul>
            <div className={styles.modalInfo}>
              <p>💡 Zettelkasten tip:</p>
              <p>
                Atomic notes (one idea each) are easier to link and reuse. Consider splitting this
                into separate notes.
              </p>
            </div>
            <div className={styles.modalActions}>
              <button
                onClick={handleKeepAsIs}
                className={`${styles.modalButton} ${styles.primary}`}
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
                className={`${styles.modalButton} ${styles.secondary}`}
              >
                Edit Note
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Zero Links Warning Modal */}
      {showZeroLinksWarning && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <h3 className={styles.modalTitle}>💡 No connections found</h3>
            <p className={styles.modalText}>
              This note has no connections to other notes. Zettelkasten works best when ideas link
              together.
            </p>
            <p className={styles.modalText}>Consider:</p>
            <ul className={styles.modalList}>
              <li>What concepts does this relate to?</li>
              <li>What led to this idea?</li>
              <li>Where might you apply this?</li>
            </ul>
            <div className={styles.modalActions}>
              <button
                onClick={handleGetAISuggestions}
                className={`${styles.modalButton} ${styles.primary}`}
              >
                Get AI Link Suggestions
              </button>
              <button
                onClick={handleSaveAnyway}
                disabled={saving}
                className={`${styles.modalButton} ${styles.secondary}`}
                style={{ opacity: saving ? 0.5 : 1 }}
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
