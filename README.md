# CodePilot Edu 后端（P0 · MySQL 版）

## 1. 项目是什么

CodePilot Edu 是面向高校与职业院校程序设计初学者的智能实训平台。第一阶段聚焦 C 语言基础：
学生在网页编辑器中写代码并提交，后端在受限容器中编译与评测，给出**基于真实证据**的错因诊断，
并按一、二、三层递进给出纠错提示，最后把提交与提示使用过程记录下来，供教师查看待辅导列表与汇总。

设计原则：**评测负责判断程序行为，规则与 AI 负责解释错误，学习记录负责保存纠错过程。**
大模型不承担程序正确性的唯一判断。

本项目为第十届中华职业教育创新创业大赛本科组参赛作品的后端 P0 版本。当前只支持 C 语言、
单个演示班级与预置题目，不声称已支持 Java/Python，也不是正式教学平台。

## 2. 后端实现了什么

| 模块 | 状态 | 说明 |
|---|---|---|
| 题目管理 | 已实现 | 3 道题（求和 / 成绩等级 / 偶数累加），含公开与非公开用例 |
| C 代码评测 | 已实现 | Docker 受限容器内 GCC 编译、逐用例执行、输出比较 |
| 安全隔离 | 已实现 | 禁网、只读根文件系统、cap-drop ALL、非 root、内存/CPU/进程/时间/输出限制 |
| 结构化诊断 | 已实现 | 编译错误、输出不符、运行异常等归类；证据不足返回 UNKNOWN_ERROR；JSON 保存完整诊断 |
| 分层提示 | 已实现 | 三层递进、防跳级、AI 预生成但逐层解锁、同层并发唯一、AI 故障降级 RULE |
| 学习记录 | 已实现 | 提交、用例详情、提示记录落 MySQL，中文 UTF-8 往返 |
| 学生进度 | 已实现 | 个人提交/通过/错因分布/提示使用/最近记录 |
| 教师端 | 已实现 | 汇总统计 + 由真实记录计算的待辅导列表（透明规则） |
| 数据库 | 已实现 | MySQL 8.4 LTS（InnoDB / utf8mb4），PyMySQL，连接池与失效连接检测 |
| 测试 | 已实现 | 42 项自动化测试通过（2026-10-24 实测，真实 MySQL + 真实 Docker 评测，详见 docs/TEST_REPORT.md） |

## 3. 运行环境要求

- Windows 10/11（本机演示）或任意支持 Docker 的 Linux
- Python 3.11+（本机验证使用 3.13.15）
- Docker Desktop（WSL2 backend），用于运行 MySQL 与评测容器
- 磁盘约 2 GB（MySQL 镜像 + 评测镜像 + 数据卷）

## 4. 安装依赖

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" pydantic pydantic-settings `
  sqlalchemy "pymysql[rsa]" httpx pytest pytest-asyncio
```

核心依赖包含 `sqlalchemy>=2.0`、`pymysql[rsa]>=1.1`（含 caching_sha2_password 所需的
cryptography）与 `fastapi`。不建议只装 `pymysql` 而不装 RSA 依赖，否则首次连接
MySQL 8.4 默认认证插件可能失败。

## 5. 配置 .env

```powershell
Copy-Item .env.example .env
```

至少填写：

```
DATABASE_URL=mysql+pymysql://codepilot:<业务密码>@127.0.0.1:3306/codepilot_edu?charset=utf8mb4
TEST_DATABASE_URL=mysql+pymysql://codepilot:<业务密码>@127.0.0.1:3306/codepilot_edu_test?charset=utf8mb4
MYSQL_ROOT_PASSWORD=<仅容器初始化使用的 root 密码>
MYSQL_PASSWORD=<业务账号密码>
DEMO_TOKEN=<演示令牌>
```

注意：

- 应用只使用业务账号 `codepilot`，不使用 root；root 仅由 MySQL 容器初始化使用。
- `DATABASE_URL` / `TEST_DATABASE_URL` 只接受 `mysql+pymysql://`。写入 SQLite 或其他 scheme 时应用直接启动失败，**没有 SQLite 回退路径**。
- `TEST_DATABASE_URL` 的库名必须以 `_test` 结尾；pytest 启动时会重建该库的表。
- 所有 `/api/v1/*` 接口要求请求头 `X-Demo-Token`，值为 `DEMO_TOKEN`。未配置令牌时接口失败关闭（503 `DEMO_TOKEN_NOT_CONFIGURED`），不会静默放行。
- 评测与限流参数（`MAX_SOURCE_BYTES`、`JUDGE_TIMEOUT_SECONDS`、`JUDGE_CASE_TIMEOUT_MS`、
  `JUDGE_MAX_OUTPUT_BYTES`、`JUDGE_MAX_CASES`、`JUDGE_MAX_CONCURRENCY`、`JUDGE_BUSY_TIMEOUT_SECONDS`）、
  数据库连接池（`DB_*`）与服务绑定（`HOST`/`PORT`/`CORS_ORIGINS`）均有默认值，说明见 `.env.example` 内注释。
