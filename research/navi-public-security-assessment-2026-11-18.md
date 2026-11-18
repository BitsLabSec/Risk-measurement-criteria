# NAVI Lending 公开证据评级

核验日期为 2026-11-18。代码评估对象为 Sui 主网 NAVI Lending 的 `lending_core v26` 和 `oracle v5`，部署定位沿用 2026-11-16 的 checkpoint 345771824。业务攻防范围是 Lending 的钱包、应用、API、交易执行及发布链路。Volo 金库事件作为关联事件披露。

| 维度 | 发布结果 | 依据 |
| --- | --- | --- |
| 代码安全 v0.5 | **审计覆盖估算 97.50／100** | 总权重 40，报告范围确认 24，历史及增量证据推断 15，待核验 1。报告发现单独披露 |
| 业务攻防 v0.5 | **当前公开证据覆盖 0／7 条候选流程**，正式分待核验 | 对应 0／49 个候选检查，0／4 个关键检查。Salus 公开件能核实历史委托及工期 |
| 盘外情报 v0.1 | **92.86／100** | 13 项符合，治理空间 G1 计 0。14 项均适用，26 ÷ 28 × 100 |
| 链上安全 | **79.53／100** | 沿用已有加权评估 |

[代码标准](../code-security-rating-standard.md) · [业务攻防标准](../web3-business-security-rating-standard.md) · [盘外情报标准](../offchain-intelligence-rating-standard.md) · [链上加权记录](./navi-onchain-weighted-rating-2026-11-18.json)

## 公开报告与版本

