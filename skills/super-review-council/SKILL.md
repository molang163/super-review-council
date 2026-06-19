---
name: super-review-council
description: "Use when the user explicitly asks for Super Review Council, super-review-council, 超级审查会, or a heavy multi-agent review council workflow; or when a loaded coordinator workflow explicitly invokes this skill as a bounded child review pass. Do not trigger for plain review, built-in codex review, Guardian auto_review, normal maintenance, commits, shipping, CI checks, old skill-name mentions, or mere path mentions."
tags:
  - coding
  - code-review
  - software-engineering
  - multi-agent
  - verification
allowed-tools:
  - read
  - write
  - exec
license: MIT
---

# Super Review Council / 超级审查会

Run a heavy structured multi-agent review-and-fix loop when the user explicitly asks for this `super-review-council` workflow. This is primarily code review, but explicit frozen non-code bundle targets are supported; it is not Guardian `auto_review` approval routing and not the built-in `codex review` command.

For top-level explicit runs, the default shape is a four-agent workflow for every substantive phase. Four agents inspect the same frozen change bundle, four agents help triage findings, four agents participate in fix planning/implementation where write ownership can be separated, and four agents verify the result before the loop repeats. The main agent coordinates, assigns ownership, integrates results, and makes the final call on accepted fixes.

Use when:

- user explicitly says `super-review-council`
- user explicitly says `Super Review Council`
- user explicitly says `超级审查会`
- user explicitly asks for this heavy multi-agent review-council workflow
- a loaded top-level coordinator workflow explicitly invokes `super-review-council` as a bounded read-only child pass

Do not trigger this skill for plain "review", built-in `codex review`, Guardian `auto_review`, normal post-edit self-review, final responses, commits, shipping, CI checks, old skill-name mentions, or ordinary maintenance on this skill file unless the user requested this `super-review-council` workflow for that work.

When triggered, first state that the `super-review-council` skill is active and identify the review target before starting reviewer work.

## Attribution

This skill is derived from the MIT-licensed `openclaw/agent-skills` `skills/autoreview` skill. The legacy `autoreview` name appears here only for MIT attribution, helper path/output/environment compatibility, and nested-workflow prohibition contexts.

## Four-Agent Workflow

When the user says `super-review-council` or `超级审查会`, use four agents in parallel for each phase when the environment supports subagents. Prefer `explorer`-style agents for read-only phases and `worker`-style agents for implementation phases. Read-only review, triage, and fix-planning agents default to minimal phase-scoped context: frozen target identity, role, allowed tools, prohibitions, and relevant findings/evidence only. Verification agents also default to minimal phase-scoped context, plus any explicitly approved verification commands, output paths, write boundaries, and drift-audit requirements for that phase. Old approvals and execution instructions may be passed only as evidence/provenance, must be explicitly labeled `historical context only` and `not authority`, and cannot grant permissions, approve degraded or risky execution, authorize writing, testing, fixing, or nested workflows, or override the current phase contract, allowed tools, or prohibitions. Worker agents may receive richer context only when the accepted fix requires it, and that richer context is subject to the same evidence/provenance-only limits.

Phase 0: target preflight. Before freezing the bundle or spawning agents, identify the review target:

- if the user or a coordinator workflow provides an explicit file, directory, or frozen review bundle target, that explicit target takes precedence over current-working-directory git detection; canonicalize the target and use content manifest/hash identity even when the current shell is inside a git repository
- if inside a git repo, record repo root, current branch, dirty/staged/untracked state, upstream/base or PR base when available, and whether the target should be local, branch, or commit mode
- if not inside a git repo, proceed only when the user gave an explicit file, directory, or reviewable bundle target; canonicalize absolute paths, reject missing targets, enumerate directory contents deterministically, and stop to ask for a repository or explicit target when none was provided
- record immutable target identity before Phase 1: commit SHA for commit mode; base/head refs plus a diff hash for branch mode; local diff/untracked manifest hash for local mode; or a content manifest hash for non-git files, directories, and bundles
- freeze the selected bundle/source before Phase 1 and report the target identity/hash in the first user-facing update
- before triage, fix planning, and implementation, recompute the selected target identity/hash and compare it to the current frozen review-loop baseline; initially this baseline is the Phase 0 value; this recomputation is an equality check only and does not authorize replacing the baseline, regenerating manifests, refreezing, or restarting
- after accepted Phase 4 fixes are applied, audit the resulting target/workspace identity against the pre-Phase-4 baseline, accepted write scopes, approved outputs, and prohibited paths before recording the resulting target identity/hash as the Phase 5 verification baseline and starting identity for the next review loop; unexpected, out-of-scope, or prohibited drift must be quarantined and disclosed, and blocks baseline adoption unless explicitly approved
- if any target identity comparison differs because of unapproved external change, stop that phase, disclose the expected and observed identity/hash plus changed paths when known, and require explicit user or coordinator approval before refreezing, restarting, or adopting a new baseline; in read-only child mode, return this as a blocker to the coordinator

