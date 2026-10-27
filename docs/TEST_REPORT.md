# 测试记录（真实执行结果 · 2026-10-24，覆盖 2026-10-23 版本）

本报告对应 2026-10-24 冻结前代码（含当日修复：用例数超上限拒绝、评测排队繁忙提示、
教师页待辅导表格接入、提示拒绝话术、移除预留枚举、`generated_at` 统一无时区后缀）。
上一版报告（2026-10-23）的 41 项结果无法与现行代码互证（pytest 缓存测试集与现行不一致），
已用本次全新执行结果整体替代。

## 1. 测试环境

| 项目 | 值 |
|---|---|
| 执行日期 | 2026-10-24 |
| 操作系统 | Windows 11 + WSL2 |
| Python | 3.13.15（项目虚拟环境 `.venv`） |
| FastAPI / Pydantic / SQLAlchemy / httpx | 0.161.1 / 2.14.1 / 2.1.6 / 0.28.1 |
| PyMySQL（运行时 import 实测） | 2.2.8 |
| Docker | Docker Desktop 29.9.2（linux 容器） |
| 评测镜像 | `judge-c:latest`（python:3.12-slim-bookworm + gcc） |
| 数据库 | MySQL 8.4.13（InnoDB / utf8mb4，`SELECT VERSION()` 实测），业务账号非 root |
| 测试库 | `codepilot_edu_test`（真实 MySQL，conftest 强制校验库名后缀，不使用 SQLite） |
| AI | 本地兼容 OpenAI Chat Completions 接口（127.0.0.1:31415），`source=AI` 已实测并复演 |

## 2. 自动化测试执行（2026-10-24）

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

实际输出：

```
..........................................                               [100%]
42 passed, 1 warning in 19.74s
```

| 分组 | 用例数 | 结果 |
|---|---|---|
| 单元测试 `tests/unit` | 32 | 全部通过 |
| 集成测试 `tests/integration`（真实 Docker） | 10 | 全部通过 |

### 单元测试覆盖

| 文件 | 覆盖点 |
|---|---|
| `test_diagnosis.py` | ACCEPTED / SYSTEM_ERROR 无学生诊断；WA + 公开证据 → OUTPUT_MISMATCH；仅非公开用例失败 → UNKNOWN_ERROR；编译错误 → SYNTAX_ERROR；超时不臆断为循环边界错误 |
| `test_container_security.py` | 容器参数包含禁网、只读、cap-drop ALL、no-new-privileges、非 root、内存/CPU/进程限制；参数以列表传递 |
| `test_api_basics.py` | 健康检查双状态、全部 `/api/v1` 路由令牌校验（缺失返回 401）、服务端未配置令牌失败关闭（503）、MySQL 不可用返回 503 `DATABASE_UNAVAILABLE`、题目列表/详情、非公开用例不泄露、参数校验、源码大小限制、非法提交 ID、Docker 不可用返回 503 且不回退、**用例数超过上限返回 500 `PROBLEM_MISCONFIGURED`（2026-10-24 新增，防静默截断）** |
| `test_hints.py` | 提示不可跳级、AI 未配置时 RULE 降级、重复请求一致、已通过/系统故障提交拒绝提示、AI 预生成的未解锁层级不可跳读、并发同层只产生一条记录 |
| `test_mysql_behavior.py` | 引擎为真实 MySQL + utf8mb4 + InnoDB、中文源码/诊断往返、种子幂等且不清空历史提交 |
| `test_teacher_pending.py` | 教师待辅导规则：3 次失败仍未过、解锁第 3 层仍未过、最近通过移出、SYSTEM_ERROR 不计学生错、未解锁层级不计入 |

### 集成测试覆盖（真实容器）

| 编号 | 场景 | 预期结果 | 实际结果 | 结论 |
|---|---|---|---|---|
| T01 | 三道题的正确解 | ACCEPTED，诊断为空 | 3/3 ACCEPTED，`diagnosis=null` | 通过 |
| T02 | C 语言语法错误 | COMPILATION_ERROR | COMPILATION_ERROR，诊断 SYNTAX_ERROR | 通过 |
| T03 | 循环边界错误（`i < n`） | WRONG_ANSWER + 证据 | WRONG_ANSWER，诊断 OUTPUT_MISMATCH（未臆断为 LOOP_BOUNDARY_ERROR） | 通过 |
| T04 | 输出格式不符合题意 | WRONG_ANSWER | WRONG_ANSWER，0/4 通过 | 通过 |
| T05 | 死循环 | TIME_LIMIT_EXCEEDED | TIME_LIMIT_EXCEEDED | 通过 |
| T06 | 空指针写入 | RUNTIME_ERROR | RUNTIME_ERROR | 通过 |
| T10 | 无限输出 | 资源限制生效，响应体受限 | RESOURCE_LIMIT_EXCEEDED，响应体受限 | 通过 |
| X02/X03 | 执行后无容器残留 | 无 `judge-*` 容器 | `docker ps -aq --filter name=judge-` 为空 | 通过 |

## 3. 评测环境自检（2026-10-24）

```powershell
.\.venv\Scripts\python.exe scripts\smoke_docker.py
```

真实输出：

```
[1] Docker 守护进程: OK
[2] 评测镜像 judge-c:latest: OK
[3] 正确程序 → ACCEPTED: ACCEPTED OK
[4] 语法错误 → COMPILATION_ERROR: COMPILATION_ERROR OK
[5] 循环边界错误 → WRONG_ANSWER: WRONG_ANSWER OK
[6] 死循环 → TIME_LIMIT_EXCEEDED: TIME_LIMIT_EXCEEDED OK
[7] 空指针写入 → RUNTIME_ERROR: RUNTIME_ERROR OK
[8] 巨量输出 → RESOURCE_LIMIT_EXCEEDED: RESOURCE_LIMIT_EXCEEDED OK
[9] 容器残留检查: OK

结果：全部通过
```

