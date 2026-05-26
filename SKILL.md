---
name: talktrack-master
version: v0.4.9
github_repo: LIGHTNINGAI-CO-LIMITED/TalkTrack-Master
github_path: "."
github_branch: main
description: Use when configuring, creating, updating, validating, or packaging Shandian Intelligent normal-node and jump-node IVR scenes in the admin backend, especially tasks involving 普通节点, 跳转节点, 结束节点, 系统 TTS, recordType=2, ttsPlaybackList, ttsPlaybackListJson, 知识库答案, NLP 匹配知识库, 大模型意图分析 2.0, /ivr/findSceneList/{ivrId}, readback reports, and Obsidian archival. Do not use for 智能Agent/智能节点 Prompt or llmNodeModelConfig work; use talktrack-agent for those.
---

# TalkTrack-Master

Use this skill for Shandian Intelligent normal-node and jump-node IVR configuration. The v0.2 path supports new-test-IVR creation, readback-only audits, system TTS checks, mandatory NLP knowledge-base matching, mandatory large model intent recognition 2.0, page text-debug layered-recognition regression, and strategy optimization plans, then proves the result through API readback, page spot checks, redacted reports, and Obsidian archival.

## Skill Update Check

For backend write/import/configuration tasks, first run the project-level preflight when the workspace is `D:\闪电智能`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\闪电智能\tools\talktrack_skill_preflight.ps1" -Skill talktrack-master -Mode Write
```

If preflight fails because the local skill is stale and the local GitHub mirror under `D:\闪电智能\github\TalkTrack-Master` is trusted/current, run the same preflight with `-InstallFromLocalRepo` and re-check. Do not request backend write authorization until preflight prints `PREFLIGHT_PASS`.

At the start of any task using this skill, run the bundled update check:

```powershell
python "C:\Users\luona\.codex\skills\talktrack-master\scripts\check_skill_update.py" --check
```

If the result is `update_available`, tell the user the local version and GitHub version, then recommend updating before continuing. Do not update automatically. Only when the user confirms, run:

```powershell
python "C:\Users\luona\.codex\skills\talktrack-master\scripts\check_skill_update.py" --apply
```

If the check fails because GitHub, TLS, certificate chain, or the network is unavailable, do not treat the local skill as up to date. For backend write/import/configuration tasks, pause and ask the user to update or explicitly approve continuing with the current local version. For urgent read-only work, you may continue only after clearly stating that the update status is unknown. The update check must not use, print, store, or request business API tokens; it only reads the public GitHub skill repository.

The bundled checker must prefer `git ls-remote` to read the real GitHub remote HEAD SHA, fetch files by explicit GitHub tree/blob SHA, then fall back through GitHub Contents API and raw GitHub. It must also fall back across Python urllib, certifi, curl.exe, and PowerShell WebClient. A Python certificate-chain failure or branch-content cache is a transport problem, not proof that the skill is current.

### Old Local Version Bootstrap

If a coworker is still on `v0.4.0` and the old update checker is blocked by Python certificate-chain or raw.githubusercontent.com access, the old checker may not be able to self-heal. For backend write/import/configuration work, do not continue on the stale local copy until one of these happens:

1. The user explicitly accepts using the stale local skill for this one run.
2. The coworker runs the project-level preflight with local-repo install or the one-time bootstrap script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\闪电智能\tools\talktrack_skill_preflight.ps1" -Skill talktrack-master -Mode Write -InstallFromLocalRepo
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\talktrack-master\scripts\bootstrap_update_talktrack_master.ps1"
```

If the bootstrap script is missing in their local skill folder, give them the copy-ready bootstrap prompt documented in:

