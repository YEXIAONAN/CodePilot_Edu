# 测试记录（真实执行结果 · 2026-10-23）

## 1. 测试环境

| 项目 | 值 |
|---|---|
| 执行日期 | 2026-10-23 |
| 操作系统 | Windows 11 + WSL2 |
| Python | 3.13.15（项目虚拟环境 `.venv`） |
| FastAPI / Pydantic / SQLAlchemy / httpx | 0.161.1 / 2.14.1 / 2.1.6 / 0.28.1 |
| Docker | Docker Desktop 29.9.2（linux 容器） |
| 评测镜像 | `judge-c:latest`（python:3.12-slim-bookworm + gcc） |
| 数据库 | MySQL 8.4.13（InnoDB / utf8mb4_0900_ai_ci），PyMySQL 1.2.3 |
| 测试库 | `codepilot_edu_test`（真实 MySQL，不使用 SQLite） |
| AI | 本地兼容 OpenAI Chat Completions 接口（`source=AI` 已实测） |

## 2. 自动化测试执行

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

实际输出：

```
.........................................                                [100%]
41 passed, 1 warning in 18.61s
```

| 分组 | 用例数 | 结果 |
|---|---|---|
| 单元测试 `tests/unit` | 31 | 全部通过 |
| 集成测试 `tests/integration`（真实 Docker） | 10 | 全部通过 |

### 单元测试覆盖

| 文件 | 覆盖点 |
|---|---|
| `test_diagnosis.py` | ACCEPTED / SYSTEM_ERROR 无学生诊断；WA + 公开证据 → OUTPUT_MISMATCH；仅非公开用例失败 → UNKNOWN_ERROR；编译错误 → SYNTAX_ERROR；超时不臆断为循环边界错误 |
| `test_container_security.py` | 容器参数包含禁网、只读、cap-drop ALL、no-new-privileges、非 root、内存/CPU/进程限制；参数以列表传递 |
| `test_api_basics.py` | 健康检查双状态、全部 7 条 `/api/v1` 路由的令牌校验（缺失返回 401）、服务端未配置令牌失败关闭（503）、MySQL 不可用返回 503 `DATABASE_UNAVAILABLE`、题目列表/详情、非公开用例不泄露、参数校验、源码大小限制、非法提交 ID、Docker 不可用返回 503 且不回退 |
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
| T10 | 无限输出 | 资源限制生效，响应体受限 | RESOURCE_LIMIT_EXCEEDED，响应体 < 20 KB | 通过 |
| X02/X03 | 执行后无容器残留 | 无 `judge-*` 容器 | `docker ps -aq --filter name=judge-` 为空 | 通过 |

## 3. 评测环境自检

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

## 4. 端到端演示验证

```powershell
docker compose up -d
.\.venv\Scripts\python.exe scripts\init_db.py
.\.venv\Scripts\python.exe scripts\seed_data.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe scripts\demo.py
```

| 步骤 | 实际结果 | 结论 |
|---|---|---|
| 查看题目 | 返回 3 道题，中文正常 | 通过 |
| 正确代码基线 | ACCEPTED，4/4 | 通过 |
| 语法错误 | COMPILATION_ERROR；诊断 SYNTAX_ERROR，确定程度“有明确依据” | 通过 |
| 边界错误 | WRONG_ANSWER，0/4；公开用例 1 预期 15、实际 10；诊断 OUTPUT_MISMATCH，确定程度“待确认” | 通过 |
| 请求第 1 层 | `source=AI`、`is_fallback=false`，内容为循环边界方向 | 通过 |
| 直接请求第 3 层 | 400 `HINT_LEVEL_INVALID`，提示下一次可请求第 2 层 | 通过 |
| 请求第 2 层 | 200，返回 AI 预生成的第 2 层；未重复调用模型 | 通过 |
| 修改后再次提交 | ACCEPTED，4/4 | 通过 |
| 学生进度 | 总提交 4、通过 2、错误分布 SYNTAX_ERROR/OUTPUT_MISMATCH、提示使用 level_1=1/level_2=1/level_3=0 | 通过 |
| 教师端 | 提交总数 4、学生 1、完成题目 1；最近提交已通过 → 待辅导列表为 0 | 通过 |

保存的提示记录为 3 条/次（AI 生成），其中第 1/2 层已解锁、第 3 层未解锁；统计未把未解锁层计入使用量。
重复执行两次演示后，数据库中累计 8 条提交、6 条提示（4 条已解锁），重启 MySQL 与后端后仍可查询。

## 5. 手工验证记录

| 编号 | 操作 | 预期 | 实际 | 结论 |
|---|---|---|---|---|
| M01 | 启动 `uvicorn app.main:app` | 服务可启动 | 启动成功，启动时确认 MySQL 可连接 | 通过 |
| M02 | `GET /health` | 区分 API 与 MySQL | `{"status":"ok","version":"0.2.0","api":"ok","database":true,"database_status":"ok","database_latency_ms":3,"docker":true}` | 通过 |
| M03 | `GET /api/v1/problems`（带令牌） | 3 道题，中文正常 | 返回 3 道题，UTF-8 正确 | 通过 |
| M04 | 停止 Docker 后提交（monkeypatch 模拟） | 503 `JUDGE_UNAVAILABLE`，不回退宿主执行 | 503，未执行任何本机编译 | 通过 |
| M05 | `init_db.py` + `seed_data.py`（各执行两次） | 建表并写入 3 题；重复跑不重复、不清历史 | 第一次 3 题/13 用例，第二次 0 新增；字符集校验通过 | 通过 |
| M06 | 重启 MySQL 容器与后端进程后查询 | 提交/提示仍在，中文无乱码 | 8 条提交、6 条提示（4 条已解锁）仍可查；提交证据与题目中文完整 | 通过 |
| M07 | 停止 MySQL 后请求业务接口 | 503 依赖故障，不返回 SQLite 数据 | 503 `DATABASE_UNAVAILABLE`；`/health` 200 `degraded`、database=false；重启后恢复 200 | 通过 |
| M08 | 并发两次请求同一层提示 | 数据库中只有一条有效记录 | pytest 并发用例通过，计数为 1 | 通过 |

## 6. 未覆盖项（如实说明）

| 项目 | 状态 | 原因 |
|---|---|---|
| AI 正式厂商/公网环境复验 | 未执行 | 已在本地兼容 OpenAI 接口完成真实调用；未使用正式厂商账号与公网链路复验 |
| AI 证据一致性人工复核流程 | 未建立 | 已做结构校验与长度限制；证据矛盾的人工复核仍由开发者承担 |
| 全班并发压测 | 未执行 | P0 仅要求单机演示；评测并发上限 2，MySQL 连接池 5+5 |
| 恶意代码逃逸测试 | 未执行 | 依赖 Docker 默认 seccomp，未做渗透测试 |
| 前端教师待辅导表格 | 未接入 | 后端已返回 `pending_tutoring`，页面展示待前端实现 |
| Alembic 迁移 | 未引入 | 当前由 `init_db.py` 建表；后续 schema 变更需手写迁移 |

## 7. 复现方式

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
