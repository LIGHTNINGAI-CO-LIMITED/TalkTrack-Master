# System TTS Normal Node v0.1

This reference is for Shandian Intelligent backend work on the domestic or overseas admin backend:

- domestic API: `https://ai.sd6g.com:1904/api/web`
- overseas API: `https://ai.tbot360.com/api/web`

Use it for TalkTrack-Master v0.1 tasks involving normal nodes, jump nodes, end nodes, system TTS, and knowledge-base answers.

## Safety

- Header: `token: Bearer <TOKEN>`, not raw `token: <TOKEN>` and not `Authorization`.
- Resolve backend first. If the user provides a URL, infer domestic from `ai.sd6g.com:1904` and overseas from `ai.tbot360.com`. If the user only provides a token, normalize raw 32-hex / `Bearer ...` / `token=Bearer%20...` / curl header text and probe both backends with `GET /account/findInfo`; continue only when the selected or single matching backend returns `code=0`.
- Do not store real token values in scripts, reports, logs, screenshots, Markdown, JSON, or final replies.
- Use a new test IVR unless the user explicitly authorizes editing a target IVR.
- Snapshot before write with `GET /ivr/findSceneList/{ivrId}`.
- Treat `debug=true` as a front-end visibility/debug switch, not proof of backend write permission.

## Base Read Calls

- `GET /account/findInfo`
- `GET /ivr/findAllTtsVoiceBaseInfo`
- `POST /ivr/findPage` with:

```json
{"query":{"searchName":""},"page":{"current":1,"size":10}}
```

- `GET /ivr/findSceneList/{ivrId}`

## System TTS

v0.1 uses backend system TTS, not uploaded recordings.

Expected shape:

- `recordType=2`
- TTS paths look like `tts/YYYY-MM-DD/*.wav`
- `recordType=1` and `ivr/YYYY-MM-DD/*.mp3` are out of scope for v0.1

Generation sequence:

1. Pick a system voice from `/ivr/findAllTtsVoiceBaseInfo`.
2. Call `/ivr/createNodeTextTtsRecord` with `ivrId`, `ttsVoiceId`, `speechRate`, and `text`.
3. Poll `/ivr/queryTtsRecord` with the same relevant parameters until a path is returned.
4. Write returned `recordFilePath` back into node or knowledge-base answer payload.
5. Read back through the backend API; do not rely on the create/query response alone.

## Normal Nodes

Use normal nodes for spoken robot turns.

Required readback evidence:

- node exists in `/ivr/findSceneList/{ivrId}`
- node type is the expected normal-node type from the cloned or known-good shape
- `recordType=2`
- `ttsPlaybackList` is non-empty
- each spoken item has the intended spoken text and a `recordFilePath` under `tts/YYYY-MM-DD/*.wav`

Do not put node names, field names, comments, JSON keys, or test instructions into spoken TTS text.

## Jump Nodes

Use jump nodes for flow routing, not spoken content.

Required consistency checks:

- target node ID is valid in the same IVR scene
- outgoing port labels match the intended branch
- backend `sceneList` and frontend `sceneListFrontend` agree
- graph cell custom data points to the same node and target relationship
- page view opens at `/script-graph?ivrId=<ivrId>` and shows the intended flow

If the jump-node field shape is uncertain, copy a known-good jump node from readback evidence and change only business values. Do not invent backend-only fields.

## End Nodes

End nodes must be visible in API readback and page spot checks when they are part of the configured flow.

If an end node has spoken text, treat it like a system TTS node:

- `recordType=2`
- non-empty TTS list
- returned path under `tts/YYYY-MM-DD/*.wav`

## Knowledge-Base Answers

Knowledge-base answers in v0.1 use system TTS, not uploaded recordings.

Expected answer shape:

- answer `recordType=2`
- `recordPlaybackListJson=[]`
- `ttsPlaybackListJson` is non-empty
- generated `recordFilePath` is under `tts/YYYY-MM-DD/*.wav`

Readback must include both list and detail evidence when available:

- knowledge-base list endpoint confirms the item exists
- detail endpoint confirms answer text, `recordType`, and `ttsPlaybackListJson`

