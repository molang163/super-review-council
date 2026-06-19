# Super Review Council / 超级审查会

[中文](#中文) | [English](#english)

## 中文

给 Codex 用的重型多代理审查 skill。适合复杂改动、重要 PR 和发布前检查。

它会先冻结审查目标，再让多个 AI 分头审同一份内容。主 agent 负责合并意见、筛掉不成立的问题、安排修复和验证。只要修复改动了目标，就会重新审查，直到没有可处理的问题为止。

### 快速开始

```bash
git clone https://github.com/molang163/super-review-council.git
cd super-review-council
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/super-review-council "${CODEX_HOME:-$HOME/.codex}/skills/"
```

重启或重新加载 Codex 后，明确调用：

```text
$super-review-council
```

也可以直接说：

```text
超级审查会
```

### 它会做什么

- 审查前冻结目标，防止中途混入未批准的变化。
- 让多个审查 agent 分别看同一份内容。
- 由主 agent 统一整理结论，决定哪些问题要修。
- 修复后重新验证；目标有变化时再审一轮。
- 被上层协调器调用时，可以只做有边界的只读子审查。
- 明确记录 helper 执行、联网搜索和隐私边界。

### 适合什么时候用

适合：

- 准备合并复杂 PR。
- 发布前做最后一轮严格检查。
- 改动跨多个模块，普通 review 容易漏上下文。
- 你希望多个 AI 分别审一遍，再由主 agent 统一裁决。

不适合：

- 很小的单文件改动。
- 只想快速问一个代码问题。
- 不希望启动多轮审查和验证的场景。

### 安装

前提：你需要有支持 skill 的 Codex，以及 `git`。

本地 skill 安装：

```bash
git clone https://github.com/molang163/super-review-council.git
cd super-review-council
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/super-review-council "${CODEX_HOME:-$HOME/.codex}/skills/"
```

如果没有设置 `CODEX_HOME`，复制后的目录通常是：

```text
~/.codex/skills/super-review-council
```

这个仓库也带有 `.codex-plugin/plugin.json`。如果你的 Codex 版本支持从仓库安装 plugin，可以按你当前 Codex 的 plugin 安装流程使用它。

### 验证

确认 skill 文件存在：

```bash
test -f "${CODEX_HOME:-$HOME/.codex}/skills/super-review-council/SKILL.md"
```

查看 skill metadata：

```bash
sed -n '1,12p' "${CODEX_HOME:-$HOME/.codex}/skills/super-review-council/SKILL.md"
```

查看 helper：

```bash
"${CODEX_HOME:-$HOME/.codex}/skills/super-review-council/scripts/autoreview" --help
```

### 仓库结构

```text
.
├── .codex-plugin/plugin.json
├── skills/
│   └── super-review-council/
│       ├── SKILL.md
│       ├── LICENSE
│       ├── NOTICE
│       └── scripts/
│           └── autoreview
├── LICENSE
├── NOTICE
└── README.md
```

`SKILL.md` 是 Codex 真正读取的 skill 指令。README 只是给人看的安装和项目说明。

### 兼容说明

`scripts/autoreview` 仍然保留为 helper 命令名。这是为了兼容原始实现和测试工具，不是公开调用名。

有些 helper 输出里仍可能出现 `autoreview`，部分环境变量也可能继续使用 `AUTOREVIEW_*`。这些都是兼容细节。对用户来说，应该调用的是 `$super-review-council` 或 `超级审查会`。

### 许可证和来源

本项目使用 MIT 许可证。

它派生自 `openclaw/agent-skills` 里的 MIT 许可 `skills/autoreview` skill。这个版本保留了上游 openclaw 的版权声明，并加入了 `molang163` 的派生修改。

中文说法：这是基于 openclaw 原版 `skills/autoreview` 改出来的版本，不是从零原创。发布时保留了原 MIT 许可证和版权声明。细节见 `NOTICE` 和 `LICENSE`。

## English

Super Review Council is a heavy multi-agent review skill for Codex. It is meant for complex changes, important pull requests, and release checks.

It freezes the review target first, then asks multiple AI reviewers to inspect the same content independently. The main agent merges their feedback, rejects weak findings, plans fixes, verifies the result, and repeats the review when the target changes.

### Quick Start

```bash
git clone https://github.com/molang163/super-review-council.git
cd super-review-council
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/super-review-council "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Restart or reload Codex, then invoke the skill explicitly:

```text
$super-review-council
```

Chinese invocation also works:

```text
超级审查会
```

### What It Does

- Freezes the review target before review starts, so unapproved drift is caught.
- Runs multiple review agents against the same target.
- Lets the main agent triage findings and decide what actually needs fixing.
- Verifies fixes and repeats review when the target changes.
- Supports bounded read-only child review when called by a higher-level coordinator.
- Keeps helper execution, web search, and privacy boundaries explicit.

### When To Use

Use it for:

- Complex pull requests.
- Final checks before a release.
- Changes that cross multiple modules.
- Cases where you want several AI reviewers and one main agent to make the final call.

Do not use it for:

- Tiny single-file edits.
- Quick code questions.
- Work where you do not want multi-round review and verification.

### Install

Prerequisites: Codex with skill support, plus `git`.

Install as a local skill:

```bash
git clone https://github.com/molang163/super-review-council.git
cd super-review-council
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/super-review-council "${CODEX_HOME:-$HOME/.codex}/skills/"
```

If `CODEX_HOME` is not set, the copied skill usually ends up here:

```text
~/.codex/skills/super-review-council
```

This repository also includes `.codex-plugin/plugin.json`. If your Codex build supports installing plugins from repositories, use your current Codex plugin installation flow.

### Verify

Check that the skill file exists:

```bash
test -f "${CODEX_HOME:-$HOME/.codex}/skills/super-review-council/SKILL.md"
```

Inspect the skill metadata:

```bash
sed -n '1,12p' "${CODEX_HOME:-$HOME/.codex}/skills/super-review-council/SKILL.md"
```

Check the helper:

```bash
"${CODEX_HOME:-$HOME/.codex}/skills/super-review-council/scripts/autoreview" --help
```

### Repository Layout

```text
.
├── .codex-plugin/plugin.json
├── skills/
│   └── super-review-council/
│       ├── SKILL.md
│       ├── LICENSE
│       ├── NOTICE
│       └── scripts/
│           └── autoreview
├── LICENSE
├── NOTICE
└── README.md
```

`SKILL.md` is the instruction file Codex actually loads. This README is for humans who need installation and project context.

### Compatibility

`scripts/autoreview` remains the helper command name for compatibility with the original implementation and test harness. It is not the public invocation name.

Some helper output may still mention `autoreview`, and some environment variables may still use `AUTOREVIEW_*`. Those are compatibility details. Users should invoke `$super-review-council` or `超级审查会`.

### License And Attribution

This project is MIT licensed.

It is derived from the MIT-licensed `skills/autoreview` skill in `openclaw/agent-skills`. This version preserves the upstream openclaw copyright notice and adds derivative changes by `molang163`.

In plain terms: this is a derivative version of openclaw's original `skills/autoreview`, not a from-scratch rewrite. The original MIT license and copyright notice are preserved. See `NOTICE` and `LICENSE` for details.
