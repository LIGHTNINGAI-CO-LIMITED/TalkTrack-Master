#!/usr/bin/env python3
"""
Check and optionally apply updates for the local talktrack-master skill.

The script reads only the public GitHub repository. It does not use business
API tokens, Obsidian secrets, browser cookies, or Shandian backend credentials.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Tuple


SKILL_NAME = "talktrack-master"
REPO = "LIGHTNINGAI-CO-LIMITED/TalkTrack-Master"
BRANCH = "main"
REMOTE_PREFIX = ""
ALLOWED_ROOTS = ("SKILL.md", "references/", "scripts/", "agents/")
LOCAL_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "TalkTrack-Skill-Update-Check/1.0"


class UpdateCheckError(RuntimeError):
    pass


def request_bytes_urllib(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def request_bytes_urllib_certifi(url: str) -> bytes:
    try:
        import certifi  # type: ignore
    except Exception as exc:  # pragma: no cover - optional fallback
        raise RuntimeError(f"certifi_unavailable error={exc}") from exc
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=20, context=context) as response:
        return response.read()


def request_bytes_curl(url: str) -> bytes:
    completed = subprocess.run(
        ["curl.exe", "-L", "--fail", "--silent", "--show-error", url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=40,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", errors="replace").strip())
    return completed.stdout


def request_bytes_powershell(url: str) -> bytes:
    command = (
        "$ProgressPreference='SilentlyContinue';"
        "[Net.ServicePointManager]::SecurityProtocol="
        "[Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13;"
        "$wc=New-Object System.Net.WebClient;"
        "$wc.Headers.Add('User-Agent','TalkTrack-Skill-Update-Check/1.0');"
        "$bytes=$wc.DownloadData($args[0]);"
        "[Console]::Out.Write([Convert]::ToBase64String($bytes))"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command, url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=40,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip())
    return base64.b64decode(completed.stdout.strip())


def request_bytes(url: str) -> bytes:
    channels: List[Tuple[str, Callable[[str], bytes]]] = [
        ("urllib", request_bytes_urllib),
        ("urllib_certifi", request_bytes_urllib_certifi),
        ("curl", request_bytes_curl),
        ("powershell", request_bytes_powershell),
    ]
    errors: List[str] = []
    for name, getter in channels:
        try:
            return getter(url)
        except Exception as exc:  # pragma: no cover - surfaced as a concise CLI error
            errors.append(f"{name}: {exc}")
    raise UpdateCheckError(
        f"all_fetch_channels_failed url={url} errors={' | '.join(errors)}"
    )


def request_text(url: str) -> str:
    return request_bytes(url).decode("utf-8")


def raw_url(path: str) -> str:
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path}"


def contents_url(path: str) -> str:
    return f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}"


def tree_url() -> str:
    return f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"


def remote_skill_path() -> str:
    return f"{REMOTE_PREFIX}/SKILL.md" if REMOTE_PREFIX else "SKILL.md"


def decode_contents_payload(text: str, path: str) -> bytes:
    payload = json.loads(text)
    if payload.get("type") != "file":
        raise UpdateCheckError(f"github_contents_not_file path={path}")
    if payload.get("encoding") != "base64":
        raise UpdateCheckError(
            f"github_contents_unexpected_encoding path={path} "
            f"encoding={payload.get('encoding')}"
        )
    return base64.b64decode((payload.get("content") or "").encode("ascii"))


def request_contents_bytes(path: str) -> bytes:
    return decode_contents_payload(request_text(contents_url(path)), path)


def request_remote_file_bytes(path: str) -> bytes:
    try:
        return request_contents_bytes(path)
    except Exception:
        return request_bytes(raw_url(path))


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
    return parse_frontmatter(request_remote_file_bytes(remote_skill_path()).decode("utf-8"))


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
        target_path.write_bytes(request_remote_file_bytes(remote_path))
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
        try:
            local_version = local_metadata().get("version", "unknown")
        except Exception:
            local_version = "unknown"
        error = {
            "skill": SKILL_NAME,
            "local_version": local_version,
            "remote_version": "unknown",
            "status": "check_failed",
            "error": str(exc),
            "manual_action": (
                "Do not treat this as up-to-date. For backend write/import tasks, "
                "pause and ask the user to update or explicitly accept using the local version."
            ),
        }
        print_result(error, as_json=args.json)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
