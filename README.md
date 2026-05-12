# TalkTrack-Master

TalkTrack-Master is a Codex skill for Shandian Intelligent normal-node and jump-node IVR work.

It covers:

- normal nodes, jump nodes, and end nodes
- system TTS readback and regression
- knowledge-base answer system TTS checks
- NLP / knowledge-base matching checks
- large model intent recognition 2.0 checks
- page text-debug layered-recognition regression
- normal-node strategy optimization plans
- redacted Obsidian archival workflows

Use `sd-admin-ivr-config` instead for smart Agent / smart-node Prompt work, `llmNodeModelConfig`, terminal intent rules, and smart-node intent governance.

## Skill Layout

```text
SKILL.md
agents/openai.yaml
references/system-tts-normal-node-v0.1.md
scripts/validate_system_tts_ivr.py
docs/TalkTrack-Master_v0.2_Skill封装说明与同事使用手册_20260512.md
```

## Install Locally

Copy or clone this repository into a Codex skill folder as `talktrack-master`.

Example:

```powershell
git clone https://github.com/Larry220/TalkTrack-Master.git "$env:USERPROFILE\.codex\skills\talktrack-master"
```

If the target folder already exists, back it up or pull updates from inside that folder.

## Safety Rules

- Do not commit access tokens, API keys, passwords, cookies, browser state, raw customer exports, or large artifacts.
- Backend requests use `token: Bearer <TOKEN>`, not `Authorization`.
- Keep tokens in an external secret store or the current process environment only.
- Verify backend writes through readback. A successful API response is not enough.
- Prefer read-only audits unless the user explicitly authorizes backend writes.

## Core Runtime Model

The normal-node recognition chain is:

```text
NLP / intent model / knowledge-base matching first
then large model intent recognition 2.0 as semantic fallback
```

For NLP / knowledge-base matching, keep trigger text short and atomic:

- good: `价格`, `多少钱`, `收费`, `费用`
- poor: `我想了解一下你们这个活动到底怎么收费以及后续有没有额外费用`

Use 2.0 for semantic fallback after first-pass matching misses or cannot satisfy the user reply.

## Model Intent Recognition 2.0

Use the authenticated backend API base for:

```text
POST <authenticated-api-base>/ivr/updateModelIntentRecognitionConfig
```

Important defaults for TalkTrack-Master:

| Field | Default | Meaning |
| --- | --- | --- |
| `modelIntentRecognitionEnabled` | `1` | Enables IVR-level 2.0 |
| `modelId` | `55` | Fixed model id |
| `modelIntentRecognitionTimeoutMilliSecond` | `2000` | Max return time |
| `modelMaxTokens` | `4096` or higher | Do not use `0` when enabled |
| `modelEnableThinking` | `0` | Keep real-time IVR latency stable |
| `modelRecognitionRound` | `0` | Default all-round setting, not an on/off switch |

## Validation

For code changes, at minimum run:

```powershell
python -m py_compile .\scripts\validate_system_tts_ivr.py
```

Before publishing, scan the repository for secrets and generated cache files.

## Documentation

The coworker-facing v0.2 manual is in:

```text
docs/TalkTrack-Master_v0.2_Skill封装说明与同事使用手册_20260512.md
```