Native subagent registry: coordinator-side management is the primary control, not filesystem locking. Before each native subagent starts, the coordinator records phase and role, declared tools, explicit allowed and prohibited actions, allowed read/write paths, prohibited paths, sandbox and permission profile when available, baseline target identity/hash, and repo/workspace status and manifests, or an equivalent whole-workspace mutation baseline sufficient to discover writes outside the target. After the subagent returns, compare target identity, allowed/prohibited path manifests, repo/workspace status, and tool/sandbox/permission metadata against that snapshot. Quarantine, do not rely on, and disclose any target mismatch, unexpected write inside or outside the target, allowed-path drift, prohibited-path touch, tool drift, permission or sandbox expansion, unexplained mutation, unauthorized drift, or unexpected writes before continuing. Filesystem read-only modes, immutable directories, and sandbox restrictions are useful supplemental guardrails or evidence when available, but they never replace the coordinator's prompt contract, registry, snapshot/drift audit, quarantine decision, integration review, and final decision.

Phase failure handling: if any required agent, helper engine, or worker errors, times out, violates the phase contract, returns missing required fields, or produces unusable output, that phase is incomplete. Quarantine or ignore the suspect output, disclose the failure, and retry or replace the participant only within the same phase contract and engine/model constraints, or stop for explicit degraded-mode approval or a blocker. Never count absent, stale, or unusable output as clean four-agent coverage.

Phase 1: four-agent review. Give each reviewer the same frozen diff/bundle and one primary focus:

- correctness and regressions
- security and trust boundaries
- tests, edge cases, and failure modes
- maintainability, integration contracts, and user-visible behavior

Review constraints:

- every reviewer engine must be constrained by the coordinator as a read-only reviewer: the launch brief must name allowed read-only tools/actions, prohibit writes and mutating commands, prohibit nested review/orchestration/agent creation, and bind the reviewer to the frozen target; use sandbox, tool policy, helper flags, filesystem read-only controls, or immutable bundles only as optional extra evidence when available, but never require them; do not use an engine as a reviewer when the coordinator cannot reasonably forbid, observe, and audit writes or tool drift
- reviewers must not edit files, run formatters, install packages, mutate git state, push, commit, or run commands that write files
- reviewers may inspect files, types, docs, dependency contracts, and current public docs when needed
- for diff, branch, commit, or patch reviews, reviewers must report only actionable defects introduced or exposed by the reviewed change
- when the frozen target is a whole-file, non-code bundle, plan, spec, docs, or artifact bundle, reviewers report actionable defects present in that artifact against its stated purpose and constraints rather than code-only or diff-provenance issues
- reviewers must not propose broad rewrites, stylistic preferences, or unrelated cleanup

Phase 2: four-agent triage. First pass the stale-target guard from Phase 0, then ask four agents to independently classify the merged findings as accepted, rejected, duplicate, or needs-more-evidence. Triage agents must be constrained by the coordinator with the same no-write, no-mutating-command, no-git-mutation, no-install, no-formatter, no-tests-that-write-output, no-nested-review/orchestration/agent-creation contract used for read-only review phases; they must inspect only the frozen target, merged findings, supplied evidence, and explicitly in-scope adjacent context. The main agent deduplicates, rejects speculative or low-value findings, resolves disagreement by reading the reviewed code path or artifact plus in-scope adjacent context, and records the accepted fix set.

