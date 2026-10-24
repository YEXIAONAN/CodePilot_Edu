# CodePilot Edu 前端对接任务书（交给 Agent 执行）

> 本文档面向负责前端的 AI Agent。后端已实现并可运行，**接口契约以本文档为准**；
> 凡本文档未定义的字段，不要臆造，先读 `GET /openapi.json` 或查看后端源码。
> 项目目录：`C:\Users\21089\Documents\Trae-CN\temp_20261022_01`
> 后端目录：`codepilot-edu-backend`，前端请新建 `codepilot-edu-frontend`。

---

## 一、你的任务

为 CodePilot Edu 实现一个可现场演示的前端，覆盖三个页面：

1. **题目列表**：展示 3 道 C 语言练习题。
2. **练习页**：题面 + 代码编辑器 + 提交 + 结果面板 + 三层提示。
3. **数据看板**：学生学习记录与教师端统计。

**目标**：把后端已有的能力完整、准确地呈现出来，形成一条可重复演示的链路：
看题 → 写错代码 → 提交 → 看到失败证据与诊断 → 逐层要提示 → 改对 → 再提交通过 → 查看记录与统计。

**这不是**：在线商城、用户系统、课程管理后台。不要加登录注册、支付、题库编辑、AI 聊天窗口。

## 二、技术栈与工程约束

- Vue 3 + Vite + TypeScript，`<script setup>` 组合式 API
- 路由：Vue Router 4；状态：Pinia（只放当前题目、学生 ID、提交结果）
- 代码编辑器：CodeMirror 6 + `@codemirror/lang-cpp`（不要用 Monaco，体积大）
- HTTP：`fetch` 或 axios 均可；**提交接口超时至少设 30 秒**
- 样式：CSS 变量 + 手写样式即可，不强制 UI 库；配色以"教学工具"为主，克制、清晰
- 不使用任何 mock 数据、不伪造统计数字

## 三、后端契约

- Base URL：`http://127.0.0.1:8000`
- 业务接口前缀：`/api/v1`
- 请求/响应均为 JSON（UTF-8）
- 跨域：后端默认只允许 `http://localhost:5173` 与 `http://127.0.0.1:5173`，**Vite 请使用 5173 端口**；换端口需改后端 `.env` 的 `CORS_ORIGINS` 并重启
- 演示令牌：**所有 `/api/v1/*` 接口**都要求请求头 `X-Demo-Token`，值为后端 `.env` 的 `DEMO_TOKEN`。
  前端在 `codepilot-edu-frontend/.env.local` 中配置 `VITE_DEMO_TOKEN`（与后端保持一致），
  `src/api/client.ts` 会自动附加请求头。后端未配置令牌时接口失败关闭（503），不会静默放行。
- 交互文档：`http://127.0.0.1:8000/docs`

### 3.1 健康检查

`GET /health`

```json
{
  "status": "ok",
  "version": "0.2.0",
  "api": "ok",
  "database": true,
  "database_status": "ok",
  "database_latency_ms": 3,
  "docker": true
}
```

- `api` 表示 API 进程存活；`database` / `database_status` 表示 MySQL 依赖状态；
  `status=degraded` 时应显示「数据库异常」，`database=false` 时业务接口会返回 503 `DATABASE_UNAVAILABLE`。
- `docker=false` 时，练习页顶部要显示「评测服务未就绪」的提示条，提交会失败（503 `JUDGE_UNAVAILABLE`）。

### 3.2 题目列表

`GET /api/v1/problems`

```json
[
  {"id": 1, "title": "1 到 N 求和", "difficulty": "EASY",
   "knowledge_points": ["循环结构", "循环边界", "累加求和"]}
]
```

### 3.3 题目详情

`GET /api/v1/problems/{id}`

```json
{
  "id": 1,
  "title": "1 到 N 求和",
  "description": "给定一个正整数 N，计算 1 + 2 + ... + N 的结果并输出。",
  "difficulty": "EASY",
  "knowledge_points": ["循环结构", "循环边界", "累加求和"],
  "input_description": "一行一个正整数 N（1 ≤ N ≤ 10000）。",
  "output_description": "输出一个整数，表示 1 到 N 的累加和。",
  "sample_input": "5\n",
  "sample_output": "15\n",
  "public_cases": [{"input_data": "5\n", "expected_output": "15\n"}]
}
```

