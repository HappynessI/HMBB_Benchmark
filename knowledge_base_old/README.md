# 海马爸比客服知识库

本知识库按“产品事实层 + 客服意图层 + 全局规则层”组织，用于客服 Agent、Skill 训练和问答数据构造。推荐处理链路是：先识别产品，再识别问题类型，最后按对应意图文档和全局规则回答、追问或转人工。

## 使用原则

1. 先查 `aliases.yaml` 识别用户口语中的产品或型号。
2. 再查 `10_products/` 中的产品事实、参数、功能和兼容关系。
3. 再查 `20_intents/` 中对应的客服处理流程。
4. 涉及风险、未知信息、价格订单、医疗安全时，必须再查 `00_global/` 和 `retrieval_rules.md`。
5. `_archive/` 只作历史备查，不作为优先检索来源。

## 五类客服问题

| 意图 | 文档 |
|---|---|
| 产品选购 | `20_intents/01_product_selection.md` |
| 连接配网 | `20_intents/02_connection_pairing.md` |
| 安装设置 | `20_intents/03_installation_settings.md` |
| 功能使用 | `20_intents/04_function_usage.md` |
| 售后安全 | `20_intents/05_service_safety.md` |

## 产品事实入口

| 类型 | 文档 |
|---|---|
| 看护器总览 | `10_products/monitor/monitor_overview.md` |
| 参数矩阵 | `10_products/monitor/monitor_specs_matrix.md` |
| 功能矩阵 | `10_products/monitor/monitor_feature_matrix.yaml` |
| 配件兼容 | `10_products/monitor/monitor_compatibility_matrix.yaml` |
| 看护器型号详情 | `10_products/monitor/models/` |
| 电商商品 | `10_products/ecommerce/` |

## 检索顺序

```text
aliases.yaml
→ 10_products/ 产品事实
→ 20_intents/ 意图处理流程
→ 00_global/ 全局边界
→ retrieval_rules.md
→ 必要时转人工
```

## 禁止事项

- 不编造价格、库存、促销、保修、参数和兼容范围。
- 不做医疗判断，不说“没报警就是安全”。
- 不承诺 AI 功能 100% 识别。
- 不默认配件通用。
- 不直接建议格式化、重置、删除设备；必须先提醒数据风险。
- 不把 `_archive/` 历史文档作为优先依据。
