# AGENTS.md — CodePilot Edu 竞赛材料工作规范

本文件对整个仓库生效，包括 `CodePilot-Edu-Competition/`、`competition/`、`.competition-build/`。
所有 Agent 与会话在生成、修改、审核参赛材料前必须遵守本文件；子目录不再重复定义同一套规则。

**项目**：CodePilot Edu — 基于AI错因诊断与学习行为分析的程序设计智能实训平台
**赛事**：第十届中华职业教育创新创业大赛，学生赛道，本科组
**单位**：广西职业师范学院 计算机与信息工程学院

---

## A. 项目身份规范

以下字符串为唯一合法写法，任何文档、PPT、文件名、讲稿不得改写、简写或翻译替换：

| 项 | 唯一写法 |
|---|---|
| 英文品牌 | CodePilot Edu |
| 中文全称 | 基于AI错因诊断与学习行为分析的程序设计智能实训平台 |
| 团队 | ZERO团队（4名学生） |
| 负责人 | 叶兴楠 |
| 学校 | 广西职业师范学院 |
| 学院 | 计算机与信息工程学院 |
| 赛道/组别 | 学生赛道 / 本科组 |

- 英文品牌与中文全称不可互换使用：正式封面用中文全称，品牌位置用 CodePilot Edu。
- 不得出现“CodePilot”“Code Pilot”“代码领航”等变体，不得出现其他学校名称作为参赛单位。
- 学校公章的学校名称、学院名称、组别一经进入校赛即不可变更。

## B. 事实来源优先级

1. 有效且适用的正式官方文件（`competition/data/source-index.md` 的 S01—S08）。
2. 项目负责人明确确认的最新事实（S09、S10）。
3. 经核验的项目源码、测试与调研证据。
4. 有可追溯来源的第三方资料（S14 竞品核查等）。
5. 明确标注的商业假设与未来规划。

- 冲突时**记录冲突**（写入 `evidence-ledger.csv` 的 notes 或 `project-facts.yaml` 的 `open_questions`），不得静默择一。
- 不得猜测官方规则；未取得的原件登记为缺口（M 编号），并标“待核验”。
- 官方规则摘要以 `competition/sources/official-requirements.md` 为唯一副本，不得在别处另建一套规则说明。

## C. 信息真实性

每条对外主张必须有状态，取值仅限：

| 状态 | 含义 | 最低证据 |
|---|---|---|
| VERIFIED | 已核验 | 原件、源码、测试记录、可复现实验或有效链接 |
| USER_REPORTED | 负责人提供，缺独立佐证 | 负责人确认记录；材料中不得写成“已核实” |
| IN_PROGRESS | 正在开展 | 可指认的进行中工作产物 |
| PLANNED | 计划开展 | 计划说明；必须用“拟/计划/将” |
| UNKNOWN | 尚不明确 | 无；材料中留占位符并列入待补清单 |

- **禁止**把 PLANNED 改写为 VERIFIED，或把 UNKNOWN 补成看似合理的数字。
- 不确定内容必须使用“拟”“计划”“待验证”“据…（待核验）”。
- 事实登记落在 `competition/data/project-facts.yaml`，证据落在 `competition/data/evidence-ledger.csv`；五个 Skill 共用这一份，不得各存一套。

## D. 商业内容规范

- 无真实数据时可做**情景测算**，但必须写明：假设、公式、单位、适用时间、计算过程。
- 一律称“情景测算/假设”，不得表述为报价、订单、已实现收入、净利润或市场份额。
- 禁止编造：营业收入、采购合同、客户数量、投资金额、市场份额、教学效果、用户增长、企业合作、知识产权、研发成果、获奖记录。
- 必须区分三种角色：产品使用者（学生）、商业决策者（任课教师/课程负责人）、付费主体（院系或课程经费）。付费主体未经验证前只能写“假设”。
- 竞品分析不得为突出本项目而省略竞品已有能力；不得使用贬损性表述；未确认的功能写“公开资料未确认”，不写“不支持”。

## E. 技术内容规范

- 架构口径：Vue 3；Python + FastAPI；MySQL；GCC + 受限隔离执行；兼容 API 接入通用模型。
- 必须区分三档，并在材料中可辨识：**已实现**（有源码/运行证据）、**开发中**、**后续规划**。
- 当前已实现边界为 UNKNOWN（无源码与测试证据），因此不得写“已部署”“已接入某模型”“自动评测已完成”“系统已上线”。
- 不得声称使用了自主训练的基础模型、原创编译器、原创判题内核或独创算法。
- 概念图、设计稿必须标注“产品设计示意图”，不得冒充真实运行截图。

