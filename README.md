# Super Review Council / 超级审查会

超级审查会是一个给 Codex 用的重型审查 skill。

它不是让 AI 随便扫一眼代码。它会先把审查目标冻结下来，再让多个 AI 分头检查同一份内容。主 agent 负责合并意见、判断哪些问题真的要修、安排修复和验证。只要修复改动了目标，就会再审一轮。

这个流程比较重，适合放在重要改动、复杂 PR、发布前检查这些场景里用。你也可以在自己不放心的时候调用它，让多个 AI 互相校对，减少一个模型单独判断时的盲区。

English summary: Super Review Council is a heavy multi-agent review workflow for Codex. It coordinates review, triage, fixing, verification, and repeated checks against a frozen target.

## 它会做什么

- 只在你明确要求 `$super-review-council` 或 `超级审查会` 时触发。
- 审查前冻结目标，后面如果出现未批准的变化，会拦下来。
- 把审查、问题归类、修复计划、实施、验证和复审拆成几个阶段。
- 被上层协调器调用时，可以只做有边界的只读子审查。
- helper 执行、联网搜索和隐私边界都会写清楚，避免审查过程自己失控。

## 安装

前提：你需要有支持 plugin 或 skill 的 Codex，以及 `git`。

先克隆仓库：

```bash
git clone https://github.com/molang163/super-review-council.git
cd super-review-council
```

作为本地 skill 安装：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/super-review-council "${CODEX_HOME:-$HOME/.codex}/skills/"
```

如果你没有设置 `CODEX_HOME`，复制后的目录通常会在：

```text
~/.codex/skills/super-review-council
```

如果你的 Codex 版本支持 plugin 安装，也可以从这个本地 checkout 或 GitHub 仓库安装为 Codex plugin。安装后如果 Codex 已经加载过 skill 列表，需要重启或重新加载。

## 使用

安装完成后，明确调用它：

```text
$super-review-council
```

也可以直接用中文说：

```text
超级审查会
```

建议在这些时候用：

- 准备合并一个复杂 PR。
- 发布前想做最后一轮严格检查。
- 改动跨了多个模块，你担心普通 review 漏掉上下文。
- 你希望多个 AI 分别审一遍，再由主 agent 统一裁决。

## 兼容说明

`scripts/autoreview` 仍然保留为 helper 命令名。这是为了兼容原始实现和测试工具，不是公开调用名。

有些 helper 输出里仍可能出现 `autoreview`，部分环境变量也可能继续使用 `AUTOREVIEW_*`。这些都是兼容细节。对用户来说，应该调用的是 `$super-review-council` 或 `超级审查会`。

## 许可证和来源

本项目使用 MIT 许可证。

它派生自 `openclaw/agent-skills` 里的 MIT 许可 `skills/autoreview` skill。这个版本保留了上游 openclaw 的版权声明，并加入了 `molang163` 的派生修改。

中文说法：这是基于 openclaw 原版 `skills/autoreview` 改出来的版本，不是从零原创。发布时保留了原 MIT 许可证和版权声明。细节见 `NOTICE` 和 `LICENSE`。
