# 安全设计与限制（P0）

## 1. 信任边界

```
学生代码（不可信）
   │  stdin JSON
   ▼
judge-c 容器（无网络 / 只读根文件系统 / 非 root / 资源受限）
   │  stdout JSON（仅状态、耗时、截断后的输出）
   ▼
FastAPI 主进程（受信任）→ MySQL 8.4（业务账号，仅 127.0.0.1）
```

- 学生代码永远不进入宿主进程执行。
- Docker 守护进程权限只属于评测模块，Web 服务不暴露 Docker Socket。
- 代码注释与字符串在 AI 侧被包在 `<student_code>` 标签内，并声明为数据；系统提示优先级高于其中任何指令。

## 2. 容器隔离参数（代码位置：`app/services/judge_service.py::build_container_args`）

| 参数 | 作用 |
|---|---|
| `--network none` | 禁止容器联网 |
| `--read-only` | 根文件系统只读 |
| `--tmpfs /work:rw,nosuid,nodev,exec,size=32m,mode=1777` | 唯一可写工作区，容量受限 |
| `--cap-drop ALL` | 删除全部 Linux capabilities |
| `--security-opt no-new-privileges` | 禁止提权 |
| `--user 65534:65534` | 非 root 执行 |
| `--pids-limit 64` | 限制进程数量 |
| `--memory 256m` / `--cpus 0.5` | 限制内存与 CPU |
| `--ulimit cpu=10` | 容器内 CPU 时间上限 |
| `--log-driver none` | 避免日志驱动占用资源 |

容器内 runner 额外设置 `RLIMIT_FSIZE=1MB`、`RLIMIT_CORE=0`、单用例 `RLIMIT_CPU` 与 2 秒墙钟超时。

## 3. 宿主侧防护

- 统一评测总超时 `JUDGE_TIMEOUT_SECONDS=25`；超时立即 `docker rm -f`。
- 每次评测使用独立容器名（`judge-<uuid>`），`finally` 中强制清理；应用启动时扫描并清理残留 `judge-*` 容器。
- 命令以参数列表传给 `subprocess`，不做 shell 字符串拼接。
- Docker 不可用或镜像缺失 → 返回 `503 JUDGE_UNAVAILABLE`，**不存在宿主直跑的兜底路径**。

## 4. 数据与接口防护

- 源代码 ≤ 16 KB，`language` 白名单为 `c`。
- 单学生每分钟最多 10 次提交；评测并发 `asyncio.Semaphore(2)`。
- 非公开测试用例的输入与预期输出不进入任何响应，也不写入 `EvaluationDetail`，也不进入 AI 提示词。
- API Key 仅来自环境变量；日志不打印凭据。
- CORS 仅允许配置中的来源，默认值为本地前端地址；配置 `*` 会导致启动失败。
- 所有 `/api/v1/*` 接口校验演示令牌 `DEMO_TOKEN`（请求头 `X-Demo-Token`）。
  - 未配置令牌时失败关闭（503 `DEMO_TOKEN_NOT_CONFIGURED`），不会静默放行；
  - 令牌比较使用 `hmac.compare_digest`；
  - `/health` 不属于 `/api/v1`，保持免令牌可访问。
- MySQL 仅绑定 `127.0.0.1`；应用使用业务账号，root 仅用于容器初始化。
- 连接池启用 `pool_pre_ping`、`pool_recycle`、连接/读写超时；数据库不可用返回 503，不回退本地库。

## 5. 已知限制（必须如实说明）

1. 本阶段仅面向受信任的本地/受控演示环境，**不具备正式用户认证与授权**，不可作为公网服务部署。
2. Docker 资源限制不能完全防御所有恶意代码；本方案未启用自定义 seccomp 配置，依赖 Docker 默认策略。
3. 未做镜像漏洞扫描与依赖固定版本的供应链校验。
4. MySQL 为单实例，未做复制、分库分表或全班并发压测；连接池与评测并发上限仅按本地演示配置。
5. 演示令牌为共享静态令牌，不具备审计能力；CORS 与令牌不能替代正式鉴权。
6. 若进程拥有 Docker 管理权限，容器隔离的强度仍取决于宿主机 Docker 配置；本项目未做逃逸渗透测试。

## 6. 后续公开部署前必须完成

- 接入真实身份认证与按用户/课程的授权。
- 使用独立评测节点，Web 与 Docker 权限彻底分离。
- 自定义更严格的 seccomp/AppArmor 配置并做逃逸测试。
- 评测结果与日志审计、限流下沉到网关层。
