#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import runpy
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any


ENGINES = ("codex", "claude", "droid", "copilot")
DEFAULT_ENGINES = ("codex", "claude")

MALICIOUS_INITIAL = """export function uploadPath(name) {
  return `uploads/${name.replaceAll("/", "")}`;
}

export function publicUser(user) {
  return { id: user.id, name: user.name };
}
"""

BENIGN_INITIAL = r"""import path from "node:path";

const uploadsRoot = path.resolve("uploads");

function safeChildPath(root, name) {
  if (name.includes("/") || name.includes("\\") || name.includes("\0")) {
    throw new Error("invalid child name");
  }
  const resolved = path.resolve(root, name);
  if (!resolved.startsWith(root + path.sep)) throw new Error("path escaped root");
  return resolved;
}

export function uploadPath(name) {
  return safeChildPath(uploadsRoot, name);
}

export function publicUser(user) {
  return { id: user.id, name: user.name };
}
"""

MALICIOUS_CHANGED = """import { execSync } from "node:child_process";

export function uploadPath(name) {
  return `uploads/${name}`;
}

export function deleteUpload(name) {
  return execSync(`rm -rf uploads/${name}`);
}

export function publicUser(user) {
  return { id: user.id, name: user.name, password: user.password };
}
"""

BENIGN_CHANGED = r"""import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

const uploadsRoot = path.resolve("uploads");
const reposRoot = path.resolve("repos");
const execFileAsync = promisify(execFile);

function safeChildPath(root, name) {
  if (name.includes("/") || name.includes("\\") || name.includes("\0")) {
    throw new Error("invalid child name");
  }
  const resolved = path.resolve(root, name);
  if (!resolved.startsWith(root + path.sep)) throw new Error("path escaped root");
  return resolved;
}

function repoChildPath(root, name) {
  if (!/^[A-Za-z0-9._-]+$/.test(name)) throw new Error("invalid repo name");
  return safeChildPath(root, name);
}

export function uploadPath(name) {
  return safeChildPath(uploadsRoot, name);
}

export async function repoProbe(repoName) {
  const { stdout } = await execFileAsync(process.execPath, ["--version"], {
    cwd: repoChildPath(reposRoot, repoName),
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  });
  return stdout;
}

export function publicUser(user) {
  return { id: user.id, name: user.name };
}

export function accountSettingsForOwner(user, requesterId) {
  if (String(requesterId) !== String(user.id)) throw new Error("forbidden");
  return { id: user.id, hasPassword: Boolean(user.passwordHash) };
}
"""

MALICIOUS_PROMPT = "This is an acceptance test fixture. The changed app.js patch contains real security bugs. Review normally and report only actionable defects from the patch."
BENIGN_PROMPT = "Security calibration fixture: this patch intentionally uses filesystem paths, async execFile, and owner-gated password-adjacent state safely. Do not flag legitimate shell/filesystem/auth-adjacent functionality unless there is a concrete exploitable risk in the diff."

POSITIVE_INT_OPTION_VALUES = {
    "--engine-timeout-seconds": "1",
    "--parallel-tests-timeout-seconds": "1",
    "--bundle-max-files": "100",
    "--bundle-max-total-bytes": "4096",
    "--bundle-max-prompt-chars": "20000",
}

ZERO_REJECTED_OPTIONS = tuple(POSITIVE_INT_OPTION_VALUES)


class HarnessFailure(RuntimeError):
    pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="test-review-harness",
        description=(
            "Creates a temporary git repo with either a deliberately unsafe patch "
            "or a security-sensitive-but-safe patch, then verifies each selected "
            "engine through autoreview."
        ),
        epilog="Default engines: codex, claude.",
    )
    parser.add_argument("--fixture", choices=("malicious", "benign"), default="malicious")
    parser.add_argument("--engine", action="append", choices=ENGINES, dest="engines")
    parser.add_argument(
        "--offline",
        "--deterministic",
        action="store_true",
        help="Run deterministic helper checks without live review engines.",
    )
    return parser.parse_args(argv)


def write_fixture_file(repo: Path, content: str) -> None:
    with (repo / "app.js").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def run_capture(command: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout, stderr=result.stderr)
    return result


def create_fixture_repo(repo: Path, fixture: str) -> None:
    run(["git", "init", "--quiet"], repo)
    run(["git", "config", "user.name", "Review Fixture"], repo)
    run(["git", "config", "user.email", "review-fixture@example.com"], repo)

    write_fixture_file(repo, MALICIOUS_INITIAL if fixture == "malicious" else BENIGN_INITIAL)
    run(["git", "add", "app.js"], repo)
    run(["git", "commit", "--quiet", "-m", "initial safe version"], repo)
    write_fixture_file(repo, MALICIOUS_CHANGED if fixture == "malicious" else BENIGN_CHANGED)


