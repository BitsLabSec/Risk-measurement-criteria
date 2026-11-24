# BitsScore 链上评估标准与类型索引

链上评估用**权限管理、参数配置、资金与外部依赖**判断协议当前能否长期正常运行。固定范围、快照和权限关系后，按通用和业务专项判据定档，再按已核实的独立问题计算档内分。 [执行流程](./链上评估复用指南.md) · [定档及扣分](./通用链上安全评估标准.md#13-先定档再计算档内分) · [共同适用边界](./共同规则.md)

## 类型专项

| 专项 | 先确定的业务和必要操作 | 参数、资金及依赖的专项输入 |
| --- | --- | --- |
| [Lending v0.15](./lending-onchain-security-rating-standard.md) | 指定借贷市场及模式的借款、还款、清算、提款 | 资产及价格绑定、准入及清算联动、限额、利率、模式；池级债权、同币现金、实际可达资金和报价替代。 |
| [DEX v0.5](./dex-onchain-security-rating-standard.md) | 原生 AMM 交易、结算、撤资；聚合签入交易与资产返还；RFQ 报价与库存取回 | CLMM／DLMM 生效收费及退出，聚合实际净到账和退款，RFQ 有效报价、库存、结算与提款分开核实。 |
| [收益金库 v0.5](./yield-vault-onchain-security-rating-standard.md) | 份额兑付、领取、赎回和从策略取回资产 | 份额及策略绑定、复投和兑付规则，现金、待付及按期可调回额度。 |
| [杠杆仓位 v0.3](./margin-onchain-security-rating-standard.md) | 开仓、减仓、还款、清算及合资格提款 | 借贷及交易的实际联动、报价接受规则、项目仓位与外部储备资金边界、还款退出路径。 |
| [条件订单 v0.3](./order-execution-onchain-security-rating-standard.md) | 限价单与 DCA 开单、存量执行、取消退款 | 订单对象和签入条件、每期资产与净输出、托管余额、报价、签名或执行者及独立退出。 |
| [Farming 与奖励池 v0.3](./farm-incentives-onchain-security-rating-standard.md) | 已产生奖励的领取、存入资产的取回 | 计奖、释放、支付规则和同币奖励库，已释放与未来排放分开。 |
| [锁仓赎回与分红 v0.3](./staking-redemption-onchain-security-rating-standard.md) | 锁仓、到期赎回、分红领取和已承诺分配履约 | 锁仓实际转移、发行与兑付口径、已登记分红资金、净利润归属及独立领取路径。 |
| [Launchpad 发行与退款 v0.3](./launchpad-onchain-security-rating-standard.md) | 配售、代币领取、退款及已结束发行的存量权利 | 发行阶段、清算及分配、未领预算和退款预留、已提取资金与必要依赖。 |
| [LP 永久封存与历史补偿 v0.3](./lp-burn-onchain-security-rating-standard.md) | 封存后保留的收费领取权、已声明补偿的领取 | 封存与领取权益的实质、可领取余额、到期补偿、底层结算及必要授权。 |
| [永续合约 v0.5](./perpetuals-onchain-security-rating-standard.md) | 已声明市场的减仓、权益结算和可用保证金提款 | 保证金与结算绑定、风险约束、当前可核应付和现金、实际采用的价格及资金释放路径。 |
| [同质化代币 v0.6](./fungible-token-onchain-security-rating-standard.md) | 发行与控制、持有人的必要转移、适用兑现权 | 转账方向、暂停、费率与豁免、外部校验状态；实际兑现义务由承担它的业务专项判断。 |

同一个项目可按功能采用多个专项。先确认用户权益及评估范围，再按这些权利选择机制、参数和适用扣分条件。共享对象沿用同一证据。业务封顶后，每个项目大项对适用业务等权平均，再按三大项权重加权和执行项目级封顶。 [汇总规则](./链上评估复用指南.md#3-项目汇总与正式交付) · [现行 JSON](./project-onchain-rollup-v2.json)

## 已有案例与规则追溯

- NAVI 的借贷配置和持续运营试评保留其快照、公式及权重。该快照的参数和情景使用见 Lending 专项的历史规则区。 [NAVI 配置研究](../research/lending-configuration-research-2026-11-17.md) · [NAVI 资金研究](../research/lending-sustainable-operations-research-2026-11-18.md) · [试评结果](../research/navi-onchain-weighted-rating-2026-11-18.json)
- Cetus 的现货、杠杆、金库、订单、奖励、锁仓分红、LP 封存及发行按各自业务路径拆分。专项案例引用具名对象和当轮已采用的规则。 [配置判定底稿](../research/cetus-configuration-assessment-346896130.json) · [资金与依赖底稿](../research/cetus-funds-dependencies-review-346896130.json) · [当轮停供试评](../research/cetus-funds-dependencies-method-research-2026-11-20.json)
- 永续和同质化代币按自身机制识别实际资金义务与必要操作，规则包含相关配置和依赖的档内扣分。
