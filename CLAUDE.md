# CLAUDE.md — a2agora/spec

## Good first issues — relevance check after refactors

The `good first issue` label is used on issues that point at a specific `[OPEN]`
marker inside a `layers/NN-*.md` file (see [CONTRIBUTING.md](CONTRIBUTING.md)).
These go stale silently: a merge can answer, remove, or renumber the referenced
question without anyone touching the issue.

**Run this check after merging any PR that touches `layers/*.md`, `RFC-0001-vision.md`,
or `A2A-MAPPING.md` — and after any merge in the sibling `sdk-reference` repo that
implements a layer these issues reference (e.g. an escrow-agent PR can retire a
Layer 4 open question even though no file in this repo changed):**

1. `gh issue list --repo a2agora/spec --label "good first issue" --state open`
2. For each issue, open it and find the `[OPEN]` question(s) it points at
   (usually linked as `layers/NN-*.md#open-questions`).
3. Check the current file: does that exact `[OPEN]` bullet still exist?
   - Still there, unanswered → issue stays open, no action.
   - Answered, removed, or folded into normative text → close the issue with a
     comment linking the commit/PR that resolved it.
   - Section renumbered/renamed → update the issue body's link, don't close it.
4. If a merge added *new* `[OPEN]` bullets that are good newcomer-sized questions,
   consider filing new `good first issue` entries via the issue-form templates
   (`.github/ISSUE_TEMPLATE/`) rather than leaving them undiscoverable.

Never assume an issue is still valid just because it's open — the label is a
promise to newcomers that the task is real and doable; a stale one wastes their
first contribution.