Phase 3: four-agent fix planning. First pass the stale-target guard from Phase 0, then ask four read-only planning agents to propose minimal fix plans and ownership boundaries. Fix-planning agents must be constrained by the coordinator with the same no-write, no-mutating-command, no-git-mutation, no-install, no-formatter, no-nested-review/orchestration/agent-creation contract used for read-only review phases; they must not edit files, write artifacts, apply patches, run tests that write output, must not invoke `super-review-council`, must not invoke legacy `autoreview`, must not invoke `goal-orchestrator`, must not invoke built-in `codex review`, open review panels, or create extra agents. They may inspect the frozen target and accepted findings only to propose plans. For non-code targets, plans should name the exact artifact sections or line-level edits rather than code ownership boundaries. Prefer small fixes at the right ownership boundary. Do not plan broad refactors unless it clearly fixes the bug class.

Phase 4: four-agent implementation. First pass the stale-target guard from Phase 0, then use four worker agents only when the accepted fixes can be split into disjoint write scopes. Assign explicit ownership of files/modules to each worker. Tell every worker they are not alone in the codebase, must not revert edits made by others, and must adapt to parallel changes. Workers may edit only assigned repo-local files/modules, must avoid overlapping writes, must not format unrelated files, must not install packages or dependencies, and must not push, commit, reset, check out/switch/restore, revert, clean, stash, rebase, merge, delete branches/tags, remove untracked files, or run broad destructive filesystem commands such as `rm -rf` or `find -delete`. Workers must not invoke `super-review-council`, legacy `autoreview`, `goal-orchestrator`, built-in `codex review`, review panels, planning panels, or extra agents. Workers must report conflicts instead of resolving them by undoing user or peer changes. The main agent reviews worker patches before accepting them. If fewer than four independent write scopes exist, use the remaining agents for read-only verification, test planning, or implementation review rather than forcing overlapping edits.

Phase 5: four-agent verification. First pass the stale-target guard against the current verification baseline, then run four verification agents in parallel where possible:

- focused tests and command output
- diff audit for unintended changes
- regression/security re-check of accepted findings
- generated artifacts, docs, snapshots, or user-visible output consistency

Verification agents must be launched with explicit role, baseline identity/hash, allowed commands and tools, allowed read/write/output paths, prohibited paths and actions, finite timeouts, and a prohibition on installs, formatters, git mutation, destructive filesystem commands, nested review/orchestration, and extra agents. Tests or verification commands may write only to coordinator-approved paths outside protected target roots unless the accepted fix explicitly owns those outputs. Verification that may mutate the reviewed target must be serialized, or any parallel verifier results collected against the older baseline must be invalidated and rerun against the audited post-write baseline. After each verifier or test command, the coordinator compares target identity/hash, allowed and prohibited path manifests, repo/workspace status, and command artifacts against the Phase 5 baseline. Unexpected drift, prohibited writes, or undeclared outputs must be quarantined and disclosed before continuing. If approved verification writes legitimately change the reviewed target, record the audited post-verification target identity/hash as the starting identity for the next review loop before Phase 6 reruns review. Read-only child mode does not run Phase 5 commands.

Phase 6: repeat. After any accepted fix changes the reviewed target, including code, docs, skill text, generated output, or other bundle content, rerun the four-agent review phase against the updated diff or artifact. Continue until the four-agent review/triage process leaves no accepted/actionable findings and required tests or artifact-specific proofs pass. Do not loop indefinitely: by default stop after three full review/fix cycles unless the user explicitly asks to continue, and stop earlier if the same finding repeats without progress or no safe fix is available. Stopping because of this guardrail is not clean; report unresolved accepted findings, test status, and the reason the loop stopped.

Read-only child review pass: when a top-level coordinator workflow explicitly invokes `super-review-council` as a bounded child pass for an already frozen bundle, run only Phase 0 target preflight, Phase 1 review, and Phase 2 triage. In this child mode, Phase 0 only verifies and canonicalizes the coordinator-provided frozen target path, manifest, and hash, and may recompute the manifest/hash read-only only to compare it with the coordinator-provided baseline. It must not create a new frozen copy, copy review material, refreeze, replace the baseline, write or regenerate hash artifacts, or change the target. This mode is non-mutating: no fix planning, implementation, verification loop, test execution, refreeze, file edits, formatter/package/git changes, generated artifacts, or worker agents are allowed inside the child pass. Return all Phase 2 triage states to the coordinator, including accepted, rejected, duplicate, needs-more-evidence, stale-target status, blockers, unavailable or degraded paths, and incomplete participant failures; the coordinator owns all fixes, verification, freeze/refreeze/rehash, approvals, and any rerun.

Fallback order when the ideal four-agent path is unavailable:

