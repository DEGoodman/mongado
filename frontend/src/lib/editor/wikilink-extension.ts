/**
 * TipTap extension for [[wikilink]] syntax with autocomplete
 */

import { Mark, mergeAttributes } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";

export interface WikilinkOptions {
  HTMLAttributes: Record<string, unknown>;
  onLinkClick?: (noteId: string) => void;
}

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    wikilink: {
      /**
       * Set a wikilink
       */
      setWikilink: (noteId: string) => ReturnType;
      /**
       * Unset a wikilink
       */
      unsetWikilink: () => ReturnType;
    };
  }
}

export const Wikilink = Mark.create<WikilinkOptions>({
  name: "wikilink",

  addOptions() {
    return {
      HTMLAttributes: {},
      onLinkClick: undefined,
    };
  },

  addAttributes() {
    return {
      noteId: {
        default: null,
        parseHTML: (element) => element.getAttribute("data-note-id"),
        renderHTML: (attributes) => {
          if (!attributes.noteId) {
            return {};
          }

          return {
            "data-note-id": attributes.noteId,
          };
        },
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'span[data-type="wikilink"]',
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      "span",
      mergeAttributes(this.options.HTMLAttributes, HTMLAttributes, {
        "data-type": "wikilink",
        class: "wikilink",
      }),
      ["span", { class: "wikilink-bracket" }, "[["],
      ["span", { class: "wikilink-text" }, 0],
      ["span", { class: "wikilink-bracket" }, "]]"],
    ];
  },

  addCommands() {
    return {
      setWikilink:
        (noteId: string) =>
        ({ commands }) => {
          return commands.setMark(this.name, { noteId });
        },
      unsetWikilink:
        () =>
        ({ commands }) => {
          return commands.unsetMark(this.name);
        },
    };
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey("wikilink-handler"),
        props: {
          handleClick: (view, pos, event) => {
            const { schema } = view.state;
            const target = event.target as HTMLElement;

            // Check if clicked on wikilink
            if (target.closest('[data-type="wikilink"]')) {
              const $pos = view.state.doc.resolve(pos);
              const mark = $pos.marks().find((m) => m.type === schema.marks.wikilink);

              if (mark && this.options.onLinkClick) {
                event.preventDefault();
                this.options.onLinkClick(mark.attrs.noteId);
                return true;
              }
            }

            return false;
          },
          decorations: (state) => {
            const decorations: Decoration[] = [];
            const { doc } = state;

            doc.descendants((node, pos) => {
              if (!node.isText) return;

              const text = node.text || "";
              // Match [[note-id]] pattern
              const regex = /\[\[([a-z0-9-]+)\]\]/g;
              let match;

              while ((match = regex.exec(text)) !== null) {
                const from = pos + match.index;
                const to = from + match[0].length;

                decorations.push(
                  Decoration.inline(from, to, {
                    class: "wikilink-decoration",
                    "data-note-id": match[1],
                  })
                );
              }
            });

            return DecorationSet.create(doc, decorations);
          },
        },
      }),
    ];
  },
});

/**
 * Autocomplete plugin for wikilinks
 */
export interface AutocompleteOptions {
  suggestions: Array<{ id: string; title: string }>;
  onSelect: (noteId: string) => void;
}

export function createWikilinkAutocomplete(options: AutocompleteOptions) {
  return new Plugin({
    key: new PluginKey("wikilink-autocomplete"),
    state: {
      init() {
        return {
          active: false,
          query: "",
          range: null,
        };
      },
      apply(tr, value) {
        // Check if we're typing [[
        const { selection } = tr;
        const { $from } = selection;
        const textBefore = $from.parent.textContent.slice(0, $from.parentOffset);

        const match = textBefore.match(/\[\[([a-z0-9-]*)$/);
        if (match) {
          return {
            active: true,
            query: match[1],
            range: {
              from: $from.pos - match[0].length,
              to: $from.pos,
            },
          };
        }

        return {
          active: false,
          query: "",
          range: null,
        };
      },
    },
    props: {
      handleKeyDown(view, event) {
        const state = this.getState(view.state);
        if (!state.active) return false;

        // Handle autocomplete navigation
        if (event.key === "ArrowDown" || event.key === "ArrowUp") {
          event.preventDefault();
          return true;
        }

        // Handle selection
        if (event.key === "Enter" || event.key === "Tab") {
          // Autocomplete selection logic
          return false;
        }

        return false;
      },
    },
  });
}
