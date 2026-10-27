# CodePilot Edu 后端 API 说明（P0）

统一前缀：`/api/v1`；所有业务数据使用 JSON。
交互式文档：启动服务后访问 `http://127.0.0.1:8000/docs`。

## 通用错误结构

```json
{"error": {"code": "JUDGE_UNAVAILABLE", "message": "评测服务不可用：Docker 守护进程未运行", "detail": null}}
```

| HTTP | code | 说明 |
|---|---|---|
| 400 | `HINT_LEVEL_INVALID` | 提示层級跳跃，`detail` 为下一次可请求的层级 |
| 400 | `HINT_NOT_AVAILABLE` | 该提交已通过，不再提供纠错提示 |
| 401 | `UNAUTHORIZED` | 演示令牌缺失或不匹配 |
| 503 | `DEMO_TOKEN_NOT_CONFIGURED` | 后端未配置演示令牌，接口失败关闭 |
| 404 | `PROBLEM_NOT_FOUND` / `SUBMISSION_NOT_FOUND` | 资源不存在 |
| 422 | `VALIDATION_ERROR` | Pydantic 参数校验失败 |
| 429 | `RATE_LIMITED` | 单学生每分钟超过 10 次提交 |
| 503 | `JUDGE_UNAVAILABLE` | Docker 或评测镜像不可用；**不会回退宿主机执行** |
| 503 | `DATABASE_UNAVAILABLE` | MySQL 依赖不可用；**不会回退 SQLite/内存库** |
| 500 | `INTERNAL_ERROR` | 未预期异常 |

## 演示令牌

除 `GET /health` 外，所有 `/api/v1/*` 接口都要求请求头：

```
X-Demo-Token: <与后端 .env 的 DEMO_TOKEN 一致>
```

这是演示身份，不是正式认证；令牌缺失/错误返回 401，后端未配置令牌返回 503。

## 接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查，区分 API、MySQL 依赖与 Docker 评测环境 |
| GET | `/api/v1/problems` | 题目列表 |
| GET | `/api/v1/problems/{id}` | 题目详情（仅返回公开用例） |
| POST | `/api/v1/submissions` | 提交代码并同步返回评测结果 |
| GET | `/api/v1/submissions/{id}` | 查询历史提交结果 |
| POST | `/api/v1/submissions/{id}/hints` | 请求下一层提示 |
| GET | `/api/v1/students/{id}/progress` | 学生学习记录与统计 |
| GET | `/api/v1/teacher/overview` | 教师端汇总 + 由真实记录计算的待辅导列表 |

## 提交请求

```json
{
  "problem_id": 1,
  "student_id": "demo-student-01",
  "language": "c",
  "source_code": "#include <stdio.h>\nint main(void){return 0;}"
}
```

约束：`language` 仅接受 `"c"`；`source_code` ≤ 16384 字节；`student_id` 为 3~64 位字母数字下划线或短横线。

## 评测响应

```json
{
  "submission_id": "sub-1a2b3c4d5e6f",
  "problem_id": 1,
  "status": "WRONG_ANSWER",
  "passed_cases": 1,
  "total_cases": 4,
  "execution_time_ms": 320,
  "diagnosis": {
    "category": "OUTPUT_MISMATCH",
    "knowledge_point": "循环结构",
    "evidence": "题目「1 到 N 求和」公开用例 1 未通过：预期输出「15」，实际输出「10」（状态 WRONG_ANSWER）",
    "source": "RULE",
    "confidence": "MEDIUM"
  },
  "message": "",
  "cases": [
    {"case_index": 1, "is_public": true, "status": "WRONG_ANSWER", "execution_time_ms": 8,
     "expected_output": "15", "actual_output": "10", "error_message": null},
    {"case_index": 3, "is_public": false, "status": "WRONG_ANSWER", "execution_time_ms": 8,
     "expected_output": null, "actual_output": null, "error_message": null}
  ]
}
```

状态取值：`ACCEPTED`、`COMPILATION_ERROR`、`WRONG_ANSWER`、`RUNTIME_ERROR`、`TIME_LIMIT_EXCEEDED`、`RESOURCE_LIMIT_EXCEEDED`、`SYSTEM_ERROR`、`JUDGE_UNAVAILABLE`。

诊断类别：`SYNTAX_ERROR`、`LOOP_BOUNDARY_ERROR`、`CONDITION_ERROR`、`VARIABLE_ERROR`、`OUTPUT_MISMATCH`、`UNKNOWN_ERROR`。诊断与评测状态解耦，`WRONG_ANSWER` 默认不会自动升级为 `LOOP_BOUNDARY_ERROR`。

`ACCEPTED` 时 `diagnosis` 为 `null`，内部 `error_category` 记为 `NONE`。

## 输出比较规则

1. 逐行比较，每行去掉行尾空白；
2. 忽略文末多余空行；
3. 不忽略行内差异、大小写差异，不做模糊匹配；
4. 单个用例输出最多保留 4096 字节，超出标记 `truncated`；
5. 非公开用例只返回状态与耗时。

## 提示接口

请求 `{"level": 1}`；响应：

```json
{
  "submission_id": "sub-1a2b3c4d5e6f",
  "level": 1,
  "source": "RULE",
  "knowledge_point": "循环结构",
  "hint": "评测已确认输出与预期不符。先明确题目要求的输出格式与计算目标……",
  "is_fallback": true
}
```

- 必须按 1 → 2 → 3 顺序请求，跳级返回 400 并告知下一个可请求层级。
- 首次请求会尝试一次性生成三层并入库；AI 不可用时降级为规则提示，`source=RULE` 且 `is_fallback=true`。
- 同一提交的同一层级提示内容保持不变。
