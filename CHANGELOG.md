# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once a first version is
tagged.

## [0.3.0] - 2026-11-22

Few-person mode, a corrections lifecycle that keeps its own books, and a start-load check. keel
stays a firm-of-one template in identity: running with a second person, or with several sessions
at once, is now a documented mode with its own contract, templates and tools. Every new tool reads
and reports by default; the few that can write need an explicit flag. keel still ships zero hooks:
enforcement is a lint or a checklist your instance may wire into its own hooks.

### Added

- **Two verification disciplines on the session-rules template (`os/session-rules.template.md`)**,
  extending Verify-Before-Claim: a blast-radius verification ladder for newly built tools (seeded
  smoke, real-data read, adversarial pass, fresh-context reproduction, scaled to change size),
  extended into one rule covering both sides of a build: a plan-verification rung ahead of the
  existing rungs (re-derive every count, path, version and status a plan asserts before work
  starts), and the fourth rung run by a fresh-context reviewer whose findings are fixed in the
  same change. Beside it, a "report the instrument, not just the number" rule for metric claims.
  Both are content-free Layer-2 patterns proven in a keel instance and funnelled back down into
  the base (the keelson path).
- **The Framing Gate and the Entry Gate (`os/session-rules.template.md`)**: two three-line
  frontmatter blocks that open a scoped piece of work, as the Exit Gate closes it. `framing:`
  carries `who`, `what` and a falsifiable `signal`; `entry_gate:` carries `scope`, `consumer` and
  `blocking_unknowns`. Each has a pass condition a one-line frontmatter parse can check.
- **Few-person mode (`docs/operating-with-more-than-one.md`)**: parallel sessions and worktrees
  (one owner per file, ids assigned up front, a recount at merge, reap only what is merged and
  clean), the shared-versus-personal knowledge contract (git files reviewed by pull request are
  the shared tier; runtime memory is personal and machine-local), and when to switch on the team
  close mode. `operating_mode` in `os/project-state.template.yaml` holds the settings.
- **Operator profiles (`os/operators/operator.template.md`)**: one profile per person, matched by
  `git config user.email`, with preferences and approval rights. The agent-context template's
  "How to Work with the Operator" section now points at the matched profile.
- **Per-operator handoff with rotation (`os/handoff.template.md`)**: `os/handoff/<operator-id>.md`,
  newest entry first; keep the newest N (`operating_mode.handoff.keep_newest`) and move older
  entries, unchanged and in order, to an archive. Nothing is deleted.
- **A knowledge-ownership axis**: `layer: methodology | engagement | hybrid` plus `approver:`,
  documented beside keelson's `origin:` tag as a separate axis, not a replacement.
- **`session-start` and `session-end` starter skills (`skills/templates/`)**: thin triggers over
  the Start Sequence (now in its own small `os/session-start.template.md`, which runs every
  session) and over The Session Close Sequence, with eval cases and registry entries. The Exit Gate
  report is persisted to the handoff file or the pull request body, not only to chat; an opt-in
  PR-only close mode (`operating_mode.close_mode: pr`) suits a team.
- **Session-rules sections**: The Session Close Sequence, Tools by Capability (a step names the
  capability it needs and its fallback, never the server that provides it today) and Failure
  Recovery.
- **A root `AGENTS.md` with a thin `CLAUDE.md` that imports it**, so one set of instructions loads
  whichever runtime you use; **`SETUP.md`** for joining an instance that already runs, with a
  cold-start test.
- **Few-person tooling (`os/`)**, each read-only or report-first:
  - `resolve_operator.py`: `git config user.email` to exactly one active profile; zero or two
    matches exit nonzero, by name. A firm of one with no profile is a stated skip, never an identity.
  - `id_allocator.py`: counts ids across every local and remote branch and every worktree
    (uncommitted files included) and prints the next free id; `--reserve N` hands out disjoint
    blocks. Never writes.
  - `worktree_report.py`: branch, merged, dirty, age and lock state per worktree, and the reapable
    set. It has no flag that removes anything.
  - `handoff_rotate.py`: the rotation rule above. Reports by default; `--apply` writes the archive
    first, reads it back, and only then shortens the handoff.
  - `cold_start_check.py`: clones to a fresh temp directory and checks the start files, their `@`
    imports, every path they name, refs a fresh clone lacks, and one email per active profile.
    `--strict` exits 1 on a failure.
