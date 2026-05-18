---
name: talktrack-master
version: v0.4.0
github_repo: LIGHTNINGAI-CO-LIMITED/TalkTrack-Master
github_path: "."
github_branch: main
description: Use when configuring, creating, updating, validating, or packaging Shandian Intelligent normal-node and jump-node IVR scenes in the admin backend, especially tasks involving 普通节点, 跳转节点, 结束节点, 系统 TTS, recordType=2, ttsPlaybackList, ttsPlaybackListJson, 知识库答案, NLP 匹配知识库, 大模型意图分析 2.0, /ivr/findSceneList/{ivrId}, readback reports, and Obsidian archival. Do not use for 智能Agent/智能节点 Prompt or llmNodeModelConfig work; use talktrack-agent for those.
---

# TalkTrack-Master

Use this skill for Shandian Intelligent normal-node and jump-node IVR configuration. The v0.2 path supports new-test-IVR creation, readback-only audits, system TTS checks, mandatory NLP knowledge-base matching, mandatory large model intent recognition 2.0, page text-debug layered-recognition regression, and strategy optimization plans, then proves the result through API readback, page spot checks, redacted reports, and Obsidian archival.

## Skill Update Check

At the start of any task using this skill, run the bundled update check:

```powershell
python "C:\Users\luona\.codex\skills\talktrack-master\scripts\check_skill_update.py" --check
```

If the result is `update_available`, tell the user the local version and GitHub version, then recommend updating before continuing. Do not update automatically. Only when the user confirms, run:

```powershell
python "C:\Users\luona\.codex\skills\talktrack-master\scripts\check_skill_update.py" --apply
```

If the check fails because GitHub or the network is unavailable, mention the failed check briefly and continue with the current local skill. The update check must not use, print, store, or request business API tokens; it only reads the public GitHub skill repository.

## Boundary

- Use `talktrack-master` for normal nodes, jump nodes, end nodes, system TTS, knowledge-base answers, node-level NLP knowledge-base matching, IVR-level Advanced Settings large model intent recognition 2.0, routed-node model intent configuration, and readback validation.
- Use `talktrack-agent` for smart Agent nodes, smart-node Prompt import, `llmNodeModelConfig`, terminal intent rules, and intent-label governance.
- Do not mix the two skills unless the user explicitly asks for a workflow crossing both surfaces.

## Non-Negotiables

- Do not print, store, screenshot, or archive real tokens, passwords, cookies, or browser login state.
- Use request header `token: Bearer <TOKEN>`, not `Authorization`.
- Verify token first with `GET https://ai.sd6g.com:1904/api/web/account/findInfo`; continue only when `code=0`.
- Prefer a new test IVR. Modify production IVRs only with explicit user authorization and a pre-write snapshot.
- For write operations, verify through backend readback. A successful write response is not enough.
- For normal-node and jump-node talktrack work, NLP knowledge-base matching is mandatory for normal nodes that can route on user replies. Each such node must read back with `matchKnowledgeBaseEnabled=1`, `knowledgeBaseMatchType=2`, `knowledgeBaseMatchList` containing all current IVR knowledge-base IDs, `notMatchedKnowledgeBaseList=[]`, and a `-2` knowledge-base intent in backend `sceneList`, frontend `sceneListFrontend.nodeList`, and graph `customData`.
- Treat NLP and knowledge-base matching as the first-pass regex/short-trigger layer. Keep KB questions, keywords, and node intent labels short, atomic, and easy to match; put long natural-language explanations in KB answers or the 2.0 prompt, not in regex-like trigger text.
- For normal-node and jump-node talktrack work, Advanced Settings large model intent recognition 2.0 is mandatory. Configure the IVR-level switch with `POST <authenticated-api-base>/ivr/updateModelIntentRecognitionConfig`; the payload `id` must equal the IVR ID, `modelIntentRecognitionEnabled=1`, `modelIntentRecognitionTimeoutMilliSecond=2000`, `modelId=55`, `modelMaxTokens>=4096`, and `modelRecognitionRound=0`. With the current `testtoken`, the verified API base is `https://ai.sd6g.com:1904/api/web`; the `https://aicc-test.sd6g.com/api/web` host requires a token valid for that host.
- Runtime order matters: the system attempts NLP and intent-model matching first; large model intent recognition 2.0 is a semantic fallback for cases NLP cannot match or satisfy. Do not design long NLP triggers and expect 2.0 to compensate for poor first-pass matching.
- For routed normal nodes, keep the node-level 2.0 execution fields consistent as well: every normal node that can route on user replies must read back with `modelIntentRecognitionEnabled=1` and a non-empty `modelIntentRecognitionConfig` in backend `sceneList`, frontend `sceneListFrontend.nodeList`, and graph `customData`. These node fields do not replace the IVR-level Advanced Settings API call.
- On Windows, avoid Windows PowerShell 5 inline Chinese JSON for write calls; use Python `requests` or UTF-8 files.
- Archive final docs, summaries, prompts, SOPs, and reports to `D:\ObsidianVault\闪电智能知识库`, not the repo root.

## v0.1 Workflow