- **`.env` 已被 `.gitignore` 忽略，禁止提交真实密码或 API Key。**

AI 配置（可选，兼容 OpenAI Chat Completions 协议）：

```
AI_ENABLED=true
AI_BASE_URL=https://你的兼容服务/v1
AI_API_KEY=你的密钥
AI_MODEL=模型名
AI_TIMEOUT=15
```

API Key 不进入前端、不写入日志、不提交 Git。AI 不可用时系统全程使用规则提示，并在响应中如实标记
`source=RULE`、`is_fallback=true`。

## 6. 启动 MySQL 与后端

MySQL 8.4 单实例由 `docker-compose.yml` 管理：命名卷 `codepilot_mysql_data` 持久化数据，
健康检查、`127.0.0.1:3306` 本机绑定、InnoDB + utf8mb4 + UTC 时区，数据卷与判题临时工作区分离。

```powershell
# 1. 启动 MySQL（首次会初始化 codepilot_edu 与 codepilot_edu_test 两个库）
docker compose up -d
docker compose ps

# 2. 建表（可重复执行，不清空已有提交）
.\.venv\Scripts\python.exe scripts\init_db.py

# 3. 导入题目种子（幂等）
.\.venv\Scripts\python.exe scripts\seed_data.py

# 4. 启动后端
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

访问 `http://127.0.0.1:8000/docs` 查看 OpenAPI 文档。

`GET /health` 会分别返回：

- `api`: API 进程存活状态；
- `database` / `database_status`: MySQL 依赖状态；
- `docker`: 评测环境（Docker + 镜像）就绪状态。

数据库不可用时，业务接口返回 `503 DATABASE_UNAVAILABLE`，不会切换 SQLite/内存库假装持久化成功。

若 Docker Hub 直连不可用，可先通过镜像站拉取并本地打 tag（本项目实测使用 daocloud）：

```powershell
docker pull docker.m.daocloud.io/library/mysql:8.4
docker tag docker.m.daocloud.io/library/mysql:8.4 mysql:8.4
docker compose up -d
```

若复用已有 MySQL 服务，请由 DBA 创建两个 utf8mb4 库并授权业务账号（应用不使用 root）：

```sql
CREATE DATABASE IF NOT EXISTS codepilot_edu
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE IF NOT EXISTS codepilot_edu_test
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON codepilot_edu.* TO 'codepilot'@'127.0.0.1';
GRANT ALL PRIVILEGES ON codepilot_edu_test.* TO 'codepilot'@'127.0.0.1';
```

注意两条路径的账号主机差异：`docker-compose.yml` 通过 `MYSQL_USER` 创建的是
`'codepilot'@'%'`（端口仅绑定 `127.0.0.1:3306`，外部不可达）；上面 DBA 手工路径用
`'127.0.0.1'` 更收紧。两条路径不要混用，以免出现"容器里能用、手工库连不上"的问题。

已有旧数据卷但缺少测试库时，同样补建 `codepilot_edu_test`；不要为补库执行会清空数据卷的操作。

## 7. 运行隔离评测环境

```powershell
# 首次：拉取基础镜像并构建评测镜像
docker pull docker.m.daocloud.io/library/python:3.12-slim-bookworm
docker tag docker.m.daocloud.io/library/python:3.12-slim-bookworm python:3.12-slim-bookworm
docker build -t judge-c:latest runner/

# 自检：ACCEPTED / 编译错误 / 边界错误 / 死循环 / 运行异常 / 巨量输出
.\.venv\Scripts\python.exe scripts\smoke_docker.py
```

若 Docker 未运行，提交接口返回 `503 JUDGE_UNAVAILABLE`，**不会回退到宿主机执行学生代码**。
Docker 不可用属于系统故障，不计入学生失败次数。

## 8. 演示与验收

```powershell
.\.venv\Scripts\python.exe scripts\demo.py
```

脚本自动执行并打印：

1. 正确代码 → `ACCEPTED`；
2. 语法错误 → `COMPILATION_ERROR`；
3. 边界错误 → `WRONG_ANSWER`，显示公开用例的真实预期/实际输出；
4. 请求第 1 层提示；
5. 尝试直接请求第 3 层 → 被拒绝（400 `HINT_LEVEL_INVALID`）；
6. 请求第 2 层 → 返回已生成内容（不重复调用模型）；
7. 修改后再次提交 → `ACCEPTED`；
8. 学生进度与教师待辅导列表。

手工调用示例（注意令牌头）：

```powershell
$headers = @{ "X-Demo-Token" = $env:DEMO_TOKEN }
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/problems -Headers $headers
```

完整说明见 `scripts/demo.md`。没有完成至少一次真实模型调用时，交付状态必须标注“AI 接入未完成”；
本次已在本地兼容接口上完成真实调用，详见「已知问题」。

## 9. 执行自动化测试

