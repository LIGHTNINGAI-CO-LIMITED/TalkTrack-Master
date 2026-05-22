#!/usr/bin/env python3
"""
Check and optionally apply updates for the local talktrack-master skill.

The script reads only the public GitHub repository. It does not use business
API tokens, Obsidian secrets, browser cookies, or Shandian backend credentials.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import ssl
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple


SKILL_NAME = "talktrack-master"
REPO = "LIGHTNINGAI-CO-LIMITED/TalkTrack-Master"
BRANCH = "main"
REMOTE_PREFIX = ""
ALLOWED_ROOTS = ("SKILL.md", "references/", "scripts/", "agents/")
LOCAL_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "TalkTrack-Skill-Update-Check/1.0"
_REMOTE_TREE_CACHE: Optional[List[Dict[str, object]]] = None


class UpdateCheckError(RuntimeError):
    pass


def request_bytes_urllib(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def request_bytes_urllib_certifi(url: str) -> bytes:
    try:
        import certifi  # type: ignore
    except Exception as exc:  # pragma: no cover - optional fallback
        raise RuntimeError(f"certifi_unavailable error={exc}") from exc
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=20, context=context) as response:
        return response.read()


def request_bytes_curl(url: str) -> bytes:
    completed = subprocess.run(
        [
            "curl.exe",
            "-L",
            "--fail",
            "--silent",
            "--show-error",
            "-H",
            "Accept: application/vnd.github+json",
            "-H",
            "Cache-Control: no-cache",
            "-H",
            "Pragma: no-cache",
            url,
        ],
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
        "$wc.Headers.Add('Accept','application/vnd.github+json');"
        "$wc.Headers.Add('Cache-Control','no-cache');"
        "$wc.Headers.Add('Pragma','no-cache');"
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


def request_json(url: str) -> Dict[str, object]:
    return json.loads(request_text(url))


def raw_url_for_ref(path: str, ref: str) -> str:
    return f"https://raw.githubusercontent.com/{REPO}/{ref}/{path}"


def raw_url(path: str) -> str:
    return raw_url_for_ref(path, BRANCH)


def archive_url(ref: str) -> str:
    return f"https://codeload.github.com/{REPO}/zip/{ref}"


def ref_url() -> str:
    return f"https://api.github.com/repos/{REPO}/git/ref/heads/{BRANCH}"


def commit_url(sha: str) -> str:
    return f"https://api.github.com/repos/{REPO}/git/commits/{sha}"


def tree_by_sha_url(sha: str) -> str:
    return f"https://api.github.com/repos/{REPO}/git/trees/{sha}?recursive=1"


def blob_url(sha: str) -> str:
    return f"https://api.github.com/repos/{REPO}/git/blobs/{sha}"


def contents_url(path: str) -> str:
    return f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}"


def tree_url() -> str:
    return f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"


def remote_skill_path() -> str:
    return f"{REMOTE_PREFIX}/SKILL.md" if REMOTE_PREFIX else "SKILL.md"


def remote_head_sha() -> str:
    try:
        completed = subprocess.run(
            [
                "git",
                "ls-remote",
                f"https://github.com/{REPO}.git",
                f"refs/heads/{BRANCH}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=40,
            check=False,
        )
        if completed.returncode == 0:
            first = completed.stdout.strip().split()[0]
            if re.fullmatch(r"[0-9a-fA-F]{40}", first):
                return first
    except Exception:
        pass

    payload = request_json(ref_url())
    obj = payload.get("object")
    if not isinstance(obj, dict):
        raise UpdateCheckError(f"github_ref_missing_object branch={BRANCH}")
    sha = obj.get("sha")
    if not isinstance(sha, str) or not sha:
        raise UpdateCheckError(f"github_ref_missing_sha branch={BRANCH}")
    return sha


def remote_tree_items() -> List[Dict[str, object]]:
    global _REMOTE_TREE_CACHE
    if _REMOTE_TREE_CACHE is not None:
        return _REMOTE_TREE_CACHE

    head_sha = remote_head_sha()
    commit_payload = request_json(commit_url(head_sha))
    tree = commit_payload.get("tree")
    if not isinstance(tree, dict):
        raise UpdateCheckError(f"github_commit_missing_tree sha={head_sha}")
    tree_sha = tree.get("sha")
    if not isinstance(tree_sha, str) or not tree_sha:
        raise UpdateCheckError(f"github_commit_missing_tree_sha sha={head_sha}")

    tree_payload = request_json(tree_by_sha_url(tree_sha))
    items = tree_payload.get("tree")
    if not isinstance(items, list):
        raise UpdateCheckError(f"github_tree_missing_items sha={tree_sha}")
    _REMOTE_TREE_CACHE = [
        item for item in items if isinstance(item, dict)
    ]
    return _REMOTE_TREE_CACHE


def request_blob_bytes(path: str) -> bytes:
    normalized_path = path.replace("\\", "/")
    for item in remote_tree_items():
        if item.get("type") != "blob":
            continue
        if item.get("path") != normalized_path:
            continue
        sha = item.get("sha")
        if not isinstance(sha, str) or not sha:
            raise UpdateCheckError(f"github_blob_missing_sha path={path}")
        payload = request_json(blob_url(sha))
        if payload.get("encoding") != "base64":
            raise UpdateCheckError(
                f"github_blob_unexpected_encoding path={path} "
                f"encoding={payload.get('encoding')}"
            )
        return base64.b64decode((payload.get("content") or "").encode("ascii"))
    raise UpdateCheckError(f"github_blob_missing path={path}")


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
        return request_blob_bytes(path)
    except Exception:
        pass
    try:
        return request_contents_bytes(path)
    except Exception:
        pass
    try:
        return request_bytes(raw_url_for_ref(path, remote_head_sha()))
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
    for item in remote_tree_items():
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


def remote_archive_files(ref: str) -> Iterable[Tuple[str, bytes]]:
    data = request_bytes(archive_url(ref))
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if not names:
            raise UpdateCheckError(f"github_archive_empty ref={ref}")
        top_prefix = names[0].split("/", 1)[0] + "/"
        remote_prefix = f"{REMOTE_PREFIX}/" if REMOTE_PREFIX else ""
        for name in names:
            if name.endswith("/") or not name.startswith(top_prefix):
                continue
            repo_path = name[len(top_prefix):].replace("\\", "/")
            if REMOTE_PREFIX:
                if not repo_path.startswith(remote_prefix):
                    continue
                relative_path = repo_path[len(remote_prefix):]
            else:
                relative_path = repo_path
            if allowed_relative_path(relative_path):
                yield relative_path, archive.read(name)


def apply_update(force: bool = False) -> List[str]:
    status = get_status()
    if status["status"] == "local_newer" and not force:
        raise UpdateCheckError(
            "remote_version_is_older; refusing_to_downgrade_without_--force"
        )

    try:
        file_items = [
            (relative_path, request_remote_file_bytes(remote_path))
            for remote_path, relative_path in remote_files()
        ]
    except Exception:
        file_items = list(remote_archive_files(remote_head_sha()))
    if not file_items:
        raise UpdateCheckError("remote_skill_files_empty")

    updated: List[str] = []
    for relative_path, content in file_items:
        target_path = LOCAL_ROOT / Path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)
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
