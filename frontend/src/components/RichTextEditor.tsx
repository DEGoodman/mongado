"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import { useCallback, useEffect, useRef } from "react";
import { logger } from "@/lib/logger";
import TurndownService from "turndown";

interface RichTextEditorProps {
  content: string;
  onChange: (html: string, markdown: string) => void;
  placeholder?: string;
}

export default function RichTextEditor({
  content,
  onChange,
  placeholder = "Start typing...",
}: RichTextEditorProps) {
  const turndownService = useRef<TurndownService | null>(null);

  // Initialize Turndown service once
  useEffect(() => {
    turndownService.current = new TurndownService({
      headingStyle: "atx",
      codeBlockStyle: "fenced",
    });
  }, []);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Image.configure({
        inline: true,
        allowBase64: true,
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: "text-blue-600 underline",
        },
      }),
      Placeholder.configure({
        placeholder,
      }),
    ],
    content,
    immediatelyRender: false,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      const markdown = turndownService.current?.turndown(html) || "";
      onChange(html, markdown);
    },
    editorProps: {
      attributes: {
        class:
          "prose prose-sm sm:prose lg:prose-lg xl:prose-xl focus:outline-none min-h-[200px] px-4 py-3",
      },
    },
  });

  const handleImageUpload = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      const formData = new FormData();
      formData.append("file", file);

      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const response = await fetch(`${API_URL}/api/upload-image`, {
          method: "POST",
          body: formData,
        });

        if (response.ok) {
          const data = await response.json();
          const imageUrl = `${API_URL}${data.url}`;
          editor?.chain().focus().setImage({ src: imageUrl }).run();
          logger.info("Image uploaded and inserted", { url: imageUrl });
        } else {
          logger.error("Failed to upload image", { status: response.status });
        }
      } catch (error) {
        logger.error("Error uploading image", error);
      }
    };
    input.click();
  }, [editor]);

  const setLink = useCallback(() => {
    const previousUrl = editor?.getAttributes("link").href;
    const url = window.prompt("URL", previousUrl);

    if (url === null) {
      return;
    }

    if (url === "") {
      editor?.chain().focus().extendMarkRange("link").unsetLink().run();
      return;
    }

    editor?.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
  }, [editor]);

  if (!editor) {
    return null;
  }

  return (
    <div className="overflow-hidden rounded-md border border-gray-300">
      {/* Toolbar */}
      <div className="flex flex-wrap gap-1 border-b border-gray-300 bg-gray-50 p-2">
        {/* Text formatting */}
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBold().run()}
          disabled={!editor.can().chain().focus().toggleBold().run()}
          className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
            editor.isActive("bold") ? "bg-gray-300 font-bold" : ""
          }`}
        >
          Bold
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          disabled={!editor.can().chain().focus().toggleItalic().run()}
          className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
            editor.isActive("italic") ? "bg-gray-300 italic" : ""
          }`}
        >
          Italic
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleStrike().run()}
          disabled={!editor.can().chain().focus().toggleStrike().run()}
          className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
            editor.isActive("strike") ? "bg-gray-300 line-through" : ""
          }`}
        >
          Strike
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
          Bullet List
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
            editor.isActive("orderedList") ? "bg-gray-300" : ""
          }`}
        >
          Numbered List
        </button>

        <div className="mx-1 h-6 w-px bg-gray-300" />

        {/* Other formatting */}
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
            editor.isActive("blockquote") ? "bg-gray-300" : ""
          }`}
        >
          Quote
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleCodeBlock().run()}
          className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
            editor.isActive("codeBlock") ? "bg-gray-300" : ""
          }`}
        >
          Code Block
        </button>

        <div className="mx-1 h-6 w-px bg-gray-300" />

        {/* Links and Images */}
        <button
          type="button"
          onClick={setLink}
          className={`rounded px-3 py-1 text-sm hover:bg-gray-200 ${
            editor.isActive("link") ? "bg-gray-300" : ""
          }`}
        >
          Link
        </button>
        <button
          type="button"
          onClick={handleImageUpload}
          className="rounded px-3 py-1 text-sm hover:bg-gray-200"
        >
          Image
        </button>

        <div className="mx-1 h-6 w-px bg-gray-300" />

        {/* Undo/Redo */}
        <button
          type="button"
          onClick={() => editor.chain().focus().undo().run()}
          disabled={!editor.can().chain().focus().undo().run()}
          className="rounded px-3 py-1 text-sm hover:bg-gray-200 disabled:opacity-50"
        >
          Undo
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().redo().run()}
          disabled={!editor.can().chain().focus().redo().run()}
          className="rounded px-3 py-1 text-sm hover:bg-gray-200 disabled:opacity-50"
        >
          Redo
        </button>
      </div>

      {/* Editor */}
      <EditorContent editor={editor} />
    </div>
  );
}
