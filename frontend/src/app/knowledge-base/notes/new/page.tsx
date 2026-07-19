"use client";

import { Suspense, useState, useEffect } from "react";
import { ClockCounterClockwise } from "@phosphor-icons/react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";

// AI panel loads on demand, not in first-load JS
const AIPanel = dynamic(() => import("@/components/AIPanel"), { ssr: false });
import type { PanelTab } from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
import NoteEditorForm, {
  EMPTY_NOTE_VALUES,
  NoteEditorValues,
  ParsedNoteValues,
} from "@/components/NoteEditorForm";
import { createNote } from "@/lib/api/notes";
import { logger } from "@/lib/logger";
import { useSettings } from "@/hooks/useSettings";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
import { saveDraft, loadDraft, clearDraft } from "@/lib/draft";
import styles from "./page.module.scss";

// Check if note appears non-atomic (covers multiple topics)
function checkAtomicity(content: string, title: string): string[] {
  const issues: string[] = [];

  // Count top-level bullet points (lines starting with - or *)
  const bulletPoints = content.split("\n").filter((line) => /^[-*]\s/.test(line.trim()));
  if (bulletPoints.length > 5) {
    issues.push(`${bulletPoints.length} bullet points - might cover multiple concepts`);
  }

  // Count H2/H3 headings (## or ###)
  const headings = content.split("\n").filter((line) => /^#{2,3}\s/.test(line.trim()));
  if (headings.length > 3) {
    issues.push(`${headings.length} section headings - consider splitting by topic`);
  }

  // Check for "and" in title suggesting multiple topics
  if (title && (title.includes(" and ") || title.includes(" & "))) {
    issues.push('Title contains "and" - might be combining multiple ideas');
  }

  return issues;
}

function NewNoteContent() {
  const { llmFeaturesEnabled } = useFeatureFlags();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { settings } = useSettings();

  // Initial form values; changing formKey remounts the form with new values
  const [initialValues, setInitialValues] = useState<NoteEditorValues>(() => ({
    ...EMPTY_NOTE_VALUES,
    // Pre-check "Quick Reference" if URL has ?ref=true
    isReference: searchParams.get("ref") === "true",
  }));
  const [formKey, setFormKey] = useState(0);
  // Mirror of the form's current values, for draft autosave and the cancel prompt
  const [currentValues, setCurrentValues] = useState<NoteEditorValues | null>(null);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [panel, setPanel] = useState<{ open: boolean; tab?: PanelTab }>({ open: false });
  const [draftRestored, setDraftRestored] = useState(false);
  const [savedNoteId, setSavedNoteId] = useState<string | null>(null);
  const [showAtomicityWarning, setShowAtomicityWarning] = useState(false);
  const [atomicityIssues, setAtomicityIssues] = useState<string[]>([]);

  // Load draft from localStorage on mount, or pre-fill from URL params (e.g., from article)
  useEffect(() => {
    // Check if coming from an article (URL params take precedence over drafts)
    const urlTitle = searchParams.get("title");
    const urlContent = searchParams.get("content");

    if (urlTitle || urlContent) {
      // Pre-fill from URL parameters (from "Create Note from Article" button)
      setInitialValues((prev) => ({
        ...prev,
        title: urlTitle ?? prev.title,
        content: urlContent ?? prev.content,
      }));
      setFormKey((k) => k + 1);
      logger.info("Note pre-filled from URL parameters");
      return; // Don't load draft if URL params present
    }

    // Otherwise, try to restore draft
    const draft = loadDraft();
    if (draft) {
      setInitialValues((prev) => ({
        title: draft.title,
        content: draft.content,
        tags: draft.tags,
        isReference: draft.isReference ?? prev.isReference,
      }));
      setFormKey((k) => k + 1);
      setDraftRestored(true);
      logger.info("Draft restored from localStorage", {
        savedAt: new Date(draft.savedAt).toISOString(),
      });
    }
  }, [searchParams]);

  // Auto-save draft to localStorage (debounced)
  useEffect(() => {
    if (!currentValues) return;
    const { title, content, tags, isReference } = currentValues;

    // Don't save if all fields are empty
    if (!title && !content && !tags) return;

    const timeoutId = setTimeout(() => {
      saveDraft({ title, content, tags, isReference });
    }, 500); // 500ms debounce

    return () => clearTimeout(timeoutId);
  }, [currentValues]);

  const handleDiscardDraft = () => {
    clearDraft();
    setInitialValues(EMPTY_NOTE_VALUES);
    setCurrentValues(null);
    setFormKey((k) => k + 1);
    setDraftRestored(false);
  };

  const handleSave = async (values: ParsedNoteValues) => {
    try {
      setSaving(true);
      setError(null);

      const note = await createNote({
        content: values.content,
        title: values.title,
        tags: values.tags.length > 0 ? values.tags : undefined,
        is_reference: values.isReference,
      });

      logger.info("Note created successfully", { id: note.id });
      setSavedNoteId(note.id);

      // Clear draft after successful save
      clearDraft();
      setDraftRestored(false);

      // Check atomicity and show warning if issues detected
      const issues = checkAtomicity(values.content, values.title ?? "");
      if (issues.length > 0) {
        setAtomicityIssues(issues);
        setShowAtomicityWarning(true);
      } else {
        goToNote(note.id);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create note";
      setError(message);
      logger.error("Failed to create note", err);
    } finally {
      setSaving(false);
    }
  };

  // Navigate to the saved note; in real-time AI mode, open its suggestions panel on arrival
  const goToNote = (noteId: string) => {
    const suffix = settings.aiMode === "real-time" ? "?suggest=1" : "";
    router.push(`/knowledge-base/notes/${noteId}${suffix}`);
  };

  const handleAtomicityKeepAsIs = () => {
    setShowAtomicityWarning(false);
    if (savedNoteId) {
      goToNote(savedNoteId);
    }
  };

  const handleCancel = () => {
    if (currentValues?.content.trim() && !confirm("Discard unsaved changes?")) {
      return;
    }
    router.push("/knowledge-base/notes");
  };

  return (
    <div className={styles.container}>
      {/* AI Panel (only when LLM features enabled) */}
      {llmFeaturesEnabled && (
        <AIPanel
          isOpen={panel.open}
          onClose={() => setPanel({ open: false })}
          defaultTab={panel.tab}
        />
      )}

      {/* AI Button (only when LLM features enabled) */}
      {llmFeaturesEnabled && !panel.open && <AIButton onClick={() => setPanel({ open: true })} />}

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
          </div>
          <h1 className={styles.title}>Create New Note</h1>
          <p className={styles.subtitle}>Add a new note to your Zettelkasten knowledge base</p>
        </div>

        {/* Draft Restored Banner */}
        {draftRestored && (
          <div className={styles.draftBanner}>
            <span>
              <ClockCounterClockwise size={16} aria-hidden="true" /> Draft restored from your
              previous session
            </span>
            <button onClick={handleDiscardDraft} className={styles.discardButton}>
              Discard draft
            </button>
          </div>
        )}

        <NoteEditorForm
          key={formKey}
          mode="create"
          initialValues={initialValues}
          saving={saving}
          error={error}
          onSave={handleSave}
          onCancel={handleCancel}
          onOpenAIPanel={(tab) => setPanel({ open: true, tab })}
          onValuesChange={setCurrentValues}
        />
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
              <p>Zettelkasten tip:</p>
              <p>
                Atomic notes (one idea each) are easier to link and reuse. Consider splitting this
                into separate notes.
              </p>
            </div>
            <div className={styles.modalActions}>
              <button
                onClick={handleAtomicityKeepAsIs}
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
    </div>
  );
}

export default function NewNotePage() {
  return (
    <Suspense fallback={<div className={styles.loadingContainer}>Loading...</div>}>
      <NewNoteContent />
    </Suspense>
  );
}
