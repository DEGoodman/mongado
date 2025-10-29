-- Mongado Zettelkasten Database Schema
-- SQLite database for atomic notes with bidirectional linking

-- Atomic notes (Zettelkasten)
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,              -- adjective-noun format (e.g., "curious-elephant")
    title TEXT,                       -- Optional human-readable title
    content TEXT NOT NULL,            -- Markdown content
    author TEXT DEFAULT 'admin',      -- Author name (default: 'admin')
    -- DEPRECATED: is_ephemeral BOOLEAN DEFAULT 0,   -- No longer used (all notes are persistent)
    -- DEPRECATED: session_id TEXT,                  -- No longer used (auth required)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tags TEXT,                        -- JSON array: ["tag1", "tag2"]
    metadata TEXT                     -- JSON: {views: 0, ai_summary: "", etc.}
);

-- Bidirectional links between notes
CREATE TABLE IF NOT EXISTS note_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,          -- Note containing the link
    target_id TEXT NOT NULL,          -- Note being linked to
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES notes(id) ON DELETE CASCADE,
    UNIQUE(source_id, target_id)      -- Prevent duplicate links
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_notes_author ON notes(author);
-- DEPRECATED: CREATE INDEX IF NOT EXISTS idx_notes_ephemeral ON notes(is_ephemeral);
-- DEPRECATED: CREATE INDEX IF NOT EXISTS idx_notes_session ON notes(session_id);
CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_links_source ON note_links(source_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON note_links(target_id);

-- Trigger to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_note_timestamp
AFTER UPDATE ON notes
BEGIN
    UPDATE notes SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