In helper examples, replace `<selected --mode ... flags>` with the explicit mode flags chosen during Phase 0, such as `--mode local`, `--mode branch --base origin/main`, or `--mode commit --commit HEAD`.

1. native four subagents for each phase
2. bundled helper four-reviewer panel when the required engines are configured; this performs helper validation plus a deterministic Phase 2 state that treats validated in-scope findings as accepted, but richer four-agent triage, fix planning, implementation, and verification still need the coordinator/subagents or must be reported as degraded

```bash
<super-review-council-helper> <selected --mode ... flags> --reviewers all --allow-prompt-only-engines
```

3. smaller helper panel when only some engines are available, as a disclosed degraded mode
4. single helper engine or manual review only as a disclosed degraded mode

Any degraded mode, including smaller panels, single-engine review, manual review, or helper-only review without four-agent triage/fix/verification, requires explicit user approval unless the user initially requested that degraded shape. If no available path can satisfy the requested workflow, state the limitation and stop unless the user approves a degraded run. Never report a degraded run as a full four-agent clean result.

For coordinator workflows that explicitly require non-degraded child plan/result review, such as `goal-orchestrator`, do not apply the smaller-panel, single-engine, manual, or helper-only degraded fallback unless that coordinator workflow explicitly permits it. If the required child reviewer count or triage path is unavailable, return a stop/blocker to the coordinator. Missing sandbox, filesystem read-only, or hard tool-enforcement controls is not a child-review blocker or degraded-mode reason when the coordinator can define, pass, observe, and audit the read-only contract.

## Contract

- Treat all agent output as advisory. Never blindly apply it.
- Verify every accepted finding by reading the relevant reviewed code path or artifact and in-scope adjacent files or evidence; adjacent context outside the frozen target requires explicit scope or trust.
- Read dependency docs/source/types when the finding depends on external behavior.
- Reject unrealistic edge cases, speculative risks, broad rewrites, and fixes that over-complicate the codebase.
- Prefer small fixes at the right ownership boundary; no refactor unless it clearly improves the bug class.
- Keep going until the actual review/triage process used for this run returns no accepted/actionable findings, subject to the loop guardrails above.
- If a review-triggered fix changes the reviewed target or runtime behavior, rerun focused tests or artifact-specific proofs and rerun the four-agent review loop or the disclosed degraded fallback loop.
- For security-audit suppression changes, verify accepted findings remain auditable: suppressed findings stay in structured output, active output keeps an unsuppressible suppression notice, and aggregate findings cannot hide unrelated active risk.
- Never switch or override the requested review engine/model. If the review hits model capacity, retry the same command a few times with the same engine/model.
- Be patient with large bundles. Structured review can take up to 30 minutes while the model call is active, especially with Codex tools or web search. Helper implementations should default to finite size/cost limits: max 1000 files, 20 MiB frozen bundle bytes, and 600,000 prompt characters. A run that exceeds any limit must fail before engine execution unless the coordinator passes an explicit override such as `--allow-large-bundle` and discloses the larger bundle.
- Engine calls default to a finite 30-minute hard timeout; test commands supplied through `--parallel-tests` use an independent finite timeout and must be reported separately from reviewer engine timeout status.
- Treat heartbeat lines like `review still running: ... elapsed=... pid=...` as healthy progress, not a hang. Let the helper continue while heartbeats are advancing. Pass `--stream-engine-output` when live engine text is useful; Codex and Claude filter tool/file chatter, other engines pass raw output through.
- Do not kill a review just because it has been quiet for 2-5 minutes, or because it is still running under the 30-minute window. Inspect the process only after missing multiple expected heartbeats, after 30 minutes, or after an obviously failed subprocess; prefer letting the same helper command finish.
- Tools are useful in review mode. The helper allows read-only inspection tools by default. Web search is opt-in with `--web-search` so reviewers can check public dependency contracts, upstream docs, and current behavior when needed. Web searches must use minimal privacy-safe queries: do not include secrets, credentials, private URLs, proprietary or private code, private diffs or patch hunks, customer/user data, non-public repo/org/branch/issue/PR identifiers, exact local or private filesystem paths, or target-specific private paths; prefer public package names, error identifiers, API names, and official docs or public general behavior. Keep web search disabled when a safe query cannot be formed. Because raw reviewer web queries are not mediated by the helper, `--web-search` is reported as degraded privacy coverage.
- Security perspective is always included, but it should not cripple legitimate functionality. Report security findings only when the change creates a concrete, actionable risk or removes an important safety check.
- For regression provenance, keep roles separate: blamed code author, blamed PR author, PR merger/committer, current PR author, and PR/date. If no blamed PR is traceable, use the blamed commit as the provenance: commit SHA, date, and author username. Do not guess a merger or frame missing PR metadata as a separate finding.
- If the blamed PR was merged by `clawsweeper[bot]` or another automation, identify the human trigger when practical. Check timeline/comments first; if rate-limited, use gitcrawl/cache or public PR HTML. Look for maintainer commands such as `@clawsweeper automerge`, `/landpr`, or labels/status comments that armed automerge. Report `automerge triggered by @login`; if not found, say trigger unknown.
- Individual reviewers and helper engines must not invoke built-in `codex review`, nested `super-review-council`, legacy `autoreview`, `goal-orchestrator`, nested reviewers, nested planning panels, or nested reviewer panels from inside their own review. The top-level coordinator may use the explicit `super-review-council` four-agent workflow or helper panel requested by the user.
- User approval for degraded mode, risky execution, or repair commands never authorizes reviewer, helper, or worker agents to invoke nested review or orchestration workflows.
- Stop as soon as the helper exits 0 with no accepted/actionable findings and required tests or artifact-specific proofs passed or were explicitly not required. Do not run an extra review just to get a nicer "clean" line, a second opinion, or clearer closeout wording.
- Treat the helper's successful exit plus absence of actionable findings as the clean review result only when required tests or artifact-specific proofs also passed or were explicitly not required, even if the underlying Codex CLI output is terse; otherwise report the non-clean test/proof status while still including the mandatory Final Report fields.
- For explicit `super-review-council`, use four agents for review, triage, fixing, and verification by default. Outside explicit `super-review-council`, multi-agent panels remain opt-in only. The main agent still verifies every accepted finding before fixing or accepting worker patches.
- During approved writable code implementation phases only, if rejecting a finding as intentional/not worth fixing, add a brief inline code comment only when it explains a real invariant or ownership decision that future reviewers should know. Do not add comments from read-only review, triage, planning, child, or non-code artifact phases.
- If `gh`/Gitcrawl reports `database disk image is malformed`, only the coordinator may run `gitcrawl doctor --json`, and only after explicit user approval. Do not run it from read-only reviewer, worker, or helper-engine contexts. Report that cache repair was approved and attempted if it changes state.
- If Gitcrawl reports a portable manifest mismatch, source/runtime DB health error, or stale portable-store checkout, only the coordinator may ask the user for approval to run `gitcrawl doctor --json` and inspect `source_db_health`, `runtime_db_health`, and `portable_store_status` before falling back to live GitHub. Treat this as cache/runtime repair outside the reviewed checkout, not as a reviewer read-only command.
- Do not push just to review. Push only when the user requested push/ship/PR update.