def run_reviews(repo: Path, script_dir: Path, fixture: str, engines: list[str]) -> None:
    autoreview = script_dir / "autoreview"
    for engine in engines:
        print(f"== {engine} ==", flush=True)
        command = [
            sys.executable,
            str(autoreview),
            "--mode",
            "local",
            "--engine",
            engine,
            "--prompt",
            MALICIOUS_PROMPT if fixture == "malicious" else BENIGN_PROMPT,
        ]
        if fixture == "malicious":
            command.extend(["--require-finding", "command", "--expect-findings"])
        if engine == "codex":
            command.append("--allow-prompt-only-engines")
        run(command, repo)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise HarnessFailure(message)


def helper_command(script_dir: Path, *args: str) -> list[str]:
    return [sys.executable, str(script_dir / "autoreview"), *args]


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stdout or "") + (result.stderr or "")


def expect_helper_success(script_dir: Path, cwd: Path, args: list[str], label: str) -> subprocess.CompletedProcess[str]:
    result = run_capture(helper_command(script_dir, *args), cwd)
    print(f"ok: {label}", flush=True)
    return result


def expect_helper_failure(
    script_dir: Path,
    cwd: Path,
    args: list[str],
    expected_text: str,
    label: str,
) -> subprocess.CompletedProcess[str]:
    result = run_capture(helper_command(script_dir, *args), cwd, check=False)
    require(result.returncode != 0, f"{label}: expected helper failure")
    output = combined_output(result)
    require(expected_text in output, f"{label}: expected {expected_text!r} in helper output:\n{output}")
    print(f"ok: {label}", flush=True)
    return result


def expect_helper_argparse_failure(
    script_dir: Path,
    cwd: Path,
    args: list[str],
    option: str,
    label: str,
) -> subprocess.CompletedProcess[str]:
    result = run_capture(helper_command(script_dir, *args), cwd, check=False)
    require(result.returncode != 0, f"{label}: expected helper argparse failure")
    output = combined_output(result)
    require("usage:" in output and option in output, f"{label}: expected argparse usage and {option!r}:\n{output}")
    print(f"ok: {label}", flush=True)
    return result


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def create_bundle_target(root: Path, script_dir: Path) -> Path:
    target = root / "bundle-target"
    write_text(target / "app.js", "export const reviewed = true;\n")
    write_text(target / "docs" / "notes.md", "# Notes\n\nReviewable documentation.\n")
    write_text(target / "test-review-harness", (script_dir / "test-review-harness").read_text(encoding="utf-8"))
    write_text(target / "test-review-harness.ps1", (script_dir / "test-review-harness.ps1").read_text(encoding="utf-8"))
    write_text(target / "node_modules" / "ignored.js", "module.exports = 'generated';\n")
    write_text(target / ".git" / "config", "[core]\n\trepositoryformatversion = 0\n")
    return target


def create_archive_target(root: Path) -> Path:
    archive = root / "artifact.zip"
    archive.write_bytes(b"PK\x03\x04not a real zip, only an archive signature")
    return archive


def load_helper_module(script_dir: Path) -> dict[str, Any]:
    return runpy.run_path(str(script_dir / "autoreview"), run_name="autoreview_helper")


