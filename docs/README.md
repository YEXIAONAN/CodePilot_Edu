# CodePilot Edu 竞赛材料工作区

**项目**：CodePilot Edu — 基于AI错因诊断与学习行为分析的程序设计智能实训平台
**赛事**：第十届中华职业教育创新创业大赛 · 学生赛道 · 本科组
**单位**：广西职业师范学院 计算机与信息工程学院（ZERO团队，4 人）

本仓库同时承载**参赛材料**与**材料生产规范**。规范优先于成品：任何内容必须能追溯到官方原件或有明确状态。

## 快速开始

```bash
python3 .agents/skills/codepilot-submission-audit/scripts/validate_skills.py   # Skill 结构校验
python3 .agents/skills/codepilot-source-review/scripts/validate_facts.py       # 事实库/台账校验
python3 .agents/skills/codepilot-submission-audit/scripts/audit_materials.py   # 材料审核（结构+一致性）
```

三个脚本只用 Python 标准库，不依赖 python-docx / PyYAML / LibreOffice。

## 目录

```text
.
├── AGENTS.md                       # 全局规范（身份、来源、真实性、商业、技术、文件、输出）
├── competition/
│   ├── data/                       # 唯一事实源
│   │   ├── project-facts.yaml      # 项目事实 + 状态 + 证据引用
│   │   ├── evidence-ledger.csv     # C001… 主张与证据台账
│   │   └── source-index.md         # S01… 来源 / M01… 缺口
│   └── sources/
│       ├── official-requirements.md# 官方要求摘要（唯一副本）
│       └── README.md               # 原始资料存放规则
├── .agents/skills/                 # 5 个 Codex Skill
│   ├── codepilot-source-review/    # 事实核查
│   ├── codepilot-application/      # 申报评审书
│   ├── codepilot-business-plan/    # 商业计划书
│   ├── codepilot-pitch-deck/       # 答辩 PPT
│   └── codepilot-submission-audit/ # 提交前审核（含校验脚本）
├── CodePilot-Edu-Competition/      # 交付物
│   ├── 01-项目申报评审书/
│   ├── 02-商业计划书/
│   ├── 03-答辩PPT/
│   ├── 04-资料与佐证/              # 官方原件、竞品核查、真实佐证
│   └── 05-审核记录/
└── .competition-build/             # 内部构建与渲染产物（非交付物、非证据）
```

## 使用顺序

1. 需要确认某条事实能否写 → `codepilot-source-review`。
2. 写材料 → `codepilot-application` / `codepilot-business-plan` / `codepilot-pitch-deck`。
3. 提交前 → `codepilot-submission-audit`，存在 BLOCKER 时结论只能是“不可提交”。

## 当前状态（2026-10-23）

- 官方原件已具备：本校 2026-10-21 校赛通知、附件1 评审书、附件2 评审规则；区赛桂统字〔2026〕1号。
- 已核验：本科组 25/35/20/20、3—5 人团队、1—2 名导师、查重 ≤15%、院级推荐 10-29、校赛 11-02。
- 待确认：指导教师、成员学籍与个人字段、学院内 10-25 20:00 截止原件、校赛与区赛时间衔接、正式查重、签章。
- 未提供：项目源码、测试记录、部署证据、调研与试点数据。研发完成度记为 UNKNOWN。
- 既有申报书仍有 29 处 `【待确认】`，提交审核脚本判定为 BLOCKER。

详细口径见 `AGENTS.md` 与 `competition/data/`；不使用二手转述替代原件。