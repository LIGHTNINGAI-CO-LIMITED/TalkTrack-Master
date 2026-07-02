---
tags:
  - 闪电智能
  - TalkTrack-Master
  - Skill
  - 使用手册
created: 2026-05-12
status: v0.2-draft-ready
---

# TalkTrack-Master v0.2 Skill 封装说明与同事使用手册

## 一句话定位

`TalkTrack-Master` 用于闪电智能后台“普通节点 + 跳转节点”话术配置、读回验收、文本调试回归和策略优化。

它不负责智能 Agent / 智能节点 Prompt。智能 Agent、`llmNodeModelConfig`、terminal intent 规则使用 `sd-admin-ivr-config`。

## 什么时候使用

适用场景：

- 从 DOCX / 客户材料新建普通节点、跳转节点、结束节点话术。
- 给普通节点或知识库答案补系统 TTS。
- 检查已有话术的普通节点、跳转节点、知识库答案、系统 TTS。
- 检查 NLP / 知识库匹配是否显式绑定当前知识库。
- 检查“高级设置 -> 大模型意图分析 2.0”是否真的启用。
- 使用页面文本调试验证“短触发词先行、2.0 兜底”的分层命中。
- 将失败 case 转为普通节点策略优化方案。

不适用场景：

- 智能 Agent / 智能节点 Prompt 导入。
- `llmNodeModelConfig`、智能节点出口意图规则。
- MiniMax 克隆音或最终上传录音交付。
- 未授权直接修改生产 IVR。
- 短信、转人工、黑名单、信息采集、DTMF、坐席接管等高级能力自动化。

## 输入材料

同事发起任务前至少给出：

- 任务类型：新建 / 读回体检 / 系统 TTS / 文本调试 / 策略优化。
- 话术 ID 或源文件路径。
- 是否允许写后台；默认只读，除非明确授权。
- token 所在 secret 名称；默认使用 Obsidian `secretStorage` 的 `testtoken`。
- 输出报告应写入的 Obsidian 目录；默认 `D:\ObsidianVault\闪电智能知识库\30-SOP\话术配置`。

大文件规则：

- DOCX、raw JSON、截图批量、音频、视频默认不复制进 Obsidian。
- Obsidian 只写报告、索引、结论和必要的小图片附件。

## 安全边界

- 不打印、不截图、不写入 access token、API key、密码、Cookie、浏览器登录态。
- 后端请求使用 `token: Bearer <TOKEN>`，不是 `Authorization`。
- token 只进入当前进程环境变量。
- 写后台前必须有明确授权和 before snapshot。
- API 返回 `success` 不等于完成，必须读回验证。

token 读取模板：

```powershell
$raw = obsidian 'vault=闪电智能知识库' eval code="(async()=>{await app.secretStorage.load?.(); return await app.secretStorage.getSecret('testtoken');})()"
$secret = ($raw | Out-String).Trim()
$secret = $secret -replace '^Bearer\s+', ''
$candidates = [regex]::Matches($secret, '[A-Za-z0-9._-]{20,}') | ForEach-Object { $_.Value }
$token = $candidates | Sort-Object Length -Descending | Select-Object -First 1
$env:SD_ADMIN_TOKEN = $token
```

## 核心规则

### NLP / 知识库匹配

系统先走 NLP 和意图模型；NLP / 意图模型没有命中或不能满足时，再走大模型意图分析 2.0。

因此，NLP / 知识库匹配是先行命中层，更接近正则或短触发词匹配：

- 知识库问题、关键词、节点意图标签应短、原子化、同义词覆盖。
- 推荐：`价格`、`多少钱`、`收费`、`费用`。
- 不推荐：`我想了解一下你们这个活动到底怎么收费以及后续有没有额外费用`。
- 长句、业务解释、复杂语义判断放到知识库答案或 2.0 Prompt。

必验字段：

- `matchKnowledgeBaseEnabled=1`
- `knowledgeBaseMatchType=2`
- `knowledgeBaseMatchList` 显式包含当前 IVR 全部知识库 ID，除非用户明确要求子集
- `notMatchedKnowledgeBaseList=[]`
- `intentList` 包含 `-2`
- 后端 `sceneList`、前端 `sceneListFrontend.nodeList`、画布 `graph.data.customData` 三处一致

### 大模型意图分析 2.0

“高级设置 -> 大模型意图分析 2.0”必须通过话术级接口路径写入：

```text
POST <authenticated-api-base>/ivr/updateModelIntentRecognitionConfig
```

当前 `testtoken` 已验证可用的 API base：