## Pick Target

Start with the Phase 0 preflight. Use the observed target state to choose one of the modes below; do not force a dirty/local review for committed, pushed, or PR work.

Explicit file, directory, or frozen bundle target:

Use this when Phase 0 selected an explicit reviewable target, even when the
current shell is inside a git repository. Do not run the helper git modes for
this path; use bundle mode so reviewers receive the exact frozen content target:

```bash
<super-review-council-helper> --mode bundle --target /absolute/path/to/frozen-bundle --reviewers all --allow-prompt-only-engines
```

In read-only child mode for an already frozen coordinator-provided bundle, do
not follow the top-level freeze/copy/capture instructions below. Only verify
and canonicalize the provided target path, reviewed manifest, and hash; if the
bundle is missing, stale, or needs copying/refreezing/rehashing, return that
blocker to the coordinator.

For top-level non-child explicit targets, freeze the target before Phase 1 by
recording the exact path(s), resolving symlinks, and copying the review
material to a temporary frozen directory or capturing an immutable manifest
plus file contents. Optional read-only filesystem permissions may be applied
as extra evidence, but the required control is that the coordinator gives reviewers only that
frozen bundle and require findings to cite paths inside it. For directories,
bundle mode includes the frozen target contents by default so reviewed evidence
is not silently omitted; use `--exclude-generated` only when generated,
dependency, build, and cache paths are explicitly out of scope. Archive targets
are not expanded by the helper; extract archives to a frozen directory first.
Single-file binary bundle targets are rejected as opaque; place binary evidence
inside a frozen directory with surrounding review context. If no explicit target
was provided, stop and ask for one.

