# Operating with more than one

Keel is built for a firm of one, and it stays that way: one person's judgment is what the
scaffold is shaped around. This page is the **few-person mode**, for the day that stops being
the whole story. It arrives in one of two ways, and usually in the first one before the second:

1. **One operator, parallel sessions.** You run two or three agent sessions at once, each in its
   own worktree. Nobody else has joined, and you already have two writers who cannot see each
   other's uncommitted work.
2. **A second person.** A collaborator, a partner, or a contractor starts running sessions on the
   same instance.

The same rules cover both, because the hazard is the same: more than one writer, each working
from a picture of the repository that the others are changing. Nothing on this page changes a
solo instance until you switch the mode on.

## Switching the mode on

`os/project-state.yaml` carries an `operating_mode` block:

```yaml
operating_mode:
  operators: solo        # solo | few
  close_mode: commit     # commit | pr
  handoff:
    keep_newest: 5
```

Set `operators: few` when you start running sessions in parallel or when a second person gets
push access. Set `close_mode: pr` when you want every session to close through a pull request
(see [Closing in team mode](#closing-in-team-mode) below). The two are separate on purpose: one
operator running parallel sessions needs the parallel rules but may not want pull requests for
every session.

## Parallel sessions and worktrees

**One session, one worktree, one branch.** Two sessions in one checkout share a working tree,
an index, and a current branch; one session's checkout or commit moves the ground under the
other. Give each session its own worktree (`git worktree add`) on its own branch.

**One owner per file.** Before you start sessions that will run at the same time, write down
which session owns which files. A session that needs a change in a file it does not own reports
the change instead of making it, and the owner applies it. Files every session wants to touch (a
registry, the decision log, a changelog, an index) get exactly one designated writer for the
whole batch; everyone else reports the edit they need. Most merge conflicts in parallel work are
two sessions appending to the same index.

**Assign ids up front.** Any record with sequential ids (corrections, decisions, plan items)
collides when two sessions each take "the next free id" from their own branch. Before the
sessions start, count the ids on the default branch and on every open branch
(`git for-each-ref` lists them), hand each session its own block, and have each session use only
its block. `python3 os/id_allocator.py` does the count across every branch and worktree, and
`--reserve N` hands out disjoint blocks; it never writes.

**Recount at merge.** Counts a branch computed (the `meta` totals in a registry, a skill count in
a summary) were true on that branch. After merging, recompute them on the merged tree, not by
adding the branches' numbers together.

**Bring in the default branch by merging it,** and regenerate any generated file rather than
hand-resolving its conflict.

**Reap only what is merged and clean.** A worktree is safe to remove when its branch is merged
into the remote default branch (check after a fetch, against the remote ref rather than your
local copy of it) and its tree has no uncommitted changes. A dirty tree or a branch with commits
the default branch lacks is never reapable, whatever its name suggests. Never remove the
worktree a live session is running in. `python3 os/worktree_report.py` lists every worktree with
its merged, dirty and age state and prints the reapable set; it has no flag that removes
anything, so the removal stays a person's step.

**No stranded branches.** At session close every branch with unmerged commits reaches one of
three states: a pull request is open, the branch is pushed as a backup, or it is explicitly
abandoned (`os/session-rules.md`, The Session Close Sequence).

## Shared knowledge and personal knowledge

The question a second operator forces is which knowledge belongs to the firm and which belongs
to one person. The answer that holds up is plain:

| Tier | What it is | Who writes it | How it changes |
|---|---|---|---|
| **Shared** | Files in this repository: decisions, corrections, rules, skills, operator profiles, handoffs, knowledge files | any operator, within their approval rights | by commit in solo mode, by reviewed pull request in team mode |
| **Personal** | Your agent runtime's own memory, your local-only settings file, a memory store on your own machine | you only | however you like; nobody else reads it |

Three consequences:

- **A fact the firm depends on lives in the shared tier.** If something your runtime remembered
  turns out to matter to the whole firm, port it into a shared file in a pull request, then
  treat the personal copy as a convenience rather than the record. A second operator's session
  cannot read your runtime memory, so a rule that lives only there does not exist for them.
- **Runtime memory is machine-local.** It does not follow you to a second machine, and it does
  not reach another person. Plan as if it vanishes, because from everyone else's side it already
  has.
- **A searchable memory store has one writer at a time.** If you use a memory backend
  (`docs/memory.md`), either each operator runs their own (personal tier), or one designated
  session applies the saves the others send in their pull requests. Two people's sessions
  writing one store at once, with nothing that grants and expires a write lease, is how one
  session's careful change gets silently undone by another session's restore.

## Who owns what: the ownership axis

`origin:` (from [keelson](../keelson/README.md)) answers one question about a file: can it travel
to the shared keel base, or is it specific to your instance? A team needs a second, separate
question answered: what kind of knowledge is this, and whose approval does a change to it need?
That is the ownership axis: two fields, `layer:` and `approver:`.

| `layer:` | What the file holds | `approver:` |
|---|---|---|
| `methodology` | how the firm works: skills, protocols, session rules, voice, operating principles | required; usually the founding operator |
| `engagement` | knowledge about one client, project, or engagement | optional |
| `hybrid` | both at once, such as a playbook illustrated with one client's material | required; consider splitting the file in two |

`approver:` names an operator id (the `operator` value in `os/operators/<operator-id>.md`).

**The approval rule, the only one.** A change to a file needs the approval of the operator its
`approver:` names. When the file names none (an engagement file, or an untagged one), any
operator whose profile lists the file's layer under `approves` may approve it; an untagged file
needs someone who `approves` all three layers. Nothing else grants approval: a profile's `role`
is descriptive, and being the founder confers nothing a field does not say.

The word is the same as in the [three-layer model](three-layer-model.md) but the axis is not:
`layer:` here sorts knowledge by who owns it, and has nothing to do with the Runtime,
Configuration, and Deployment layers that sort what you rent from what you own.

**Where the fields go.** At the head of the file, beside `origin:` where the file can carry it:

- A Markdown file without frontmatter: one HTML comment per field on the lines straight after
  the `origin:` comment (or at the top, if the file carries no `origin:` tag), for example
  `<!-- layer: methodology -->` then `<!-- approver: [operator-id] -->`. Keep the `origin:`
  comment alone on the first non-empty line, where the separability check reads it.
- YAML, Python, and other text files: header comments in the first lines,
  `# layer: engagement`, as `# origin:` is.
- A Markdown file that opens with YAML frontmatter (a skill's `SKILL.md`): `layer:` and
  `approver:` as frontmatter keys. Such a file cannot carry an `origin:` tag the separability
  check reads today, because the check looks for an HTML comment on the first non-empty line and
  a frontmatter file's first line is `---`. An `origin:` written in its frontmatter is skipped
  without a warning, so do not rely on one there.

**How the two axes relate.** They are independent, and neither overrides the other:

- `origin:` is the only answer to "may this file travel to the base?" `layer:` is the only
  answer to "what kind of knowledge is this?" `approver:` is the only answer to "who signs off on
  a change?" Read each field for its own question; never infer one from another.
- Who may approve follows the one approval rule above: the file's `approver:` first, then
  profiles' `approves`.
- One combination is almost always a mistake: `origin: keel` with `layer: engagement`.
  Engagement knowledge is about one client and does not travel to a shared base. When you see
  it, one of the two tags is wrong; fix the tag rather than the file's content.

Tag files as you touch them. An untagged file makes no claim on either axis.

## Operators and handoffs

Each person who runs sessions has two files:

- **A profile**, `os/operators/<operator-id>.md`, copied from
  [`os/operators/operator.template.md`](../os/operators/operator.template.md): identity (matched
  by `git config user.email`), how to work with them, preferences, and approval rights. A session
  loads exactly one profile, the one whose `git_emails` matches (the template and any
  `status: inactive` profile never count). Zero matches or two matches
  means the session stops and asks; it never falls back to a default identity, because a default
  quietly gives one person's preferences and approval rights to another.
- **A handoff file**, `os/handoff/<operator-id>.md`, copied from
  [`os/handoff.template.md`](../os/handoff.template.md): one entry per closed session, newest
  first, each entry the persisted Exit Gate report. Each operator's next session starts from
  their own newest entry, so two people's sessions never interleave in one log. In PR close mode
  the entry rides on the session's pull request, so until it merges the next session reads that
  pull request's body instead (`os/session-start.md`, step 3).

**The rotation rule.** A handoff file keeps its newest `operating_mode.handoff.keep_newest`
entries. At session close, after writing the new entry, older entries move unchanged and in
order to the archive file the handoff names. Entries are moved, never deleted, so the full
history survives and the file you read at session start stays short enough to read.

## Closing in team mode

`close_mode: pr` is the opt-in PR-only close. In it, no session commits straight to the default
branch: each session closes on its own branch, pushes it, and opens a pull request whose body is
the Exit Gate report. A change to a `methodology` file goes in its own pull request for that
file's approver, separate from engagement work, so a rule change can be reviewed and reverted on
its own.

Switch it on when:

- a second person can push to the instance, or
- your parallel sessions regularly touch the same shared files, or
- you want a second pair of eyes on every change to how the firm works.

Leave it off while you are one person working one session at a time. For a firm of one, a pull
request per session costs more than the review it buys.

## When a second person joins

[`SETUP.md`](../SETUP.md) is the joining path: access, your operator profile and handoff file,
your first session, and the cold-start test to run before you hand an instance to someone new.

## What this does not do

These are conventions, checked by a person or by the report-first scripts named above. Nothing on
this page installs automation into your runtime, decides who should be an approver, or settles
a disagreement between two operators. Those stay with the people running the firm.