```text
https://ai.sd6g.com:1904/api/web
```

`https://aicc-test.sd6g.com/api/web` 只有在 token 对该 host 有效时才可用；同一个 token 不能默认跨 host 使用。

启用 payload 核心字段：

```json
{
  "id": 3500,
  "modelIntentRecognitionEnabled": 1,
  "modelIntentRecognitionTimeoutMilliSecond": 2000,
  "modelPrompt": "<适配当前场景的提示词>",
  "modelId": 55,
  "modelResultFormat": "<当前可用意图的输出格式示例>",
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

开关参数判断：

| 字段 | 含义 | TalkTrack-Master 默认 | 什么时候填 `0` | 什么时候填 `1` |
| --- | --- | --- | --- | --- |
| `modelIntentRecognitionEnabled` | 话术级 2.0 总开关 | `1` | 用户明确关闭、A/B off 测试、延迟/成本要求禁用 2.0 | 普通节点 / 跳转节点需要 NLP 未命中后的语义兜底 |
| `modelEnableThinking` | 模型思考开关 | `0` | 实时 IVR 意图识别，优先延迟稳定 | 复杂语义分析且人工确认可接受更高延迟 |

不是开关的字段：

- 话术级 `modelRecognitionRound=0` 表示默认全轮次；`1` 到 `4` 表示指定轮次，不支持大于 `4`。
- 节点级 `modelIntentRecognitionConfig.modelConfig.recognitionRound=0` 表示页面“识别节点轮次：全部轮次”；所有启用大模型意图分析 2.0 的普通节点 / 跳转节点都必须使用 `0`，不能只修第一个节点，也不能继承模板里的 `1`。
- `modelTopP`、`modelTopK`、`modelTemperature`、`modelPresencePenalty` 是采样/生成参数，不是开关。
- `modelMaxTokens` 启用时最低 `4096`，不要填 `0`。

必验字段：

- 写接口返回 `code=0`
- `/ivr/findSceneList/{ivrId}` 读回话术级 `modelIntentRecognitionEnabled=1`
- `modelId=55`
- `modelPrompt` 非空或等价配置非空
- 如后端暴露，确认 `modelMaxTokens>=4096`、`modelRecognitionRound=0`
- 页面 `高级设置 -> 大模型意图分析2.0` 已勾选
- 承接用户回复的普通节点仍需保留 / 补齐节点级 `modelIntentRecognitionEnabled=1`、非空 `modelIntentRecognitionConfig`、正确区域模型 ID，以及 `modelIntentRecognitionConfig.modelConfig.recognitionRound=0`

## 标准任务模板

### 1. 新建普通节点 / 跳转节点话术

```text
请使用 TalkTrack-Master 从源材料新建测试 IVR。

源材料：<DOCX/PDF/截图/客户材料路径>
允许写后台：是，仅限新建测试 IVR，不修改生产 IVR
token：Obsidian secretStorage / testtoken

必须完成：
- 解析普通节点、跳转节点、结束节点
- 写入系统 TTS
- 写入代表性知识库答案系统 TTS
- 启用 NLP / 知识库匹配，显式绑定当前 IVR 全部知识库
- 通过 updateModelIntentRecognitionConfig 启用话术级 2.0
- 保留 / 补齐承接用户回复普通节点的节点级 2.0
- /ivr/findSceneList 读回
- 页面抽查
- 报告写入 Obsidian 并更新索引
- unresolved total=0
- TOKEN_LEAK_CHECK=PASS
```

### 2. 已有话术只读体检

```text
请使用 TalkTrack-Master 对话术 ID <ivrId> 做只读体检。

禁止修改后台配置。
读取 /ivr/findSceneList/<ivrId> 和知识库列表/详情，检查：
- 普通节点、跳转节点、结束节点结构
- 系统 TTS / 上传录音状态
- NLP / 知识库匹配字段
- 话术级 2.0 高级设置
- 节点级 2.0 配置
- 是否存在未绑定当前知识库、空配置、三处不一致

输出只读体检报告到 Obsidian，并更新索引。
```

### 3. 系统 TTS / 知识库答案回归

```text
请使用 TalkTrack-Master 对话术 ID <ivrId> 做系统 TTS 回归。

根据用户授权决定是否写后台。未授权时只读检查。
重点验证：
- 普通节点 `recordType=2` 且 `ttsPlaybackList` 非空
- 结束节点 `recordType=2` 且 `ttsPlaybackList` 非空
- 知识库答案 `recordType=2` 且 `ttsPlaybackListJson` 非空
- TTS 路径形如 `tts/YYYY-MM-DD/*.wav`
- 页面显示 `试听` / `重新合成`
```

### 4. NLP / 知识库匹配检查

```text
请使用 TalkTrack-Master 检查话术 ID <ivrId> 的 NLP / 知识库匹配。