> `public_cases` 只包含公开用例。**非公开用例不会以任何形式返回**，不要尝试构造。

### 3.4 提交代码（核心）

`POST /api/v1/submissions`

```json
{
  "problem_id": 1,
  "student_id": "demo-student-01",
  "language": "c",
  "source_code": "#include <stdio.h>\nint main(void){return 0;}"
}
```

| 字段 | 约束 |
|---|---|
| `problem_id` | 正整数 |
| `student_id` | 3~64 位，仅字母、数字、下划线、短横线；演示可用固定值 |
| `language` | 只能是 `"c"` |
| `source_code` | 1~16384 字节 |

响应（同步返回，实测最长约 10 秒）：

```json
{
  "submission_id": "sub-1a2b3c4d5e6f",
  "problem_id": 1,
  "status": "WRONG_ANSWER",
  "passed_cases": 0,
  "total_cases": 4,
  "execution_time_ms": 703,
  "diagnosis": {
    "category": "OUTPUT_MISMATCH",
    "knowledge_point": "循环结构",
    "evidence": "题目「1 到 N 求和」公开用例 1 未通过：预期输出「15」，实际输出「10」（状态 WRONG_ANSWER）",
    "source": "RULE",
    "confidence": "MEDIUM",
    "possible_cause": "输出内容与题目预期不一致，具体逻辑原因需结合代码进一步确认",
    "certainty": "待确认"
  },
  "message": "",
  "cases": [
    {"case_index": 1, "is_public": true, "status": "WRONG_ANSWER", "execution_time_ms": 8,
     "expected_output": "15\n", "actual_output": "10\n", "error_message": null},
    {"case_index": 3, "is_public": false, "status": "WRONG_ANSWER", "execution_time_ms": 8,
     "expected_output": null, "actual_output": null, "error_message": null}
  ]
}
```

字段语义：

- `status`：见下表，决定结果面板主色。
- `diagnosis`：**`ACCEPTED` 时为 `null`**，前端必须处理空值。
- `message`：编译错误时是清理后的 GCC 错误信息，其它情况为空字符串。
- `cases[].case_index`：**从 1 开始**。
- `cases[].is_public=false` 时 `expected_output` / `actual_output` 恒为 `null`，只能显示「未通过 / 通过」。
- `execution_time_ms` 包含容器启动开销，约 700 ms，不要在前端自行换算成"算法耗时"。

`status` 枚举与展示建议：

| 值 | 含义 | 建议文案/颜色 |
|---|---|---|
| `ACCEPTED` | 全部通过 | 通过 / 绿 |
| `COMPILATION_ERROR` | 编译失败 | 编译错误 / 橙 |
| `WRONG_ANSWER` | 输出不符 | 答案错误 / 红 |
| `RUNTIME_ERROR` | 运行异常 | 运行错误 / 红 |
| `TIME_LIMIT_EXCEEDED` | 超时 | 运行超时 / 橙 |
| `RESOURCE_LIMIT_EXCEEDED` | 资源超限 | 资源超限 / 橙 |
| `SYSTEM_ERROR` | 评测内部错误 | 系统错误 / 灰 |
| `JUDGE_UNAVAILABLE` | 评测环境不可用 | 评测服务不可用 / 灰 |

### 3.5 查询历史提交

`GET /api/v1/submissions/{submission_id}`

返回结构与 3.4 完全一致（含 `cases` 与 `diagnosis`）。

### 3.6 分层提示

`POST /api/v1/submissions/{submission_id}/hints`

```json
{"level": 1}
```

```json
{
  "submission_id": "sub-1a2b3c4d5e6f",
  "level": 1,
  "source": "RULE",
  "knowledge_point": "循环结构",
  "hint": "这道题的核心是循环结构。请重点检查循环变量、循环条件和每轮的更新方式。",
  "is_fallback": true
}
```

规则（前端必须遵守）：

- 必须 1 → 2 → 3 顺序请求，跳级会返回 400。
- 同一提交已获取的层可直接再次请求，内容不变（前端可缓存）。
- 已 `ACCEPTED` 的提交请求提示会返回 400 `HINT_NOT_AVAILABLE`，此时隐藏提示区。
- **每次重新提交都会产生新的 `submission_id`，提示进度重置。**
- `source=RULE` 且 `is_fallback=true` 表示 AI 不可用、使用规则提示，界面上要如实标注「规则提示」，不能显示成「AI 生成」。

