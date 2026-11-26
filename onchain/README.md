# BitsScore 链上评估索引

## 先读这两份

1. [链上安全评估标准 v1.1](./链上安全评估标准.md)：唯一的通用规则，包括流程、权限分表、四档判定、致命项、汇总、证据不足的处理和结果字段。
2. 适用的类型专项（见下表）：规定这类业务要读哪些对象、用什么公式、阈值是多少。

机器可读的汇总规则和结果模板：[project-onchain-rollup-v3.json](./project-onchain-rollup-v3.json)

上述规则的上位依据是[评分骨架 v1.1](../评分骨架.md)。

## 类型专项

| 专项 | 状态 | 适用业务 |
| --- | --- | --- |
| [Lending v1.2](./lending-onchain-security-rating-standard.md) | **现行** | 超额抵押借贷市场 |
| [DEX v1.0](./dex-onchain-security-rating-standard.md) | **现行** | 原生 AMM、聚合路由、RFQ |
| [收益金库 v1.0](./yield-vault-onchain-security-rating-standard.md) | **现行** | 份额兑付、赎回、策略取回 |
| [杠杆仓位 v1.0](./margin-onchain-security-rating-standard.md) | **现行** | 开仓、减仓、还款、清算 |
| [条件订单 v1.0](./order-execution-onchain-security-rating-standard.md) | **现行** | 限价单、DCA、取消退款 |
| [Farming 与奖励池 v1.0](./farm-incentives-onchain-security-rating-standard.md) | **现行** | 领取奖励、取回存入资产 |
| [锁仓赎回与分红 v1.0](./staking-redemption-onchain-security-rating-standard.md) | **现行** | 锁仓、到期赎回、分红领取 |
| [Launchpad v1.0](./launchpad-onchain-security-rating-standard.md) | **现行** | 配售、领取、退款 |
| [LP 永久封存与补偿 v1.0](./lp-burn-onchain-security-rating-standard.md) | **现行** | 封存后的收费领取、补偿领取 |
| [永续合约 v1.1](./perpetuals-onchain-security-rating-standard.md) | **现行** | 减仓、结算、保证金提款 |
| [同质化代币 v1.0](./fungible-token-onchain-security-rating-standard.md) | **现行** | 发行控制、持有人转移 |
| [CDP 稳定币 v1.0](./cdp-stablecoin-onchain-security-rating-standard.md) | **现行** | 抵押铸造稳定币、还款、清算、赎回 |
| [流动性质押 LST v1.0](./liquid-staking-onchain-security-rating-standard.md) | **现行** | 质押换凭证、赎回、领取 |
| [跨链桥 v1.0](./bridge-onchain-security-rating-standard.md) | **现行** | 桥接资产赎回、失败退款 |

新增专项按[专项模板](./专项模板.md)编写。2026-11-25 的警戒阈值提案已逐条确认并写入各专项，原文见 [archive/警戒阈值提案-2026-11-25.md](./archive/警戒阈值提案-2026-11-25.md)。

一个项目可以同时用多个专项：每个业务模块选一个专项。

## 历史

[archive/](./archive/) 中保存了旧版的通用标准、复用指南、共同规则、汇总 JSON v1/v2、全部 11 个专项的旧版本，以及 NAVI 的试评资料。这些文件只用于按原版本复算历史结果，新评估不要引用。