只读或可写：<只读/可写>
检查：
- 所有承接用户回复普通节点是否 `matchKnowledgeBaseEnabled=1`
- 是否 `knowledgeBaseMatchType=2`
- `knowledgeBaseMatchList` 是否显式等于当前 IVR 全部知识库 ID
- `notMatchedKnowledgeBaseList=[]`
- `intentList` 是否包含 `-2`
- 后端、前端、画布三处是否一致
- 触发词是否短、原子化、同义词覆盖
```

### 5. 大模型意图分析 2.0 生效检查

```text
请使用 TalkTrack-Master 检查话术 ID <ivrId> 的大模型意图分析 2.0。

只读或可写：<只读/可写>
检查：
- 话术级 `modelIntentRecognitionEnabled`
- `modelId`
- `modelPrompt`
- `modelResultFormat`
- `modelMaxTokens`
- `modelRecognitionRound`
- 承接用户回复普通节点的节点级 `modelIntentRecognitionEnabled` / `modelIntentRecognitionConfig`
- 节点级 `modelIntentRecognitionConfig.modelConfig.recognitionRound=0`，页面弹窗显示 `识别节点轮次：全部轮次`
- 页面高级设置是否显示大模型意图分析2.0已勾选

若可写且未开启，使用 `POST <authenticated-api-base>/ivr/updateModelIntentRecognitionConfig` 补齐，写后读回。
```

### 6. 文本调试分层命中回归

```text
请使用 TalkTrack-Master 对话术 ID <ivrId> 做页面文本调试分层命中回归。

禁止修改后台配置。
使用页面文本调试，不使用语音调试。
覆盖：
- 短触发词
- 短同义词
- 长句语义
- 干扰与边界
- 知识库答案自然问法

记录每条 case 的预期层级、实际层级、命中意图/知识库/节点、最终回复、是否通过和问题归因。
```

### 7. 普通节点策略优化方案

```text
请使用 TalkTrack-Master 基于上一轮文本调试报告产出普通节点策略优化方案。

禁止修改后台配置。
把失败 case 分为：
- 应补短触发词
- NLP 误拦截 / 误命中
- 应交给 2.0
- 2.0 兜底失败 / 需消歧
- 测试预期需调整

输出 P0/P1/P2 优化清单、短触发词 Top 10、NLP 收敛建议、2.0 承接建议和 20-30 条最小回归集。
```

## 统一验收清单

- [ ] 任务边界已写清：只读 / 可写 / 新建测试 IVR / 禁止生产修改。
- [ ] token 未出现在报告、JSON、截图、索引或最终回复中。
- [ ] 写后台前已保存 before snapshot。
- [ ] API 写入后已通过 `/ivr/findSceneList/{ivrId}` 读回。
- [ ] NLP / 知识库匹配三处一致。
- [ ] 话术级 2.0 高级设置通过正确接口写入或读回。
- [ ] 节点级 2.0 配置三处一致。
- [ ] 页面抽查证据与当前 UI 文案一致。
- [ ] 报告写入正式 Obsidian。
- [ ] 相关 Skill / SOP / 总览索引已更新。
- [ ] `obsidian 'vault=闪电智能知识库' unresolved total` 返回 `0`。
- [ ] 如果读取 token，`TOKEN_LEAK_CHECK=PASS`；如果未读取，`TOKEN_NOT_USED=TRUE`。

## 版本路线

| 版本 | 状态 | 价值 |
| --- | --- | --- |
| v0.1 | 已完成 | 能从材料生成普通节点 / 跳转节点测试 IVR，并验证系统 TTS |
| v0.1.1 | 已完成 | NLP 匹配知识库和大模型意图分析 2.0 成为必选项 |
| v0.1.2 | 已完成 | 验证 3500 的分层命中链路，发现短触发词层不足 |
| v0.1.3 | 已完成 | 将失败 case 转为普通节点策略优化方案 |
| v0.2 | 当前文档 | 封装为同事可复用 Skill 使用手册和 Prompt 包 |

## 下一步

v0.2 之后的重点不是继续堆文档，而是做一次“同事按手册独立执行”的试运行：

- 选一个非 3500 的测试 IVR 或新建测试 IVR。
- 由非本轮参与者只看本手册执行。
- 观察是否能独立完成读回、调试、报告、索引更新和安全检查。
- 根据卡点补齐 v0.2.1。
