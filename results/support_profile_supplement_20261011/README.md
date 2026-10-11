# 产品类别：六组补充实验

比较完整原版（旧system prompt＋旧总Skill＋旧知识库）与师兄产品咨询版（分别接入旧、新知识库），每种配置各使用LLM-Wiki和Utopia。六组各60题，共360份回答记录、360份评分记录；359份有预览分，1份裁决无效。

实际模型沿用上一轮的 `doubao-seed-2-1-lite`，Rubric v3不变。主比较为答题前选定的12道产品题，其余48道故障、实时业务和混合风险题单独报告。全部题目为开发或校准题，逐题标准待业务确认，做题与评分使用同一模型的独立调用。

| 组 | system prompt＋总Skill | 知识库 | 后端 | 产品题均分 | 正常完成 | 有效正文 | 预算耗尽 |
|---|---|---|---|---:|---:|---:|---:|
| O_W | 原版 | 旧 | LLM-Wiki | 47.50 | 12/12 | 12/12 | 0 |
| S_O_W | 师兄版 | 旧 | LLM-Wiki | 58.00 | 12/12 | 12/12 | 0 |
| S_N_W | 师兄版 | 新 | LLM-Wiki | 56.25 | 12/12 | 12/12 | 0 |
| O_U | 原版 | 旧 | Utopia | 63.58 | 10/12 | 11/12 | 2 |
| S_O_U | 师兄版 | 旧 | Utopia | 48.83 | 7/12 | 9/12 | 5 |
| S_N_U | 师兄版 | 新 | Utopia | 47.00 | 7/12 | 7/12 | 5 |

Wiki的产品题均分提高，Utopia的产品题均分下降，尚不能认定师兄版稳定优于原版。新知识库的主要收益出现在其余48道流程题；不能用全60题均分替代产品类别的评估。主比较72份评分全部有预览分；唯一无效裁决为原版Wiki的第10题，属于其他场景。

## 阅读与数据

- [完整报告](report.md)：结果解释、六组统计、配对变化、人工抽查及修正建议。
- 完整脱敏回答与评分索引：[O_W](index_O_W.md)、[S_O_W](index_S_O_W.md)、[S_N_W](index_S_N_W.md)、[O_U](index_O_U.md)、[S_O_U](index_S_O_U.md)、[S_N_U](index_S_N_U.md)。
- 各组 `answers_组名.md` 保留完整模型回答与评分摘要；`answers_组名.jsonl` 保留完整脱敏回答、原数值评分、封顶及精简裁决理由。
- [逐题指标CSV](metrics.csv)、[JSON](metrics.json)、[分组汇总](group_summary.json)、[产品／其他／全题汇总](scope_summary.json)、[同题配对比较](paired_comparisons.json)。
- [调用用量](wire_usage.json)、[评分锚点检查](calibration_pairs.json)、[实际输入核验](verification.json)、[实验配置](experiment_manifest.json)、[完成记录](completion.json)、[公开导出说明](publication.json)。

正常完成、正文结构、有效正文和业务质量分别记录。“有效正文”仅检查三部分及工具标记泄漏；“可直接发送”由评分模型判定，均不代表人工业务验收。预算耗尽的原始输出保留并评分；裁决无效保留空分数，不改成0分。数值指标、评分、维度等级及封顶保持原值，文本仅替换敏感内容。`answer_chars`沿用脱敏前统计。

人工抽查发现评分口径和事实依据问题，详见报告。评分锚点6组好坏次序均通过，仍不能证明所有裁决的语义判断正确。本轮没有使用师兄AI补问材料训练模型或提供答案，不能据此评价其数据增补效果。

## 与上一轮的关系

[上一轮四组实验](../support_v3_kb2x2_20261010/README.md)固定的是用户更新后的候选system prompt和总Skill，仅比较新旧知识库与两种后端。本轮补齐完整原版和师兄版的六组配置，复用上一轮冻结的知识来源及编译内容。

每组只有一次作答采集，主比较仅12题，没有独立正式测试集。原版与师兄旧库的配对同时检查prompt和总Skill变化，不能进一步拆开两者贡献；师兄新旧库的配对检查知识库更新。两个后端使用各自原生检索过程，成绩不代表纯检索算法的等成本比较。

## 导出与公开范围

[导出程序](../../scripts/export_support_v3_results.py)使用Python标准库，无模型调用。示例中的路径需替换成私有运行目录：

```bash
python3 scripts/export_support_v3_results.py \
  --profile-comparison \
  --run-root /path/to/private/completed-run \
  --report /path/to/private/report.md \
  --contracts /path/to/private/contracts.jsonl \
  --alias-source /path/to/private/labelled-dialogues.jsonl \
  --output-dir results/support_profile_supplement_20261011
```

公开完整脱敏模型输出和精简评分理由。客户原始输入、私有逐题标准、知识库及prompt／Skill快照、证据目录、完整调用轨迹、凭据和本机路径保持私有。公开材料不能独立重建证据行绑定或一键重跑完整实验。模型输出中的产品或政策说法属于被测回答，不能直接当作官方结论。
