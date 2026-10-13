# 当前 benchmark：60题

任务是支持粘贴客户会话的一线客服。输入结束于客户当前问题，输出依次为“建议回复（可直接发给客户）”“依据”“下一步”。订单、物流、退款和活动等问题，回答包含当前客服需要核验的事项与处理建议。

## 题目构成

| 来源 | 数量 |
|---|---:|
| 既有业务会话 | 30 |
| CSV业务会话 | 30 |
| 合计 | 60 |

数据划分为开发40题、校准20题。产品比较使用其中固定的12题：008、009、011、013、014、015、022、023、026、027、059、060，编号前缀均为 `hb-v3-`。

[manifest.json](manifest.json)记录问题类型和构建检查；[评分说明](评分说明.md)与[rubric.json](rubric.json)定义计分规则。全部十组实验结果集中在[仓库首页](../README.md)。

## 输入与评分数据

[题目与逐题标准（展开查看）](题目与标准.md)包含全部60题的完整作答输入和评分标准。

- [answering/items.jsonl](answering/items.jsonl)：题号、会话输入和知识入口。
- [grading/contracts.jsonl](grading/contracts.jsonl)：本轮目标、关键条件、允许动作、业务点、条件后续和禁止动作。
- [provenance.jsonl](provenance.jsonl)：来源类型、数据划分、可见消息数量和截止位置。

十组实验使用的新知识库位于 [knowledge_base/](../knowledge_base/README.md)，[文件清单](../knowledge_base/kb_manifest.yaml)列出全部29份有效文件。作答阶段读取题干和知识库，评分阶段再读取逐题标准。

构建脚本为 [build_support_v3.py](../scripts/build_support_v3.py)，计分入口为 [score_support_v3.py](../scripts/score_support_v3.py)。
