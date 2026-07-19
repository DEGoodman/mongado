"use client";

import { Suspense, useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { prefetchOnce } from "@/lib/prefetch";
import dynamic from "next/dynamic";

// AI panel loads on demand, not in first-load JS
const AIPanel = dynamic(() => import("@/components/AIPanel"), { ssr: false });
import type { PanelTab } from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
import Breadcrumb from "@/components/Breadcrumb";
import Badge from "@/components/Badge";
import { TagPillList } from "@/components/TagPill";
import { LoadingState, ErrorState } from "@/components/PageState";
import NoteEditorForm, { NoteEditorValues, ParsedNoteValues } from "@/components/NoteEditorForm";
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
import { useHydrated } from "@/hooks/useHydrated";
import styles from "./page.module.scss";

function noteToEditorValues(note: Note): NoteEditorValues {
  return {
    title: note.title || "",
    tags: note.tags.join(", "),
    content: note.content,
    isReference: note.is_reference || false,
  };
}

function NoteDetailContent() {
  const { llmFeaturesEnabled } = useFeatureFlags();
  // Gate ssr:false panels out of the hydration render (see useHydrated)
  const llmUiReady = useHydrated() && llmFeaturesEnabled;
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
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
  const [panel, setPanel] = useState<{ open: boolean; tab?: PanelTab }>({ open: false });
  const [aiPrewarming, setAiPrewarming] = useState(false);

  // Editor seed: initial values + key so suggestion actions can patch the draft via remount
  const [editorSeed, setEditorSeed] = useState<{ values: NoteEditorValues; key: number } | null>(
    null
  );
  // Mirror of the form's current values while editing
  const [currentValues, setCurrentValues] = useState<NoteEditorValues | null>(null);

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

  // Open the panel on Suggest when arriving from a fresh save (?suggest=1)
  useEffect(() => {
    if (searchParams.get("suggest") === "1") {
      setPanel({ open: true, tab: "suggest" });
    }
  }, [searchParams]);

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

  const startEditing = () => {
    if (!note) return;
    const values = noteToEditorValues(note);
    setEditorSeed({ values, key: Date.now() });
    setCurrentValues(values);
    setIsEditing(true);
  };

  const stopEditing = () => {
    setIsEditing(false);
    setEditorSeed(null);
    setCurrentValues(null);
    setError(null);
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
      stopEditing();
      logger.info("Note updated successfully", { id: noteId });

      await refreshLinks();

      // Offer suggestions for the fresh content (only if AI mode is real-time/automatic)
      if (settings.aiMode === "real-time") {
        setPanel({ open: true, tab: "suggest" });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update note";
      setError(message);
      logger.error("Failed to update note", err);
    } finally {
      setSaving(false);
    }
  };

  // Patch the draft while editing: remount the form with updated seed values
  const applyDraftPatch = (next: NoteEditorValues) => {
    setEditorSeed((seed) => ({ values: next, key: (seed?.key ?? 0) + 1 }));
    setCurrentValues(next);
  };

  const handleInsertLinkFromPanel = async (linkNoteId: string) => {
    if (isEditing && currentValues) {
      // Editing: append to the unsaved draft
      applyDraftPatch({
        ...currentValues,
        content: currentValues.content.trim() + `\n\n[[${linkNoteId}]]`,
      });
      logger.info("Link inserted into draft from AI suggestion", { linkNoteId });
      return;
    }

    // View mode: update the saved note directly
    if (!note) return;
    if (!isAuthenticated()) {
      setError("You must be logged in to save notes. Changes you make will not be persisted.");
      logger.warn("Unauthenticated user attempted to insert link");
      return;
    }

    try {
      // Fetch fresh state first: rapid successive panel actions would otherwise
      // clobber each other via the stale `note` closure
      const fresh = await getNote(noteId);
      const updatedNote = await updateNote(noteId, {
        content: fresh.content.trim() + `\n\n[[${linkNoteId}]]`,
        title: fresh.title || undefined,
        tags: fresh.tags,
      });

      setNote(updatedNote);
      await refreshLinks();
      logger.info("Inserted link from AI suggestion", { linkNoteId });
    } catch (err) {
      logger.error("Failed to insert link from suggestion", err);
    }
  };

  const handleAddTagFromPanel = async (tag: string) => {
    if (isEditing && currentValues) {
      // Editing: add to the unsaved draft
      const tags = currentValues.tags
        .split(",")
        .map((t) => t.trim())
        .filter((t) => t);
      if (!tags.includes(tag)) {
        applyDraftPatch({ ...currentValues, tags: [...tags, tag].join(", ") });
        logger.info("Tag added to draft from AI suggestion", { tag });
      }
      return;
    }

    // View mode: update the saved note directly
    if (!note || note.tags.includes(tag)) return;
    if (!isAuthenticated()) {
      setError("You must be logged in to save notes. Changes you make will not be persisted.");
      logger.warn("Unauthenticated user attempted to add tag");
      return;
    }

    try {
      // Fetch fresh state first: rapid successive panel actions would otherwise
      // clobber each other via the stale `note` closure
      const fresh = await getNote(noteId);
      if (fresh.tags.includes(tag)) return;
      const updatedNote = await updateNote(noteId, {
        content: fresh.content,
        title: fresh.title || undefined,
        tags: [...fresh.tags, tag],
      });

      setNote(updatedNote);
      logger.info("Tag added from AI suggestion", { tag });
    } catch (err) {
      logger.error("Failed to add tag from suggestion", err);
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
        <LoadingState variant="content" width="wide" label="Loading note" />
      </div>
    );
  }

  if (error && !note) {
    return (
      <div className={styles.container}>
        <ErrorState
          message={error}
          width="wide"
          backHref="/knowledge-base/notes"
          backLabel="← Back to notes"
        />
      </div>
    );
  }

  if (!note) return null;

  return (
    <div className={styles.container}>
      {/* AI Panel with note-aware Suggest tab (only when LLM features enabled) */}
      {llmUiReady && (
        <AIPanel
          isOpen={panel.open}
          onClose={() => setPanel({ open: false })}
          defaultTab={panel.tab}
          suggest={{
            noteId,
            aiMode: settings.aiMode,
            content: isEditing ? currentValues?.content : undefined,
            onAddTag: handleAddTagFromPanel,
            onInsertLink: handleInsertLinkFromPanel,
          }}
        />
      )}

      {/* AI Button (only when LLM features enabled) */}
      {llmUiReady && !panel.open && <AIButton onClick={() => setPanel({ open: true })} />}

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
                    onClick={startEditing}
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
                      onClick={() => setPanel({ open: true, tab: "suggest" })}
                      className={`${styles.button} ${styles.aiSuggestionsButton}`}
                      aria-label="Get AI suggestions for related notes and tags"
                    >
                      AI Suggestions
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Error message (view mode; edit mode errors render inside the form) */}
            {error && !isEditing && <ErrorState inline message={error} />}

            {/* Content */}
            {isEditing && editorSeed ? (
              <NoteEditorForm
                key={editorSeed.key}
                mode="edit"
                initialValues={editorSeed.values}
                saving={saving}
                error={error}
                onSave={handleSave}
                onCancel={stopEditing}
                onOpenAIPanel={(tab) => setPanel({ open: true, tab })}
                onValuesChange={setCurrentValues}
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
    </div>
  );
}

export default function NoteDetailPage() {
  return (
    <Suspense fallback={<LoadingState variant="content" width="wide" label="Loading note" />}>
      <NoteDetailContent />
    </Suspense>
  );
}
