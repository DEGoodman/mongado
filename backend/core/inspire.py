"""Pure business logic for content inspiration features (Functional Core).

This module contains pure functions with no I/O or side effects.
All functions are deterministic and fully unit-testable.

Suggestion philosophy (see #259):
    A short note is not a defect. In a Zettelkasten an atomic note *should*
    be brief -- the note editor itself calls 300-500 chars the ideal band
    (see NoteEditorForm.tsx). Suggestions therefore describe *structural*
    problems (orphaned, oversized, duplicated, uncovered) and never ask the
    author to pad a well-formed note.
"""

import hashlib
import json
import logging
import re
from typing import Any

from core.ai import cosine_similarity, extract_json_payload

logger = logging.getLogger(__name__)

# --- thresholds ------------------------------------------------------------
# These deliberately mirror the guidance the note editor shows while typing
# (NoteEditorForm.tsx). If you change one, change both, or Inspire will start
# contradicting the editor again.

SPLIT_MIN_LENGTH = 1000
"""Editor says '>1000: consider splitting into multiple notes'."""

PROMOTE_MIN_BACKLINKS = 5
"""A note this many others reference is load-bearing -- article material."""

DUPLICATE_MIN_SIMILARITY = 0.85
"""Embedding similarity at/above which a pair *may* be redundant."""

DUPLICATE_MIN_TITLE_OVERLAP = 0.8
"""Title agreement required to call a similar pair an actual duplicate.

Embedding similarity alone cannot separate "5 Dysfunctions of a Team" /
"Five Dysfunctions of a Team" (a true duplicate, 0.87) from "Developer
Productivity: People Factors" / "...: Process Factors" (deliberate siblings,
0.86). Normalized title overlap does.
"""

CONNECTION_MIN_SIMILARITY = 0.70
"""Floor for suggesting a wikilink between two unlinked notes."""

HUB_MIN_CLUSTER_SIZE = 3
"""Mutually-similar notes at/above this count want a hub note."""

ARTICLE_GAP_MIN_NOTES = 4
"""Notes sharing a tag before an uncovered tag becomes an article idea."""

# Number words, so "5 Dysfunctions" and "Five Dysfunctions" normalize alike.
_NUMBER_WORDS = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
    "10": "ten", "11": "eleven", "12": "twelve",
}

_STOPWORDS = frozenset({"a", "an", "the", "of", "for", "and", "to", "in", "on"})


def normalize_tag(tag: str) -> str:
    """Normalize a tag for comparison (prod has both 'Leadership' and 'leadership')."""
    return tag.strip().lower().replace("_", "-").replace(" ", "-")


def _title_tokens(title: str) -> frozenset[str]:
    """Tokenize a title for duplicate detection.

    Lowercases, drops punctuation and stopwords, and spells out small numbers
    so numeric and written forms of the same title agree.
    """
    words = re.findall(r"[a-z0-9]+", title.lower())
    return frozenset(
        _NUMBER_WORDS.get(w, w) for w in words if _NUMBER_WORDS.get(w, w) not in _STOPWORDS
    )


def title_overlap(title_a: str, title_b: str) -> float:
    """Jaccard overlap of two normalized titles (0.0 to 1.0). Pure."""
    tokens_a = _title_tokens(title_a)
    tokens_b = _title_tokens(title_b)
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


# --- structural gap detection ----------------------------------------------


