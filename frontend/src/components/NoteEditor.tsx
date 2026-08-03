"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { ArrowsInSimple, ArrowsOutSimple } from "@phosphor-icons/react";
import { useResolvedTheme } from "@/hooks/useResolvedTheme";
import { markdown } from "@codemirror/lang-markdown";
import { EditorView } from "@codemirror/view";
import { logger } from "@/lib/logger";
import { Note } from "@/lib/api/notes";
import EditorDropdown, { EditorDropdownItem } from "@/components/EditorDropdown";
import {
  SlashCommandDef,
  detectSlashCommandTrigger,
  filterSlashCommands,
  getParagraphBounds,
  getPrecedingText,
} from "@/lib/slashCommands";
import { runEditorAssist, streamEditorAssist, EditorLinkSuggestion } from "@/lib/api/editorAssist";
import styles from "./NoteEditor.module.scss";

interface NoteEditorProps {
  content: string;
  onChange: (content: string) => void;
  placeholder?: string;
  allNotes?: Note[];
  onNoteClick?: (noteId: string) => void;
  /** Whether the slash-command palette ("/", #146) is armed. When false, "/"
   * is a plain character with zero interception - gated by user setting +
   * aiMode + auth in NoteEditorForm.tsx. */
  slashCommandsArmed?: boolean;
  /** Current note title, sent as prompt context for slash commands. */
  noteTitle?: string;
  /** Saved note ID (edit mode only); undefined for a note being created. */
  noteId?: string;
}

const slashCommandLogger = logger.withContext("SlashCommands");