NAVI 官方合约仓库列有 13 份 PDF。11 份是代码审计，另有 1 份形式化验证报告和 1 份 Salus 渗透测试概览。表中审计日期采用报告落款或报告注明的测试时间。NAVI GitBook 另列 NAVX 代币审计，属于代币合约范围。 [官方审计目录](https://github.com/naviprotocol/navi-smart-contracts/tree/main/audits) · [GitBook 审计索引](https://naviprotocol.gitbook.io/navi-protocol-docs/security/audit-report) · [官方版本映射](https://github.com/naviprotocol/navi-smart-contracts/blob/main/audits/README.md)

| 机构与资料 | 时间 | 报告范围及版本 |
| --- | --- | --- |
| MoveBit 初版全审计 | 2023-05-24 至 07-13 | 初版借贷、预言机及数学库，`838650c`，v1/v1。[报告](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Full_Audit_Movebit_2023.pdf) |
| OtterSec 初版全审计 | 2023-05-22 至 06-07 | 初版借贷核心，`838650c`，v1/v1。[报告](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Full_Audit_OtterSec_2023.pdf) |
| OtterSec 后续审计 | 复核至 2024-01-10 | 借贷核心后续检查，至 `aadfd92`，借贷 v14。[报告](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Increment_Audit_OtterSec_2024.pdf) |
| Salus 渗透测试概览 | 2024-01-31 创建，02-09 接收 | 公开件共两页，记载 8 天测试；仓库文件名标 2023，时间以正文为准。[概览第 2 页](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Penetration_Test_Salus_2023.pdf#page=2) |
| Veridise 预言机增量 | 2024-08-21 | 去中心化预言机集成，`cb7ea49`，预言机 v3。[报告](https://veridise.com/wp-content/uploads/2024/11/VAR_Navi-240607-Decentralized_Oracle_Integration.pdf) |
| Veridise 借贷全审计 | 2024-10-16 | 借贷核心，`945878c`，借贷 v16。[报告](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Full_Audit_Veridise_2024.pdf) |
| MoveBit 奖励增量 | 2025-02-06 | 激励 V3，`d46b85f → dd8d847`，官方映射为借贷 v22。[报告](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Incentive_Increment_Audit_Movebit_2025.pdf) |
| OtterSec 借贷与预言机全审计 | 2025-05-23 | 借贷核心、闪电贷、预言机，`6ae8e49`，v22/v3。[报告](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Full_Audit_OtterSec_2025.pdf) |
| OtterSec vSUI 池管理增量 | 2025-12-05 | 资金池与质押集成，`f8f6118`，借贷 v23、`liquid_staking v1`。[报告](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Pool_Increment_Audit_OtterSec_2025.pdf) |
| Veridise E-mode 增量 | 2026-01-19 | `bc86742`，v24/v4。报告中的 1 个 Medium 和 4 个 Low 已标为 Fixed。[报告](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_EMode_Increment_Audit_Veridise_2026.pdf) |
| MoveBit E-mode 增量 | 2026-01-28 | 差异 `2954d3b → bc86742`，修复复核至 `61d4292`，v24/v4。[报告](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_EMode_Increment_Audit_MoveBit_2026.pdf) |
| MoveBit Pyth Pro 迁移增量 | 2026-07-23 | 迁移以及 v2/v3 读写价路径，`762f00a → eab7a4e`，v26/v5。[报告](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Oracle_PythPro_Increment_Audit_MoveBit_2026.pdf) |
| Asymptotic 形式化验证 | 2026-09-29 入公开仓库 | `96fa224`，v26/v5。覆盖已建模的借贷、预言机、激励、E-mode 和版本门控性质。[报告](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Formal_Verification_Asymptotic_2026.pdf) · [入库记录](https://github.com/naviprotocol/navi-smart-contracts/commit/7ca9079dc59cf6c60c7c6d88288eed3d32e2785f) |

## 代码安全

沿用既有主网 v26/v5 的代码范围与总权重 40。先把 Asymptotic 的正式报告映射到仓库列明的现行部署，按实际审查的代码范围纳入审计覆盖。其他报告按版本和增量范围衔接，重叠权重只计一次。 [正式报告范围](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Formal_Verification_Asymptotic_2026.pdf#page=4) · [部署与报告映射](https://github.com/naviprotocol/navi-smart-contracts/blob/main/audits/README.md)

| 代码范围 | 权重 | 覆盖状态 | 依据 |
| --- | ---: | --- | --- |
| 资产、债务及利息记账 | 5 | 已确认 | v26 形式化报告直接覆盖储备、记账及资金守恒性质 |
| 核心头寸与结算代码 | 5 | 推断覆盖 | 较早全审计和后续增量审查与现行形式化范围衔接 |
| 资金池与质押接入代码 | 5 | 推断覆盖 | OtterSec 资金池和质押集成审计、后续改动及现行形式化范围衔接 |
| 闪电贷模块 | 5 | 推断覆盖 | 既有借贷审计、v24 增量及 v26 形式化范围共同支持 |
| E-mode 规则与状态管理 | 5 | 已确认 | v26 形式化报告列明实际审查范围，已有两份增量审计 |
| 激励与费用代码 | 5 | 已确认 | v26 形式化报告列明激励和借款费用实现范围 |
| 权限检查与暂停门控 | 3 | 已确认 | v26 报告列明门控审查范围，v24 管理代码有哈希匹配依据 |
| 对象迁移代码 | 2 | 已确认 | v26 形式化报告第 32–34 页明确覆盖多个对象的版本门控和迁移实现 |
| 价格簿与有效性检查 | 2 | 已确认 | v5 形式化报告列明价格簿、预言机管理和有效性检查 |
| Pyth Pro 适配和报价入口 | 2 | 已确认 | MoveBit 迁移报告所列两个入口源码哈希匹配 |
| 新读价和辅助集成 | 1 | 待核验 | 归档评分的待核验范围。后续完整公开源码文件核对见下文 |

~~~text
C 已确认下界 = 24 ÷ 40 × 100 = 60.00
C 估算 = (24 + 15) ÷ 40 × 100 = 97.50
C 上界 = 40 ÷ 40 × 100 = 100.00
代码安全分采用 C，当前以覆盖估算展示
~~~

### 报告实效性与部署核对

旧报告按审查版本和明确代码范围使用。有版本衔接依据时，旧版报告对部分现行路径提供推断覆盖。两份最新报告的公开版本映射指向 NAVI 的 v26/v5。完整内部开发提交和每次升级的差异尚未独立复现。[审计版本映射](https://github.com/naviprotocol/navi-smart-contracts/blob/db60087a454c84279c285bbd29c8e0e2543e1c07/audits/README.md)

| 核对环节 | 2026-11-18 结论 |
| --- | --- |
| 评估包身份 | 通过 Sui 主网 GraphQL 核对了两条记录，借贷包为 v26、21 个模块，Oracle 包为 v5、14 个模块 |
| 最新增量审计文件与公开源码 | MoveBit 文件表中列出的 5 个 SHA-1 均与公开提交 `db60087a454c` 一致。此前本地归档缺失的两份 Oracle 文件也已在公开版本找到并匹配 |
| 公开源码与部署字节码 | 项目披露 Oracle 通过源码验证。借贷 11 个模块逐字节一致，10 个模块的差异由项目方归因于导入顺序。完整的独立重建与逐模块比对仍待核验 |

这些核对结果在前端作为独立提示，覆盖分继续显示归档估算。[公开源码提交](https://github.com/naviprotocol/navi-smart-contracts/tree/db60087a454c84279c285bbd29c8e0e2543e1c07) · [项目验证说明](https://github.com/naviprotocol/navi-smart-contracts/blob/db60087a454c84279c285bbd29c8e0e2543e1c07/README.md#-notes-on-source-verification-and-tests) · [Sui GraphQL](https://docs.sui.io/develop/accessing-data/graphql/query-with-graphql)

**报告发现。** Asymptotic 在审查范围内证伪两项记账不变量，公开报告未定级。MoveBit 迁移报告记录三条 Minor 为 Acknowledged。历史 Veridise 报告中的 Critical／Partially Fixed 和 High／Acknowledged 发现仍待核对与当前版本的对应关系。逐项保留原始判断与复核状态。 [Asymptotic 发现](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Formal_Verification_Asymptotic_2026.pdf#page=19) · [MoveBit 问题统计](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Oracle_PythPro_Increment_Audit_MoveBit_2026.pdf#page=5) · [历史借贷报告](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Full_Audit_Veridise_2024.pdf#page=11) · [历史预言机报告](https://veridise.com/wp-content/uploads/2024/11/VAR_Navi-240607-Decentralized_Oracle_Integration.pdf#page=7)

## 业务攻防

已查 NAVI 的审计库与 GitBook、Salus 公开检索及 NAVI 的公开安全披露渠道。已找到 Salus 历史委托的公开件，内容仅含封面和元数据。公开资料未找到可匹配当前 Lending 应用和 API 的完整终审或复测结果。NAVI 后续升级公告也记录过合约与集成更新。 [Salus 概览](https://raw.githubusercontent.com/naviprotocol/navi-smart-contracts/main/audits/NAVI_Penetration_Test_Salus_2023.pdf#page=2) · [Lending 升级公告](https://naviprotocol.gitbook.io/navi-protocol-developer-docs/smart-contract-overview/release-history/navi-lending-protocol-upgrade-announcement-2025-11-17)

| 候选流程 | 权重 | 本次确认状态 |
| --- | ---: | --- |
| 钱包身份与账户权限 | 5 | 当前覆盖待核验，关键检查 D1 |
| 市场与头寸数据展示 | 3 | 当前覆盖待核验 |
| 授权签名与交易意图 | 5 | 当前覆盖待核验，关键检查 D4 |
| 存借还提及交易提交 | 5 | 当前覆盖待核验，关键检查 D4 |
| 结果确认与状态核对 | 3 | 当前覆盖待核验 |
| 特权操作与生产发布 | 5 | 当前覆盖待核验，关键检查 D1 |
| 故障处置与恢复 | 3 | 当前覆盖待核验 |

**当前公开证据确认 0／7 条候选流程、0／49 个候选检查、0／4 个关键检查。** 49 个格子的实际测试结果标 U。Salus 只公布历史委托信息，Web 赏金页列受理范围。这两项材料均未提供对应当前版本的测试结果。C、G、R 仍待核验。 [NAVI Web 赏金范围](https://hackenproof.com/programs/navi-protocol-web)

## 盘外情报

| 小项 | 分 | 证据与口径 |
| --- | ---: | --- |
| I1 官网 | 2 | 官网可访问，官方文档链接同一主域和应用。[官网](https://naviprotocol.io/) |
| I2 官方 X | 2 | 文档与 GitHub 组织交叉确认 `@navi_protocol`。[官方 X](https://x.com/navi_protocol) |
| I3 官方社区 | 2 | 官方文档列 Telegram 与 Discord。[官方社区入口](https://naviprotocol.gitbook.io/navi-protocol-docs) |
| S1 审计索引 | 2 | 已定位厂商、报告和日期或版本。[官方审计归档](https://github.com/naviprotocol/navi-smart-contracts/tree/main/audits) |
| S2 赏金 | 2 | HackenProof 分别列合约和 Web 赏金专页。[合约](https://hackenproof.com/programs/navi-protocol) · [Web](https://hackenproof.com/programs/navi-protocol-web) |
| S3 公开事件检索 | 2 | 已匹配 2026-04-21 UTC 的 Volo 金库事件。NAVI 公告称 Lending 未受直接影响，并记录预防性暂停及恢复。所查公开库未匹配到 NAVI Lending 直接损失事件。[DefiLlama 事件记录](https://defillama.com/protocol/navi-protocol) · [Volo 公告](https://x.com/volo_sui/status/2046715584201511351) · [NAVI 暂停公告](https://x.com/navi_protocol/status/2046723877334659157) · [恢复公告](https://x.com/navi_protocol/status/2046822052896571539) |
| S4 具名管理者 | 2 | NAVI 与 Sui Foundation 均公开具名联合创始人 Elliscope Fang。[NAVI 复盘](https://naviprotocol.io/blog/NAVI-Protocol-Q2-2025-Recap-10ea9d87af1f4d69946e6c5bf59cae3c) · [Sui Foundation](https://www.sui.io/blog/sui-basecamp-2025-lands-in-dubai) |
| S5 投资方 | 2 | OKX Ventures 的公开稿确认共同领投。[投资方公告](https://www.globenewswire.com/news-release/2024/02/01/2821670/0/en/OKX-Ventures-Co-Leads-Investment-in-NAVI-Sui-s-First-Native-One-Stop-Liquidity-Protocol.html) |
| M1 TVL | 2 | DefiLlama 的 Sui **NAVI Lending** 记录为 **$91,809,475**，2026-11-18 06:07:59 UTC。[TVL 序列](https://api.llama.fi/protocol/navi-lending) |
| M2 价格与市值 | 2 | CoinGecko 的 NAVX 为 **$0.00798026**，市值 **$6,514,780**，2026-11-18 07:03:58 UTC。[行情](https://www.coingecko.com/en/coins/navi) |
| M3 DEX 池 | 2 | 按官方 NAVX 类型匹配，2026-11-18 DexScreener 返回池中，流动性最高的是 Cetus NAVX/SUI，约 **$154,110**。[交易对](https://dexscreener.com/sui/0x0254747f5ca059a1972cd7f6016485d51392a3fde608107b93bbaebea550f703) |
| G1 治理空间 | 0 | 文档称 NAVX 用于投票。官方链接、Snapshot 与 Tally 的公开检索未确认对应提案空间。Snapshot 查询也未返回可用于确认的记录。[NAVX 文档](https://naviprotocol.gitbook.io/navi-protocol-docs/dao-and-token/navx-tokenomics) |
| A1 公开域名 | 2 | 官方资料列出主域、Lending 应用、Package API 与 SDK，证书透明度记录佐证公开应用入口。核验于 2026-11-18。[状态资料](https://naviprotocol.gitbook.io/navi-protocol-developer-docs/navi-uptime-status-page) · [SDK](https://sdk.naviprotocol.io/lending) · [应用证书记录](https://crt.sh/?q=app.naviprotocol.io) |
| A2 官方仓库 | 2 | 合约仓库与 SDK monorepo 在官方组织下，并由文档交叉确认。[合约](https://github.com/naviprotocol/navi-smart-contracts) · [SDK](https://github.com/naviprotocol/naviprotocol-monorepo) |

盘外情报 **92.86** 依据披露和可核验程度单独计算。市场数据沿各自来源的日期和口径展示。