## F. 文件操作规范

- 官方原件只读：不覆盖、不改名、不二次编辑、不删除；压缩包保留原包。
- 不删除团队已有文档；修改既有材料前先读取，保留可追溯版本。
- 不擅自修改项目源代码仓库；不改动 `.competition-build/` 中的历史构建产物（仅可新增）。
- 不向公开 Git 仓库提交学生个人信息（学籍号、身份证号、完整住址、完整手机号）、未公开内部材料。
- 不写入 API Key、账号密码、内网地址、数据库连接串。
- 未经明确授权，不推送远端、不发送邮件、不发布文件。
- 输出文件命名统一：`CodePilot_Edu_<材料名>_<版本或日期>.<扩展名>`；正式提交版与草稿分开存放。
- 不生成学籍证明、证书、合同、查重报告或任何签章内容。

## G. 最终输出规范

任何重要成果必须附带以下六项，缺项视为未完成：

1. 生成/修改文件清单（绝对或仓库相对路径）。
2. 实际采用的资料来源（S/C 编号）。
3. 已完成内容。
4. 未核验内容及其状态。
5. 需要负责人处理的事项（对应 `open_questions` 的 Q 编号）。
6. 验证结果（执行了什么检查、通过/未通过、未执行的原因）。

禁止声明未实际执行的检查（如“已渲染检查”“查重已通过”“已与官方核对”）为已完成。

## H. 目录职责

| 路径 | 职责 | 规则 |
|---|---|---|
| `competition/data/` | 唯一事实源：`project-facts.yaml`、`evidence-ledger.csv`、`source-index.md` | 只登记有来源内容；变更需更新 `facts_version` |
| `competition/sources/` | 规则摘要与原始资料规则 | `official-requirements.md` 为唯一规则副本 |
| `CodePilot-Edu-Competition/01-项目申报评审书/` | 申报书成品与版本 | 在官方附件1母版上填写，保留字段与签章位 |
| `CodePilot-Edu-Competition/02-商业计划书/` | 独立商业计划书 | 与评审书内商业计划书正文一致 |
| `CodePilot-Edu-Competition/03-答辩PPT/` | 答辩 PPTX 与讲稿 | 16:9、可编辑、需渲染检查 |
| `CodePilot-Edu-Competition/04-资料与佐证/` | 官方原件、竞品核查、真实佐证 | 原件只读；佐证按 `01-…06-` 分类 |
| `CodePilot-Edu-Competition/05-审核记录/` | 审核报告与待补清单 | 审核报告按 `audits/` 规则命名 |
| `.competition-build/` | 内部构建脚本、渲染与中间产物 | 非交付物、非官方原件；不作为证据 |
| `.agents/skills/` | 本项目 5 个 Skill | 单一职责，触发条件互不重叠 |

## I. Skills 索引

| Skill | 何时使用 | 主要产物 |
|---|---|---|
| `codepilot-source-review` | 核实事实、查官方规则、查竞品、确认某成果有无证据、更新进度 | 事实库与台账更新 |
| `codepilot-application` | 编写/修改/校验申报评审书（含 A/B/C/D） | DOCX（+PDF 预览） |
| `codepilot-business-plan` | 写商业计划书、竞品分析、商业模式、成本与财务情景 | DOCX/Markdown |
| `codepilot-pitch-deck` | 制作/修改答辩 PPT 与讲稿 | PPTX（+渲染图） |
| `codepilot-submission-audit` | 提交前综合审核、一致性核查、分级问题报告 | Markdown 审核报告 |

调用原则：先 `codepilot-source-review` 确认事实，再进入生成类 Skill；生成后由 `codepilot-submission-audit` 收口。
排版微调不触发市场调研；代码开发、后端修复等非竞赛任务不触发任何竞赛 Skill。

## J. 可用校验命令

```bash
python3 .agents/skills/codepilot-submission-audit/scripts/validate_skills.py
python3 .agents/skills/codepilot-source-review/scripts/validate_facts.py
python3 .agents/skills/codepilot-submission-audit/scripts/audit_materials.py
```

- 脚本仅用 Python 标准库，不依赖第三方包。
- 当前环境实测（2026-10-23）：`python3` 为 3.14，未安装 `python-docx`、`python-pptx`、`PyYAML`，未发现 LibreOffice/`soffice`。因此本轮不具备真实 DOCX/PPTX 渲染能力；需要渲染时必须先安装工具或以可复现方式说明，否则只能做 ZIP/XML 结构检查并明确报告“未做视觉验收”。
- 校验脚本的结论只覆盖确定性检查项；语义正确性、学籍、签章、查重由人工与有权机构完成。