### 3.7 学生学习记录

`GET /api/v1/students/{student_id}/progress`

```json
{
  "student_id": "demo-student-01",
  "total_submissions": 2,
  "accepted_count": 1,
  "error_category_distribution": {"OUTPUT_MISMATCH": 1},
  "per_problem": [
    {"problem_id": 1, "title": "1 到 N 求和", "submissions": 2, "accepted": 1}
  ],
  "hint_usage": {"level_1": 1, "level_2": 1, "level_3": 1, "fallback_count": 3},
  "recent_submissions": [
    {"submission_id": "sub-8dce3456e8d2", "problem_id": 1, "status": "ACCEPTED",
     "error_category": "NONE", "passed_cases": 4, "total_cases": 4,
     "execution_time_ms": 752, "submitted_at": "2026-10-23T04:04:11.258760"}
  ]
}
```

- 无记录时返回全 0 与空数组（不会 404），前端显示「暂无数据」。
- `recent_submissions[].error_category` 在通过时为内部标记 `"NONE"`，**不要把它当成错因展示**。
- `submitted_at` 是**不带时区后缀的 UTC 时间字符串**（后端 MySQL 统一存 UTC 无时区，精度到微秒）。前端展示时需 `new Date(value.endsWith('Z') ? value : value + 'Z')` 再格式化，否则本地时间会差 8 小时。

### 3.8 教师端统计

`GET /api/v1/teacher/overview`

```json
{
  "total_submissions": 2,
  "distinct_students": 1,
  "accepted_submissions": 1,
  "per_problem": [
    {"problem_id": 1, "title": "1 到 N 求和", "submissions": 2, "accepted": 1, "unique_students": 1}
  ],
  "error_distribution": {"OUTPUT_MISMATCH": 1},
  "knowledge_point_errors": [{"knowledge_point": "循环结构", "count": 1}],
  "completed_problem_count": 1,
  "hint_usage": {"level_1": 1, "level_2": 1, "level_3": 0, "fallback_count": 0},
  "system_error_count": 0,
  "pending_tutoring": [
    {
      "student_id": "demo-student-02",
      "problem_id": 1,
      "problem_title": "1 到 N 求和",
      "last_submission_id": "sub-1a2b3c4d5e6f",
      "last_status": "WRONG_ANSWER",
      "submission_count": 3,
      "failure_count": 3,
      "max_hint_level": 2,
      "last_submitted_at": "2026-10-23T04:04:11.258760"
    }
  ],
  "pending_tutoring_rule": "同一学生同一题至少 3 次学生代码失败且最近一次仍未通过，或已解锁第 3 层提示且最近一次仍未通过；最近一次通过即移出；SYSTEM_ERROR 不计入学生失败。列表仅建议教师查看，不代表能力判断。",
  "generated_at": "2026-10-23T04:04:11.258760"
}
```

`generated_at` 同样按 UTC 处理。`hint_usage` 只统计已解锁（实际返回给学生）的提示层，
AI 预生成但尚未解锁的层级不计入。

### 3.9 错误响应

所有错误统一为：

```json
{"error": {"code": "JUDGE_UNAVAILABLE", "message": "评测服务不可用：Docker 守护进程未运行", "detail": null}}
```

| HTTP | code | 前端处理 |
|---|---|---|
| 400 | `HINT_LEVEL_INVALID` | 用 `detail`（字符串形式的下一层）更新按钮可用层级 |
| 400 | `HINT_NOT_AVAILABLE` | 隐藏提示区并提示「本题已通过」 |
| 401 | `UNAUTHORIZED` | 提示令牌缺失或错误 |
| 503 | `DEMO_TOKEN_NOT_CONFIGURED` | 后端未配置演示令牌，提示联系开发者 |
| 503 | `DATABASE_UNAVAILABLE` | MySQL 依赖故障，显示「数据库异常」，保留当前代码，禁止自动重试 |
| 404 | `PROBLEM_NOT_FOUND` / `SUBMISSION_NOT_FOUND` | 显示空状态，不弹技术错误 |
| 422 | `VALIDATION_ERROR` | 把 `detail` 直接展示在表单下方（如代码超长） |
| 429 | `RATE_LIMITED` | 提示「提交过于频繁，请稍后再试」，禁用提交按钮 60 秒 |
| 503 | `JUDGE_UNAVAILABLE` | 顶部常驻警告条，禁止自动重试 |
| 500 | `INTERNAL_ERROR` | 通用失败提示，保留当前代码不清空 |

