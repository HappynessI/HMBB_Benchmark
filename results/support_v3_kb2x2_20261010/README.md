# 客服支持助手 v3：四组开发比较

已完成新旧知识库 × LLM-Wiki／Utopia的四组实验，每组60题，共240份回答与240份评分。固定候选Skill、system prompt、Rubric v3，使用实际模型`doubao-seed-2-1-lite`；没有订单、物流、退款等业务接口。

这是dev40＋calibration20上的模型评分预览，全部逐题标准待业务确认，部分开发来源用于更新知识流程。没有独立冻结测试集，做题与评审使用同一模型的独立调用。本轮不能验证最终泛化排名，也没有单独测量Skill／prompt改动的贡献。

| 组 | 知识库 | 接入方式 | 预览均分 | 程序完成 | 正文结构合格 | 检索降级 | 预算耗尽 |
|---|---|---|---:|---:|---:|---:|---:|
| A | 旧 | LLM-Wiki | 84.27 | 60/60 | 60/60 | 6 | 0 |
| B | 新 | LLM-Wiki | 88.48 | 60/60 | 60/60 | 6 | 0 |
| C | 旧 | Utopia | 86.60 | 58/60 | 59/60 | 0 | 2 |
| D | 新 | Utopia | 92.03 | 60/60 | 60/60 | 0 | 0 |

新库相对旧库的配对平均变化为Wiki +4.22分、Utopia +5.43分。正文结构合格只检查可见内容与格式，不能视为业务正确；可直接发送的数量由评分模型判定，也需要业务复核。预算结束后的兜底回答保留并评分，但不计为程序正常完成。

## 阅读与数据

- [完整报告](report.md)：配置、分组统计、按划分配对比较、异常处理和解释边界。
- [A组完整回答索引](index_A.md)、[B组](index_B.md)、[C组](index_C.md)、[D组](index_D.md)：每组60份完整模型回答及评分摘要。
- `answers_A.jsonl`至`answers_D.jsonl`：完整脱敏回答、原数值评分、维度等级、封顶及精简评分理由。
- [逐题指标CSV](metrics.csv)、[JSON](metrics.json)、[分组汇总](group_summary.json)、[配对比较](paired_comparisons.json)。
- [调用与token用量](wire_usage.json)、[评分锚点配对结果](calibration_pairs.json)、[实验配置](experiment_manifest.json)、[完成标记](completion.json)。
- [公开导出说明](publication.json)：脱敏替换次数及未公开内容。

模型回答保持完整三部分，仅将敏感文字替换为占位符。数值指标、评分、维度等级和封顶未重新计算或改写。`answer_chars`沿用脱敏前统计，`native_usage`沿用原运行计数；完整调用token另见`wire_usage.json`，其中包含Wiki内层导航及评分重试／复核调用。

没有公开客户原始输入、私有逐题标准、知识库复制品、证据目录、完整调用轨迹、密钥或本机路径。精简理由省略原始context、sources及evidence_ids，不能独立复核私有证据绑定；原始评分与转换记录保留在本地。完整回答中有关政策或参数的结论是被测输出，不代表仓库认可或现行政策。

## 导出与校验

[导出程序](../../scripts/export_support_v3_results.py)使用Python标准库，无模型调用。需要完成的私有运行目录、报告、逐题标题目录；可选原始素材仅用于识别昵称，绝不复制其消息或元数据。

```bash
python3 scripts/export_support_v3_results.py \
  --run-root /path/to/private/completed-run \
  --report /path/to/private/report.md \
  --contracts /path/to/private/contracts.jsonl \
  --alias-source /path/to/private/labelled-dialogues.jsonl \
  --output-dir results/support_v3_kb2x2_20261010
```

导出后必须复核姓名、详细地址、联系方式、账号、订单／运单／设备编号、本机路径及敏感字段。原运行保持私有，公开仓库不能独立重跑完整实验。评分规则与计分脚本见[Rubric v3](../../rubric/support_v3/评分说明.md)。
