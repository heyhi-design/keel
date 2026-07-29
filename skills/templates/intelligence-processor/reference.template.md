# Intelligence Processor Reference

<!-- AUTHORING NOTE: knowledge and a light procedure (the cascade-ordering logic) that's
     stable enough to belong here rather than in the main skill file. -->

## Change Proposal template

```markdown
# Change Proposal: [short title] — [date]

## Source
[What new information triggered this: a research finding, a client conversation, an outside
development. Link or cite it if there's a source document.]

## Documents affected

### [Document 1 path]
- Classification: [contradicts / extends / confirms / obsoletes]
- Proposed change: [specific, not vague]
- Why: [one or two sentences]

### [Document 2 path]
- Classification: [...]
- Proposed change: [...]
- Why: [...]

## Review checklist
- [ ] Every proposed change accurately reflects the source information.
- [ ] Nothing proposed contradicts a binding constraint.
- [ ] Each change is the smallest one that actually addresses the finding.
- [ ] No affected document is missing from this list.

## Decision
[Approved as-is / approved with edits / not approved — reasoning]
```

## Dependency-cascade ordering

When applying an approved proposal that touches more than one document, apply changes in the order
your dependency graph implies: a canonical or foundational document (one other documents reference)
updates before the documents that reference it. This avoids a window where a downstream document
has already been updated to match a fact that its own upstream source doesn't state yet.

If you haven't built a formal dependency graph, a simpler heuristic works for a solo practice:
update your most foundational, most-referenced documents first (your profile, your core service
definitions), then work outward to anything more specific that depends on them.

## Domain-to-document lookup

<!-- AUTHORING NOTE: as your project grows, a quick lookup from subject area to the documents
     that cover it saves re-deriving Step 2's search every time. Build this out as patterns
     emerge. -->

| Subject area | Documents to check |
|---|---|
| [Subject 1, e.g., "services and pricing"] | [Document list] |
| [Subject 2, e.g., "voice and writing"] | [Document list] |
