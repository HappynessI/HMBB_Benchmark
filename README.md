# 海马爸比客服助手评测

当前 benchmark 为60题：既有会话30题、CSV会话30题，包含40道开发题和20道校准题。模型为 `doubao-seed-2-1-lite`，十组实验均采用同一套 Rubric v3。

## 十组实验结果

之前的四组实验与补充的六组实验合并如下。每组60题，共600份作答、599份数值评分。产品12题是60题中的固定子集；之前四组的产品子集分数由已有评分重新汇总，未重新作答。

| system prompt＋总 Skill | 知识库 | Wiki：全部60题 | Utopia：全部60题 | Wiki：产品12题 | Utopia：产品12题 |
|---|---|---:|---:|---:|---:|
| 旧版 | 旧 | [53.53](results/answers/original_old_wiki.md) | [65.77](results/answers/original_old_utopia.md) | [47.50](results/answers/original_old_wiki.md) | [63.58](results/answers/original_old_utopia.md) |
| 我的 v3 | 旧 | [84.27](results/answers/user_v3_old_wiki.md) | [86.60](results/answers/user_v3_old_utopia.md) | [74.58](results/answers/user_v3_old_wiki.md) | [78.00](results/answers/user_v3_old_utopia.md) |
| 我的 v3 | 新 | [88.48](results/answers/user_v3_new_wiki.md) | [92.03](results/answers/user_v3_new_utopia.md) | [80.00](results/answers/user_v3_new_wiki.md) | [86.33](results/answers/user_v3_new_utopia.md) |
| 师兄版 | 旧 | [51.15](results/answers/senior_old_wiki.md) | [59.17](results/answers/senior_old_utopia.md) | [58.00](results/answers/senior_old_wiki.md) | [48.83](results/answers/senior_old_utopia.md) |
| 师兄版 | 新 | [83.37](results/answers/senior_new_wiki.md) | [80.78](results/answers/senior_new_utopia.md) | [56.25](results/answers/senior_new_wiki.md) | [47.00](results/answers/senior_new_utopia.md) |

分数范围为0—100，点击分数可查看该组完整回答。旧版 Wiki 的全题均分采用59份数值评分；其他九组采用60份。产品子集每组都有12份数值评分。

配置含义：旧版使用旧system prompt和旧总Skill；“我的 v3”使用更新后的客服支持system prompt和总Skill；师兄版使用产品咨询system prompt和总Skill。旧、新知识库分别包含25、29份文件。

## 文件入口

| 内容 | 位置 |
|---|---|
| 当前60题 benchmark | [说明](benchmark/README.md) · [题目构成](benchmark/manifest.json) |
| 当前评分规则 | [评分说明](benchmark/评分说明.md) · [Rubric](benchmark/rubric.json) |
| 我的 v3 配置 | [system prompt](config/system_prompt.txt) · [总 Skill](config/SKILL.md) · [评分 prompt](config/grader_prompt.txt) |
| 十组详细指标 | [逐题指标](results/metrics.csv) · [分组汇总](results/summary.json) |
| 实验参数与用量 | [配置](results/configurations.json) · [调用用量](results/usage.json) |
| 4,361条业务对话数据 | [数据说明](data/processed_dialogues/README.md) |

## 计分与检查

```bash
python3 -m unittest discover -s benchmark -p 'test_*.py'
python3 -m unittest discover -s scripts -p 'test_build_support_v3.py'
```
