# 海马爸比客服助手评测

当前 benchmark 为60题：既有会话30题、CSV会话30题，包含40道开发题和20道校准题。模型为 `doubao-seed-2-1-lite`，十组实验均采用同一套 Rubric v3。

## 为什么补充新 benchmark

真实会话题 **hb-real-001（换地点后连不上）** 中，Hermes＋原 Skill＋原知识库生成的回复包含3项追问、5项通用检查、2项提醒，以及供电排查和售后检测分支。旧规则评分演示记录为 **100 分**。保留同一份完整答案，用当前 **Rubric v3** 重新评分，得到 **59 分**；评分模型将客户草稿的可发送性标为 `rewrite`（需要重写）。

<details>
<summary>展开查看实际输出的“建议回复”原文</summary>

```markdown
## 建议回复（可直接发给客户）

您好，先别着急，我们一起看一下～ 设备换了个地方使用，通常相当于换到了一个新的 Wi‑Fi 网络环境，这种情况大多需要把设备重新联网才能恢复，不一定是机器坏了，我们先逐步排查。

为了给您**准确**的步骤（不同型号的指示灯表现和重新联网方式不一样），麻烦您先告诉我三点：
1. 您用的是哪一款看护器？（例如四代 / 三代 / 二代焕新版 / 二代 PLUS，或包装、APP 里显示的型号）
2. 现在指示灯具体是什么状态：红灯闪烁 / 红灯常亮 / 蓝灯闪烁 / 完全不亮？
3. 这台设备是**第一次添加**，还是**原来已绑定、这次换了地方才连不上**？

在您回复之前，可以先做几项**通用检查**（不涉及重置，放心操作）：
- 使用原装电源适配器供电，确认插头插紧、供电正常；
- 确认新位置的 Wi‑Fi 名称和密码正确，且该 Wi‑Fi 能正常上网；
- 把看护器尽量靠近路由器，减少隔墙遮挡，并远离金属物、微波炉等干扰源；
- 如果路由器是光猫自带路由或 AP 面板，可能相对不稳定；
- 手机蓝牙打开，APP 更新到最新版，并用主账号操作。

特别提醒两点：
- 无论后续用哪种方式重新联网，请**先不要删除 APP 里的设备、不要解绑、不要更换绑定账号**，以免影响已有的视频 / 图片记录；
- 看护器只是辅助看护设备，这段时间如果您无法远程查看，请务必安排家人就近看护宝宝。

如果插电后指示灯**完全没有反应**，请先换回原装电源适配器或原装 Type‑C 电源线再试一次，排查供电异常；若用原装供电仍无反应、也无法重置，我们再帮您转官方售后检测。您把上面三点信息发给我，我马上给您对应的重新联网步骤～
```

</details>

| 评分规则 | 同一份完整答案的分数 | 评分记录 |
|---|---:|---|
| 旧 rubric＋临时演示公式 | 100 | 旧规则评分演示中的记录值。 |
| Rubric v3 | 59 | 本轮业务点9/30、处理决策10/20、客户负担0/10；自然表达10/10、依据10/10、内部支持20/20。评分模型将客户负担标为 `poor`，计分程序记录59分封顶，可发送性标为 `rewrite`。 |

可见会话中，客户说的是“换了个地方用”，未确认Wi-Fi是否变化；回复中写的是“通常相当于换到了一个新的 Wi-Fi 网络环境”。在等待客户补充信息之前，回复同时列出了 **3 个问题、5 项通用检查**，以及无灯反应、供电排查和售后检测等分支。

评分对象是包含“建议回复、依据、下一步”的完整答案，上面展示的是客户回复部分；重评没有重新生成答案。100分是当时旧规则的演示值，59分是本次使用`doubao-seed-2-1-lite`和Rubric v3得到的模型重评分。[完整答案与评分记录](results/readme_example_v3.json)保留了六个维度、封顶和判分理由。此单题重评不计入下节十组实验。

当前Rubric分别记录本轮业务点、处理决策、客户负担、自然表达、依据和客服内部支持六个维度。当前题集增加了从真实会话节点截取的问题。

新增真实会话题最初来自17份对话DOCX和聊天汇编中的50段案例。当前60题从既有真实会话中选取30题，再补充30道CSV会话题，覆盖产品咨询、技术处理以及订单、物流、退款、活动等客服核验场景。

## 十组实验结果

之前的四组实验与补充的六组实验合并如下。每组60题，共600份作答、599份数值评分。产品12题是60题中的固定子集；之前四组的产品子集分数由已有评分重新汇总，未重新作答。

