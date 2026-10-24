# 演示流程（P0 验收主线）

> 目标：现场用一条可重复的链路证明“评测 → 证据 → 提示 → 改正 → 记录”闭环。

## 准备

```powershell
# 1. 启动 MySQL 8.4（命名卷持久化，健康检查通过后再继续）
docker compose up -d
docker compose ps

# 2. 初始化数据库与题目（幂等，不清空历史提交）
.\.venv\Scripts\python.exe scripts\init_db.py
.\.venv\Scripts\python.exe scripts\seed_data.py

# 3. 构建评测镜像（首次）
docker build -t judge-c:latest runner/

# 4. 启动后端
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 5. 确认 API、MySQL、Docker 三态
curl http://127.0.0.1:8000/health
```

`.env` 中必须有 `DATABASE_URL`、`TEST_DATABASE_URL`、`DEMO_TOKEN`、`MYSQL_ROOT_PASSWORD`、`MYSQL_PASSWORD`。
前端联调时在 `codepilot-edu-frontend/.env.local` 写入相同的 `VITE_DEMO_TOKEN`。

## 一键执行

```powershell
.\.venv\Scripts\python.exe scripts\demo.py
```

脚本会依次输出：

1. 题目列表（3 道）；
2. 正确代码基线 → `ACCEPTED`；
3. 语法错误 → `COMPILATION_ERROR`，显示真实编译信息；
4. 循环边界错误 → `WRONG_ANSWER`，显示公开用例预期/实际差异；
5. 请求第 1 层提示（AI 可用时为 `source=AI`，否则 `source=RULE, is_fallback=true`）；
6. 尝试直接请求第 3 层 → 400 `HINT_LEVEL_INVALID`；
7. 按顺序请求第 2 层 → 返回已生成内容，不重复调用模型；
8. 修正后再次提交 → `ACCEPTED`；
9. 学生进度：总提交、通过数、错因分布、提示使用；
10. 教师待辅导列表与汇总（最近提交已通过则移出）。

## 现场讲解要点

- 评测结果来自真实 Docker 容器，不是预置文本。
- 诊断类别必须能追溯到具体证据（第 3/4 步会打印 evidence、possible_cause、certainty）。
- 提示层级严格递进：AI 预生成的 2/3 层先存为未解锁，跳级请求会被拒绝。
- 同一层重复/并发请求只保留一份有效记录（唯一约束 + upsert）。
- 统计数字全部来自 MySQL 真实记录，没有硬编码。
- 若现场 Docker 异常，接口返回 `503 JUDGE_UNAVAILABLE`，不会在本机直接运行学生代码。
- 若现场 MySQL 异常，接口返回 `503 DATABASE_UNAVAILABLE`，不会回退 SQLite 或内存库。

## 常见问题

| 现象 | 处理 |
|---|---|
| `/health` 中 `database=false` | `docker compose up -d`，等待健康检查通过；确认 `.env` 的 DATABASE_URL 账号密码 |
| 提交返回 503 `DATABASE_UNAVAILABLE` | MySQL 未启动或账号/库名错误；查看容器日志 |
| 提交返回 503 `JUDGE_UNAVAILABLE` | 确认 Docker Desktop 已启动、镜像已构建；`python scripts\smoke_docker.py` 自检 |
| 接口返回 401 `UNAUTHORIZED` | 请求头缺少或错误的 `X-Demo-Token`；与 `.env` 的 `DEMO_TOKEN` 对齐 |
| 提示全部是 RULE | `.env` 未配置 AI 或 AI 不可达；属预期降级行为，如实说明即可 |
| 首次评测较慢 | 容器冷启动 200~400 ms，属正常 |