`D:\ObsidianVault\闪电智能知识库\20-Skills\talktrack-master\TalkTrack-Master_v0.4.1_更新检查与旧版自救升级_20260519.md`

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
- Every normal node or jump node that uses large model intent recognition 2.0 must use model `闪电26BMoE-fast`, represented by `modelId=55` / node-level `modelIntentRecognitionConfig.modelConfig.id=55`. Do not rely on page defaults or first-node inheritance. When preserving an existing node-level config, force the model ID back to `55` in backend `sceneList`, frontend `sceneListFrontend.nodeList`, and graph `customData`, while preserving the node's prompt and result format.
- `兜底` / `-1` is a system fallback route, not a business intent. It may exist as a default route in backend/frontend/graph data, but NLP keywords, node intent labels, 2.0 `modelPrompt`, and `modelResultFormat` must not ask the model to output `兜底` as an intent. Text-debug or readback should interpret fallback as "no explicit intent matched", not "matched an intent named 兜底".
- Keep backend route lists and frontend canvas intent lists in their own shapes. Backend `sceneList.nodeList[].intentList` uses route dictionaries such as `{"27620":"node-xxx"}` / `{"-2":""}` / `{"-1":"node-yyy"}`. Frontend `sceneListFrontend.nodeList[].intentList` and graph `data.customData.intentList` must use option rows with `value`, `label`, and `digitSequence`. Do not deep-copy backend nodes into frontend canvas data without converting `intentList`; the page save logic reads `value` from the frontend list and can rebuild broken routes, causing generic `system error` on save.
- Preserve the page-native graph render shape in `sceneListFrontend.graph.cells`. Do not rebuild canvas node cells with generic `in` / `out` ports. Normal-node / jump-node routed cells must keep or restore the platform's `keypadPort` port group, existing node geometry (`position`, `size`), `shape`, `attrs`, and hidden data needed by the page. When patching knowledge-base matching, intent labels, node-level 2.0, or model IDs, patch the existing frontend cell in place or restore render-only fields from the pre-write snapshot; do not synthesize a new generic graph node.
- Before claiming a graph write is safe, run canvas-save validation. From the user's perspective, `/script-graph?ivrId=<ivrId>` must open and the page must be able to save/update without `system error` or route/config corruption. If real browser save is unavailable, simulate the page-save shape: every routed frontend node and graph `customData` intent row must have `value`; graph ports / edges must still point to the same targets as backend routes; then state the limitation in the report. A backend-only save success is not enough when `sceneListFrontend` was touched.
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
6. For jump nodes and routed normal nodes, keep target node IDs, ports, backend `sceneList`, frontend `sceneListFrontend`, and graph custom data consistent. Preserve the format split: backend intent routes stay as `{intentId: targetNodeId}`, while frontend canvas intent lists stay as `{value,label,digitSequence}` option rows.
7. Generate TTS with `/ivr/createNodeTextTtsRecord`, poll `/ivr/queryTtsRecord`, then write back returned `recordFilePath`.
8. Enable NLP knowledge-base matching on every normal node that handles user replies. Bind all current IVR knowledge-base IDs explicitly with `knowledgeBaseMatchType=2`, and add the `-2` knowledge-base intent when missing.
9. Review NLP trigger quality: prefer short, synonym-friendly keywords / regex phrases for knowledge-base matching and node intents. Long customer-style sentences belong in answers or the 2.0 prompt. Do not create a keyword / intent label named `兜底`; fallback is handled by the system route.
10. Enable Advanced Settings large model intent recognition 2.0 with `POST <authenticated-api-base>/ivr/updateModelIntentRecognitionConfig`. Use the target IVR ID as `id`, set `modelIntentRecognitionEnabled=1`, use the approved scene-specific `modelPrompt` and `modelResultFormat`, keep `modelId=55`, timeout `2000`, `modelMaxTokens>=4096`, and `modelRecognitionRound=0`. The prompt/result format must not include `兜底` as an output intent.
11. Enable or preserve node-level large model intent recognition 2.0 on every normal node that handles user replies. Preserve existing valid node prompts and result formats, but always normalize the node-level model to `modelIntentRecognitionConfig.modelConfig.id=55` (`闪电26BMoE-fast`) when the node has 2.0 enabled or a 2.0 config. Create a node-level `modelIntentRecognitionConfig` from the approved template when it is missing.
12. Read back with `/ivr/findSceneList/{ivrId}` plus knowledge-base list/detail endpoints when answers are touched. For knowledge-base matching and node-level 2.0, validate backend nodes, frontend node copies, and graph `customData`; for node-level 2.0 model selection, validate every enabled/configured normal or jump node reads back with model ID `55` in all three copies; for frontend canvas intent lists, validate every intent row has `value`; for graph rendering, validate frontend graph node cells still have page-native `keypadPort` ports and were not rewritten to generic `in` / `out`; for Advanced Settings 2.0, validate the IVR-level fields and page echo.
13. For graph-affecting writes, run canvas-save validation at `/script-graph?ivrId=<ivrId>`: refresh any old page tab, confirm UI opens with intended config, click page save/update when available, or run simulated page-save shape validation and report why real click-save was unavailable. Current system TTS UI evidence is `试听` / `重新合成`; current NLP UI evidence is checked `匹配知识库` with explicit selected knowledge bases; current 2.0 UI evidence is checked `大模型意图分析2.0`.
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

Use `scripts/check_skill_update.py --check` before starting a task to compare the local skill version with GitHub. Use `--apply` only after the user confirms they want to update the local installed skill. If the check reports `check_failed`, do not silently continue with backend writes; use the bootstrap path above or get explicit user confirmation.

Read `references/system-tts-normal-node-v0.1.md` before implementing or reviewing any backend write or readback involving normal nodes, jump nodes, system TTS, knowledge-base answers, NLP knowledge-base matching, or large model intent recognition 2.0.

For coworker-facing task selection and prompt templates, use the Obsidian manual:

`D:\ObsidianVault\闪电智能知识库\20-Skills\talktrack-master\TalkTrack-Master_v0.2_Skill封装说明与同事使用手册_20260512.md`
