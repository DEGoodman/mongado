"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { prefetchOnce } from "@/lib/prefetch";
import dynamic from "next/dynamic";

// AI panels load on demand, not in first-load JS
const AIPanel = dynamic(() => import("@/components/AIPanel"), { ssr: false });
const PostSaveAISuggestions = dynamic(() => import("@/components/PostSaveAISuggestions"), {
  ssr: false,
});
import AIButton from "@/components/AIButton";
import Breadcrumb from "@/components/Breadcrumb";
import Badge from "@/components/Badge";
import { TagPillList } from "@/components/TagPill";
import NoteEditorForm, { ParsedNoteValues } from "@/components/NoteEditorForm";
import {
  getNote,
  updateNote,
  deleteNote,
  getBacklinks,
  getOutboundLinks,
  Note,
  formatNoteDate,
} from "@/lib/api/notes";
import { logger } from "@/lib/logger";
import { mascotFor } from "@/lib/delight";
import { recordRecent } from "@/lib/recents";
import { sanitizeHtml } from "@/lib/sanitize";
import { useSettings } from "@/hooks/useSettings";
import { isAuthenticated } from "@/lib/api/client";
import { config } from "@/lib/config";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
import styles from "./page.module.scss";

export default function NoteDetailPage() {
  const { llmFeaturesEnabled } = useFeatureFlags();
  const params = useParams();
  const router = useRouter();
  const noteId = params.id as string;
  const { settings } = useSettings();

  // Check if AI features should be available
  // AI is available if: LLM features enabled AND (user is authenticated OR unauthenticated AI is allowed)
  const aiAvailable = llmFeaturesEnabled && (isAuthenticated() || config.allowUnauthenticatedAI);

  const [note, setNote] = useState<Note | null>(null);
  const [backlinks, setBacklinks] = useState<Note[]>([]);
  const [outboundLinks, setOutboundLinks] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [showPostSaveSuggestions, setShowPostSaveSuggestions] = useState(false);
  const [aiPrewarming, setAiPrewarming] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);

        // Fetch note, backlinks, and outbound links in parallel
        const [noteData, backlinksData, outboundData] = await Promise.all([
          getNote(noteId),
          getBacklinks(noteId),
          getOutboundLinks(noteId),
        ]);

        setNote(noteData);
        setBacklinks(backlinksData.backlinks);
        setOutboundLinks(outboundData.links);
        recordRecent({ type: "note", id: noteData.id, title: noteData.title || noteData.id });

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

  const refreshLinks = async () => {
    const [backlinksData, outboundData] = await Promise.all([
      getBacklinks(noteId),
      getOutboundLinks(noteId),
    ]);
    setBacklinks(backlinksData.backlinks);
    setOutboundLinks(outboundData.links);
  };

  const handleSave = async (values: ParsedNoteValues) => {
    try {
      setSaving(true);
      setError(null);

      const updatedNote = await updateNote(noteId, {
        content: values.content,
        title: values.title,
        tags: values.tags.length > 0 ? values.tags : undefined,
        is_reference: values.isReference,
      });

      setNote(updatedNote);
      setIsEditing(false);
      logger.info("Note updated successfully", { id: noteId });

      await refreshLinks();

      // Show AI suggestions modal after save (only if AI mode is real-time/automatic)
      if (settings.aiMode === "real-time") {
        setShowPostSaveSuggestions(true);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update note";
      setError(message);
      logger.error("Failed to update note", err);
    } finally {
      setSaving(false);
    }
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
      await refreshLinks();

      logger.info("Inserted link from post-save suggestion", { linkNoteId });
    } catch (err) {
      logger.error("Failed to insert link from suggestion", err);
    }
  };

  const handlePrewarmAndOpenSuggestions = async () => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    setAiPrewarming(true);

    try {
      // Pre-warm Ollama model
      await fetch(`${API_URL}/api/ollama/warmup`, {
        method: "POST",
      });
      logger.info("Ollama model pre-warmed for suggestions");
    } catch (err) {
      logger.error("Failed to pre-warm Ollama", err);
      // Continue anyway - warmup will happen on first suggestion request
    } finally {
      setAiPrewarming(false);
      // Open suggestions panel
      setShowPostSaveSuggestions(true);
    }
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

  const handleTagClick = (tag: string) => {
    router.push(`/knowledge-base/notes?tag=${encodeURIComponent(tag)}`);
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loadingContainer}>
          <div className={styles.loadingSkeleton}>
            <div className={styles.skeletonHeader}></div>
            <div className={styles.skeletonContent}></div>
          </div>
        </div>
      </div>
    );
  }

  if (error && !note) {
    return (
      <div className={styles.container}>
        <div className={styles.errorContainer}>
          <div className={styles.errorCard}>
            <h2 className={styles.errorTitle}>Error</h2>
            <p className={styles.errorMessage}>{error}</p>
            <Link href="/knowledge-base/notes" className={styles.backLink}>
              ← Back to notes
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!note) return null;

  return (
    <div className={styles.container}>
      {/* AI Panel (only when LLM features enabled) */}
      {llmFeaturesEnabled && <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />}

      {/* AI Button (only when LLM features enabled) */}
      {llmFeaturesEnabled && !aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      <div className={styles.main}>
        <div className={styles.contentGrid}>
          {/* Main content */}
          <div className={styles.mainContent}>
            {/* Header */}
            <div className={styles.header}>
              {/* Breadcrumb */}
              <div className={styles.headerTop}>
                <Breadcrumb section="notes" />
              </div>

              {/* Content Type Badge */}
              <div className={styles.badge}>
                <Badge type="note" />
              </div>

              {/* Title and metadata */}
              <div className={styles.titleRow}>
                <div className={styles.noteIdRow}>
                  {mascotFor(note.id) && (
                    <span className="delight-mascot" aria-hidden="true">
                      {mascotFor(note.id)}
                    </span>
                  )}
                  <code className={styles.noteId}>{note.id}</code>
                  {note.is_reference && <span className={styles.referenceBadge}>Reference</span>}
                </div>
                <h1 className={styles.noteTitle}>{note.title || "Untitled Note"}</h1>
              </div>

              {/* Metadata */}
              <div className={styles.meta}>
                <span>
                  Created{" "}
                  <time dateTime={String(note.created_at)}>{formatNoteDate(note.created_at)}</time>
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

              {/* Tags */}
              {note.tags.length > 0 && !isEditing && (
                <div className={styles.tags}>
                  <TagPillList tags={note.tags} onClick={handleTagClick} variant="note" />
                </div>
              )}

              {/* Actions */}
              {!isEditing && (
                <div className={styles.actions}>
                  <Link
                    href={`/knowledge-base/notes/graph?node=${note.id}`}
                    className={`${styles.button} ${styles.viewGraphButton}`}
                  >
                    View in Graph
                  </Link>
                  <button
                    onClick={() => setIsEditing(true)}
                    onMouseEnter={() =>
                      prefetchOnce("chunk:note-editor", () => import("@/components/NoteEditor"))
                    }
                    className={`${styles.button} ${styles.editButton}`}
                    aria-label="Edit this note"
                  >
                    Edit
                  </button>
                  <button
                    onClick={handleDelete}
                    className={`${styles.button} ${styles.deleteButton}`}
                    aria-label="Delete this note"
                  >
                    Delete
                  </button>
                  {aiAvailable && (
                    <button
                      onClick={handlePrewarmAndOpenSuggestions}
                      className={`${styles.button} ${styles.aiSuggestionsButton} ${aiPrewarming ? styles.prewarming : ""}`}
                      disabled={aiPrewarming}
                      aria-label={
                        aiPrewarming
                          ? "Preparing AI suggestions"
                          : "Get AI suggestions for related notes and tags"
                      }
                    >
                      {aiPrewarming ? "Preparing AI..." : "AI Suggestions"}
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Error message (view mode; edit mode errors render inside the form) */}
            {error && !isEditing && (
              <div className={styles.errorBox}>
                <p className={styles.errorMessage}>{error}</p>
              </div>
            )}

            {/* Content */}
            {isEditing ? (
              <NoteEditorForm
                mode="edit"
                noteId={noteId}
                initialValues={{
                  title: note.title || "",
                  tags: note.tags.join(", "),
                  content: note.content,
                  isReference: note.is_reference || false,
                }}
                saving={saving}
                error={error}
                onSave={handleSave}
                onCancel={() => {
                  setIsEditing(false);
                  setError(null);
                }}
                onOpenAIPanel={() => setAiPanelOpen(true)}
              />
            ) : (
              <div>
                {/* Server-rendered markdown (shared pipeline with articles, #233) */}
                <div className={styles.contentCard}>
                  {note.html_content ? (
                    <div
                      className={styles.renderedContent}
                      dangerouslySetInnerHTML={{ __html: sanitizeHtml(note.html_content) }}
                    />
                  ) : (
                    <div className={styles.plainContent}>{note.content}</div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Sidebar - Links and Backlinks */}
          <div className={styles.sidebar}>
            {/* Outbound Links */}
            {outboundLinks.length > 0 && (
              <div className={styles.sidebarSection}>
                <h3 className={styles.sectionTitle}>Links ({outboundLinks.length})</h3>
                <div className={styles.linksList}>
                  {outboundLinks.map((link) => (
                    <Link
                      key={link.id}
                      href={`/knowledge-base/notes/${link.id}`}
                      className={styles.linkItem}
                    >
                      <code className={styles.linkId}>{link.id}</code>
                      {link.title && <div className={styles.linkTitle}>{link.title}</div>}
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Backlinks */}
            {backlinks.length > 0 && (
              <div className={styles.sidebarSection}>
                <h3 className={styles.sectionTitle}>Backlinks ({backlinks.length})</h3>
                <div className={styles.linksList}>
                  {backlinks.map((backlink) => (
                    <Link
                      key={backlink.id}
                      href={`/knowledge-base/notes/${backlink.id}`}
                      className={styles.linkItem}
                    >
                      <code className={styles.linkId}>{backlink.id}</code>
                      {backlink.title && <div className={styles.linkTitle}>{backlink.title}</div>}
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* No links message */}
            {outboundLinks.length === 0 && backlinks.length === 0 && (
              <div className={styles.sidebarSection}>
                <p className={styles.emptyMessage}>
                  No links yet. Use <code>[[note-id]]</code> to connect notes
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Post-Save AI Suggestions Modal (only when LLM features enabled) */}
      {llmFeaturesEnabled && (
        <PostSaveAISuggestions
          noteId={noteId}
          isOpen={showPostSaveSuggestions}
          onClose={() => setShowPostSaveSuggestions(false)}
          onInsertLink={handleInsertLinkFromSuggestion}
        />
      )}
    </div>
  );
}