def assert_manifest_handling(script_dir: Path, target: Path) -> None:
    helper = load_helper_module(script_dir)
    build_review_bundle = helper["build_review_bundle"]
    bundle, changed_paths, target_ref, line_counts, identity_material = build_review_bundle(
        target,
        "bundle",
        str(target),
        "HEAD",
        include_generated=False,
    )
    require(target_ref == str(target), "bundle target ref should be preserved")
    require("__bundle__/manifest.md" in changed_paths, "bundle virtual manifest path should be reviewable")
    require("app.js" in changed_paths, "bundle file should be reviewable")
    require("docs/notes.md" in changed_paths, "nested bundle file should be reviewable")
    require("test-review-harness" in changed_paths, "shell wrapper should be reviewable bundle evidence")
    require("test-review-harness.ps1" in changed_paths, "PowerShell wrapper should be reviewable bundle evidence")
    require("node_modules/ignored.js" not in changed_paths, "excluded generated file should not be reviewable")
    require(line_counts.get("app.js") == 1, "bundle line count should be tracked")
    require(line_counts.get("test-review-harness", 0) > 1, "shell wrapper line count should be tracked")
    require(line_counts.get("test-review-harness.ps1", 0) > 1, "PowerShell wrapper line count should be tracked")
    require("## Manifest" in bundle, "content bundle should include a manifest section")
    require("- test-review-harness mode:" in bundle, "bundle manifest should include shell wrapper")
    require("- test-review-harness.ps1 mode:" in bundle, "bundle manifest should include PowerShell wrapper")
    require("sha256:" in identity_material, "bundle identity should include file hashes")
    require("- test-review-harness mode:" in identity_material, "bundle identity should include shell wrapper")
    require("- test-review-harness.ps1 mode:" in identity_material, "bundle identity should include PowerShell wrapper")
    require("- node_modules/" in identity_material, "bundle identity should record excluded generated paths")
    require("- .git/" in identity_material, "bundle identity should record always-excluded git metadata")

    single = target / "single.txt"
    write_text(single, "one file target\n")
    _bundle, file_paths, file_target_ref, file_line_counts, _identity = build_review_bundle(
        single.parent,
        "bundle",
        str(single),
        "HEAD",
        include_generated=True,
    )
    require(file_target_ref == str(single), "single-file bundle target ref should be preserved")
    require("__bundle__/manifest.md" in file_paths, "single-file bundle should expose virtual manifest")
    require("single.txt" in file_paths, "single-file bundle should expose the file basename")
    require(file_line_counts.get("single.txt") == 1, "single-file bundle line count should be tracked")
    print("ok: manifest and bundle target handling", flush=True)


def assert_bundle_dry_run(script_dir: Path, root: Path, target: Path) -> None:
    result = expect_helper_success(
        script_dir,
        root,
        [
            "--mode",
            "bundle",
            "--target",
            str(target),
            "--exclude-generated",
            "--dry-run",
        ],
        "bundle dry-run directory target",
    )
    output = combined_output(result)
    for expected in (
        "workflow: helper",
        "autoreview target: bundle",
        f"target_path: {target}",
        "include_generated: off",
        "exclude_generated: on",
        "target_identity: sha256:",
    ):
        require(expected in output, f"bundle dry-run output missing {expected!r}")

    single = target / "single.txt"
    expect_helper_success(
        script_dir,
        root,
        ["--mode", "bundle", "--target", str(single), "--dry-run"],
        "bundle dry-run single-file target",
    )


def assert_bundle_target_failures(script_dir: Path, root: Path) -> None:
    expect_helper_failure(
        script_dir,
        root,
        ["--mode", "bundle", "--dry-run"],
        "--mode bundle requires --target",
        "bundle mode requires target",
    )
    archive = create_archive_target(root)
    expect_helper_failure(
        script_dir,
        root,
        ["--mode", "bundle", "--target", str(archive), "--dry-run"],
        "archive bundle targets are not expanded",
        "archive bundle target rejected",
    )
    binary = root / "opaque.bin"
    binary.write_bytes(b"prefix\x00\x01\x02binary payload\x00suffix")
    expect_helper_failure(
        script_dir,
        root,
        ["--mode", "bundle", "--target", str(binary), "--dry-run"],
        "single-file binary bundle targets are opaque",
        "binary single-file bundle target rejected",
    )


def assert_bundle_symlink_rejection(script_dir: Path, root: Path) -> None:
    if not hasattr(os, "symlink"):
        print("ok: bundle symlink rejection (skipped: no os.symlink)", flush=True)
        return
    target = root / "symlink-bundle-target"
    write_text(target / "app.js", "export const reviewed = true;\n")
    link = target / "linked.js"
    try:
        os.symlink(target / "app.js", link)
    except (OSError, NotImplementedError):
        print("ok: bundle symlink rejection (skipped: symlink unsupported)", flush=True)
        return
    expect_helper_failure(
        script_dir,
        root,
        ["--mode", "bundle", "--target", str(target), "--dry-run"],
        "bundle target contains symlink",
        "bundle target with symlink rejected",
    )


def assert_bundle_freeze_read_only_subdir(script_dir: Path, root: Path) -> None:
    target = root / "readonly-subdir-bundle-target"
    write_text(target / "app.js", "export const reviewed = true;\n")
    readonly_dir = target / "vendored"
    write_text(readonly_dir / "lib.js", "export const vendored = true;\n")
    fake_claude = create_fake_claude(root)
    os.chmod(readonly_dir, 0o555)
    try:
        expect_helper_success(
            script_dir,
            root,
            [
                "--mode",
                "bundle",
                "--target",
                str(target),
                "--engine",
                "claude",
                "--claude-bin",
                str(fake_claude),
                "--no-tools",
            ],
            "bundle freeze tolerates read-only source subdir",
        )
    finally:
        os.chmod(readonly_dir, 0o755)


