"use client";

import { useCallback, useEffect, useState } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { markdown } from "@codemirror/lang-markdown";
import { EditorView } from "@codemirror/view";
import { logger } from "@/lib/logger";
import { Note } from "@/lib/api/notes";

interface NoteEditorProps {
  content: string;
  onChange: (content: string) => void;
  placeholder?: string;
  allNotes?: Note[];
  onNoteClick?: (noteId: string) => void;
}

export default function NoteEditor({
  content,
  onChange,
  placeholder = "Start typing your note... Use [[note-id]] to link to other notes",
  allNotes = [],
  onNoteClick,
}: NoteEditorProps) {
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [autocompleteQuery, setAutocompleteQuery] = useState("");
  const [autocompletePosition, setAutocompletePosition] = useState({ top: 0, left: 0 });
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [editorView, setEditorView] = useState<EditorView | null>(null);

  // Filter notes for autocomplete
  const filteredNotes = autocompleteQuery
    ? allNotes.filter(
        (note) =>
          note.id.toLowerCase().includes(autocompleteQuery.toLowerCase()) ||
          (note.title && note.title.toLowerCase().includes(autocompleteQuery.toLowerCase()))
      )
    : allNotes;

  // Handle content changes
  const handleChange = useCallback(
    (value: string, viewUpdate: any) => {
      onChange(value);

      // Check for [[ pattern to trigger autocomplete
      const view = viewUpdate.view as EditorView;
      const pos = view.state.selection.main.head;
      const textBefore = view.state.doc.sliceString(Math.max(0, pos - 50), pos);
      const match = textBefore.match(/\[\[([a-z0-9-]*)$/);

      if (match) {
        setAutocompleteQuery(match[1]);
        setSelectedIndex(0);

        // Get cursor coordinates for autocomplete dropdown
        const coords = view.coordsAtPos(pos);
        if (coords) {
          setAutocompletePosition({
            top: coords.bottom,
            left: coords.left,
          });
        }

        setShowAutocomplete(true);
      } else {
        setShowAutocomplete(false);
      }
    },
    [onChange]
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
        editorView.dispatch({
          changes: { from: matchStart, to: pos, insert: `[[${noteId}]]` },
          selection: { anchor: matchStart + noteId.length + 4 },
        });
      }

      setShowAutocomplete(false);
      setAutocompleteQuery("");
    },
    [editorView]
  );

  // Handle keyboard navigation in autocomplete
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!showAutocomplete) return;

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
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showAutocomplete, filteredNotes, selectedIndex, insertWikilink]);

  return (
    <div className="relative">
      <div className="overflow-hidden rounded-md border border-gray-300 bg-white">
        <CodeMirror
          value={content}
          height="400px"
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

        {/* Autocomplete dropdown */}
        {showAutocomplete && filteredNotes.length > 0 && (
          <div
            className="fixed z-50 max-h-60 overflow-y-auto rounded-lg border border-gray-300 bg-white shadow-xl"
            style={{
              top: `${autocompletePosition.top}px`,
              left: `${autocompletePosition.left}px`,
              width: "320px",
              maxWidth: "calc(100vw - 2rem)",
            }}
          >
            {filteredNotes.slice(0, 10).map((note, index) => (
              <button
                key={note.id}
                type="button"
                onClick={() => insertWikilink(note.id)}
                className={`w-full border-b border-gray-100 px-4 py-3 text-left transition-colors last:border-0 hover:bg-blue-50 ${
                  index === selectedIndex ? "bg-blue-50" : ""
                }`}
              >
                <div className="mb-1 font-mono text-xs text-blue-600">{note.id}</div>
                {note.title && (
                  <div className="mb-1 text-sm font-medium text-gray-900">{note.title}</div>
                )}
                {note.tags && note.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {note.tags.slice(0, 3).map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                      >
                        {tag}
                      </span>
                    ))}
                    {note.tags.length > 3 && (
                      <span className="text-xs text-gray-400">+{note.tags.length - 3}</span>
                    )}
                  </div>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Help text */}
      <div className="mt-2 text-xs text-gray-500">
        Type <code className="rounded bg-gray-100 px-1">[[</code> to link to other notes. Use arrow
        keys and Enter to select from autocomplete. Supports{" "}
        <a
          href="https://www.markdownguide.org/basic-syntax/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:underline"
        >
          Markdown syntax
        </a>
        .
      </div>
    </div>
  );
}