Dirty local work:

```bash
<super-review-council-helper> --mode local --reviewers all --allow-prompt-only-engines
```

Use this only when the patch is actually unstaged/staged/untracked in the
current checkout. `--mode uncommitted` is accepted as an alias for `--mode local`.
For committed, pushed, or PR work, point the helper at the commit
or branch diff instead; do not force dirty modes just
because the helper docs mention dirty work first. A clean local review
only proves there is no local patch.

Branch/PR work:

```bash
<super-review-council-helper> --mode branch --base origin/main --reviewers all --allow-prompt-only-engines
```

Optional review context is first-class:

```bash
<super-review-council-helper> --mode branch --base origin/main --prompt-file /tmp/review-notes.md --dataset /tmp/evidence.json --reviewers all --allow-prompt-only-engines
```

If an open PR exists, use its actual base:

```bash
base=$(gh pr view --json baseRefName --jq .baseRefName)
<super-review-council-helper> --mode branch --base "origin/$base" --reviewers all --allow-prompt-only-engines
```

Committed single change:

```bash
<super-review-council-helper> --mode commit --commit HEAD --reviewers all --allow-prompt-only-engines
```

Use commit review for already-landed or already-pushed work on `main`. Reviewing
clean `main` against `origin/main` is usually an empty diff after push. For a
small stack, review each commit explicitly or review the branch before merging
with `--base`.

## Parallel Closeout

In writable top-level post-fix git-mode runs, format first if formatting can change line locations. Do not format during Phase 0-2, read-only child passes, bundle mode, or any read-only/non-writable verification phase. Then it is OK to run tests and review git-mode targets in parallel. Do not use `--parallel-tests` with `--mode bundle`; read-only child bundle review is Phase 0/1/2 only and does not run verification commands.

```bash
<super-review-council-helper> <selected --mode ... flags> --parallel-tests "<focused test command>" --reviewers all --allow-prompt-only-engines
```

On Windows, the default `--parallel-tests` shell preserves the platform `cmd.exe`
semantics used by Python `shell=True`. Use `--parallel-tests-shell powershell`
or `--parallel-tests-shell pwsh` when the focused test command is PowerShell-specific.

Tradeoff: tests may force code or artifact changes that stale the review. If tests or review lead to reviewed target edits, rerun the affected tests or artifact-specific proofs and rerun the four-agent review loop until no accepted/actionable findings remain, subject to the loop guardrails. Once that rerun exits cleanly, stop; do not spend another long review cycle on redundant confirmation.

## Review Panels

When using the helper fallback for explicit `super-review-council`, prefer four reviewers against one frozen bundle for that helper panel. This does not replace the native four-subagent workflow above; helper-only coverage remains the disclosed fallback/degraded path unless the user initially requested that shape or explicitly approved it:

```bash
<super-review-council-helper> <selected --mode ... flags> --reviewers all --allow-prompt-only-engines
```

Use a smaller panel only when four reviewers are unavailable or the user asks for a cheaper run. This is a degraded run unless the user explicitly requested the smaller panel:

```bash
<super-review-council-helper> <selected --mode ... flags> --reviewers codex,claude --allow-prompt-only-engines
```

Set reviewer models and thinking/effort explicitly:

```bash
<super-review-council-helper> <selected --mode ... flags> --reviewers all --allow-prompt-only-engines --model codex=gpt-5.1 --thinking codex=high --model claude=sonnet --thinking claude=max
```

Inline syntax is also supported:

```bash
<super-review-council-helper> <selected --mode ... flags> --reviewers codex:gpt-5.1:high,claude:sonnet:max,droid,copilot --allow-prompt-only-engines
```

Codex maps thinking to `model_reasoning_effort` and accepts `low`, `medium`,
`high`, or `xhigh`. Claude maps thinking to `--effort` and also accepts `max`.
Engines without a real thinking knob reject `--thinking`.

Panel members inherit the top-level review privacy constraints:

- read-only inspection only; they must not edit files, run formatters, install packages, mutate git state, push, commit, reset, check out, revert, or run commands that write files
- no nested panels, nested `super-review-council`, do not invoke legacy `autoreview`, `goal-orchestrator`, built-in `codex review`, or second-order reviewer workflows
- web search follows the coordinator-selected mode; if web search is disabled, keep it disabled for every panel member, and if it is enabled, search only public docs/general behavior without sending private code, private diffs or patches, secrets, customer data, private URLs, non-public repo/org/branch/issue/PR identifiers, local/private filesystem paths, or target-specific private paths to search providers