**任何情况下都不要因为请求失败而清空编辑器内容。**

## 四、TypeScript 类型（可直接使用）

```ts
export type SubmissionStatus =
  | 'ACCEPTED' | 'COMPILATION_ERROR' | 'WRONG_ANSWER' | 'RUNTIME_ERROR'
  | 'TIME_LIMIT_EXCEEDED' | 'RESOURCE_LIMIT_EXCEEDED' | 'SYSTEM_ERROR' | 'JUDGE_UNAVAILABLE'

export type DiagnosisCategory =
  | 'SYNTAX_ERROR' | 'LOOP_BOUNDARY_ERROR' | 'CONDITION_ERROR'
  | 'VARIABLE_ERROR' | 'OUTPUT_MISMATCH' | 'UNKNOWN_ERROR'

export type DiagnosisSource = 'RULE' | 'AI' | 'HUMAN'
export type Confidence = 'HIGH' | 'MEDIUM' | 'LOW' | 'UNDETERMINED'
export type HintSource = 'RULE' | 'AI'

export interface ProblemListItem {
  id: number
  title: string
  difficulty: string
  knowledge_points: string[]
}

export interface PublicCase { input_data: string; expected_output: string }

export interface ProblemDetail extends ProblemListItem {
  description: string
  input_description: string
  output_description: string
  sample_input: string
  sample_output: string
  public_cases: PublicCase[]
}

export interface Diagnosis {
  category: DiagnosisCategory
  knowledge_point: string
  evidence: string
  source: DiagnosisSource
  confidence: Confidence
  possible_cause: string
  certainty: string
}

export interface CaseResult {
  case_index: number
  is_public: boolean
  status: SubmissionStatus
  execution_time_ms: number
  expected_output: string | null
  actual_output: string | null
  error_message: string | null
}

export interface SubmissionResult {
  submission_id: string
  problem_id: number
  status: SubmissionStatus
  passed_cases: number
  total_cases: number
  execution_time_ms: number
  diagnosis: Diagnosis | null
  message: string
  cases: CaseResult[]
}

export interface Hint {
  submission_id: string
  level: 1 | 2 | 3
  source: HintSource
  knowledge_point: string
  hint: string
  is_fallback: boolean
}

export interface HintUsage {
  level_1: number; level_2: number; level_3: number; fallback_count: number
}

export interface ProblemProgress {
  problem_id: number; title: string; submissions: number; accepted: number
}

export interface SubmissionSummary {
  submission_id: string
  problem_id: number
  status: SubmissionStatus
  error_category: string
  passed_cases: number
  total_cases: number
  execution_time_ms: number
  submitted_at: string
}

export interface StudentProgress {
  student_id: string
  total_submissions: number
  accepted_count: number
  error_category_distribution: Record<string, number>
  per_problem: ProblemProgress[]
  hint_usage: HintUsage
  recent_submissions: SubmissionSummary[]
}

export interface ProblemOverview extends ProblemProgress { unique_students: number }

export interface PendingTutoringItem {
  student_id: string
  problem_id: number
  problem_title: string
  last_submission_id: string
  last_status: string
  submission_count: number
  failure_count: number
  max_hint_level: number
  last_submitted_at: string
}

export interface TeacherOverview {
  total_submissions: number
  distinct_students: number
  accepted_submissions: number
  per_problem: ProblemOverview[]
  error_distribution: Record<string, number>
  knowledge_point_errors: { knowledge_point: string; count: number }[]
  completed_problem_count: number
  hint_usage: HintUsage
  system_error_count: number
  pending_tutoring: PendingTutoringItem[]
  pending_tutoring_rule: string
  generated_at: string
}

export interface ApiErrorBody {
  error: { code: string; message: string; detail: string | null }
}
```

## 五、页面与交互要求

### 5.1 题目列表 `/`

- 卡片展示：标题、难度标签、知识点标签。
- 点击进入 `/problems/:id`。
- 顶部显示评测环境状态（读 `/health`）。

### 5.2 练习页 `/problems/:id`

