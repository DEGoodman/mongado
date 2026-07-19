"use client";

import { useEffect, useState } from "react";
import { Lightbulb, Sparkle, X, Check } from "@phosphor-icons/react";
import dynamic from "next/dynamic";

// Heavy editor (CodeMirror) and AI panel load on demand, not in first-load JS
const NoteEditor = dynamic(() => import("@/components/NoteEditor"), {
  ssr: false,
  loading: () => <div style={{ minHeight: "400px" }}>Loading editor…</div>,
});
const AISuggestionsPanel = dynamic(() => import("@/components/AISuggestionsPanel"), {
  ssr: false,
});
import TemplateSelector from "@/components/TemplateSelector";
import { listNotes, Note } from "@/lib/api/notes";
import { listTemplates, getTemplate, TemplateMetadata } from "@/lib/api/templates";
import { logger } from "@/lib/logger";
import { useSettings } from "@/hooks/useSettings";
import { isAuthenticated } from "@/lib/api/client";
import { config } from "@/lib/config";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
import styles from "./NoteEditorForm.module.scss";

export interface NoteEditorValues {
  title: string;
  tags: string; // raw comma-separated input
  content: string;
  isReference: boolean;
}

export interface ParsedNoteValues {
  content: string;
  title?: string;
  tags: string[];
  isReference: boolean;
}

export const EMPTY_NOTE_VALUES: NoteEditorValues = {
  title: "",
  tags: "",
  content: "",
  isReference: false,
};

interface NoteEditorFormProps {
  mode: "create" | "edit";
  /** Existing note id (edit mode); create mode uses a placeholder id for AI suggestions */
  noteId?: string;
  initialValues: NoteEditorValues;
  saving: boolean;
  /** Error from the parent (API failures etc.); merged with form-level validation errors */
  error: string | null;
  /** Called once validation and the zero-links gate have passed */
  onSave: (values: ParsedNoteValues) => Promise<void> | void;
  onCancel: () => void;
  /** Opens the floating AI panel (owned by the page) from the zero-links modal */
  onOpenAIPanel: () => void;
  /** Fires on every field change; used by the create page for draft autosave */
  onValuesChange?: (values: NoteEditorValues) => void;
}

function hasWikilinks(text: string): boolean {
  return /\[\[[a-z0-9-]+\]\]/i.test(text);
}