If only a file path changes but playback type stays wrong, report the exact endpoint and field mismatch. Do not mark the run complete.

## Mandatory NLP Knowledge-Base Matching

For normal-node and jump-node talktrack work, enable NLP knowledge-base matching on every normal node that can route on user replies.

Required readback fields:

- `matchKnowledgeBaseEnabled=1`
- `knowledgeBaseMatchType=2`
- `knowledgeBaseMatchList` explicitly contains all current IVR knowledge-base IDs, unless the user explicitly requested a smaller subset
- `notMatchedKnowledgeBaseList=[]`
- node `intentList` contains `-2` for the knowledge-base intent
- the same matching state in backend `sceneList`
- the same matching state in frontend `sceneListFrontend.nodeList`
- the same matching state in frontend graph `data.customData`

Do not treat "enabled with an empty list" as the default success state. The field may have ambiguous runtime/UI interpretation; for TalkTrack-Master, prefer explicit binding to all current IVR knowledge bases for page clarity and pressure-test stability. If new knowledge bases are added later, rerun matching so every routed normal node includes the new IDs.

### Frontend Canvas Intent List Shape

The backend and the canvas frontend use different `intentList` shapes.

Backend route shape in `sceneList.nodeList[].intentList`:

```json
[{"27620":"node-xxx"},{"-2":""},{"-1":"node-yyy"}]
```

Frontend canvas option shape in `sceneListFrontend.nodeList[].intentList` and graph `data.customData.intentList`:

```json
[{"value":"27620","label":"客户肯定/默认","digitSequence":""},{"value":"-2","label":"知识库","digitSequence":""},{"value":"-1","label":"兜底","digitSequence":""}]
```

Here `-1` / `兜底` is only the system fallback/default route. It is not a business intent and must not be configured as an NLP keyword, ordinary intent label, or large-model 2.0 output. If runtime falls through to `-1`, report it as "no explicit intent matched", not as "matched an intent named 兜底".

Do not deep-copy a backend node into `sceneListFrontend` or graph `customData` without converting `intentList`. The page save logic reads `value` from the frontend option rows and then rebuilds routes from canvas ports / edges. If the frontend list is accidentally replaced by backend route dictionaries, page save may generate abnormal routes and the backend can return a generic `system error`.

Canvas-save acceptance:

- backend `sceneList` keeps route dictionaries and preserves real target node IDs
- frontend `sceneListFrontend.nodeList` uses option rows with `value`, `label`, and `digitSequence`
- graph `data.customData.intentList` uses the same frontend option-row shape
- graph `data.ports`, cell port items, and edge source ports use the same `value`
- graph node cells preserve the page-native render shape: routed ordinary-node / jump-node cells must use `ports.groups.keypadPort` and port items with `group="keypadPort"`, not generic `in` / `out` groups
- graph node cells preserve existing render-only fields from the pre-write snapshot, including `position`, `size`, `shape`, `attrs`, `zIndex`, and hidden cell data that the page depends on
- `兜底` / `-1`, when present, is only a fallback route and is not included in NLP / 2.0 business-intent candidates
- after graph-affecting writes, open `/script-graph?ivrId=<ivrId>` and verify the page can save/update from the user's canvas view
- if real click-save is unavailable, simulated page-save rebuild must return success and the report must state the limitation
- if a user keeps an old `/script-graph` browser tab open, refresh before clicking page save because stale page memory may overwrite repaired canvas data

### Frontend Canvas Render Shape / Port Schema

The canvas is rendered from `sceneListFrontend.graph.cells`, not directly from backend `sceneList`. A backend readback with all nodes present does not prove that the user's canvas can render.

Do not reconstruct graph node cells from a generic X6 / diagram template. The current page expects routed normal-node / jump-node cells to use the platform-specific `keypadPort` schema. Replacing it with generic groups such as `in` / `out` can make the central canvas look empty even when `sceneList` still contains every backend node.

Safe update rule:

- Start from the current readback or the pre-write snapshot.
- Patch only the business fields that must change, such as `data.customData`, `data.ports` option rows, node label text, knowledge-base matching fields, and node-level 2.0 config.
- Preserve the existing cell `id`, `shape`, `position`, `size`, `attrs`, `zIndex`, and existing page-native port groups.
- If a new routed port must be added, add it under `keypadPort`; do not introduce `in` / `out`.
- For production or existing IVRs, prefer restoring render-only fields from the pre-write snapshot after business-field updates.

