"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { useCallback, useEffect, useState } from "react";
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

  // Filter notes for autocomplete
  const filteredNotes = autocompleteQuery
    ? allNotes.filter(
        (note) =>
          note.id.toLowerCase().includes(autocompleteQuery.toLowerCase()) ||
          (note.title && note.title.toLowerCase().includes(autocompleteQuery.toLowerCase()))
      )
    : allNotes;

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({
        placeholder,
      }),
    ],
    content,
    immediatelyRender: false,
    onUpdate: ({ editor }) => {
      const text = editor.getText();
      onChange(text);

      // Check for [[ pattern to trigger autocomplete
      const { from } = editor.state.selection;
      const textBefore = editor.state.doc.textBetween(Math.max(0, from - 50), from);
      const match = textBefore.match(/\[\[([a-z0-9-]*)$/);

      if (match) {
        setAutocompleteQuery(match[1]);
        setSelectedIndex(0);

        // Get cursor position for autocomplete dropdown
        const coords = editor.view.coordsAtPos(from);
        setAutocompletePosition({
          top: coords.bottom,
          left: coords.left,
        });

        setShowAutocomplete(true);
      } else {
        setShowAutocomplete(false);
      }
    },
    editorProps: {
      attributes: {
        class: "prose prose-sm sm:prose lg:prose-lg focus:outline-none min-h-[300px] px-4 py-3",
      },
      handleDOMEvents: {
        keydown: (view, event) => {
          if (!showAutocomplete) return false;

          if (event.key === "ArrowDown") {
            event.preventDefault();
            setSelectedIndex((prev) => (prev < filteredNotes.length - 1 ? prev + 1 : prev));
            return true;
          }

          if (event.key === "ArrowUp") {
            event.preventDefault();
            setSelectedIndex((prev) => (prev > 0 ? prev - 1 : 0));
            return true;
          }

          if (event.key === "Enter" && filteredNotes.length > 0) {
            event.preventDefault();
            insertWikilink(filteredNotes[selectedIndex].id);
            return true;
          }

          if (event.key === "Escape") {
            setShowAutocomplete(false);
            return true;
          }

          return false;
        },
      },
    },
  });

  const insertWikilink = useCallback(
    (noteId: string) => {
      if (!editor) return;

      const { from } = editor.state.selection;
      const textBefore = editor.state.doc.textBetween(Math.max(0, from - 50), from);
      const match = textBefore.match(/\[\[([a-z0-9-]*)$/);

      if (match) {
        const matchStart = from - match[0].length;
        editor
          .chain()
          .focus()
          .deleteRange({ from: matchStart, to: from })
          .insertContent(`[[${noteId}]]`)
          .run();
      }

      setShowAutocomplete(false);
      setAutocompleteQuery("");
    },
    [editor]
  );

  // Handle click on wikilinks in the editor
  useEffect(() => {
    if (!editor) return;

    const handleClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      const text = editor.state.doc.textContent;
      const clickPos = editor.view.posAtCoords({
        left: event.clientX,
        top: event.clientY,
      });

      if (!clickPos) return;

      // Find if we clicked on a wikilink
      const regex = /\[\[([a-z0-9-]+)\]\]/g;
      let match;
      while ((match = regex.exec(text)) !== null) {
        const linkStart = match.index;
        const linkEnd = linkStart + match[0].length;

        if (clickPos.pos >= linkStart && clickPos.pos <= linkEnd) {
          event.preventDefault();
          const noteId = match[1];
          if (onNoteClick) {
            onNoteClick(noteId);
          } else {
            logger.info("Wikilink clicked", { noteId });
          }
          return;
        }
      }
    };

    const editorElement = editor.view.dom;
    editorElement.addEventListener("click", handleClick);

    return () => {
      editorElement.removeEventListener("click", handleClick);
    };
  }, [editor, onNoteClick]);

  if (!editor) {
    return null;
  }

  return (
    <div className="relative">
      <div className="overflow-hidden rounded-md border border-gray-300 bg-white">
        {/* Toolbar */}
        <div className="flex flex-wrap gap-1 border-b border-gray-300 bg-gray-50 p-2">
          {/* Text formatting */}
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleBold().run()}
            className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
              editor.isActive("bold") ? "bg-gray-300 font-bold" : ""
            }`}
          >
            Bold
          </button>
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleItalic().run()}
            className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
              editor.isActive("italic") ? "bg-gray-300 italic" : ""
            }`}
          >
            Italic
          </button>
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleCode().run()}
            className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
              editor.isActive("code") ? "bg-gray-300 font-mono" : ""
            }`}
          >
            Code
          </button>

          <div className="mx-1 h-6 w-px bg-gray-300" />

          {/* Headings */}
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
            className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
              editor.isActive("heading", { level: 1 }) ? "bg-gray-300 font-bold" : ""
            }`}
          >
            H1
          </button>
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
              editor.isActive("heading", { level: 2 }) ? "bg-gray-300 font-bold" : ""
            }`}
          >
            H2
          </button>
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
              editor.isActive("heading", { level: 3 }) ? "bg-gray-300 font-bold" : ""
            }`}
          >
            H3
          </button>

          <div className="mx-1 h-6 w-px bg-gray-300" />

          {/* Lists */}
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
              editor.isActive("bulletList") ? "bg-gray-300" : ""
            }`}
          >
            • List
          </button>
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
              editor.isActive("orderedList") ? "bg-gray-300" : ""
            }`}
          >
            1. List
          </button>

          <div className="mx-1 h-6 w-px bg-gray-300" />

          {/* Wikilink button */}
          <button
            type="button"
            onClick={() => {
              const noteId = prompt("Enter note ID to link:");
              if (noteId) {
                editor.chain().focus().insertContent(`[[${noteId}]]`).run();
              }
            }}
            className="rounded bg-blue-50 px-3 py-1 text-sm hover:bg-gray-200"
          >
            [[Link]]
          </button>
        </div>

        {/* Editor */}
        <div className="relative">
          <EditorContent editor={editor} />

          {/* Autocomplete dropdown */}
          {showAutocomplete && filteredNotes.length > 0 && (
            <div
              className="absolute z-50 max-h-60 overflow-y-auto rounded-md border border-gray-300 bg-white shadow-lg"
              style={{
                top: `${autocompletePosition.top}px`,
                left: `${autocompletePosition.left}px`,
                minWidth: "250px",
              }}
            >
              {filteredNotes.slice(0, 10).map((note, index) => (
                <button
                  key={note.id}
                  type="button"
                  onClick={() => insertWikilink(note.id)}
                  className={`w-full px-3 py-2 text-left hover:bg-gray-100 ${
                    index === selectedIndex ? "bg-blue-50" : ""
                  }`}
                >
                  <div className="font-mono text-sm text-gray-600">{note.id}</div>
                  {note.title && <div className="text-sm text-gray-800">{note.title}</div>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Help text */}
      <div className="mt-2 text-xs text-gray-500">
        Type <code className="rounded bg-gray-100 px-1">[[</code> to link to other notes. Use arrow
        keys and Enter to select from autocomplete.
      </div>
    </div>
  );
}
