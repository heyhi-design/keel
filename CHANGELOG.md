# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once a first version is
tagged.

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
