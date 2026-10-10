# 客服支持助手 v3：60题试点

本轮已在本地生成60个会话节点及逐题标准：30题改编自既有真实120题，30题新增自CSV。回答对象是粘贴对话的当前客服；助手没有订单、物流、退款等查询或操作接口。业务状态题评价客服核验建议的质量，不要求助手查出不存在的实时结果。

这是开发与评分校准试点：**dev40、calibration20；全部待业务确认，没有冻结测试集**。已用同一60题完成[新旧知识库×两种接入方式的四组开发比较](../../results/support_v3_kb2x2_20261010/README.md)，得到模型评分预览。它不是旧test50或真实120题的替代版本。公开[manifest](manifest.json)只提供汇总和结构检查状态，完整输入、逐题标准与来源留在本地被Git忽略的`private/support_v3_pilot60/`。

## 题目构成

| CSV当前诉求 | 数量 |
|---|---:|
| 催发货 | 6 |
| 物流状态 | 4 |
| 退款退货 | 6 |
| 优惠活动 | 4 |
| 投诉 | 4 |
| 发票 | 2 |
| 延迟发货等订单修改 | 1 |
| 产品与配件咨询 | 3 |

既有30题保留产品、连接、功能、存储、账号、隐私和售后检测等场景。60题来自60个来源记录组，不等于60个经核实的独立客户，也不代表业务发生频率。每个来源组只进入一个划分；CSV组按record_id，旧题按source_case。未核实的跨记录同一客户关系仍需以后补查。

## 当前题集的字段

- 作答侧：`answering/items.jsonl`只有id、prompt、input_files。会话结束在当前客户问题；不携带全记录分类、后续回复、逐题标准或参考答案。
- 评审侧：`grading/contracts.jsonl`含本轮目标、关键未知、允许动作、客户草稿要求、客服内部要求、当轮业务点、条件后续、禁止动作及知识定位。
- 追溯侧：`provenance.jsonl`保留源记录、截止位置、可见消息、原角色和候选角色提示。CSV显示角色是人工按文字语义暂定，原始unknown始终保留。
- 人工阅读：`审阅版.md`逐题展示完整作答输入与本轮标准。

运行时只将当前作答输入和知识入口放进Agent工作目录；不要把整个`private/support_v3_pilot60/`挂载给它。评审与追溯文件留在独立评测进程。文件夹分开和prompt禁止读取都不能代替实际的文件访问隔离。

条件后续不进入当轮必答分母。比如先确认是否换了Wi-Fi时，可以暂不索取型号和全部灯态；一旦准备执行型号专用重置，就必须满足相关前置条件并提醒数据风险。

## 本地重建

在本仓库根目录执行，路径变量由本机实际私有材料位置提供：

```bash
python3 private/support_v3_pilot60/author_cases.py
python3 scripts/build_support_v3.py \
  --authoring private/support_v3_pilot60/authoring.json \
  --legacy-provenance "$LEGACY_PROVENANCE_PATH" \
  --corpus data/processed_dialogues/dialogues.jsonl \
  --knowledge-root "$OLD_KNOWLEDGE_ROOT" \
  --output private/support_v3_pilot60 \
  --manifest benchmarks/support_v3_pilot60/manifest.json
```

下载公开仓库不能独立重建私有30题与人工标准。构建脚本本身仅用Python标准库。它验证截止点、来源组不跨划分、引用文件与章节存在等结构；不验证政策正确性或模拟客服实际办理业务。

## 后续使用

四组实验已固定候选配置比较知识库及接入方式，没有比较原配置与候选配置。接下来先由业务人员审阅calibration20及判分，再决定是否开展配置消融。校准样例`calibration_anchors.jsonl`只有人工写的好坏对照，留在评审侧，不是实际客服成绩，也不能参与盲测。正式比较前另从未用于开发的来源组采样、业务确认并冻结test；不要把这60题换个名字当test。

CSV时间是解析候选值，知识依据是所提供的知识库快照，不能宣称复原当时活动政策。活动条款没有证据时，优秀答案可以建议当前客服核验；重要政策冲突未解决时，评审应标记needs_review。