1. Run the Skill Update Check. If a newer GitHub version exists, recommend updating and wait for the user's confirmation before applying it.
2. Read the current task and classify the target: normal node, jump node, end node, knowledge-base answer, or readback-only.
3. If the task involves backend writes, validate token with `/account/findInfo`.
4. Snapshot the target IVR with `/ivr/findSceneList/{ivrId}` before changing it.
5. For system TTS, use `recordType=2`:
   - normal nodes use non-empty `ttsPlaybackList`
   - knowledge-base answers use non-empty `ttsPlaybackListJson`
   - expected audio paths look like `tts/YYYY-MM-DD/*.wav`
6. For jump nodes, keep target node IDs, ports, backend `sceneList`, frontend `sceneListFrontend`, and graph custom data consistent.
7. Generate TTS with `/ivr/createNodeTextTtsRecord`, poll `/ivr/queryTtsRecord`, then write back returned `recordFilePath`.
8. Enable NLP knowledge-base matching on every normal node that handles user replies. Bind all current IVR knowledge-base IDs explicitly with `knowledgeBaseMatchType=2`, and add the `-2` knowledge-base intent when missing.
9. Review NLP trigger quality: prefer short, synonym-friendly keywords / regex phrases for knowledge-base matching and node intents. Long customer-style sentences belong in answers or the 2.0 prompt.
10. Enable Advanced Settings large model intent recognition 2.0 with `POST <authenticated-api-base>/ivr/updateModelIntentRecognitionConfig`. Use the target IVR ID as `id`, set `modelIntentRecognitionEnabled=1`, use the approved scene-specific `modelPrompt` and `modelResultFormat`, keep `modelId=55`, timeout `2000`, `modelMaxTokens>=4096`, and `modelRecognitionRound=0`.
11. Enable or preserve node-level large model intent recognition 2.0 on every normal node that handles user replies. Preserve existing valid node configs; create a node-level `modelIntentRecognitionConfig` from the approved template when it is missing.
12. Read back with `/ivr/findSceneList/{ivrId}` plus knowledge-base list/detail endpoints when answers are touched. For knowledge-base matching and node-level 2.0, validate backend nodes, frontend node copies, and graph `customData`; for Advanced Settings 2.0, validate the IVR-level fields and page echo.
13. When a page check is needed, inspect `/script-graph?ivrId=<ivrId>`. Current system TTS UI evidence is `试听` / `重新合成`; current NLP UI evidence is checked `匹配知识库` with explicit selected knowledge bases; current 2.0 UI evidence is checked `大模型意图分析2.0`.
14. Write redacted reports and indexes to the Obsidian vault, then run `obsidian 'vault=闪电智能知识库' unresolved total`.

## v0.2 Task Modes

- New build: create a new test IVR from source material, write normal/jump/end nodes, system TTS, representative KB answers, NLP matching, and 2.0, then report.
- Readback audit: inspect an existing IVR without modifying backend configuration.
- System TTS regression: verify normal-node, end-node, and KB-answer system TTS fields and UI echo.
- NLP / KB matching check: verify short-trigger design and all required matching fields.
- Model intent 2.0 check: verify IVR-level `updateModelIntentRecognitionConfig` state and node-level 2.0 config.
- Text-debug layered-recognition regression: use page text debug to verify NLP-first and 2.0-fallback behavior.
- Strategy optimization plan: convert failed text-debug cases into P0/P1/P2 trigger-word, NLP-convergence, and 2.0 handoff recommendations without changing backend configuration.

## Human Confirmation Required

Generate candidates but ask for confirmation before finalizing:

- any exceptional node that should not handle user replies. Knowledge-base matching itself is not optional for routed normal nodes.
- whether a customer explicitly wants a subset of knowledge bases instead of the default "bind all current IVR knowledge bases" rule
- the IVR-level model intent recognition 2.0 prompt template, result-format example, and any exceptional node that should not handle user replies. Enabling 2.0 itself is not optional for routed normal nodes.
- variable playback fields and whether variables should actually be spoken
- inferred branches when source materials do not define clear flow

## Not Covered In v0.1

- MiniMax voice clone or uploaded recording delivery
- `recordType=1` / `ivr/YYYY-MM-DD/*.mp3`
- smart Agent Prompt automation
- `llmNodeModelConfig`
- SMS, manual transfer, blacklist, information collection, DTMF, seat takeover
- automatic production edits without snapshot and authorization
- bulk model intent recognition 2.0 writes without readback evidence

## References

Use `scripts/check_skill_update.py --check` before starting a task to compare the local skill version with GitHub. Use `--apply` only after the user confirms they want to update the local installed skill.

Read `references/system-tts-normal-node-v0.1.md` before implementing or reviewing any backend write or readback involving normal nodes, jump nodes, system TTS, knowledge-base answers, NLP knowledge-base matching, or large model intent recognition 2.0.

For coworker-facing task selection and prompt templates, use the Obsidian manual:

`D:\ObsidianVault\闪电智能知识库\20-Skills\talktrack-master\TalkTrack-Master_v0.2_Skill封装说明与同事使用手册_20260512.md`
