# 系统架构说明（P0 · MySQL 版）

## 1. 形态

轻量级单体后端：一个 FastAPI 进程 + 一个 MySQL 8.4 LTS 单实例 + 一个受限评测容器镜像。
不引入微服务、消息队列、缓存集群或容器编排。MySQL 通过 Docker Compose 启动，命名卷持久化，
与判题临时工作区分离。

## 2. 分层

```
app/api/             HTTP 层：参数校验、演示令牌、响应模型、HTTP 语义、异常映射
app/services/        业务层：评测编排、规则诊断、AI 提示、统计组装
app/repositories/    数据访问层：唯一执行 SQL 的位置
app/models/          SQLAlchemy 模型
app/schemas/         Pydantic 请求/响应模型
app/core/            配置、枚举、统一异常
runner/              容器内执行器与镜像定义（独立边界，可单独替换）
```

依赖方向单向：`api → services → repositories → models`；`runner` 不依赖 `app`。

## 3. 关键流程

### 提交与评测

1. `POST /api/v1/submissions` 校验演示令牌、参数（长度、语言、学生标识、题目存在）。
2. 读取题目与用例，构造纯数据 `CaseSpec` 列表。
3. **结束当前数据库事务**（`db.rollback()`），避免等待 Docker 评测期间持有 MySQL 连接/快照/行锁。
4. 以参数列表启动受限容器，宿主侧总超时 25 秒；探活放在线程池，不阻塞事件循环。
5. 容器内：`gcc -O1 -std=c11` 编译 → 逐用例运行（2 秒/用例）→ 输出落盘后截断到 4 KB。
6. 宿主解析 JSON，按优先级汇总状态：`SYSTEM_ERROR > RESOURCE_LIMIT > TIME_LIMIT > RUNTIME_ERROR > WRONG_ANSWER`，全部通过则为 `ACCEPTED`。
7. `diagnosis_service` 基于真实证据生成学习层面的诊断，同时保存结构化 JSON。
8. 在新短事务中写入 `submissions` 与 `evaluation_details`，返回结果。

### 分层提示

- 首次请求 `level=1`：尝试调用 AI 一次性生成三层 → 校验 → 入库。
  - 第 1 层 `is_unlocked=true`，第 2/3 层 `is_unlocked=false`，必须先按顺序请求才能读取。
  - AI 失败/未配置 → 只生成当前层规则提示，标记 `source=RULE, is_fallback=true`。
- 后续请求按“已解锁层级”判断：只允许请求 `max_unlocked + 1`；已获取层级直接返回原记录。
- AI 调用前同样结束数据库事务，避免外部模型等待期间占用连接。
- 写入使用 MySQL `INSERT ... ON DUPLICATE KEY UPDATE`，配合 `(submission_id, hint_level)` 唯一约束，
  并发请求同一层只保留一份有效记录，后到者回读先写入的内容。
- 统计只计入 `is_unlocked=true` 的提示，避免把 AI 预生成但尚未返回的层级算作已使用。

## 4. 数据模型

| 表 | 关键字段 | 说明 |
|---|---|---|
| `problems` | id/title/description/knowledge_points(JSON)/difficulty/sample_* | 题目 |
| `test_cases` | problem_id/input_data/expected_output/is_public/order_index | 公开与非公开用例 |
| `submissions` | id/student_id/problem_id/status/error_category/diagnosis_*/diagnosis_json/执行统计 | 每次提交一行 |
| `evaluation_details` | submission_id/test_case_id/status/time/输出（仅公开） | 单用例结果 |
| `hint_records` | submission_id/hint_level/content/source/is_fallback/is_unlocked | 三层提示 |

MySQL 约定：

- 所有表 InnoDB、`utf8mb4_0900_ai_ci`；连接串与客户端字符集 `utf8mb4`。
- 时间统一存 UTC 无时区，MySQL 使用 `DATETIME(6)`；前端按用户时区展示。
- 源码、提示、诊断证据使用 `TEXT`；结构化诊断使用 `JSON`。
- 索引：
  - `submissions(student_id, problem_id, submitted_at)`：学生历史与教师分组查询；
  - `submissions(problem_id)`：按题聚合与外键；
  - `hint_records` 唯一索引 `(submission_id, hint_level)`；
  - `evaluation_details(submission_id)`、`test_cases(problem_id)`。
- 唯一约束 `uq_hint_records_submission_level` 是提示并发正确性的最后防线。

## 5. 主要设计决策

| 决策 | 选择 | 原因 | 放弃的方案 |
|---|---|---|---|
| 主数据库 | MySQL 8.4 LTS + PyMySQL | 独立数据库服务、多人课堂持续写入、统一管理 | SQLite（已移除，无回退） |
| 评测隔离 | 每次评测启动独立容器，作业经 stdin 传入 | Windows 下 bind mount 到非 root 用户不可靠；`--rm` 保证清理 | 挂载宿主目录（权限不可控） |
| 单容器跑全部用例 | 一次启动完成编译 + 所有用例 | 省去 4~5 次容器启动开销 | 每用例一个容器（慢 1 秒以上） |
| 提交接口 | 同步返回完整结果 | 减少前端状态机与联调成本 | 异步队列 + 轮询（时间不足） |
| AI 提示 | 首次生成三层并持久化，逐层解锁 | 保证可复现、演示稳定，同时不破坏层级递进 | 每次按需生成（结果漂移）；一次返回三层（可跳级） |
| 输出比较 | 去行尾空白 + 忽略末尾空行 | 规则简单、可解释、可测试 | 模糊匹配/智能判题（不可解释） |
| 数据库故障 | 明确 503 `DATABASE_UNAVAILABLE` | 不伪装持久化成功 | 自动回退内存/SQLite |

## 6. 已知架构风险

- 同步评测会占用请求，评测并发上限 2，超出后排队；演示场景可接受，未做全班压测。
- MySQL 为单实例，未做复制/分库分表；连接池默认 5+5，池等待 5 秒。
- 容器冷启动约 200~400 ms，计入 `execution_time_ms`。
- 演示令牌是共享静态令牌，不是正式身份认证。