- **Two keelson lints (`keelson/`)**: `context_wall.py`, the separability check's phrase half,
  driven by a phrase map your instance supplies (keel ships none, and the lint refuses to run
  without one); and `close_check.py`, which checks the persisted Exit Gate report's slots.
- **`os/status_lint.py` and `os/gen_index.py`**: a planning-artifact status-vocabulary lint, and a
  folder index generated from frontmatter, deterministic so `--check` exits 1 on a stale index.
- **A start-load check (`os/start_load_check.py`)**: estimates each file of your declared start set
  in tokens (it follows `@` imports from the runtime file, then adds `os/session-start.md`, the
  core files, the matched operator profile and the newest handoff entry; `os/start-set.yaml`
  overrides the set), counts the corrections entries that load, labels a template standing in for
  an unfilled file, and lists a missing file. A budget is optional: no budget is a notice, over
  budget warns, and only `--strict` fails. No budget value ships.
- **Corrections lifecycle (`os/corrections/LIFECYCLE.md`)**: one entry at a time (add, merge or
  retire, never a wholesale rewrite); recording a fire on the entry itself; retiring as a stamped
  validity window; derived counts; the active and archive split; the optional `mistake`, `why`,
  `supersedes` and `assumes_rule` fields; seeds and the rules they assume; comparing two
  registries. The registry template's header documents the optional fields and that the CLI reads
  only `entries:`. The two superseded seeds carry `assumes_rule`. Four new contract tests in
  `tests/test_corrections_contract.py`.

### Changed

- **Starter skills: five to seven.** "Close out the session" now routes to `session-end`;
  `session-integrity` hands its report to The Session Close Sequence.
- **The setup guide and the bootstrap prompt wire `AGENTS.md`.** `docs/memory.md` no longer offers
  its Tier 3 store for several people writing one store, and gains a personal-versus-shared
  section.
- **CI test matrix pinned to `ubuntu-24.04`.** `ubuntu-latest` moved to an image with no Python
  3.9, so the pin keeps the README's "CI covers 3.9" true.

### Upgrading from 0.2.0

- Merge the updated seeds (or add `assumes_rule` to your own), then run
  `corrections audit --rules-root <your instance root>`. With agent-corrections 0.2.0, also run
  `migrate-key --from <old key>` if your registry uses another top-level key, then
  `audit --recount --write`, and record recurrences with `fire` from then on.
- Few-person mode is opt-in: copy `os/operators/operator.template.md` once per person, create
  `os/handoff/<operator-id>.md` from `os/handoff.template.md`, and set `operating_mode` in
  `os/project-state.yaml`. A firm of one can skip all three.

## [0.2.0] - 2026-09-04

Structure proven inside a keel instance, funnelled back down into the base. The headline is the
separability convention that keeps a base file provably liftable; two smaller additive lifts ride
with it.

### Added

- **keelson, the separability convention (`keelson/`)** : a file that belongs to the shareable
  base declares `origin: keel`; a file specific to your instance declares `origin: instance`.
  `keelson/separability_check.py` is the lint that enforces the promise -- it fails if an
  `origin: keel` file references a path you have declared instance-private (the `examples`
  directory by default; extend with `--private`). A reference is an import, a quoted path, or a
  Markdown link -- not a bare prose mention -- so a document can still describe the boundary it
  keeps. Wired into CI, and covered by `tests/test_separability.py`. See `keelson/README.md`.
- **Optional coverage-state fields on the skill registry** : `coverage`, `nature`, `phase`, and
  `foundation` are now documented as optional, additive fields on a registry entry
  (`skills/registry/skill-registry.template.yaml`). The search engine preserves them on load and
  ignores them for scoring, so they change no routing decision; they exist for a coverage view
  over your own skills. The field set is generic, the values are yours.