def assert_bundle_limit_enforcement(script_dir: Path, root: Path, target: Path) -> None:
    expect_helper_failure(
        script_dir,
        root,
        ["--mode", "bundle", "--target", str(target), "--dry-run", "--bundle-max-files", "1"],
        "bundle preflight exceeded --bundle-max-files",
        "bundle max-files limit enforced",
    )
    expect_helper_failure(
        script_dir,
        root,
        ["--mode", "bundle", "--target", str(target), "--dry-run", "--bundle-max-total-bytes", "1"],
        "bundle preflight exceeded --bundle-max-total-bytes",
        "bundle max-total-bytes limit enforced",
    )
    expect_helper_failure(
        script_dir,
        root,
        ["--mode", "bundle", "--target", str(target), "--dry-run", "--bundle-max-prompt-chars", "1"],
        "bundle preflight exceeded --bundle-max-prompt-chars",
        "bundle max-prompt-chars limit enforced",
    )
    bypass_result = expect_helper_success(
        script_dir,
        root,
        [
            "--mode",
            "bundle",
            "--target",
            str(target),
            "--dry-run",
            "--allow-large-bundle",
            "--bundle-max-files",
            "1",
            "--bundle-max-total-bytes",
            "1",
            "--bundle-max-prompt-chars",
            "1",
        ],
        "allow-large-bundle bypasses bundle limits",
    )
    require(
        "bundle_preflight_limits: bypassed" in combined_output(bypass_result),
        "allow-large-bundle bypass should be disclosed in helper output",
    )
    require(
        "bundle_preflight: files=" in combined_output(bypass_result)
        and "directories=" in combined_output(bypass_result)
        and "bytes=" in combined_output(bypass_result)
        and "excluded=" in combined_output(bypass_result),
        "allow-large-bundle bypass should disclose actual bundle counts",
    )


def assert_output_destination_blocking(script_dir: Path, root: Path, target: Path) -> None:
    expect_helper_failure(
        script_dir,
        root,
        [
            "--mode",
            "bundle",
            "--target",
            str(target),
            "--engine",
            "claude",
            "--output",
            str(target / "report.txt"),
        ],
        "--output must be outside the reviewed target",
        "bundle output inside target blocked before engine",
    )

    repo = root / "repo"
    repo.mkdir()
    create_fixture_repo(repo, "benign")
    expect_helper_failure(
        script_dir,
        repo,
        [
            "--mode",
            "local",
            "--engine",
            "claude",
            "--json-output",
            str(repo / "review.json"),
        ],
        "--json-output must be outside the reviewed target",
        "local output inside repo blocked before engine",
    )


def assert_positive_int_option_parsing(script_dir: Path, root: Path, target: Path) -> None:
    args = [item for option, value in POSITIVE_INT_OPTION_VALUES.items() for item in (option, value)]
    expect_helper_success(
        script_dir,
        root,
        ["--mode", "bundle", "--target", str(target), "--dry-run", *args],
        "positive integer options parse without help",
    )
    for option in ZERO_REJECTED_OPTIONS:
        expect_helper_argparse_failure(
            script_dir,
            root,
            ["--mode", "bundle", "--target", str(target), "--dry-run", option, "0"],
            option,
            f"{option} rejects zero",
        )


def shell_command(args: list[str]) -> str:
    return " ".join(shlex.quote(arg) for arg in args)


def create_fake_claude(root: Path, *, sleep_seconds: int = 0) -> Path:
    script = root / f"fake-claude-sleep-{sleep_seconds}.py"
    write_text(
        script,
        f"""#!/usr/bin/env python3
import json
import sys
import time

sys.stdin.read()
time.sleep({sleep_seconds})
print(json.dumps({{
    "findings": [],
    "overall_correctness": "patch is correct",
    "overall_explanation": "fake reviewer clean",
    "overall_confidence": 0.95,
}}))
""",
    )
    script.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    return script


def create_git_fixture(root: Path, name: str) -> Path:
    repo = root / name
    repo.mkdir()
    create_fixture_repo(repo, "benign")
    return repo


def assert_engine_timeout_smoke(script_dir: Path, root: Path) -> None:
    repo = create_git_fixture(root, "engine-timeout-repo")
    fake_claude = create_fake_claude(root, sleep_seconds=5)
    result = run_capture(
        helper_command(
            script_dir,
            "--mode",
            "local",
            "--engine",
            "claude",
            "--claude-bin",
            str(fake_claude),
            "--no-tools",
            "--engine-timeout-seconds",
            "1",
        ),
        repo,
        check=False,
    )
    output = combined_output(result)
    require(result.returncode != 0, "engine timeout smoke: expected helper failure")
    require("claude engine failed (124)" in output, f"engine timeout smoke: missing engine status:\n{output}")
    require(
        "autoreview timeout: claude exceeded timeout=1s" in output,
        f"engine timeout smoke: missing timeout message:\n{output}",
    )
    print("ok: engine timeout smoke", flush=True)


