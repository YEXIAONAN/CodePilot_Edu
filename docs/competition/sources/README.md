# 原始资料存放规则

本目录存放**来源可追溯**的原始资料与规则摘要。竞赛材料成品不放在这里。

## 现行布局

- 官方原件实体：`CodePilot-Edu-Competition/04-资料与佐证/官方资料/`（本校通知与附件、区赛盖章通知、外校同届原包）。**原件只读，不覆盖、不改名、不二次编辑。**
- 规则摘要：本目录 `official-requirements.md`（唯一副本，供所有 Skill 引用）。
- 来源索引：`competition/data/source-index.md`（S 编号）。
- 事实与证据：`competition/data/project-facts.yaml`、`competition/data/evidence-ledger.csv`。

## 新增资料时的动作

1. 原件放入 `CodePilot-Edu-Competition/04-资料与佐证/官方资料/`，保留原始文件名；压缩包解压后保留原包。
2. 在 `source-index.md` 分配新 S 编号，写明路径、类型、取得日期、状态、可支持主张。
3. 在 `evidence-ledger.csv` 为受影响的主张增加或更新 C 记录，写清页码或章节。
4. 若与既有事实冲突，在 notes 中登记冲突，并列入 `project-facts.yaml` 的 `open_questions`。
5. 更新 `project-facts.yaml` 的 `facts_version` 与 `baseline_date`。

## 禁止

- 把网页二手转述、他人整理稿标注为官方原件。
- 自行生成“官方模板”“查重报告”“学籍证明”“证书”“合同”或任何签章。
- 将含学籍号、身份证号、完整住址、手机号的个人材料提交到公开仓库。
- 在仓库中写入 API Key、账号密码、内网地址。