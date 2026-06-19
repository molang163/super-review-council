# Super Review Council / 超级审查会

超级审查会是给 Codex 用的审查 skill，流程比较重。

它不是让 AI 看一眼代码就结束。它会先冻结审查目标，再让多个 AI 分头看同一份内容。主 agent 负责合并意见、判断哪些问题真的要修、安排修复和验证。如果修复改动了目标，还要重新审查。

这个流程适合重要改动、复杂 PR、发布前检查，或者你希望多个 AI 更严格地互相制衡的时候。

English summary: Super Review Council is a heavy multi-agent review workflow for Codex. It coordinates review, triage, fixing, verification, and repeat passes against a frozen target.

## What it does

- Triggers only when you explicitly ask for `$super-review-council` or `超级审查会`.
- Freezes the review target before review and checks for unapproved drift.
- Splits review, triage, fix planning, implementation, verification, and rereview into separate phases.
- Supports bounded read-only child review when called by a coordinator workflow.
- Keeps helper execution, web search, and privacy boundaries explicit.

## Install

Prerequisites: Codex with plugin or skill support, plus git.

Clone the repository:

```bash
git clone https://github.com/molang163/super-review-council.git
cd super-review-council
```

Local skill install:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/super-review-council "${CODEX_HOME:-$HOME/.codex}/skills/"
```

The copied skill folder should end up at `~/.codex/skills/super-review-council` unless you set `CODEX_HOME`.

Install as a Codex plugin from this local checkout or GitHub source if your Codex build supports plugin installation. Restart or reload Codex if the skill list is already loaded.

After install, invoke it explicitly:

```text
$super-review-council
```

You can also ask for `超级审查会` in Chinese.

## Compatibility notes

`scripts/autoreview remains the helper command name for compatibility` with the original implementation and test harness.

Some helper output may still say autoreview for legacy autoreview compatibility. Some environment variables may still use `AUTOREVIEW_*`; those environment variables are compatibility details, not the public skill invocation.

## License and attribution

MIT licensed.

This project is derived from the MIT-licensed `openclaw/agent-skills` `skills/autoreview` skill. It keeps the upstream openclaw copyright notice and adds derivative changes by `molang163`.

中文说法：这是基于 openclaw 原版 `skills/autoreview` 改出来的派生版，不是从零原创。发布时保留了原 MIT 许可证和版权声明。细节见 `NOTICE` 和 `LICENSE`。