布局：左题面（描述、输入/输出要求、示例），右编辑器。

- 编辑器默认填入一段 C 语言模板（`#include <stdio.h>` + `main` 空壳）。
- 「提交评测」按钮：点击后进入 loading，禁用按钮，显示「正在评测…」；请求最坏约 10 秒，**不要加 5 秒超时**。
- 结果面板：
  - 状态徽标（按 3.4 颜色表）
  - 通过数 / 总数、耗时
  - `COMPILATION_ERROR` 时用等宽字体展示 `message`
  - 用例列表：公开用例展示「预期 / 实际」双栏对比（用 `<pre>` 保留空白）；非公开用例只显示「通过 / 未通过」
  - 诊断卡片：类别、知识点、证据原文、可能原因（`possible_cause`）、确定程度（`certainty`，文字化）、来源（规则/AI/人工）、置信度
- 提示区：
  - 三个按钮「提示 1/2/3」，只有下一层可点，已获取的层可重新展开
  - 每条提示标注来源：`AI 提示` 或 `规则提示（AI 不可用）`
  - 已通过时整块隐藏
- 重新提交后清空上一轮的提示与结果。

### 5.3 数据看板 `/dashboard`

- 学生视图：总提交、通过数、错因分布（条形图或标签计数）、分题提交/通过、提示使用、最近 10 条记录（点击可跳回对应提交详情）。
- 教师视图：提交总数、学生数、分题情况、错误分布、知识点错误分布、完成题目数、提示使用、生成时间。
- 教师待辅导表格（`pending_tutoring`）：匿名学生、题目、最近提交结果、提交次数、失败次数、
  最高已解锁提示层级、最后提交时间、查看失败依据/提交记录的入口。
  页面需原样展示 `pending_tutoring_rule` 规则说明；列表只表示“建议教师查看”，不得判定学生能力。
- 学生 ID 用一个输入框或固定演示值 `demo-student-01`，不做登录。
- 空数据时显示「暂无数据」，**不允许前端造数**。

## 六、验收标准（必须逐条自测）

1. 题目列表能拉到 3 道题，中文不乱码。
2. 提交 `i < n` 的错误代码 → 显示 `WRONG_ANSWER`、公开用例预期 15 / 实际 10、诊断 `OUTPUT_MISMATCH`。
3. 依次能拿到 3 层提示；直接点第 3 层时按钮不可用（或后端 400 后正确回退）。
4. 提示标签如实显示 `AI 提示` 或 `规则提示（AI 不可用）`，不能把 RULE 伪装成 AI。
5. 改成 `i <= n` 后提交 → `ACCEPTED`，提示区隐藏。
6. 看板数字与后端 `/students/{id}/progress`、`/teacher/overview` 完全一致。
7. 关掉 Docker 后提交 → 显示 503 警告，编辑器内容不丢失，不自动重试。
8. 提交后刷新页面，历史记录与提交详情仍可查询。

## 七、明确禁止

1. 前端硬编码任何统计数字、通过率、班级人数。
2. 伪造「AI 生成」提示；`source=RULE` 必须如实标注。
3. 用本地 mock 数据替代真实接口（可写类型定义，不可造响应）。
4. 编造后端没有的字段或接口；缺字段先看 `/openapi.json`。
5. 展示非公开测试用例的输入或预期输出（后端本就不返回，前端也不要猜）。
6. 为了"好看"给评测结果加动画而延迟展示真实状态。
7. 引入登录、支付、课程管理等任务书排除的功能。

## 八、交付物

- `codepilot-edu-frontend/` 可运行工程（`npm install && npm run dev`）
- 页面截图（题目列表、错误提交结果、三层提示、通过结果、看板）
- 一页 `README.md`：启动方式、端口、依赖
- 与后端联调的真实记录（哪些接口调通、哪些异常验证过）

## 九、联调前检查

```powershell
# 后端与 MySQL 是否就绪（无需令牌）
curl http://127.0.0.1:8000/health

# 是否有题目数据（需要演示令牌）
curl http://127.0.0.1:8000/api/v1/problems -Headers @{ "X-Demo-Token" = $env:DEMO_TOKEN }
```

若 `docker=false`，先启动 Docker Desktop，再确认 `judge-c:latest` 镜像存在。
若 `database=false`，执行 `docker compose up -d` 并等待 MySQL 健康检查通过。
