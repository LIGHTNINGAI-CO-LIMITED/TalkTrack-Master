#!/usr/bin/env python3
"""
Check and optionally apply updates for the local talktrack-master skill.

The script reads only the public GitHub repository. It does not use business
API tokens, Obsidian secrets, browser cookies, or Shandian backend credentials.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


SKILL_NAME = "talktrack-master"
REPO = "LIGHTNINGAI-CO-LIMITED/TalkTrack-Master"
BRANCH = "main"
REMOTE_PREFIX = ""
ALLOWED_ROOTS = ("SKILL.md", "references/", "scripts/", "agents/")
LOCAL_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "TalkTrack-Skill-Update-Check/1.0"


class UpdateCheckError(RuntimeError):
    pass


def request_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read()
    except Exception as exc:  # pragma: no cover - surfaced as a concise CLI error
        raise UpdateCheckError(f"request_failed url={url} error={exc}") from exc


def request_text(url: str) -> str:
    return request_bytes(url).decode("utf-8")


def raw_url(path: str) -> str:
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path}"


def tree_url() -> str:
    return f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"


def remote_skill_path() -> str:
    return f"{REMOTE_PREFIX}/SKILL.md" if REMOTE_PREFIX else "SKILL.md"


def parse_frontmatter(text: str) -> Dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    metadata: Dict[str, str] = {}
    for raw_line in text[3:end].splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata


def parse_version(value: str) -> Tuple[int, ...]:
    numbers = re.findall(r"\d+", value or "")
    return tuple(int(number) for number in numbers)


def compare_versions(local_version: str, remote_version: str) -> str:
    local_tuple = parse_version(local_version)
    remote_tuple = parse_version(remote_version)
    if not local_tuple or not remote_tuple:
        return "unknown"
    if remote_tuple > local_tuple:
        return "update_available"
    if remote_tuple < local_tuple:
        return "local_newer"
    return "up_to_date"


def local_metadata() -> Dict[str, str]:
    skill_path = LOCAL_ROOT / "SKILL.md"
    if not skill_path.exists():
        raise UpdateCheckError(f"local_skill_missing path={skill_path}")
    return parse_frontmatter(skill_path.read_text(encoding="utf-8"))


def remote_metadata() -> Dict[str, str]:
    return parse_frontmatter(request_text(raw_url(remote_skill_path())))


def get_status() -> Dict[str, str]:
    local_meta = local_metadata()
    remote_meta = remote_metadata()
    local_version = local_meta.get("version", "unknown")
    remote_version = remote_meta.get("version", "unknown")
    status = compare_versions(local_version, remote_version)
    return {
        "skill": SKILL_NAME,
        "local_version": local_version,
        "remote_version": remote_version,
        "status": status,
        "repo": REPO,
        "branch": BRANCH,
        "local_path": str(LOCAL_ROOT),
    }


def allowed_relative_path(relative_path: str) -> bool:
    if relative_path.endswith(".pyc") or "__pycache__/" in relative_path:
        return False
    return any(
        relative_path == root or relative_path.startswith(root)
        for root in ALLOWED_ROOTS
    )


def remote_files() -> Iterable[Tuple[str, str]]:
    payload = json.loads(request_text(tree_url()))
    for item in payload.get("tree", []):
        if item.get("type") != "blob":
            continue
        remote_path = item.get("path", "")
        if REMOTE_PREFIX:
            prefix = f"{REMOTE_PREFIX}/"
            if not remote_path.startswith(prefix):
                continue
            relative_path = remote_path[len(prefix):]
        else:
            relative_path = remote_path
        relative_path = relative_path.replace("\\", "/")
        if allowed_relative_path(relative_path):
            yield remote_path, relative_path


def apply_update(force: bool = False) -> List[str]:
    status = get_status()
    if status["status"] == "local_newer" and not force:
        raise UpdateCheckError(
            "remote_version_is_older; refusing_to_downgrade_without_--force"
        )

    updated: List[str] = []
    for remote_path, relative_path in remote_files():
        target_path = LOCAL_ROOT / Path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(request_bytes(raw_url(remote_path)))
        updated.append(relative_path)
    return sorted(updated)


def print_result(result: Dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    for key, value in result.items():
        if isinstance(value, list):
            print(f"{key}={len(value)}")
            for item in value:
                print(f"- {item}")
        else:
            print(f"{key}={value}")


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check remote version")
    parser.add_argument("--apply", action="store_true", help="apply files from GitHub")
    parser.add_argument("--force", action="store_true", help="allow applying older remote files")
    parser.add_argument("--json", action="store_true", help="print JSON output")
    args = parser.parse_args(argv)

    if not args.check and not args.apply:
        args.check = True

    try:
        result: Dict[str, object] = get_status()
        if args.apply:
            result["updated_files"] = apply_update(force=args.force)
            result["post_apply_status"] = get_status()
        print_result(result, as_json=args.json)
        return 0
    except UpdateCheckError as exc:
        error = {"skill": SKILL_NAME, "status": "check_failed", "error": str(exc)}
        print_result(error, as_json=args.json)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