```powershell
# 全部：单元 + 真实 MySQL + 真实 Docker 评测
.\.venv\Scripts\python.exe -m pytest -q

# 跳过需要 Docker 的评测集成测试
.\.venv\Scripts\python.exe -m pytest -q -m "not docker"
```

测试约束：

- 数据库测试连接 `TEST_DATABASE_URL` 指向的真实 MySQL 测试库，**禁止用 SQLite 顶替**；
- 测试启动时重建测试库表，不触碰主库；库名不以 `_test` 结尾会直接报错；
- Docker 未就绪时评测集成测试自动跳过，跳过原因写入输出，不标记为通过。

## 10. 数据库持久化、备份与恢复

- 数据卷：`codepilot_mysql_data`；容器重启、`docker compose restart mysql`、后端重启后提交与提示记录仍可查询。
- 临时判题工作区位于评测容器内的 `--tmpfs /work`，执行后随容器删除，与 MySQL 数据卷分离。
- 备份（密码从 `.env` 读出并通过 `MYSQL_PWD` 传入，避免写入命令行历史）：

```powershell
$mysqlPwd = (Select-String -Path .env -Pattern '^MYSQL_PASSWORD=').Line.Split('=', 2)[1]
docker exec -e MYSQL_PWD=$mysqlPwd codepilot-mysql `
  mysqldump -ucodepilot --single-transaction --default-character-set=utf8mb4 codepilot_edu > backup.sql
```

- 恢复：

```powershell
$mysqlPwd = (Select-String -Path .env -Pattern '^MYSQL_PASSWORD=').Line.Split('=', 2)[1]
Get-Content backup.sql | docker exec -i -e MYSQL_PWD=$mysqlPwd codepilot-mysql `
  mysql -ucodepilot --default-character-set=utf8mb4 codepilot_edu
```

P0 不自动清理历史数据，也不承诺无限期保存。后续试点需确认提交/提示记录的保留周期、匿名化与备份频率。
当前数据均由持久化记录生成，未硬编码班级人数、成绩或准确率；演示代码与真实试用数据需分开标注。

## 11. 当前安全限制

- P0 仅用于受信任的本地/受控演示环境，**没有正式用户认证与授权**，不可公开部署。
- 演示身份使用 `student_id` 字符串 + 演示令牌，不具备审计能力，不能声称是正式认证。
- Docker 资源限制不能完全抵御恶意代码；依赖 Docker 默认 seccomp。
- 非公开用例不出现在任何学生侧响应、诊断证据或 AI 提示词中。
- 评测并发上限 2，单学生每分钟最多 10 次提交。
- MySQL 仅绑定 `127.0.0.1`；业务账号不使用 root。

详细设计见 `docs/SECURITY.md`。

## 目录结构

```
app/            FastAPI 应用（api / services / repositories / models / schemas / core / db）
runner/         容器内执行器与 Dockerfile
tests/          单元与集成测试、C 代码夹具（数据库测试连接真实 MySQL）
scripts/        数据库初始化、题目导入、评测自检、端到端演示
scripts/mysql/  MySQL 容器首次初始化 SQL（测试库与授权）
docs/           API、架构、安全、测试记录
docker-compose.yml  MySQL 8.4 单实例（持久化卷 + 健康检查）
backups/        旧 SQLite 产物留档（不参与运行）
```

## 已知问题与未完成项

1. **AI 真实联调**：2026-10-23 首测、2026-10-24 复演留档（`%TEMP%\codepilot-demo-replay.log`），本地兼容 OpenAI 接口真实调用返回 `source=AI` 三层提示，未泄漏隐藏用例；但未在正式厂商账号/公网环境复验。模型输出结构校验已做，证据一致性的人工复核流程尚未建立。AI 失败的 RULE 降级路径已测试。
2. Docker Hub 直连不可用时不具备内网镜像源，需先通过镜像站拉取基础镜像并本地打 tag（本次使用 daocloud）。
3. 提交接口为同步执行，最坏情况下（多用例超时）单次请求约 10 秒；评测繁忙时返回明确错误，未引入任务队列。
4. Python 使用 3.13.15，与任务书建议的 3.11/3.12 存在版本差异，功能不受影响。
5. 未引入 Alembic：表结构由 `scripts/init_db.py` 创建；后续字段变更需要手写迁移或在测试库重建，生产库不可直接 `drop_all`。
6. MySQL 为单实例，未做复制、分库分表或全班并发压测；不能由“换成 MySQL”推断已达到全班并发评测能力。
7. 移动端触控目标尚未按 ≥44px 全量调整（本次冻结前优先保证桌面演示链路，移动端细节延后）。
8. Docker 不可用时返回 503，不写入提交记录，因此该次请求不会出现在学生历史上；这是系统故障处理，不是学生答错。
9. 未做恶意代码逃逸测试，依赖 Docker 默认 seccomp 策略。
10. 根目录旧 SQLite 文件已移至 `backups/sqlite-legacy/` 留档，不再参与运行；确认无用后可删除。