export default function NoteEditor({
  content,
  onChange,
  placeholder = "Start typing your note... Use [[note-id]] to link to other notes",
  allNotes = [],
  onNoteClick,
  slashCommandsArmed = false,
  noteTitle,
  noteId,
}: NoteEditorProps) {
  const theme = useResolvedTheme();
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [autocompleteQuery, setAutocompleteQuery] = useState("");
  const [autocompletePosition, setAutocompletePosition] = useState({ top: 0, left: 0 });
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [editorView, setEditorView] = useState<EditorView | null>(null);
  const [zen, setZen] = useState(false);

  // ===== Slash-command palette state (#146) =====
  const [slashOpen, setSlashOpen] = useState(false);
  const [slashMode, setSlashMode] = useState<"commands" | "link-results">("commands");
  const [slashQuery, setSlashQuery] = useState("");
  const [slashPosition, setSlashPosition] = useState({ top: 0, left: 0 });
  const [slashSelectedIndex, setSlashSelectedIndex] = useState(0);
  const [linkCandidates, setLinkCandidates] = useState<EditorLinkSuggestion[]>([]);
  const [pendingIndicator, setPendingIndicator] = useState<{
    top: number;
    left: number;
  } | null>(null);
  const [keepUndo, setKeepUndo] = useState<{
    position: { top: number; left: number };
    snapshotText: string;
    snapshotSelection: number;
  } | null>(null);
  const [errorFlash, setErrorFlash] = useState<{
    message: string;
    position: { top: number; left: number };
  } | null>(null);

  // Absolute doc position of the "/" that opened the palette. Kept in a ref
  // (not state) because it's read synchronously inside handleChange/keydown
  // handlers that fire between renders.
  const slashTriggerFromRef = useRef<number>(0);
  // True while a slash command is executing (removal, streaming, fallback) -
  // guards handleChange from re-arming the palette on our own programmatic
  // dispatches, and blocks starting a second command concurrently.
  const busyRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  // Running insertion cursor while a stream's tokens arrive.
  const insertPosRef = useRef(0);
  const errorFlashTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const filteredSlashCommands = filterSlashCommands(slashQuery);

  // Word count for the subtle counter in zen mode
  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;

  // Filter notes for autocomplete
  const filteredNotes = autocompleteQuery
    ? allNotes.filter(
        (note) =>
          note.id.toLowerCase().includes(autocompleteQuery.toLowerCase()) ||
          (note.title && note.title.toLowerCase().includes(autocompleteQuery.toLowerCase()))
      )
    : allNotes;

  const closeSlashPalette = useCallback(() => {
    setSlashOpen(false);
    setSlashMode("commands");
    setSlashQuery("");
    setSlashSelectedIndex(0);
    setLinkCandidates([]);
  }, []);

  const getCoords = useCallback((view: EditorView, pos: number) => {
    const coords = view.coordsAtPos(pos);
    return coords ? { top: coords.bottom, left: coords.left } : { top: 0, left: 0 };
  }, []);

  const flashError = useCallback((message: string, position: { top: number; left: number }) => {
    if (errorFlashTimeoutRef.current) clearTimeout(errorFlashTimeoutRef.current);
    setErrorFlash({ message, position });
    errorFlashTimeoutRef.current = setTimeout(() => setErrorFlash(null), 4000);
  }, []);

  // Handle content changes
  const handleChange = useCallback(
    (value: string, viewUpdate: any) => {
      onChange(value);

      // Our own programmatic edits (slash removal, token streaming, undo)
      // fire this same onChange; skip re-evaluating triggers while busy so
      // we don't reopen a palette mid-command.
      if (busyRef.current) return;

      const view = viewUpdate.view as EditorView;
      const pos = view.state.selection.main.head;

      // Check for [[ pattern to trigger wikilink autocomplete
      const textBefore = view.state.doc.sliceString(Math.max(0, pos - 50), pos);
      const wikilinkMatch = textBefore.match(/\[\[([a-z0-9-]*)$/);

      if (wikilinkMatch) {
        closeSlashPalette();
        setAutocompleteQuery(wikilinkMatch[1]);
        setSelectedIndex(0);
        setAutocompletePosition(getCoords(view, pos));
        setShowAutocomplete(true);
        return;
      }
      setShowAutocomplete(false);

      // Check for slash-command trigger (only when armed)
      if (!slashCommandsArmed) {
        if (slashOpen) closeSlashPalette();
        return;
      }

      const line = view.state.doc.lineAt(pos);
      const lineTextBeforeCursor = view.state.doc.sliceString(line.from, pos);
      const trigger = detectSlashCommandTrigger(lineTextBeforeCursor);

      if (trigger) {
        slashTriggerFromRef.current = line.from + trigger.slashIndex;
        setSlashQuery(trigger.query);
        setSlashSelectedIndex(0);
        setSlashMode("commands");
        setSlashPosition(getCoords(view, pos));
        setSlashOpen(true);
      } else if (slashOpen) {
        closeSlashPalette();
      }
    },
    [onChange, slashCommandsArmed, slashOpen, closeSlashPalette, getCoords]
  );

  // Insert wikilink at cursor
  const insertWikilink = useCallback(
    (noteId: string) => {
      if (!editorView) return;

      const pos = editorView.state.selection.main.head;
      const textBefore = editorView.state.doc.sliceString(Math.max(0, pos - 50), pos);
      const match = textBefore.match(/\[\[([a-z0-9-]*)$/);

      if (match) {
        const matchStart = pos - match[0].length;

        // Check if there are closing ]] after the cursor and include them in replacement
        const textAfter = editorView.state.doc.sliceString(
          pos,
          Math.min(editorView.state.doc.length, pos + 2)
        );
        const endPos = textAfter === "]]" ? pos + 2 : pos;

        // Find the end of the current line to position cursor there
        const line = editorView.state.doc.lineAt(pos);

        // Calculate the change in text length to adjust line end position
        const removedLength = endPos - matchStart;
        const insertedLength = noteId.length + 4; // [[noteId]]
        const delta = insertedLength - removedLength;
        const newLineEnd = line.to + delta;

        // Focus editor first, then dispatch changes with new selection
        editorView.focus();
        editorView.dispatch({
          changes: { from: matchStart, to: endPos, insert: `[[${noteId}]]` },
          selection: { anchor: newLineEnd },
        });
      }

      setShowAutocomplete(false);
      setAutocompleteQuery("");
    },
    [editorView]
  );

  // ===== Slash-command execution (#146) =====

  const restoreSnapshot = useCallback(
    (view: EditorView, snapshotText: string, selectionAnchor: number) => {
      const clampedAnchor = Math.max(0, Math.min(selectionAnchor, snapshotText.length));
      view.dispatch({
        changes: { from: 0, to: view.state.doc.length, insert: snapshotText },
        selection: { anchor: clampedAnchor },
      });
    },
    []
  );

  const finishBusy = useCallback(() => {
    busyRef.current = false;
    setPendingIndicator(null);
    abortControllerRef.current = null;
  }, []);

  const insertLinkResult = useCallback(
    (view: EditorView, insertAt: number, targetNoteId: string, snapshotText: string) => {
      const insertText = `[[${targetNoteId}]]`;
      view.dispatch({
        changes: { from: insertAt, to: insertAt, insert: insertText },
        selection: { anchor: insertAt + insertText.length },
      });
      setKeepUndo({
        position: getCoords(view, insertAt + insertText.length),
        snapshotText,
        snapshotSelection: insertAt,
      });
    },
    [getCoords]
  );

  const executeLinkCommand = useCallback(
    async (view: EditorView, snapshotText: string, targetText: string, insertAt: number) => {
      const controller = new AbortController();
      abortControllerRef.current = controller;
      const collected: EditorLinkSuggestion[] = [];
      let sawError = false;

      setSlashMode("link-results");
      setSlashSelectedIndex(0);
      setSlashOpen(true);
      setSlashPosition(getCoords(view, insertAt));
      setLinkCandidates([]);

      await streamEditorAssist(
        {
          command: "link",
          text: targetText,
          note_title: noteTitle,
          note_content: snapshotText,
          note_id: noteId,
        },
        {
          signal: controller.signal,
          onEvent: (event) => {
            if (event.type === "link") {
              collected.push({
                note_id: event.note_id,
                title: event.title,
                reason: event.reason,
                confidence: event.confidence,
              });
              setLinkCandidates([...collected]);
            } else if (event.type === "error") {
              sawError = true;
            }
          },
          onError: () => {
            sawError = true;
          },
        }
      );

      if (sawError) {
        // Fall back to the non-streaming endpoint before giving up.
        try {
          const resp = await runEditorAssist({
            command: "link",
            text: targetText,
            note_title: noteTitle,
            note_content: snapshotText,
            note_id: noteId,
          });
          if (resp.suggestions && resp.suggestions.length > 0) {
            setLinkCandidates(
              resp.suggestions.map((s) => ({
                note_id: s.note_id,
                title: s.title,
                reason: s.reason,
                confidence: s.confidence,
              }))
            );
            finishBusy();
            return;
          }
        } catch (err) {
          slashCommandLogger.error("Link fallback failed", err);
        }
        closeSlashPalette();
        flashError("Link suggestions failed - try again", getCoords(view, insertAt));
      }

      finishBusy();
    },
    [noteTitle, noteId, getCoords, finishBusy, closeSlashPalette, flashError]
  );

  const executeTransformCommand = useCallback(
    async (
      view: EditorView,
      cmd: SlashCommandDef,
      snapshotText: string,
      snapshotSelectionAnchor: number,
      targetText: string,
      insertAt: number
    ) => {
      insertPosRef.current = insertAt;
      setPendingIndicator(getCoords(view, insertAt));

      const controller = new AbortController();
      abortControllerRef.current = controller;
      let receivedAny = false;
      let sawError = false;

      await streamEditorAssist(
        {
          command: cmd.name,
          text: targetText,
          note_title: noteTitle,
          note_content: snapshotText,
          note_id: noteId,
        },
        {
          signal: controller.signal,
          onEvent: (event) => {
            if (event.type === "token") {
              receivedAny = true;
              const from = insertPosRef.current;
              view.dispatch({
                changes: { from, to: from, insert: event.text },
                selection: { anchor: from + event.text.length },
              });
              insertPosRef.current = from + event.text.length;
            } else if (event.type === "error") {
              sawError = true;
            }
          },
          onError: () => {
            sawError = true;
          },
        }
      );

      if (sawError || !receivedAny) {
        // Undo any partial tokens before attempting the non-streaming fallback.
        restoreSnapshot(view, snapshotText, snapshotSelectionAnchor);

        try {
          const resp = await runEditorAssist({
            command: cmd.name,
            text: targetText,
            note_title: noteTitle,
            note_content: snapshotText,
            note_id: noteId,
          });
          if (!resp.degraded && resp.result) {
            view.dispatch({
              changes: { from: insertAt, to: insertAt, insert: resp.result },
              selection: { anchor: insertAt + resp.result.length },
            });
            setKeepUndo({
              position: getCoords(view, insertAt + resp.result.length),
              snapshotText,
              snapshotSelection: snapshotSelectionAnchor,
            });
            finishBusy();
            return;
          }
        } catch (err) {
          slashCommandLogger.error("Editor assist fallback failed", err);
        }

        flashError(`/${cmd.name} failed - try again`, getCoords(view, insertAt));
        finishBusy();
        return;
      }

      setKeepUndo({
        position: getCoords(view, insertPosRef.current),
        snapshotText,
        snapshotSelection: snapshotSelectionAnchor,
      });
      finishBusy();
    },
    [noteTitle, noteId, getCoords, restoreSnapshot, finishBusy, flashError]
  );

  const runSlashCommand = useCallback(
    (cmd: SlashCommandDef) => {
      if (!editorView || busyRef.current) return;
      const view = editorView;
      const triggerFrom = slashTriggerFromRef.current;
      const cursorPos = view.state.selection.main.head;

      // Snapshot the whole document (and cursor) before any mutation, so a
      // mid-command failure can always be undone back to exactly this state.
      const snapshotText = view.state.doc.toString();
      const snapshotSelectionAnchor = view.state.selection.main.anchor;

      busyRef.current = true;
      closeSlashPalette();

      // Remove the typed "/cmd" trigger text.
      view.dispatch({ changes: { from: triggerFrom, to: cursorPos, insert: "" } });

      const selection = view.state.selection.main;
      const docText = view.state.doc.toString();

      let targetFrom: number;
      let targetTo: number;
      let targetText: string;

      if (!selection.empty) {
        targetFrom = selection.from;
        targetTo = selection.to;
        targetText = docText.slice(targetFrom, targetTo);
      } else if (cmd.name === "continue") {
        targetFrom = selection.head;
        targetTo = selection.head;
        targetText = getPrecedingText(docText, selection.head);
      } else {
        const bounds = getParagraphBounds(docText, selection.head);
        targetFrom = bounds.from;
        targetTo = bounds.to;
        targetText = docText.slice(targetFrom, targetTo);
      }

      if (cmd.name === "link") {
        // /link never consumes the target text - it only inserts a wikilink
        // at the cursor once a candidate is chosen.
        void executeLinkCommand(view, snapshotText, targetText, triggerFrom);
        return;
      }

      let insertAt = targetFrom;
      if (targetFrom !== targetTo) {
        view.dispatch({ changes: { from: targetFrom, to: targetTo, insert: "" } });
        insertAt = targetFrom;
      }

      void executeTransformCommand(
        view,
        cmd,
        snapshotText,
        snapshotSelectionAnchor,
        targetText,
        insertAt
      );
    },
    [editorView, closeSlashPalette, executeLinkCommand, executeTransformCommand]
  );

  const selectLinkCandidate = useCallback(
    (candidate: EditorLinkSuggestion) => {
      if (!editorView) return;
      const view = editorView;
      const insertAt = view.state.selection.main.head;
      // The document at this point is already the pre-command snapshot plus
      // the "/link" trigger removed - use current doc as the undo baseline.
      const snapshotText = view.state.doc.toString();
      closeSlashPalette();
      insertLinkResult(view, insertAt, candidate.note_id, snapshotText);
      finishBusy();
    },
    [editorView, closeSlashPalette, insertLinkResult, finishBusy]
  );

  const handleKeepUndo = useCallback(
    (action: "keep" | "undo") => {
      if (action === "undo" && editorView && keepUndo) {
        restoreSnapshot(editorView, keepUndo.snapshotText, keepUndo.snapshotSelection);
      }
      setKeepUndo(null);
    },
    [editorView, keepUndo, restoreSnapshot]
  );

  // Handle keyboard navigation in autocomplete + slash palette
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (showAutocomplete) {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setSelectedIndex((prev) => (prev < filteredNotes.length - 1 ? prev + 1 : prev));
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : 0));
        } else if (e.key === "Enter" && filteredNotes.length > 0) {
          e.preventDefault();
          insertWikilink(filteredNotes[selectedIndex].id);
        } else if (e.key === "Escape") {
          setShowAutocomplete(false);
        }
        return;
      }

      if (slashOpen) {
        const items = slashMode === "commands" ? filteredSlashCommands : linkCandidates;
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setSlashSelectedIndex((prev) => (prev < items.length - 1 ? prev + 1 : prev));
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          setSlashSelectedIndex((prev) => (prev > 0 ? prev - 1 : 0));
        } else if (e.key === "Enter" && items.length > 0) {
          e.preventDefault();
          if (slashMode === "commands") {
            runSlashCommand(filteredSlashCommands[slashSelectedIndex]);
          } else {
            selectLinkCandidate(linkCandidates[slashSelectedIndex]);
          }
        } else if (e.key === "Escape") {
          closeSlashPalette();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    showAutocomplete,
    filteredNotes,
    selectedIndex,
    insertWikilink,
    slashOpen,
    slashMode,
    filteredSlashCommands,
    linkCandidates,
    slashSelectedIndex,
    runSlashCommand,
    selectLinkCandidate,
    closeSlashPalette,
  ]);

  // Abort any in-flight command and clear timers on unmount.
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
      if (errorFlashTimeoutRef.current) clearTimeout(errorFlashTimeoutRef.current);
    };
  }, []);

  // Zen mode: Cmd/Ctrl+Shift+F toggles, Esc exits (autocomplete's Esc wins first)
  useEffect(() => {
    const handleZenKeys = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === "f") {
        e.preventDefault();
        setZen((prev) => !prev);
      } else if (e.key === "Escape" && zen && !showAutocomplete && !slashOpen) {
        setZen(false);
      }
    };

    window.addEventListener("keydown", handleZenKeys);
    return () => window.removeEventListener("keydown", handleZenKeys);
  }, [zen, showAutocomplete, slashOpen]);

  // Lock page scroll while zen mode is open
  useEffect(() => {
    if (!zen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    editorView?.focus();
    return () => {
      document.body.style.overflow = previous;
    };
  }, [zen, editorView]);

  const wikilinkItems: EditorDropdownItem[] = filteredNotes.slice(0, 10).map((note) => ({
    key: note.id,
    onSelect: () => insertWikilink(note.id),
    content: (
      <>
        <div className={styles.autocompleteNoteId}>{note.id}</div>
        {note.title && <div className={styles.autocompleteTitle}>{note.title}</div>}
        {note.tags && note.tags.length > 0 && (
          <div className={styles.autocompleteTags}>
            {note.tags.slice(0, 3).map((tag) => (
              <span key={tag} className={styles.autocompleteTag}>
                {tag}
              </span>
            ))}
            {note.tags.length > 3 && (
              <span className={styles.autocompleteOverflow}>+{note.tags.length - 3}</span>
            )}
          </div>
        )}
      </>
    ),
  }));

  const slashCommandItems: EditorDropdownItem[] = filteredSlashCommands.map((cmd) => ({
    key: cmd.name,
    onSelect: () => runSlashCommand(cmd),
    content: (
      <>
        <div className={styles.autocompleteNoteId}>/{cmd.name}</div>
        <div className={styles.autocompleteTitle}>{cmd.description}</div>
      </>
    ),
  }));

  const linkResultItems: EditorDropdownItem[] = linkCandidates.map((candidate) => ({
    key: candidate.note_id,
    onSelect: () => selectLinkCandidate(candidate),
    content: (
      <>
        <div className={styles.autocompleteNoteId}>{candidate.note_id}</div>
        <div className={styles.autocompleteTitle}>{candidate.title}</div>
        {candidate.reason && <div className={styles.autocompleteOverflow}>{candidate.reason}</div>}
      </>
    ),
  }));

  return (
    <div className={`${styles.container} ${zen ? styles.zen : ""}`}>
      <div
        className={styles.editorWrapper}
        style={zen ? undefined : { minHeight: "400px", resize: "both" }}
      >
        <button
          type="button"
          className={styles.zenToggle}
          onClick={() => setZen((prev) => !prev)}
          title={zen ? "Exit focus mode (Esc)" : "Focus mode (⌘⇧F)"}
          aria-label={zen ? "Exit focus mode" : "Enter focus mode"}
        >
          {zen ? <ArrowsInSimple size={16} /> : <ArrowsOutSimple size={16} />}
        </button>
        <CodeMirror
          theme={theme}
          value={content}
          height={zen ? "100%" : "400px"}
          extensions={[
            markdown(),
            EditorView.lineWrapping,
            EditorView.theme({
              "&": {
                fontSize: "14px",
              },
              ".cm-content": {
                minHeight: "400px",
                fontFamily: "ui-monospace, monospace",
              },
              ".cm-scroller": {
                overflow: "auto",
              },
            }),
          ]}
          onChange={handleChange}
          onCreateEditor={(view) => {
            setEditorView(view);
          }}
          placeholder={placeholder}
          basicSetup={{
            lineNumbers: false,
            foldGutter: false,
            highlightActiveLine: false,
          }}
        />

        {/* Wikilink autocomplete dropdown */}
        {showAutocomplete && wikilinkItems.length > 0 && (
          <EditorDropdown
            position={autocompletePosition}
            items={wikilinkItems}
            selectedIndex={selectedIndex}
          />
        )}

        {/* Slash-command palette (#146) */}
        {slashOpen && slashMode === "commands" && (
          <EditorDropdown
            position={slashPosition}
            items={slashCommandItems}
            selectedIndex={slashSelectedIndex}
          />
        )}
        {slashOpen && slashMode === "link-results" && linkResultItems.length > 0 && (
          <EditorDropdown
            position={slashPosition}
            items={linkResultItems}
            selectedIndex={slashSelectedIndex}
          />
        )}

        {/* AI streaming indicator (#146) */}
        {pendingIndicator && (
          <div
            className={styles.slashPending}
            style={{ top: `${pendingIndicator.top}px`, left: `${pendingIndicator.left}px` }}
          >
            <span className={styles.slashPendingDot} aria-hidden="true" />
            AI writing…
          </div>
        )}

        {/* Keep / Undo affordance after a slash command completes (#146) */}
        {keepUndo && (
          <div
            className={styles.keepUndoBar}
            style={{ top: `${keepUndo.position.top}px`, left: `${keepUndo.position.left}px` }}
          >
            <span className={styles.keepUndoLabel}>AI edit applied</span>
            <button
              type="button"
              className={`${styles.keepUndoButton} ${styles.keepUndoButtonPrimary}`}
              onClick={() => handleKeepUndo("keep")}
            >
              Keep
            </button>
            <button
              type="button"
              className={styles.keepUndoButton}
              onClick={() => handleKeepUndo("undo")}
            >
              Undo
            </button>
          </div>
        )}

        {/* Non-blocking error toast for failed slash commands (#146) */}
        {errorFlash && (
          <div
            className={styles.slashPending}
            style={{ top: `${errorFlash.position.top}px`, left: `${errorFlash.position.left}px` }}
          >
            {errorFlash.message}
          </div>
        )}
      </div>

      {/* Subtle word count, zen mode only */}
      {zen && (
        <div className={styles.zenFooter} aria-hidden="true">
          {wordCount} {wordCount === 1 ? "word" : "words"}
        </div>
      )}

      {/* Help text */}
      <div className={styles.helpText}>
        Type <code className={styles.helpCode}>[[</code> to link to other notes
        {slashCommandsArmed && (
          <>
            , or <code className={styles.helpCode}>/</code> for AI commands
          </>
        )}
        . Use arrow keys and Enter to select from autocomplete. Supports{" "}
        <a
          href="https://www.markdownguide.org/basic-syntax/"
          target="_blank"
          rel="noopener noreferrer"
          className={styles.helpLink}
        >
          Markdown syntax
        </a>
        .
      </div>
    </div>
  );
}