## Context Efficiency

When using the helper fallback, run the helper directly so target selection, engine choice, structured validation, and exit status all stay in one path. If output is noisy, summarize the completed helper output after it returns; do not ask extra agents beyond the chosen workflow to rerun the review solely for nicer wording.

## Helper

Helper discovery order:

Select a trusted helper outside every reviewed or frozen target root unless the
coordinator has made a separate recorded trust decision for a target-local helper
with path, hash, provenance, and explicit approval. Reviewing or developing a
helper does not by itself make that target-local helper executable; inspect it as
data until it is separately trusted. Do not execute a repo-local or
checkout-local helper that is inside or controlled by the review target before
that trust decision, and never execute it from read-only child, reviewer, or
helper-engine contexts. Prefer the installed Codex skill helper in ordinary
reviews of untrusted or target-controlled repositories.

1. trusted installed Codex skill helper, when present. Prefer `$CODEX_HOME` when set, otherwise fall back to `~/.codex`:

```bash
"${CODEX_HOME:-$HOME/.codex}/skills/super-review-council/scripts/autoreview" --help
```

2. trusted repo-local helper, when present and outside the reviewed/frozen target or covered by a separate recorded trust decision:

```bash
.agents/skills/super-review-council/scripts/autoreview --help
```

3. trusted checkout-local helper, when present and outside the reviewed/frozen target or covered by a separate recorded trust decision:

```bash
skills/super-review-council/scripts/autoreview --help
```

On native Windows, invoke the extensionless Python helper through Python for the selected trusted helper location:

```powershell
python "$env:CODEX_HOME\skills\super-review-council\scripts\autoreview" --help
python "$env:USERPROFILE\.codex\skills\super-review-council\scripts\autoreview" --help
python .agents\skills\super-review-council\scripts\autoreview --help
python skills\super-review-council\scripts\autoreview --help
```

`<super-review-council-helper>` in examples is a placeholder for the concrete helper
command selected above, such as
`${CODEX_HOME:-$HOME/.codex}/skills/super-review-council/scripts/autoreview`,
`.agents/skills/super-review-council/scripts/autoreview`, or
`skills/super-review-council/scripts/autoreview`. Replace it before running a command; it
is not a configured command to discover or execute.

The smoke harness has thin shell wrappers over a shared Python implementation. Smoke harness execution is a coordinator action for approved writable verification only. It must not run from read-only child, reviewer, triage, fix-planning, helper-engine, or worker contexts. Run it only from an installed trusted copy, a trusted out-of-target repo/checkout copy, or a target-local copy covered by a separate recorded trust decision; writable outputs must be coordinator-approved and outside protected target roots unless the accepted verification explicitly owns them.

From a checkout-local skill copy:

```bash
skills/super-review-council/scripts/test-review-harness --fixture benign --engine codex
```

```powershell
skills\super-review-council\scripts\test-review-harness.ps1 -Fixture benign -Engine codex
```

From an installed Codex skill copy:

```bash
~/.codex/skills/super-review-council/scripts/test-review-harness --fixture benign --engine codex
```

The helper:

- chooses dirty local changes first
- accepts `--mode uncommitted` as an alias for `--mode local`
- supports `--mode bundle --target <path>` for explicit file, directory, or frozen bundle targets, including targets inside an unrelated git repository; bundle mode includes frozen directory contents by default, use `--exclude-generated` only when generated/dependency/build/cache files are explicitly out of scope, and extract archives to a frozen directory first
- otherwise uses current PR base if `gh pr view` works
- otherwise uses `origin/main` for non-main branches
- supports `--engine codex`, `claude`, `droid`, and `copilot`; default is `AUTOREVIEW_ENGINE` or `codex`; Codex should remain the default when nothing is set, but helper runs that use prompt-only engines such as Codex must pass `--allow-prompt-only-engines` and must be reported as prompt-only technical-control coverage; this is not a missing-sandbox blocker when the coordinator supplies the read-only contract and audits the run
- resolves bare `git`, `gh`, reviewer, and PowerShell shell commands from absolute `PATH` entries only, never from the reviewed checkout; all explicit `--*-bin` paths, absolute or relative, are canonicalized before use and must resolve to trusted executables outside every protected reviewed/frozen target root and outside target-controlled checkouts unless covered by a separate recorded trust decision; relative `--*-bin` paths are resolved from the active helper execution root; in bundle mode, prefer a trusted absolute path outside the target
- use `--mode commit --commit <ref>` for already-committed work, especially clean `main` after landing
- should use an explicit `--mode branch`/`--mode commit` whenever Phase 0 selected branch/commit review; these modes require a clean worktree so reviewers cannot inspect dirty live files while the stale guard hashes only refs
- writes helper status, bundle summary, optional test status for git modes, stale-guard status, helper triage state, and the final human report to stdout; `--output` writes the same helper metadata plus final human report to a file outside the reviewed target, and `--json-output` writes validated structured JSON separately outside the reviewed target; those two output paths must be distinct
- writes heartbeats and validation warnings to stderr; with `--stream-engine-output`, filtered engine stdout may stream to stdout and engine stderr may stream to stderr, while non-streamed engine failure output is summarized by length and SHA-256 rather than echoed raw
- supports `--dry-run`, `--parallel-tests` for git modes only, `--parallel-tests-shell`, `--prompt`, `--prompt-file`, `--dataset`, `--no-tools`, `--web-search`, `--no-web-search`, and commit refs; web search is off by default, and `--no-tools` is rejected by engines that require tools to load or validate the bundle
- supports `--stream-engine-output` or `AUTOREVIEW_STREAM_ENGINE_OUTPUT=1` for live engine text while preserving structured validation; Codex and Claude hide tool/file event details, emit compact activity summaries, and report usage at turn completion
- supports opt-in review panels with `--panel` / `--reviewers`, plus per-engine `--model` and `--thinking`
- enforces bundle size/cost guardrails before engine execution: default max 1000 files, 20 MiB frozen bundle bytes, and 600,000 prompt characters; only an explicit override such as `--allow-large-bundle` may continue, and the final report must disclose the override and actual counts
- enforces separate finite timeouts for reviewer engines and `--parallel-tests`; engine timeout, test timeout, and stale-guard failure are distinct outcomes in helper output
- gives every engine the same coordinator-issued read-only, no-nested-review/no-nested-agent prompt; where the selected CLI supports tool controls, the helper limits tools to read/search/web inspection as optional extra evidence, including Codex through `codex exec` with read-only sandbox, ignored user config/rules, minimal environment, and structured output when explicitly allowed as prompt-only technical-control coverage, Claude with isolated helper config/minimal environment and only Read/Grep/Glob plus WebSearch/WebFetch when web search is enabled, Droid with isolated config/minimal environment and tools disabled, and Copilot with isolated config/minimal environment and rg/view plus `web_fetch` only when web search is enabled
- prints `review still running: <engine> elapsed=<seconds>s pid=<pid>` to stderr at long-running intervals while waiting for the selected review engine, unless streamed output or compact Codex activity has been visible recently
- prints helper stdout labels such as `autoreview degraded clean: no accepted/actionable findings reported` or `autoreview panel degraded clean: no accepted/actionable findings reported` because helper-only Phase 2 triage is always disclosed as degraded coverage
- exits nonzero when accepted/actionable findings are present

## Final Report

Include:

- requested workflow and actual workflow used
- immutable target identity: mode, repo/root or non-git target path, branch, base/ref/commit, head SHA when available, dirty/staged/untracked state, and frozen bundle source
- stale-guard result: whether the final reviewed bundle still matches the frozen target identity, or why the result is stale/blocked
- content manifest/hash for explicit file, directory, or other reviewable bundle targets, regardless of whether the current shell is inside a git repo
- actual agents/reviewers/engines used per phase
- fallback/degraded mode used, unavailable reviewers/engines, and confidence or coverage limits when the full four-agent workflow did not run
- review command used
- web-search/privacy mode: tools enabled/disabled, web search enabled/disabled, and any privacy limits applied to reviewers
- tests/proof run
- approved cache repair or Gitcrawl doctor actions, if any, including whether `gitcrawl doctor --json` changed state before retrying
- findings accepted/rejected, briefly why
- the clean review result from the final helper/review run, four-agent loop, or disclosed degraded run; or why a remaining finding was consciously rejected/unresolved

Do not run another review solely to improve the final report wording. If the final helper run exited 0, produced no accepted/actionable findings, and required tests or artifact-specific proofs passed or were explicitly not required, report that exact run as clean.