def find_orphan_notes(notes: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    """Find notes with no inbound or outbound links.

    Pure function: No I/O, no side effects, deterministic.

    An orphan is unreachable by traversal, so its ideas are effectively lost
    regardless of how well written it is. Sorted by content length descending:
    a substantial disconnected note is a bigger loss than a stub.

    Args:
        notes: Notes with link_count and backlink_count
        limit: Maximum results to return

    Returns:
        List of orphan note dicts, most substantial first
    """
    orphans = [
        {
            "note_id": note["id"],
            "title": note.get("title", note["id"]),
            "content_length": note.get("content_length", len(note.get("content", ""))),
            "tags": [normalize_tag(t) for t in note.get("tags") or []],
        }
        for note in notes
        if note.get("link_count", 0) == 0 and note.get("backlink_count", 0) == 0
    ]
    orphans.sort(key=lambda x: int(x["content_length"]), reverse=True)
    return orphans[:limit]


def find_oversized_notes(
    notes: list[dict[str, Any]],
    min_length: int = SPLIT_MIN_LENGTH,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Find notes long enough that they likely hold more than one idea.

    Pure function: No I/O, no side effects, deterministic.
    Mirrors the editor's own '>1000 chars: consider splitting' guidance.

    Args:
        notes: Notes with content_length
        min_length: Length at/above which a note is a split candidate
        limit: Maximum results to return

    Returns:
        List of oversized note dicts, longest first
    """
    oversized = [
        {
            "note_id": note["id"],
            "title": note.get("title", note["id"]),
            "content_length": note.get("content_length", len(note.get("content", ""))),
        }
        for note in notes
        if note.get("content_length", len(note.get("content", ""))) > min_length
    ]
    oversized.sort(key=lambda x: int(x["content_length"]), reverse=True)
    return oversized[:limit]


def find_promotion_candidates(
    notes: list[dict[str, Any]],
    min_backlinks: int = PROMOTE_MIN_BACKLINKS,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Find well-referenced notes that could anchor a full article.

    Pure function: No I/O, no side effects, deterministic.
    This is #148's "this note has 8 backlinks - consider a full article?".

    Args:
        notes: Notes with backlink_count
        min_backlinks: Inbound links required to qualify
        limit: Maximum results to return

    Returns:
        List of promotion candidate dicts, most referenced first
    """
    candidates = [
        {
            "note_id": note["id"],
            "title": note.get("title", note["id"]),
            "backlink_count": note.get("backlink_count", 0),
            "content_length": note.get("content_length", len(note.get("content", ""))),
        }
        for note in notes
        if note.get("backlink_count", 0) >= min_backlinks
    ]
    candidates.sort(key=lambda x: int(x["backlink_count"]), reverse=True)
    return candidates[:limit]


# --- similarity-based opportunities ----------------------------------------


def find_unlinked_similar_notes(
    note_embeddings: list[tuple[str, str, list[float]]],
    existing_links: dict[str, set[str]],
    similarity_threshold: float = CONNECTION_MIN_SIMILARITY,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Find semantically similar notes that aren't linked to each other.

    Pure function: No I/O, no side effects, deterministic.

    Each pair carries a "kind": "duplicate" when the notes are both
    semantically and lexically near-identical (merge them), or "connection"
    when they are merely related (link them).

    Args:
        note_embeddings: List of (note_id, title, embedding) tuples
        existing_links: Dict mapping note_id -> set of linked note_ids (bidirectional)
        similarity_threshold: Minimum cosine similarity to consider (0.0 to 1.0)
        limit: Maximum results to return

    Returns:
        List of opportunities with similarity scores and kind, highest first
    """
    opportunities: list[dict[str, Any]] = []
    n = len(note_embeddings)

    for i in range(n):
        note_a_id, note_a_title, embedding_a = note_embeddings[i]

        for j in range(i + 1, n):
            note_b_id, note_b_title, embedding_b = note_embeddings[j]

            # Skip if already linked (check both directions)
            a_links = existing_links.get(note_a_id, set())
            b_links = existing_links.get(note_b_id, set())
            if note_b_id in a_links or note_a_id in b_links:
                continue

            similarity = cosine_similarity(embedding_a, embedding_b)
            if similarity < similarity_threshold:
                continue

            overlap = title_overlap(note_a_title, note_b_title)
            is_duplicate = (
                similarity >= DUPLICATE_MIN_SIMILARITY and overlap >= DUPLICATE_MIN_TITLE_OVERLAP
            )

            opportunities.append(
                {
                    "note_a_id": note_a_id,
                    "note_a_title": note_a_title,
                    "note_b_id": note_b_id,
                    "note_b_title": note_b_title,
                    "similarity": round(similarity, 3),
                    "title_overlap": round(overlap, 3),
                    "kind": "duplicate" if is_duplicate else "connection",
                }
            )

    opportunities.sort(key=lambda x: float(x["similarity"]), reverse=True)
    return opportunities[:limit]


def find_hub_opportunities(
    pairs: list[dict[str, Any]],
    min_cluster_size: int = HUB_MIN_CLUSTER_SIZE,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Group mutually-similar notes into clusters that want a hub note.

    Pure function: No I/O, no side effects, deterministic.

    Builds an undirected graph from similar-but-unlinked pairs and returns
    connected components of at least min_cluster_size. This is #148's "this
    concept appears in N places - create a hub note?".

    Args:
        pairs: Output of find_unlinked_similar_notes()
        min_cluster_size: Minimum notes in a cluster to report it
        limit: Maximum clusters to return

    Returns:
        List of cluster dicts with note_ids and titles, largest first
    """
    adjacency: dict[str, set[str]] = {}
    titles: dict[str, str] = {}

    for pair in pairs:
        a, b = pair["note_a_id"], pair["note_b_id"]
        titles[a] = pair["note_a_title"]
        titles[b] = pair["note_b_title"]
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)

    clusters: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Iterate sorted keys so component discovery order is deterministic
    for start in sorted(adjacency):
        if start in seen:
            continue

        component: list[str] = []
        queue = [start]
        seen.add(start)
        while queue:
            current = queue.pop(0)
            component.append(current)
            for neighbor in sorted(adjacency[current]):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)

        if len(component) >= min_cluster_size:
            component.sort()
            clusters.append(
                {
                    "note_ids": component,
                    "titles": [titles[note_id] for note_id in component],
                    "size": len(component),
                }
            )

    clusters.sort(key=lambda x: int(x["size"]), reverse=True)
    return clusters[:limit]


# --- article-aware opportunities -------------------------------------------


def find_uncovered_tag_clusters(
    notes: list[dict[str, Any]],
    articles: list[dict[str, Any]],
    min_notes: int = ARTICLE_GAP_MIN_NOTES,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find topics with many notes but no article covering them.

    Pure function: No I/O, no side effects, deterministic.
    This is #148's "your SRE articles don't cover incident management".

    Tags are normalized before comparison, so 'Leadership' and 'leadership'
    count as one topic.

    Args:
        notes: Notes with tags
        articles: Articles with tags
        min_notes: Notes sharing a tag before it counts as a real cluster
        limit: Maximum results to return

    Returns:
        List of uncovered topic dicts, largest cluster first
    """
    covered = {
        normalize_tag(tag) for article in articles for tag in (article.get("tags") or [])
    }

    by_tag: dict[str, list[dict[str, str]]] = {}
    for note in notes:
        for tag in note.get("tags") or []:
            by_tag.setdefault(normalize_tag(tag), []).append(
                {"note_id": note["id"], "title": note.get("title", note["id"])}
            )

    uncovered: list[dict[str, Any]] = [
        {
            "tag": tag,
            "note_count": len(tagged),
            "note_ids": [n["note_id"] for n in tagged[:5]],
            "titles": [n["title"] for n in tagged[:5]],
        }
        for tag, tagged in by_tag.items()
        if tag not in covered and len(tagged) >= min_notes
    ]

    # Sort by size, then tag name, so equal-sized clusters have a stable order
    uncovered.sort(key=lambda x: (-int(x["note_count"]), str(x["tag"])))
    return uncovered[:limit]


# --- composition ------------------------------------------------------------

SUGGESTION_TYPES = ("orphan", "duplicate", "connection", "hub", "promote", "split", "article")

# Round-robin order. Highest-signal problems come first so that when the
# requested limit is small, the user sees the things most worth fixing.
_ROTATION_ORDER = ("duplicate", "orphan", "article", "hub", "promote", "connection", "split")


def compose_candidates(
    candidates: dict[str, list[dict[str, Any]]],
    limit: int,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Interleave candidates across types so no single type dominates.

    Pure function: No I/O, no side effects, deterministic.

    Round-robins through _ROTATION_ORDER taking one candidate per type per
    pass. The offset rotates each type's own list, so pressing Refresh yields
    a different slice of the same analysis without re-running it.

    Args:
        candidates: Mapping of suggestion type -> candidate list
        limit: Total candidates to return
        offset: Rotation offset applied within each type's list

    Returns:
        Interleaved list of {"type": ..., "data": ...} dicts
    """
    if limit <= 0:
        return []

    # Rotate each type's list by offset so refresh surfaces different items
    rotated: dict[str, list[dict[str, Any]]] = {}
    for suggestion_type, items in candidates.items():
        if not items:
            continue
        start = offset % len(items)
        rotated[suggestion_type] = items[start:] + items[:start]

    composed: list[dict[str, Any]] = []
    cursors = dict.fromkeys(rotated, 0)

    while len(composed) < limit:
        progressed = False
        for suggestion_type in _ROTATION_ORDER:
            if len(composed) >= limit:
                break
            pool = rotated.get(suggestion_type)
            if not pool:
                continue
            cursor = cursors[suggestion_type]
            if cursor >= len(pool):
                continue
            composed.append({"type": suggestion_type, "data": pool[cursor]})
            cursors[suggestion_type] = cursor + 1
            progressed = True
        if not progressed:
            break

    return composed


def compute_kb_fingerprint(
    notes: list[dict[str, Any]], articles: list[dict[str, Any]]
) -> str:
    """Compute a stable fingerprint of KB state, for cache invalidation.

    Pure function: No I/O, no side effects, deterministic.
    Changes when a note or article is added, removed, edited, or relinked.

    Args:
        notes: Notes with id, content_length, link_count, backlink_count
        articles: Articles with id

    Returns:
        Hex digest string
    """
    parts = sorted(
        f"{n['id']}:{n.get('content_length', 0)}:"
        f"{n.get('link_count', 0)}:{n.get('backlink_count', 0)}"
        for n in notes
    )
    parts += sorted(f"a:{a['id']}" for a in articles)
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


# --- prompting --------------------------------------------------------------

_TYPE_BRIEFS = {
    "orphan": (
        "ORPHANED NOTES (no links in or out - their ideas are unreachable). "
        "Suggest which existing note each should connect to, or what bridging "
        "note would give it a home."
    ),
    "duplicate": (
        "LIKELY DUPLICATES (near-identical topic and title). "
        "Suggest merging them into one note and keeping the better title."
    ),
    "connection": (
        "RELATED BUT UNLINKED (distinct notes covering adjacent ground). "
        "Suggest the wikilink and say what the relationship is."
    ),
    "hub": (
        "CLUSTERS WANTING A HUB (several mutually-related notes with no index). "
        "Suggest a hub note that indexes them and names the shared theme."
    ),
    "promote": (
        "WELL-REFERENCED NOTES (many other notes point here). "
        "Suggest developing this into a full article."
    ),
    "split": (
        "OVERSIZED NOTES (long enough to hold several ideas). "
        "Suggest how to split it into atomic notes."
    ),
    "article": (
        "UNCOVERED TOPICS (many notes on a topic, but no article about it). "
        "Suggest an article that would draw on those notes."
    ),
}


def _describe_candidate(suggestion_type: str, data: dict[str, Any]) -> str:
    """Render one candidate as a prompt line. Pure."""
    if suggestion_type == "orphan":
        return f'- "{data["title"]}" (id: {data["note_id"]}, no links in or out)'
    if suggestion_type in ("duplicate", "connection"):
        return (
            f'- "{data["note_a_title"]}" (id: {data["note_a_id"]}) and '
            f'"{data["note_b_title"]}" (id: {data["note_b_id"]}) '
            f'- {data["similarity"]:.0%} similar'
        )
    if suggestion_type == "hub":
        listed = ", ".join(f'"{t}"' for t in data["titles"])
        return f'- {data["size"]} related notes: {listed} (ids: {", ".join(data["note_ids"])})'
    if suggestion_type == "promote":
        return (
            f'- "{data["title"]}" (id: {data["note_id"]}, '
            f'{data["backlink_count"]} notes reference it)'
        )
    if suggestion_type == "split":
        return f'- "{data["title"]}" (id: {data["note_id"]}, {data["content_length"]} chars)'
    if suggestion_type == "article":
        listed = ", ".join(f'"{t}"' for t in data["titles"])
        return (
            f'- tag "{data["tag"]}": {data["note_count"]} notes ({listed}) but no article '
            f'(ids: {", ".join(data["note_ids"])})'
        )
    return ""


def candidate_note_ids(data: dict[str, Any]) -> list[str]:
    """Extract the note IDs a single candidate refers to. Pure."""
    ids = [str(data[key]) for key in ("note_id", "note_a_id", "note_b_id") if key in data]
    ids += [str(note_id) for note_id in data.get("note_ids") or []]
    return ids


def sanitize_suggestions(
    suggestions: list[dict[str, Any]], composed: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Reconcile LLM suggestions against the analysis that produced them.

    Pure function: No I/O, no side effects, deterministic.

    The LLM is only trusted for wording. Two things it gets wrong regularly
    are corrected here against the authoritative candidate list:

    1. Invented note IDs -- notably echoing a tag name ("sre") where note IDs
       were wanted. These would render as dead links, so they are dropped.
    2. Mislabelled types -- e.g. tagging a "promote" finding as "hub", which
       shows the wrong badge and routes the action button wrongly.

    A suggestion is matched to its candidate by note-ID overlap, and takes
    that candidate's type. Suggestions matching no candidate are dropped.

    Args:
        suggestions: Parsed LLM suggestions
        composed: The candidates the suggestions were generated from

    Returns:
        Suggestions with real note IDs and authoritative types
    """
    candidates = [(item["type"], set(candidate_note_ids(item["data"]))) for item in composed]
    valid_ids = {note_id for _, ids in candidates for note_id in ids}

    sanitized = []
    for suggestion in suggestions:
        kept = [note_id for note_id in suggestion["related_notes"] if note_id in valid_ids]
        if not kept:
            logger.debug(
                "Dropping suggestion %r: no valid note IDs in %s",
                suggestion.get("title"),
                suggestion["related_notes"],
            )
            continue

        # Take the type from whichever candidate these notes came from
        kept_set = set(kept)
        best_type, best_overlap = suggestion["type"], 0
        for candidate_type, candidate_ids in candidates:
            overlap = len(kept_set & candidate_ids)
            if overlap > best_overlap:
                best_type, best_overlap = candidate_type, overlap

        if best_type != suggestion["type"]:
            logger.debug(
                "Retyping suggestion %r: %s -> %s",
                suggestion.get("title"),
                suggestion["type"],
                best_type,
            )

        sanitized.append({**suggestion, "related_notes": kept, "type": best_type})
    return sanitized


def build_inspiration_prompt(composed: list[dict[str, Any]]) -> str:
    """Build prompt for the LLM to phrase suggestions in natural language.

    Pure function: No I/O, no side effects, deterministic.

    The analysis is already done -- the LLM's only job is wording. It is told
    explicitly not to invent suggestions and not to ask for longer notes.

    Args:
        composed: Output of compose_candidates()

    Returns:
        Complete prompt string for LLM
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in composed:
        grouped.setdefault(item["type"], []).append(item["data"])

    sections = []
    for suggestion_type in _ROTATION_ORDER:
        items = grouped.get(suggestion_type)
        if not items:
            continue
        lines = [_describe_candidate(suggestion_type, data) for data in items]
        sections.append(f"{_TYPE_BRIEFS[suggestion_type]}\n" + "\n".join(lines))

    analysis = "\n\n".join(sections) if sections else "No opportunities found."

    return f"""You are helping the owner of a Zettelkasten knowledge base.

The analysis below is already complete. Your ONLY job is to phrase each \
finding as a clear, actionable suggestion. Write exactly one suggestion per \
finding listed. Do not invent findings that are not listed.

CRITICAL RULE: never suggest making a note longer or adding more content to \
it. In a Zettelkasten a short note is correct -- atomic notes are the goal. \
Suggest connecting, merging, splitting, indexing, or promoting notes instead.

{analysis}

For each finding, produce an object with:
- type: one of {", ".join(f'"{t}"' for t in SUGGESTION_TYPES)} (use the category it was listed under)
- title: short actionable title (e.g. "Merge: Five Dysfunctions duplicates")
- description: 1-2 sentences on what to do and why it helps
- related_notes: array of the note IDs given for that finding
- action_text: short button label (e.g. "Merge Notes", "Add Link", "Draft Article")

Return ONLY a JSON array. No preamble, no explanation, no markdown fences.
Example: [{{"type": "orphan", "title": "Connect: Note Title", \
"description": "...", "related_notes": ["note-id"], "action_text": "Connect Note"}}]

JSON:"""


# --- parsing ----------------------------------------------------------------


def parse_inspiration_response(raw_response: str) -> list[dict[str, Any]]:
    """Parse LLM response into structured suggestions.

    Pure function: No I/O, no side effects, deterministic.
    Tolerates markdown fences and surrounding prose.

    Args:
        raw_response: Raw text response from LLM

    Returns:
        List of parsed suggestion dicts, or empty list if parsing fails
    """
    if not raw_response:
        return []

    response = raw_response.strip()

    # Strip markdown code block wrappers
    if response.startswith("```json"):
        response = response[7:]
    if response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]
    response = response.strip()

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        # Model wrapped the array in prose - recover it
        extracted = extract_json_payload(response, opener="[")
        if extracted is None:
            logger.warning("No JSON array found in inspiration response")
            logger.debug("Raw response (first 500 chars): %s", raw_response[:500])
            return []
        try:
            data = json.loads(extracted)
        except json.JSONDecodeError:
            logger.warning("Extracted inspiration payload is not valid JSON")
            logger.debug("Extracted (first 500 chars): %s", extracted[:500])
            return []

    if isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        logger.warning("Unexpected JSON type: %s (expected array)", type(data))
        return []

    valid_suggestions = []
    required_fields = {"type", "title", "description", "related_notes", "action_text"}

    for item in data:
        if not isinstance(item, dict):
            continue
        if not required_fields.issubset(item.keys()):
            logger.debug("Suggestion missing fields: %s", required_fields - set(item.keys()))
            continue
        if item["type"] not in SUGGESTION_TYPES:
            logger.debug("Invalid suggestion type: %s", item["type"])
            continue
        if not isinstance(item["related_notes"], list):
            logger.debug("related_notes is not a list: %s", type(item["related_notes"]))
            continue
        valid_suggestions.append(item)

    return valid_suggestions


# --- fallback (no LLM) ------------------------------------------------------


def _fallback_for(suggestion_type: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """Build one templated suggestion without an LLM. Pure."""
    if suggestion_type == "orphan":
        return {
            "type": "orphan",
            "title": f"Connect: {data['title']}",
            "description": (
                "This note has no links in or out, so nothing in the graph leads to it. "
                "Add a wikilink to a related note so it becomes reachable."
            ),
            "related_notes": [data["note_id"]],
            "action_text": "Connect Note",
        }
    if suggestion_type == "duplicate":
        return {
            "type": "duplicate",
            "title": f"Merge: {data['note_a_title']}",
            "description": (
                f"\"{data['note_a_title']}\" and \"{data['note_b_title']}\" are "
                f"{data['similarity']:.0%} similar with nearly the same title. "
                "They look like the same idea captured twice - merge them."
            ),
            "related_notes": [data["note_a_id"], data["note_b_id"]],
            "action_text": "Compare Notes",
        }
    if suggestion_type == "connection":
        return {
            "type": "connection",
            "title": f"Link: {data['note_a_title']}",
            "description": (
                f"\"{data['note_a_title']}\" and \"{data['note_b_title']}\" cover related "
                f"ground ({data['similarity']:.0%} similar) but aren't linked. Add a wikilink."
            ),
            "related_notes": [data["note_a_id"], data["note_b_id"]],
            "action_text": "Add Link",
        }
    if suggestion_type == "hub":
        return {
            "type": "hub",
            "title": f"Hub note for {data['size']} related notes",
            "description": (
                f"{data['size']} notes cover the same theme without an index: "
                f"{', '.join(data['titles'][:3])}. A hub note linking them would "
                "make the cluster navigable."
            ),
            "related_notes": data["note_ids"],
            "action_text": "Create Hub Note",
        }
    if suggestion_type == "promote":
        return {
            "type": "promote",
            "title": f"Article from: {data['title']}",
            "description": (
                f"{data['backlink_count']} notes reference this one, so it is already "
                "load-bearing in your graph. That is usually a sign there is a full "
                "article in it."
            ),
            "related_notes": [data["note_id"]],
            "action_text": "Start Article",
        }
    if suggestion_type == "split":
        return {
            "type": "split",
            "title": f"Split: {data['title']}",
            "description": (
                f"At {data['content_length']} characters this note likely holds more than "
                "one idea. Split it into atomic notes and link them together."
            ),
            "related_notes": [data["note_id"]],
            "action_text": "Split Note",
        }
    if suggestion_type == "article":
        return {
            "type": "article",
            "title": f"Article idea: {data['tag']}",
            "description": (
                f"You have {data['note_count']} notes tagged \"{data['tag']}\" but no "
                "article covering it. Those notes are the raw material for one."
            ),
            "related_notes": data["note_ids"],
            "action_text": "Draft Article",
        }
    return None


def build_fallback_suggestions(
    composed: list[dict[str, Any]], limit: int = 5
) -> list[dict[str, Any]]:
    """Build suggestions without an LLM (fallback when generation fails).

    Pure function: No I/O, no side effects, deterministic.

    Args:
        composed: Output of compose_candidates()
        limit: Maximum suggestions to return

    Returns:
        List of suggestion dicts
    """
    suggestions = []
    for item in composed:
        suggestion = _fallback_for(item["type"], item["data"])
        if suggestion is not None:
            suggestions.append(suggestion)
        if len(suggestions) >= limit:
            break
    return suggestions