Hard failure conditions:

- `sceneList` has nodes but `sceneListFrontend.graph.cells` has no corresponding node cells.
- A routed graph node cell uses `ports.groups.in` / `ports.groups.out` instead of `ports.groups.keypadPort`.
- A graph edge `source.port` references a port ID that is absent from the source node's `ports.items`.
- Page opens `/script-graph?ivrId=<ivrId>` but the center canvas is blank while the left scene list still shows scenes.

### NLP Trigger Design

NLP and knowledge-base matching run before large model intent recognition 2.0. Treat this layer as a regex / short-trigger layer:

- keep knowledge-base questions, keywords, and node intent labels short and atomic
- use multiple concise synonyms instead of one long sentence
- avoid long customer-style utterances as match text; they are harder to hit reliably
- put explanatory prose in the knowledge-base answer, not in the matching trigger
- use 2.0 as the semantic fallback after NLP fails or cannot satisfy the intent
- do not add `兜底` as a trigger, synonym, keyword, or node intent; the system fallback route handles no-match cases

Good trigger shape: `价格`, `多少钱`, `收费`, `费用`.

Poor trigger shape: `我想了解一下你们这个活动到底怎么收费以及后续有没有额外费用`.

## Mandatory Model Intent Recognition 2.0

For normal-node and jump-node talktrack work, enable Advanced Settings large model intent recognition 2.0 at the IVR level and keep routed-node execution fields consistent.

Use this IVR-level endpoint path for the page Advanced Settings switch:

```text
POST <resolved-api-base>/ivr/updateModelIntentRecognitionConfig
```

Required request headers still use `token: Bearer <TOKEN>`.

Resolved API base examples:

```text
https://ai.sd6g.com:1904/api/web
https://ai.tbot360.com/api/web
```

`code=7 invalid credential` usually means the token was not normalized, the wrong header was used, or the token belongs to the other backend. Only treat it as an expired token after `token: Bearer <TOKEN>` fails on the intended backend.

Required payload shape:

```json
{
  "id": 3636,
  "modelIntentRecognitionEnabled": 1,
  "modelIntentRecognitionTimeoutMilliSecond": 2000,
  "modelPrompt": "<scene-specific prompt>",
  "modelId": 55,
  "modelResultFormat": "<scene-specific result format>",
  "modelTemperature": 0,
  "modelTopP": 0,
  "modelTopK": 0,
  "modelPresencePenalty": 0,
  "modelMaxTokens": 4096,
  "modelThinkBudget": 0,
  "modelSeed": 0,
  "modelEnableThinking": 0,
  "modelRecognitionRound": 0
}
```

Parameter rules:

- `id` must equal the target IVR ID.
- `modelIntentRecognitionEnabled=1` is the required enabled state.
- `modelIntentRecognitionTimeoutMilliSecond=2000`.
- `modelPrompt` must be adapted to the current scene.
- `modelPrompt` must state that `兜底` is not an output intent; unclear/no-match cases should fall through to the system fallback route instead of returning `兜底`.
- `modelId` is chosen by resolved backend:
  - domestic `ai.sd6g.com:1904`: `55` / `闪电26BMoE-fast`
  - overseas `ai.tbot360.com`: `62` / `openai/gpt-5.4-mini`
- `modelTemperature` is in `[0,2)`.
- `modelPresencePenalty` is in `[-2,2]`.
- `modelMaxTokens` must be at least `4096`; do not send `0` for an enabled configuration.
- `modelRecognitionRound=0` for the default all-round setting; do not send values above `4`.
- `modelResultFormat` must list only explicit business / knowledge-base intent outputs. Do not include `兜底` as an `intentName`.

Switch parameter rules:

| Field | Meaning | Default for TalkTrack-Master | When to use `0` | When to use `1` |
| --- | --- | --- | --- | --- |
| `modelIntentRecognitionEnabled` | IVR-level Advanced Settings switch for large model intent recognition 2.0 | `1` | Only when the user explicitly asks to disable 2.0, when doing an A/B off test, or when latency/cost constraints require 2.0 off | Normal-node / jump-node talktracks that need semantic fallback after NLP |
| `modelEnableThinking` | Model thinking / reasoning switch when the selected model supports it | `0` | Real-time IVR intent recognition where latency stability matters | Only after human confirmation for complex semantic analysis where extra latency is acceptable |

Do not treat `modelRecognitionRound` as an on/off switch. `0` means the default all-round setting; `1` to `4` constrain recognition to a specific round range, and values above `4` are unsupported.

Required Advanced Settings readback:

- the update endpoint returns `code=0`
- `/ivr/findSceneList/{ivrId}` echoes the IVR-level 2.0 fields that the backend exposes, especially `modelIntentRecognitionEnabled=1`, the expected regional `modelId`, and a non-empty prompt/config where available
- the page shows `高级设置 -> 大模型意图分析2.0` checked

For every normal node that can route on user replies, also preserve or create the routed-node config:

- `modelIntentRecognitionEnabled=1`
- non-empty `modelIntentRecognitionConfig`
- `modelIntentRecognitionConfig.modelConfig.id` matches the expected regional model: domestic `55`, overseas `62`
- the same enabled/config state in backend `sceneList`
- the same enabled/config state in frontend `sceneListFrontend.nodeList`
- the same enabled/config state in frontend graph `data.customData`

When an existing valid `modelIntentRecognitionConfig` is present, preserve its prompt and result format, but still force the model selection to the expected regional model ID. Do this in backend `sceneList`, frontend `sceneListFrontend.nodeList`, and graph `customData`; otherwise the page can show later nodes using another model even when the first node is correct. Do not rely on page defaults, copy-order inheritance, or "the first node already uses the right model". When a routed normal node is missing the config, create it from the approved 2.0 template and use the node's available intent labels to choose a valid `resultFormat` example. Do not claim Advanced Settings 2.0 completion from node-level fields alone, and do not claim routed-node completion from the IVR-level switch alone.

For jump nodes, only apply node-level 2.0 when the product surface actually enables 2.0 on that jump node. If a jump node has `modelIntentRecognitionEnabled=1` or a non-empty `modelIntentRecognitionConfig`, it must follow the same regional model rule and must be read back in backend, frontend, and graph copies.

## Optional Human-Confirmed Features

These can be drafted but need human confirmation before final write:

- any explicit customer requirement to match only a subset of knowledge bases instead of all current IVR knowledge bases
- 2.0 prompt wording, result-format example, and any exceptional node that should not handle user replies
- variable playback fields
- inferred branch mapping from unclear source material

For model intent recognition 2.0, API `success` is not enough. Require page echo and `/ivr/findSceneList/{ivrId}` readback before claiming the IVR-level switch and routed-node fields landed.

Readback failures that must block acceptance:

- IVR-level `modelId` does not match the expected regional model.
- Any normal node or 2.0-enabled jump node has `modelIntentRecognitionConfig.modelConfig.id` missing or not equal to the expected regional model.
- Backend, frontend node copy, and graph `customData` disagree on the node-level model ID.
- The UI edit dialog for a sampled node shows a model other than the expected regional model.

## Page Spot Check

Open:

`<resolved-web-base>/script-graph?ivrId=<ivrId>`

Current system TTS UI evidence:

- normal-node drawer shows `试听` / `重新合成`
- knowledge-base answer drawer shows `试听` / `重新合成`

Do not fail a page check only because the literal text `语音合成` is absent.

## Report Requirements

Final report must be redacted and include:

- IVR ID and name
- whether the run used a test IVR or authorized target IVR
- touched node names and types
- normal-node `recordType` and `ttsPlaybackList` counts
- jump-node target consistency summary
- knowledge-base IDs, titles, answer IDs, `recordType`, and TTS counts
- TTS query status and whether paths match `tts/YYYY-MM-DD/*.wav`
- page spot-check result
- failed items
- Obsidian archive path
- `obsidian 'vault=闪电智能知识库' unresolved total` result

If failed items are non-empty, final status is "partial" or "not complete", not "done".