## 4. 端到端演示验证（2026-10-24 复演，AI 真实调用）

```powershell
docker compose up -d
.\.venv\Scripts\python.exe scripts\init_db.py
.\.venv\Scripts\python.exe scripts\seed_data.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe scripts\demo.py
```

复演留档：`%TEMP%\codepilot-demo-replay.log`。关键实测结果：

| 步骤 | 实际结果 | 结论 |
|---|---|---|
| 查看题目 | 返回 3 道题，中文正常 | 通过 |
| 正确代码基线 | ACCEPTED，4/4 | 通过 |
| 语法错误 | COMPILATION_ERROR；诊断 SYNTAX_ERROR，确定程度"有明确依据" | 通过 |
| 边界错误 | WRONG_ANSWER，0/4；公开用例 1 预期 15、实际 10；诊断 OUTPUT_MISMATCH，确定程度"待确认" | 通过 |
| 请求第 1 层 | **`source=AI`、`is_fallback=false`**，内容指向循环初始值/终止条件/迭代范围 | 通过 |
| 直接请求第 3 层 | 400 `HINT_LEVEL_INVALID`，提示下一次可请求第 2 层 | 通过 |
| 请求第 2 层 | 200，`source=AI`，内容点名学生代码 `i < n`；未重复调用模型 | 通过 |
| 修改后再次提交 | ACCEPTED，4/4 | 通过 |
| 学生进度 | 错因分布 OUTPUT_MISMATCH / SYNTAX_ERROR，提示使用 level_1=4 / level_2=3 / fallback=1 | 通过 |
| 教师端 | 汇总由真实记录计算；最近提交已通过 → 待辅导列表为 0（规则"通过即移出"生效） | 通过 |

AI 输入只含题意、学生代码、评测状态与公开证据；隐藏用例未出现在任何提示词或响应中。

补充验证（2026-10-24）：用演示学号 `demo-student-02` 连续提交 3 次边界错误代码后，
`GET /api/v1/teacher/overview` 返回该生的待辅导条目（failure_count=3、last_status=WRONG_ANSWER、
max_hint_level=0），且 `generated_at` / `last_submitted_at` 均为无时区后缀的 UTC 字符串。

## 5. 浏览器人工验证（2026-10-24，Chrome 1280×720）

| 检查点 | 实际结果 | 结论 |
|---|---|---|
| `/teacher` 待辅导表格 | 首屏卡片展示两条真实待辅导记录（demo-student-01 17/10 第 3 层、demo-student-02 3/3 未使用），含判定规则说明与"查看题目"入口 | 通过 |
| `/problems/999` 空态 | 显示"题目没有加载出来"卡片 + 重新加载/返回按钮，提交按钮禁用，toast"题目不存在或已下线" | 通过 |
| 提交 → 证据链路 | 载入演示错误代码 → 提交 → "答案错误 0/4"、公开用例预期/实际对照、错因诊断"输出不符（规则诊断·可信度中）"、非公开用例只显示状态 | 通过 |
| 纠错阶梯 | 第 1 层返回内容且来源标注"**AI 提示 · 由大模型基于题目与诊断证据生成**"，第 2 层"可获取"、第 3 层"待解锁" | 通过 |
| 编辑器保留 | 刷新页面后代码草稿仍在（localStorage 恢复） | 通过 |

说明：浏览器验证未接入控制台日志监听，以页面可见表现为准；验证期间未观察到错误表现。

## 6. 未覆盖项（如实说明）

| 项目 | 状态 | 原因 |
|---|---|---|
| AI 正式厂商/公网环境复验 | 未执行 | 已在本地兼容 OpenAI 接口完成真实调用（2026-10-23 首测、2026-10-24 复演留档）；未使用正式厂商账号与公网链路 |
| AI 证据一致性人工复核流程 | 未建立 | 已做结构校验与长度限制；证据矛盾的人工复核仍由开发者承担 |
| 全班并发压测 | 未执行 | P0 仅要求单机演示；评测并发上限 2，MySQL 连接池 5+5 |
| 恶意代码逃逸测试 | 未执行 | 依赖 Docker 默认 seccomp，未做渗透测试 |
| 评测排队繁忙路径（`JUDGE_BUSY_TIMEOUT_SECONDS`） | 未自动化覆盖 | 已实现（排队超 10 秒返回 503 JUDGE_UNAVAILABLE），并发触发需多端同时提交，暂靠人工验证 |
| 移动端触控目标 < 44px | 未修复 | 本次按约定先修桌面演示链路，移动端细节延后 |
| Alembic 迁移 | 未引入 | 当前由 `init_db.py` 建表；后续 schema 变更需手写迁移 |

## 7. 演示数据说明

演示数据库（MySQL `codepilot_edu`）当前记录均来自 `scripts/demo.py` 演示流程与固定演示学号
（`demo-student-01`、`demo-student-02`），属于演示数据，不是真实学生试用数据；2026-10-24 复演
后累计提交 21 条、参与学号 2 个。演示前如需干净画面，按 README §10 备份后自行评估是否清理，
不要直接清库。

## 8. 复现方式

```powershell
docker compose up -d
.\.venv\Scripts\python.exe scripts\init_db.py
.\.venv\Scripts\python.exe scripts\seed_data.py
docker build -t judge-c:latest runner/
.\.venv\Scripts\python.exe scripts\smoke_docker.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe scripts\demo.py
```