| system prompt＋总 Skill | 知识库 | Wiki：全部60题 | Utopia：全部60题 | Wiki：平均用时（秒） | Utopia：平均用时（秒） | Wiki：产品12题 | Utopia：产品12题 |
|---|---|---:|---:|---:|---:|---:|---:|
| A | 旧 | [53.53](results/answers/original_old_wiki.md) | [65.77](results/answers/original_old_utopia.md) | 41.39 | 20.94 | [47.50](results/answers/original_old_wiki.md) | [63.58](results/answers/original_old_utopia.md) |
| B | 旧 | [84.27](results/answers/user_v3_old_wiki.md) | [86.60](results/answers/user_v3_old_utopia.md) | 43.54 | 18.67 | [74.58](results/answers/user_v3_old_wiki.md) | [78.00](results/answers/user_v3_old_utopia.md) |
| B | 新 | [88.48](results/answers/user_v3_new_wiki.md) | [92.03](results/answers/user_v3_new_utopia.md) | 36.76 | 17.26 | [80.00](results/answers/user_v3_new_wiki.md) | [86.33](results/answers/user_v3_new_utopia.md) |
| C | 旧 | [51.15](results/answers/senior_old_wiki.md) | [59.17](results/answers/senior_old_utopia.md) | 36.80 | 20.73 | [58.00](results/answers/senior_old_wiki.md) | [48.83](results/answers/senior_old_utopia.md) |
| C | 新 | [83.37](results/answers/senior_new_wiki.md) | [80.78](results/answers/senior_new_utopia.md) | 36.46 | 20.80 | [56.25](results/answers/senior_new_wiki.md) | [47.00](results/answers/senior_new_utopia.md) |

分数范围为0—100，点击分数可查看该组完整回答。配置 A 的 Wiki 全题均分采用59份数值评分；其他九组采用60份。产品子集每组都有12份数值评分。

平均用时按每组全部60题的作答运行耗时计算，包含检索和生成，不包含评分；未形成答复的题也计入平均值。

配置含义：

- **A**：旧system prompt和旧总Skill。
- **B**：结合有价值的业务数据更新后的客服支持system prompt和总Skill。
- **C**：针对产品咨询场景更新后的system prompt和总Skill。

旧、新知识库分别包含25、29份文件。

<details>
<summary>1. C 组在 Utopia 中的作答与检索记录</summary>

同用新知识库和 Utopia，B、C 的全60题均分分别为 **92.03、80.78**，产品12题均分分别为 **86.33、47.00**。C 有 **5道产品题**耗尽20轮上限，未形成答复，被计0分；B 为0道。

例如“二代 Plus 和换新有什么区别”，C 的检索词从产品参数扩展到售后换新、活动和商品变体，累计18次搜索、5次文档读取，最终未生成答复。C 的 Skill 中写有“找到充分依据后停止扩展检索”。

</details>

<details>
<summary>2. LLM-Wiki 与 Utopia 的区别在哪？</summary>

本次程序的检索调用方式如下：

- **LLM-Wiki**：独立的内部模型先检索，再把资料交给客服模型回答；客服回答侧没有检索工具，不能继续追加搜索。
- **Utopia**：客服模型可以边查边决定下一步，继续搜索段落、读取文档，也负责决定何时停止并回答。

B 接新库的产品12题中，两种后端均生成了12份答复，Utopia没有耗尽迭代预算。C 接新库的产品12题中，Wiki有3次检索降级，生成了12份答复；Utopia有5题未形成答复。C 的两种后端均分分别为 **56.25、47.00**。

</details>

## 文件入口

| 内容 | 位置 |
|---|---|
| 当前60题 benchmark | [题目与逐题标准（展开查看）](benchmark/题目与标准.md) · [说明](benchmark/README.md) · [题目构成](benchmark/manifest.json) |
| 题集数据文件 | [作答输入](benchmark/answering/items.jsonl) · [逐题标准](benchmark/grading/contracts.jsonl) · [来源与划分](benchmark/provenance.jsonl) |
| 新知识库（29份文件） | [知识库入口](knowledge_base/README.md) · [文件清单](knowledge_base/kb_manifest.yaml) |
| 当前评分规则 | [评分说明](benchmark/评分说明.md) · [Rubric](benchmark/rubric.json) |
| 配置 B | [system prompt](config/system_prompt.txt) · [总 Skill](config/SKILL.md) · [评分 prompt](config/grader_prompt.txt) |
| 十组详细指标 | [逐题指标](results/metrics.csv) · [分组汇总](results/summary.json) |
| 实验参数与用量 | [配置](results/configurations.json) · [调用用量](results/usage.json) |
| 4,361条业务对话数据 | [数据说明](data/processed_dialogues/README.md) |
