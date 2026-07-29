<!--
KEEL · CONFIGURATION TEMPLATE
File: os/operating-principles.template.md

What this is: the binding constraints and foundational principles that govern all of your
  firm's work. It has two parts: a FIXED SPINE (the four architectural invariants, which you
  keep) and FILLABLE SLOTS (your own constraints, word rules, boundaries, and classification
  scheme). Agents load this after agent-context so the constraints supersede default behavior.
When it loads: after agent-context, every session that produces output.
How to fill it: keep the four invariants as written. Fill every [BRACKETED SLOT] with your
  own rules. Delete the italic authoring notes and this comment block when done.
Provider note: the invariants are provider-agnostic by design. Invariant 1 is the honest
  caveat itself: a configuration authored against one runtime is portable in principle and an
  engineering investment in practice.
Attribution: the four architectural invariants and this operating-principles pattern are a
  methodology authored by HeyHi (heyhi.design), released under MIT as a good-faith scaffold.
-->

# [Firm Name] Operating Principles

**For everyone working on this project, human and agent equally.**

Read this before doing any work that produces output for [Firm Name]. These constraints
supersede default behavior.

---

## The Four Architectural Invariants (fixed spine - keep as written)

Every technical decision this firm makes is governed by four principles. They do not bend for
convenience.

**1. Provider-Agnostic Design.** Everything is built to run with one agent runtime today and
swap to another later. Structure the stack in layers: application logic, an orchestration
abstraction, provider adapters, a protocol layer, and tools. Never hardcode a single provider
into application logic. The honest caveat travels with the claim: a configuration is
provider-agnostic in *design* even while it is authored and tuned against one runtime in
*practice*. Porting is real engineering work, not a config flag. State that plainly wherever
you claim portability.

**2. Earn the Room.** Nothing gets access, context, or authority by default. This governs both
authority (minimum permissions, a human checkpoint before any irreversible action) and context
(minimum information, loaded on discovery rather than pre-loaded). When you design any skill,
system prompt, or context bundle, classify every piece of content into one of four categories:

| Category | Load when |
|---|---|
| **always** | every session needs it (identity, voice, these principles) |
| **conditional** | the session type matches (a plan file, a client build) |
| **on-demand** | the task explicitly calls for it (a specific reference) |
| **searchable** | retrievable from a registry, never pre-loaded by default |

If content is relevant to fewer than half of sessions, it must not load by default. Measure the
token cost. This four-way split is the mechanism, not a suggestion.

**3. Evaluation Before Deployment.** Nothing ships without passing tests. Use a four-layer
model: component (unit tests), trajectory (a golden-set run of the reasoning path), outcome
(is the result semantically valid and compliant), and system (production monitoring, drift
detection). A capability that has never been evaluated is a capability you are guessing about.

**4. Protocols at Boundaries, Not Inside Them.** Select an interface by the boundary it crosses,
not the capability it offers. A cross-team, cross-company, or cross-ecosystem protocol earns its
cost; inside a controlled stack the same protocol is overhead without the interoperability
return. The exception: the moment you ship something others plug their own agents into, you have
created a boundary, and adopting the protocol becomes protection rather than overhead.

---

## Non-Negotiable Constraints (fill with your own)

*Authoring note: the hard rules that apply to every piece of work. State each as an absolute.
Below are common slot types. Delete the ones you do not need and add your own.*

- **[Word rules].** [Any words, phrases, or abbreviations your firm never uses in copy, and
  what to say instead. If you have a punctuation ceiling or a house-style rule, state it here.]
- **[Pricing / commercial rule].** [How the firm talks about price in external documents. Many
  firms keep rates out of public surfaces and use one standing line instead.]
- **[Legal / entity rule].** [Which name appears on contracts vs. brand materials, if they
  differ.]
- **[Boundary rule].** [Any bright line the firm must not cross - a former employer, a
  conflicted client, a data boundary. State what to do the moment work brushes it: name it
  immediately.]
- **[What stays human].** [The judgment calls this firm never hands to a machine: critique,
  positioning, hiring, feedback, mentorship, ethics, strategy. Name yours.]
- **[Secrets rule].** [Never commit credentials to version control. Reference secrets by name;
  store them in a secrets manager. This one is not optional for anyone.]

---

## Document Classification (fill with your own scheme)

*Authoring note: a small classification scheme keeps sensitive material from leaking. A common
two-tier shape:*

| Tier | Mark | Applies to |
|---|---|---|
| **Confidential** | `[Firm] Confidential` | trade secrets, methodology, pricing, core research |
| **Internal** | `[Firm] Internal Use Only` | operational docs, tracking, handoffs |

Documents intended to be public carry no mark. Classify every new internal file at creation
time, not later. The test: if this leaked, would it give a competitor a meaningful advantage?

---

## Structured-Over-Prose on Propagation Surfaces

When a document is something other files, agents, or scanners read to discover what exists or
what changed (an index, a state file, a status field), prefer structured fields (tables, YAML,
named headers) over prose paragraphs. Prose decays into approximations; fields stay grep-able
and diff-able. The test: if a future reader needs to scan a surface for a specific fact rather
than read it linearly, that fact belongs in a field. Narrative writing where the prose *is* the
artifact (voice rules, essays, client copy) is exempt.

---

*Fill the pointers below with your own canonical files, then delete this note:*
*Voice: [path] · Services: [path] · Session workflow: [path]*