export default function NoteEditorForm({
  mode,
  noteId,
  initialValues,
  saving,
  error,
  onSave,
  onCancel,
  onOpenAIPanel,
  onValuesChange,
}: NoteEditorFormProps) {
  const { llmFeaturesEnabled } = useFeatureFlags();
  const { settings } = useSettings();

  const [values, setValues] = useState<NoteEditorValues>(initialValues);
  const [formError, setFormError] = useState<string | null>(null);
  const [aiSuggestionsOpen, setAiSuggestionsOpen] = useState(false);
  const [showZeroLinksWarning, setShowZeroLinksWarning] = useState(false);
  const [allNotes, setAllNotes] = useState<Note[]>([]);
  const [templates, setTemplates] = useState<TemplateMetadata[]>([]);
  const [loadingTemplate, setLoadingTemplate] = useState(false);
  const [showFirstPersonReminder, setShowFirstPersonReminder] = useState(mode === "create");

  // AI is available if: LLM features enabled AND (authenticated OR unauthenticated AI allowed).
  // Initialize to false to avoid hydration mismatch (updated client-side only).
  const [aiAvailable, setAiAvailable] = useState(false);
  useEffect(() => {
    setAiAvailable(llmFeaturesEnabled && (isAuthenticated() || config.allowUnauthenticatedAI));
  }, [llmFeaturesEnabled]);

  // Load all notes for wikilink autocomplete
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

  // Load available templates (create mode only)
  useEffect(() => {
    if (mode !== "create") return;

    async function fetchTemplates() {
      try {
        const response = await listTemplates();
        setTemplates(response.templates);
        logger.info("Loaded templates", { count: response.count });
      } catch (err) {
        logger.error("Failed to load templates", err);
      }
    }

    fetchTemplates();
  }, [mode]);

  const update = (patch: Partial<NoteEditorValues>) => {
    const next = { ...values, ...patch };
    setValues(next);
    onValuesChange?.(next);
  };

  const handleApplyTemplate = async (templateId: string) => {
    if (!templateId) return;

    setLoadingTemplate(true);
    try {
      const template = await getTemplate(templateId);
      update({ content: template.content });
      // Don't override title - let user fill it in
      setShowFirstPersonReminder(false); // Hide tip after template is applied
      logger.info("Template applied", { templateId });
    } catch (err) {
      logger.error("Failed to apply template", err);
      setFormError("Failed to load template");
    } finally {
      setLoadingTemplate(false);
    }
  };

  const handleSave = async (forceSave = false) => {
    // Check authentication before saving
    if (!isAuthenticated()) {
      setFormError(
        mode === "create"
          ? "You must be logged in to create notes. Changes you make will not be persisted."
          : "You must be logged in to save notes. Changes you make will not be persisted."
      );
      logger.warn("Unauthenticated user attempted to save note");
      return;
    }

    if (!values.content.trim()) {
      setFormError("Content cannot be empty");
      return;
    }
    setFormError(null);

    // Check for zero wikilinks and show warning (unless forcing save)
    if (!forceSave && !hasWikilinks(values.content)) {
      setShowZeroLinksWarning(true);
      return;
    }

    const tagArray = values.tags
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t);

    await onSave({
      content: values.content,
      title: values.title.trim() || undefined,
      tags: tagArray,
      isReference: values.isReference,
    });
  };

  const handleSaveAnyway = async () => {
    setShowZeroLinksWarning(false);
    await handleSave(true);
  };

  const handleGetAISuggestions = () => {
    setShowZeroLinksWarning(false);
    onOpenAIPanel();
  };

  const handleAddTag = (tag: string) => {
    // Add tag if not already present
    const currentTags = values.tags
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t);

    if (!currentTags.includes(tag)) {
      update({ tags: [...currentTags, tag].join(", ") });
      logger.info("Tag added from AI suggestion", { tag });
    }
  };

  const handleInsertLink = (linkNoteId: string) => {
    // Insert wikilink at the end of content
    update({ content: values.content.trim() + `\n\n[[${linkNoteId}]]` });
    logger.info("Link inserted from AI suggestion", { noteId: linkNoteId });
  };

  const displayError = error ?? formError;
  const contentLength = values.content.length;

  return (
    <>
      {/* First-Person Voice Reminder (create mode) */}
      {showFirstPersonReminder && (
        <div className={styles.tipBox}>
          <div className={styles.tipHeader}>
            <div>
              <h4 className={styles.tipTitle}>
                <Lightbulb size={16} aria-hidden="true" /> Zettelkasten Tip: Write in first person
              </h4>
              <p className={styles.tipContent}>
                Capture YOUR understanding, not objective facts. This makes notes more memorable and
                personal.
              </p>
              <div className={styles.tipExamples}>
                <span className={styles.tipAvoid}>
                  <X size={12} aria-hidden="true" /> Avoid:
                </span>{" "}
                &quot;DORA metrics measure deployment performance&quot;
                <br />
                <span className={styles.tipBetter}>
                  <Check size={12} aria-hidden="true" /> Better:
                </span>{" "}
                &quot;I use DORA metrics to identify bottlenecks in my team&apos;s pipeline&quot;
              </div>
            </div>
            <button
              onClick={() => setShowFirstPersonReminder(false)}
              className={styles.dismissButton}
              aria-label="Dismiss"
            >
              <X size={20} aria-hidden="true" />
            </button>
          </div>
        </div>
      )}

      {/* Error message */}
      {displayError && (
        <div className={styles.errorBox}>
          <p className={styles.errorMessage}>{displayError}</p>
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
          {/* Template Selector - compact button (create mode) */}
          {mode === "create" && (
            <div className={styles.templateRow}>
              <TemplateSelector
                templates={templates}
                onSelectTemplate={handleApplyTemplate}
                disabled={loadingTemplate}
                loading={loadingTemplate}
              />
            </div>
          )}

          {/* Title (optional) */}
          <div>
            <label htmlFor="note-title" className={styles.formLabel}>
              Title (optional)
            </label>
            <input
              id="note-title"
              type="text"
              value={values.title}
              onChange={(e) => update({ title: e.target.value })}
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
            <label htmlFor="note-tags" className={styles.formLabel}>
              Tags (optional)
            </label>
            <input
              id="note-tags"
              type="text"
              value={values.tags}
              onChange={(e) => update({ tags: e.target.value })}
              placeholder="Comma-separated tags (e.g., idea, research, todo)"
              className={styles.formInput}
            />
          </div>

          {/* Reference Toggle */}
          <div className={styles.referenceToggle}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={values.isReference}
                onChange={(e) => update({ isReference: e.target.checked })}
                className={styles.checkbox}
              />
              <span className={styles.checkboxText}>Quick Reference</span>
            </label>
            <p className={styles.formHint}>
              Check for checklists, frameworks, acronyms — not personal insights
            </p>
          </div>

          {/* Content */}
          <div>
            <div className={styles.charCountWrapper}>
              <label className={styles.formLabel}>Content *</label>
              <div className={styles.charCount}>
                <span
                  className={
                    contentLength >= 300 && contentLength <= 500
                      ? styles.count + " " + styles.good
                      : styles.count
                  }
                >
                  {contentLength} chars
                </span>
                {contentLength > 0 && contentLength < 300 && (
                  <span className={styles.hint}>• Brief - good for atomic notes</span>
                )}
                {contentLength >= 300 && contentLength <= 500 && (
                  <span className={styles.hint + " " + styles.good}>
                    • ✓ Good length for atomic note
                  </span>
                )}
                {contentLength > 500 && contentLength <= 1000 && (
                  <span className={styles.hint + " " + styles.warning}>
                    • Getting long - single idea?
                  </span>
                )}
                {contentLength > 1000 && (
                  <span className={styles.hint + " " + styles.error}>
                    • Consider splitting into multiple notes
                  </span>
                )}
              </div>
            </div>
            <NoteEditor
              content={values.content}
              onChange={(content) => update({ content })}
              allNotes={allNotes}
              placeholder="Capture ONE idea. Use [[note-id]] to connect related concepts..."
              onNoteClick={(id) => {
                // Open note in new tab
                window.open(`/knowledge-base/notes/${id}`, "_blank");
              }}
            />
            <p className={styles.formHint}>
              Tip: Atomic notes are easier to link and reuse. If you&apos;re listing multiple
              concepts, consider creating separate notes.
            </p>
          </div>

          {/* Actions */}
          <div className={styles.actions}>
            <button
              onClick={() => handleSave()}
              disabled={saving || !values.content.trim()}
              className={`${styles.button} ${styles.saveButton}`}
              data-delight-sparkle
            >
              {saving ? "Saving..." : mode === "create" ? "Save Note" : "Save Changes"}
            </button>
            <button
              onClick={onCancel}
              disabled={saving}
              className={`${styles.button} ${styles.cancelButton}`}
            >
              Cancel
            </button>
            {settings.aiMode !== "off" && aiAvailable && (
              <button
                onClick={() => setAiSuggestionsOpen(!aiSuggestionsOpen)}
                className={`${styles.button} ${styles.aiButton}`}
                aria-label={
                  aiSuggestionsOpen
                    ? "Hide AI suggestions panel"
                    : "Show AI suggestions for tags and links"
                }
                aria-expanded={aiSuggestionsOpen}
              >
                {aiSuggestionsOpen ? (
                  "Hide AI Suggestions"
                ) : (
                  <>
                    <Sparkle size={16} aria-hidden="true" /> Get AI Suggestions
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {/* AI Suggestions Panel */}
        {settings.aiMode !== "off" && aiAvailable && aiSuggestionsOpen && (
          <AISuggestionsPanel
            noteId={noteId ?? "new-note-temp-id"}
            mode={settings.aiMode}
            content={values.content}
            isOpen={aiSuggestionsOpen}
            onClose={() => setAiSuggestionsOpen(false)}
            onAddTag={handleAddTag}
            onInsertLink={handleInsertLink}
          />
        )}
      </div>

      {/* Zero Links Warning Modal */}
      {showZeroLinksWarning && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <h3 className={styles.modalTitle}>No connections found</h3>
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
              >
                Save Anyway
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
