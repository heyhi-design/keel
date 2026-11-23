# Joining an existing instance

This is the path for a person joining a firm that already runs on keel. Setting up a new firm
from scratch is a different path: [`docs/bootstrap-prompt.md`](docs/bootstrap-prompt.md), or
[`docs/setup-guide.md`](docs/setup-guide.md) by hand.

Read [`docs/operating-with-more-than-one.md`](docs/operating-with-more-than-one.md) first. It is
the contract you are joining: who owns which files, which knowledge is shared and which is yours
alone, and how sessions close when more than one person runs them.

## Before you join: the cold-start test

Whoever hands the instance over runs this first, because an instance that has only ever run on
its founder's machine carries assumptions nobody can see from that machine.

1. Clone the instance fresh into an empty temporary directory, as the new person would.
2. Run the Start Sequence (`os/session-start.md`) against that clone, by hand or with the
   `session-start` skill.
3. Check that every path the start sequence and the root instruction file name exists in the
   fresh clone. A path that only exists on the founder's machine (a gitignored folder, an
   absolute path, a file in a personal settings directory) fails here.
4. Check for steps that depend on git state a fresh clone does not have: refs left behind by an
   earlier merge or rebase, a branch that only exists locally, a remote named something other
   than the default.
5. Fix what fails in the shared files, commit, and run the test again on a new clone until it
   passes.

**It passed when:** a fresh clone, with nothing but the repository, gets through the start
sequence with every step passing or skipped for a stated reason.

## Step 1: Get access

- Push access to the instance's repository, with the default branch protected so changes reach it
  by pull request. Ask the founding operator. A protected default branch means sessions reach it
  only through pull requests, so the instance runs `operating_mode.close_mode: pr` in
  `os/project-state.yaml`.
- Your own agent runtime, signed in under your own account. Never share one account between two
  people: each runtime keeps its own personal memory, and two people in one account mix theirs.
- Read the instance's `os/operating-principles.md` before anything else. If the firm works
  inside a client's or an employer's environment, its rules on which content may go into which
  tools apply to you from your first session.

**You know it worked when:** you can clone the repository and open a pull request against it.

## Step 2: Create your operator profile

Copy [`os/operators/operator.template.md`](os/operators/operator.template.md) to
`os/operators/<your-operator-id>.md` and fill it in:

- `git_emails`: every address you commit with. Check with `git config user.email` in your clone.
  Exactly one profile may match it.
- `role`: `member`, unless the founding operator says otherwise.
- `approves`: the knowledge layers you may approve changes to; usually `engagement` to start.
- How to work with you, and your preferences.

**You know it worked when:** `git config user.email` in your clone appears in your profile's
`git_emails` and in no other profile.

## Step 3: Create your handoff file

Copy [`os/handoff.template.md`](os/handoff.template.md) to
`os/handoff/<your-operator-id>.md`, set `operator`, and delete the example entry. Your sessions
start from your own newest entry; you read other people's handoffs only when a task needs them.

## Step 4: Know what is shared and what is yours

- **Shared:** everything in the repository. It changes through pull requests.
- **Yours alone:** your agent runtime's memory, your local settings, anything on your machine
  that is not committed. Nobody else's session can see it, so a fact the firm depends on never
  lives only there.

## Step 5: Open your profile in a pull request

Commit your profile and handoff file on a branch and open a pull request. Your `approves` list is
an approval-rights change, so an operator whose own `approves` covers the profile's layer accepts
it (in a new instance, usually the founding operator, whose profile lists all three layers). With
your profile, the instance has more than one operator: the same pull request, or the next one,
sets `operating_mode.operators: few` in `os/project-state.yaml`.

## Step 6: Run your first session

After the Step 5 pull request merges, branch from the default branch and start a session in your
own worktree on that branch (before the merge, your profile exists only on your profile branch, so
a session elsewhere finds no match and stops). Run `session-start`; it should match your
profile, find your empty handoff, and report the branch and the tools you have. Close with
`session-end`, which writes your first handoff entry. If the instance uses `close_mode: pr`, that
close opens a pull request.

**You know it worked when:** your handoff file has one real entry, written by `session-end`, and
your session's work reached the repository through the instance's close mode.

## When something goes wrong

`os/session-rules.md` (Failure Recovery) covers a corrupted file, two corrections that disagree,
a skill that produced bad output, and a session unsure of its own state. When the problem is
between two people rather than in a file, it goes to the people: no rule here settles it.
