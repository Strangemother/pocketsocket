from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

from export import ExportConfig, SiteExportError, export_site, load_config, path_from_config


def git(arguments: list[str], project_root: Path, *, env: dict[str, str] | None = None, capture: bool = False) -> str:
    result = subprocess.run(["git", *arguments], cwd=project_root, env=env, check=True, text=True, stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture and result.stdout else ""


def fetch_branch(remote: str, branch: str, project_root: Path) -> str | None:
    remote_ref = f"refs/remotes/{remote}/{branch}"
    result = subprocess.run(["git", "ls-remote", "--exit-code", "--heads", remote, branch], cwd=project_root, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        return None
    git(["fetch", remote, f"{branch}:{remote_ref}"], project_root)
    return remote_ref


def build_tree(output_root: Path, project_root: Path) -> str:
    with tempfile.NamedTemporaryFile(prefix="flask-to-github-index-", delete=False) as temporary_index:
        index_path = temporary_index.name
    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = index_path
    try:
        git(["read-tree", "--empty"], project_root, env=env)
        git([f"--work-tree={output_root}", "add", "-A", "."], project_root, env=env)
        return git(["write-tree"], project_root, env=env, capture=True)
    finally:
        Path(index_path).unlink(missing_ok=True)


def deploy_site(config: ExportConfig, *, remote: str, branch: str, message: str, dry_run: bool) -> str:
    written = export_site(config)
    print(f"exported {len(written)} files")
    parent_ref = fetch_branch(remote, branch, config.project_root)
    tree = build_tree(config.output_root, config.project_root)
    arguments = ["commit-tree", tree, "-m", message]
    if parent_ref:
        arguments.extend(["-p", parent_ref])
    commit = git(arguments, config.project_root, capture=True)
    if dry_run:
        print(f"would deploy {commit} to {remote}/{branch}")
        return commit
    local_ref = f"refs/heads/{branch}"
    git(["update-ref", local_ref, commit], config.project_root)
    git(["push", remote, f"{local_ref}:{branch}"], config.project_root)
    print(f"deployed {commit} to {remote}/{branch}")
    return commit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export and publish a Flask site.")
    parser.add_argument("config", nargs="?")
    parser.add_argument("--base-url")
    parser.add_argument("--output-dir")
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="gh-pages")
    parser.add_argument("--message", default="Deploy static site")
    parser.add_argument("--dry-run", action="store_true")
    return parser