- **A corrections key-contract test (`tests/test_corrections_contract.py`)** : pins the
  corrections registry to the `entries:` key its reader expects, so the schema and the tool that
  reads it cannot drift apart unnoticed.

## [0.1.0] - 2026-07-29

The first public release: a scaffold you fill in, not a product you configure.

### Added

- **Configuration layer (`os/`)** : templates for the agent context bundle, operating principles,
  session rules, a decision log, a dependency graph, project state, and the dispatch pattern for
  handing work to an agent that runs without you watching.
- **Corrections memory (`os/corrections/`)** : the registry schema, its promotion lifecycle, and a
  set of seed entries. The mechanism by which an agent stops making the same mistake twice.
- **Company profile (`profile/`)** : the intake schema that captures a firm's identity, voice, and
  services, plus a guided self-interview for filling it in by talking rather than by typing YAML.
- **Skills (`skills/`)** : five parameterized starter skills (`voice`, `proposal`,
  `session-integrity`, `project-scanner`, `intelligence-processor`), each with a procedure/knowledge
  split and hand-runnable evaluation cases.
- **Skill registry (`skills/registry/`)** : a capability index and a keyword search over it, so an
  agent loads the skills a task needs rather than every skill it owns. Includes a three-state
  confidence gate that abstains instead of guessing, and a score-gap log for noticing when keyword
  matching has stopped discriminating well.
- **Evaluation cases (`skills/evals/`)** : twenty cases across the five starter skills, plus
  `lint_cases.py`, which checks that every case is shaped like a case. What a case is *worth* stays
  a human judgment.
- **Documentation (`docs/`)** : the setup guide, a bootstrap prompt that has your own agent perform
  the setup, the three-layer model (what you rent, what you own, what you deploy), the architecture
  figures, and the memory options. `docs/memory.md` now also covers subject granularity for
  `memory_add_relation` -- attach a status-like fact to the specific thing it's about, not to a
  broad, frequently reused subject, or a supersession-detecting tool may lump unrelated facts
  together and propose discarding real information.
- **Architecture figures (`docs/diagrams/`)** : five self-contained SVGs, walked through in
  `docs/architecture.md`: the three-layer model, what loads and what doesn't, how a session runs,
  how the whole thing funnels into itself, and where the scaffold came from. No external
  dependencies, and they follow your theme where the renderer supports it.
- **Worked example (`examples/`)** : one instance filled in end to end for a firm that doesn't
  exist, so the shape of "done" is visible before you commit a weekend to reaching it. Covers the
  profile, the agent context, a decision log, a corrections registry carrying one promoted-then-
  superseded entry you can trace across three files, all five skills, and a skill registry
  adjusted to describe them. Filled content is permitted here and nowhere else; the pull request
  template and `CONTRIBUTING.md` both say so, and every example file carries a visible note that
  the firm is invented.
- **Test suite (`tests/`)** : coverage of the registry search, the confidence gate, the reporting
  helpers, and the loader's input validation and error paths (malformed or non-UTF-8 registries,
  out-of-range flags), wired into CI. Includes a bullseye harness (`test_bullseye.py`) that checks
  your own filled-in registry, not just an invented fixture: every skill's first trigger phrase has
  to route back to that skill, with a strict exemption mechanism so a documented miss can't quietly
  outlive its own fix.

### Performance

- `skills/registry/skill-registry.py` loads its YAML registry with the C-accelerated
  loader when PyYAML's libyaml bindings are available (falling back to the pure-Python
  loader otherwise, with identical parsing either way), and caches each trigger phrase's
  compiled word-boundary pattern at module scope rather than recompiling it on every
  `search()` call, so registries with many capabilities don't thrash Python's own regex
  cache across repeated searches. Neither affects matching, ranking, or scores at any
  registry size.

### Known limitations

- The registry's scoring weights ship as generic starting defaults, not calibrated values. Expect to
  tune them against your own skills once you have a handful registered; see `skills/registry/README.md`.
- `track_skill_usage()` is a supporting interface, not a wired-up feature. Calling it from a
  session-integrity routine is left to you.
- Memory is optional and unopinionated by design. See `docs/memory.md` for what that costs you.