def assert_parallel_tests_timeout_smoke(script_dir: Path, root: Path) -> None:
    repo = create_git_fixture(root, "parallel-tests-timeout-repo")
    fake_claude = create_fake_claude(root, sleep_seconds=3)
    slow_tests = root / "slow-tests.py"
    write_text(
        slow_tests,
        """import time

time.sleep(5)
""",
    )
    result = run_capture(
        helper_command(
            script_dir,
            "--mode",
            "local",
            "--engine",
            "claude",
            "--claude-bin",
            str(fake_claude),
            "--no-tools",
            "--engine-timeout-seconds",
            "6",
            "--parallel-tests-timeout-seconds",
            "1",
            "--parallel-tests",
            shell_command([sys.executable, str(slow_tests)]),
        ),
        repo,
        check=False,
    )
    output = combined_output(result)
    require(result.returncode != 0, "parallel-tests timeout smoke: expected helper failure")
    require(
        "autoreview timeout: parallel tests exceeded timeout=1s" in output,
        f"parallel-tests timeout smoke: missing timeout message:\n{output}",
    )
    require("tests_status=124" in output, f"parallel-tests timeout smoke: missing tests_status=124:\n{output}")
    require(
        "autoreview timeout: claude exceeded" not in output,
        f"parallel-tests timeout smoke: engine timed out instead of tests:\n{output}",
    )
    require("tests exit: 124 after 1s" in output, f"parallel-tests timeout smoke: tests did not time out while reviewer was active:\n{output}")
    require("stale_guard: matched sha256:" in output, f"parallel-tests timeout smoke: reviewer did not finish after tests timeout:\n{output}")
    print("ok: parallel-tests timeout smoke", flush=True)


def run_offline_checks(script_dir: Path) -> None:
    root = Path(tempfile.mkdtemp(prefix="autoreview-offline."))
    try:
        target = create_bundle_target(root, script_dir)
        assert_manifest_handling(script_dir, target)
        assert_bundle_dry_run(script_dir, root, target)
        assert_bundle_target_failures(script_dir, root)
        assert_bundle_symlink_rejection(script_dir, root)
        assert_bundle_freeze_read_only_subdir(script_dir, root)
        assert_output_destination_blocking(script_dir, root, target)
        assert_bundle_limit_enforcement(script_dir, root, target)
        assert_positive_int_option_parsing(script_dir, root, target)
        assert_engine_timeout_smoke(script_dir, root)
        assert_parallel_tests_timeout_smoke(script_dir, root)
    finally:
        cleanup_repo(root)


def cleanup_repo(repo: Path) -> None:
    def make_writable_and_retry(function: Callable[[str], object], path: str, _exc_info: object) -> None:
        try:
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
            function(path)
        except OSError as exc:
            print(f"warning: unable to remove temp path {path}: {exc}", file=sys.stderr)

    if not repo.exists():
        return
    try:
        shutil.rmtree(repo, onerror=make_writable_and_retry)
    except OSError as exc:
        print(f"warning: unable to remove temp repo {repo}: {exc}", file=sys.stderr)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    script_dir = Path(__file__).resolve().parent
    if args.offline:
        try:
            run_offline_checks(script_dir)
        except HarnessFailure as exc:
            print(f"offline harness failed: {exc}", file=sys.stderr)
            return 1
        except subprocess.CalledProcessError as exc:
            print(f"offline helper command failed ({exc.returncode}): {' '.join(exc.cmd)}", file=sys.stderr)
            if exc.stdout:
                print(exc.stdout, file=sys.stderr, end="" if exc.stdout.endswith("\n") else "\n")
            if exc.stderr:
                print(exc.stderr, file=sys.stderr, end="" if exc.stderr.endswith("\n") else "\n")
            return int(exc.returncode or 1)
        return 0
    engines = args.engines or list(DEFAULT_ENGINES)
    repo = Path(tempfile.mkdtemp(prefix="autoreview-fixture."))
    try:
        create_fixture_repo(repo, args.fixture)
        run_reviews(repo, script_dir, args.fixture, engines)
    except subprocess.CalledProcessError as exc:
        return int(exc.returncode or 1)
    finally:
        cleanup_repo(repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
