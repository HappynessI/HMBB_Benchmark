# 旧 test50：逐题作答与运行结果

本批次使用 `deepseek-v4-flash`、high，8组各50题，共400条正式运行记录。369条原生运行完成，31条未完成；366条具有约定的三个标题，3条含未解析工具标记。程序完成和格式通过不代表业务正确。本批次尚未统一业务评分。

有非空最终输出的记录为389条。每组JSONL保留全部50条记录，包括空输出、运行失败和格式异常。最终输出只作敏感文本替换，不补写失败答案。

| 实验组 | 记录数 | 运行完成 | 非空输出 | 三段标题齐全 | 平均耗时（秒） | 作答文件 |
|---|---:|---:|---:|---:|---:|---|
| Claude Code：无业务 Skill / 知识库 | 50 | 50 | 50 | 50 | 18.16 | [逐题阅读](answers/claude_code_baseline.md) · [JSONL](answers/claude_code_baseline.jsonl) |
| Claude Code：原 Skill＋原知识库 | 50 | 50 | 50 | 50 | 49.59 | [逐题阅读](answers/claude_code_original.md) · [JSONL](answers/claude_code_original.jsonl) |
| DSH：无业务 Skill / 知识库 | 50 | 41 | 44 | 41 | 10.70 | [逐题阅读](answers/dsh_baseline.md) · [JSONL](answers/dsh_baseline.jsonl) |
| DSH：原 Skill＋原知识库 | 50 | 28 | 45 | 28 | 29.27 | [逐题阅读](answers/dsh_original.md) · [JSONL](answers/dsh_original.jsonl) |
| Hermes：无业务 Skill / 知识库 | 50 | 50 | 50 | 50 | 21.23 | [逐题阅读](answers/hermes_baseline.md) · [JSONL](answers/hermes_baseline.jsonl) |
| Hermes：原 Skill＋原知识库 | 50 | 50 | 50 | 50 | 52.11 | [逐题阅读](answers/hermes_original.md) · [JSONL](answers/hermes_original.jsonl) |
| Hermes：原 Skill＋LLM-Wiki | 50 | 50 | 50 | 47 | 49.63 | [逐题阅读](answers/hermes_wiki.md) · [JSONL](answers/hermes_wiki.jsonl) |
| Hermes：原 Skill＋Utopia | 50 | 50 | 50 | 50 | 35.68 | [逐题阅读](answers/hermes_utopia.md) · [JSONL](answers/hermes_utopia.jsonl) |

## 指标与复现口径

- [逐题指标 CSV](metrics.csv) · [逐题指标 JSON](metrics.json) · [分组汇总](summary.json)。
- [实验配置与脱敏统计](manifest.json)记录模型、版本、正式批次、运行上限和替换次数。
- 脱敏后的最终输出在JSONL的 `answer` 字段中，脱敏修改由 `answer_redacted` 标记；空字符串表示没有最终作答文本。
- `score` 为 `null`，`grading_status` 为 `not_graded`。用量未知值保持 `null`，汇总仅累计已报告的 token。
- 耗时包含启动、检索、模型调用和重试；组间可能并发，Utopia通过本地中转且为单worker，不将耗时差异直接解释为后端性能差异。
- Wiki仅编译现行知识，Utopia包含归档来源；检索top_k分别为8和6。Utopia在答题前关闭自动治理并冻结图谱。
- 400条记录沿用原实验选定的正式批次；无效沙箱批次、Utopia中止的TLS故障批次与冒烟测试未混入。
- 发布文件包含最终输出和白名单运行指标；原始API流量、内部工具轨迹及本地运行环境另存于实验目录。

## 重新导出

在仓库根目录运行，并将参数替换为本机原始实验目录：

```sh
python3 scripts/export_test50_results.py --source-root /path/to/20260929_test50
```

导出程序检查400条唯一记录、每组50题、正式批次、运行状态、耗时、token合计及敏感字段。
