"""Mining-noise classifier — a write-time guard for the memory store, no model call.

The lesson behind this: the single biggest lever on recall quality is not the
retriever, it is corpus quality. A semantic store quietly fills with material
that was never a fact worth recalling — scraped web pages, session-prompt
boilerplate, raw tool dumps, orphaned headings. Every one of those dilutes what
a search has to rank against. This module is the lever: ``classify(content)``
is called on the write path so junk is refused before it ever enters the store.

High-PRECISION by design: it flags only content matching clear, direct noise
signatures, so it errs toward keeping. A borderline entry is stored, not
dropped — a false reject (losing a real fact) is worse than a false keep.

Two kinds of signature live below:

  * STRUCTURAL rules (checkpoint logs, scraped-web frontmatter, bare heading /
    table-rule / import fragments, link-dominated navigation). These are
    format-level shapes that are noise in almost any agent-memory store, so
    they ship as-is.
  * LITERAL signatures (``_SESSION_BOILER`` etc.) are EXAMPLES. The exact
    boilerplate your runtime emits is specific to your setup — replace the
    sample strings below with the literal markers your own session prompts,
    templates, and tool dumps actually contain.
"""
from __future__ import annotations

import re

_MD_LINK = re.compile(r"\]\(https?://")

# ---------------------------------------------------------------------------
# LITERAL signatures — EXAMPLES. Substring match = high precision. Replace
# these with the exact boilerplate your own runtime emits; the shapes shown
# here (a session-prompt preamble, a template placeholder, a tool-invocation
# dump) are illustrative, not exhaustive.
# ---------------------------------------------------------------------------
_SESSION_BOILER = (
    "Continue from where you left off.",
    "CONTEXT LOAD — read in this order:",
    "--- ENV CHECK",
)
_TEMPLATE_FRAG = (
    "## Remaining\n1. [Item]: [priority",
    "## Open Decisions\n- **[Decision]**",
)
_TOOL_DUMP = (
    "<scheduled-task name=",
)

# ---------------------------------------------------------------------------
# STRUCTURAL rules — format-level noise shapes, generic across stores.
# ---------------------------------------------------------------------------
# The narrow, safe heading signature is a heading whose ENTIRE payload is a
# markdown link — a scraped article title with no summary, body, or context.
# A "real fact written as a heading" ("## Decision: we chose X") survives,
# because only a heading that is nothing but a link matches.
_HEADER_LINK_ONLY_LINE = re.compile(r"^#{1,6}\s*\[.+\]\(https?://\S+\)$")
_TABLE_SEP_LINE = re.compile(r"^\|?(\s*:?-{2,}:?\s*\|)+\s*:?-{2,}:?\s*\|?$")
_IMPORT_LINE = re.compile(r"^(import\s+\w|from\s+[\w.]+\s+import\s+)")


def classify(content: str | None, source_file: str | None = None) -> tuple[bool, str | None]:
    """Return (is_noise, reason). High precision: only flag clear mining noise."""
    c = (content or "").strip()
    if not c:
        return True, "empty"
    # Auto-generated session bookkeeping: CHECKPOINT:<date>|session:<uuid>|msgs:N|recent:<raw dump>.
    if c.startswith("CHECKPOINT:") and "|session:" in c[:80]:
        return True, "session_activity_log"
    for s in _SESSION_BOILER:
        if s in c:
            return True, "session_boilerplate"
    for s in _TEMPLATE_FRAG:
        if s in c:
            return True, "template_fragment"
    for s in _TOOL_DUMP:
        if s in c:
            return True, "tool_dump"
    # Scraped web page: the scraper's frontmatter header.
    if re.match(r"^\s*---\s*\ncanonical:\s*https?://", c) or "\nmeta-description:" in c[:220]:
        return True, "scraped_web_frontmatter"
    lines = [ln.strip() for ln in c.splitlines() if ln.strip()]
    # Bare structural fragment: 1-2 lines, every one a heading/table-rule/import
    # with no attached fact. A longer or mixed-content entry always survives.
    if lines and len(lines) <= 2 and all(
        _HEADER_LINK_ONLY_LINE.match(ln) or _TABLE_SEP_LINE.match(ln) or _IMPORT_LINE.match(ln)
        for ln in lines
    ):
        return True, "structural_fragment"
    # Scraped nav: a list dominated by markdown links (>=60% of non-blank lines).
    # BUT keep citation lists ("Sources: ..."): a research entry's reference trail
    # is signal, not nav — deleting it is a precision violation.
    if len(lines) >= 3 and not c.startswith("Sources:"):
        linky = sum(1 for ln in lines if _MD_LINK.search(ln))
        if linky / len(lines) >= 0.6:
            return True, "link_dominated_nav"
    return False, None
