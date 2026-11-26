# -*- coding: utf-8 -*-
"""BitsScore 工作流产物的字段定义。

这里是每个产物文件「要填什么」的唯一来源：
- init 按这里生成空白模板；
- validate 按这里检查漏填、类型、枚举和 ID 引用。
步骤卡只解释这些字段，不另行定义。
"""

BLANK = "__填写__"

ID_PATTERNS = {
    "baseline": r"^B\d{2,}$",
    "deployment": r"^I\d{2,}$",
    "source": r"^S\d{2,}$",
    "business": r"^BZ\d{2,}$",
    "module": r"^M\d{2,}$",
    "responsibility": r"^D\d{2,}$",
    "role": r"^R\d{2,}$",
    "control": r"^K\d{2,}$",
    "gap": r"^G\d{2,}$",
    "report": r"^AR\d{2,}$",
    "market": r"^MK\d{2,}$",
    "target": r"^OT\d{2,}$",
    "reading": r"^RD\d{2,}$",
    "principal": r"^PR\d{2,}$",
    "path": r"^PA\d{2,}$",
    "check": r"^CK\d{2,}$",
    "fatal": r"^XF\d{2,}$",
}


def S(desc, **kw):
    d = {"type": "str", "desc": desc}
    d.update(kw)
    return d


def I(desc, **kw):
    d = {"type": "int", "desc": desc}
    d.update(kw)
    return d


def F(desc, **kw):
    d = {"type": "float", "desc": desc}
    d.update(kw)
    return d


def B(desc, **kw):
    d = {"type": "bool", "desc": desc}
    d.update(kw)
    return d


def E(desc, values, **kw):
    d = {"type": "enum", "desc": desc, "enum": values}
    d.update(kw)
    return d


def L(desc, item, min_items=0, **kw):
    d = {"type": "list", "desc": desc, "item": item, "min": min_items}
    d.update(kw)
    return d


def O(desc, fields, **kw):
    d = {"type": "obj", "desc": desc, "fields": fields}
    d.update(kw)
    return d


def REF(kind, desc):
    return S(desc, ref=kind)


def REFS(kind, desc, min_items=0):
    return L(desc, S("ID", ref=kind), min_items=min_items)


LOC = S("源码位置，格式 路径:起始行-结束行，例如 sources/lending.move:120-168")

RANGE = O("一段源码区间", {
    "source_id": REF("source", "所属源码记录 ID（P2）"),
    "file": S("相对于源码根目录的文件路径"),
    "start": I("起始行（含）", min=1),
    "end": I("结束行（含）", min=1),
})

GAP = O("一条证据缺口", {
    "id": S("缺口 ID，格式 G01", id="gap"),
    "step": E("在哪一步发现", ["P1", "P2", "P3", "P4", "P5", "C2", "C3", "C4",
                               "O1", "O2", "O3", "O4", "O5", "O6", "O7", "O8"]),
    "object_ids": L("受影响的对象 ID", S("ID")),
    "missing": S("缺什么证据（具体到文件、地址或报告）"),
    "searched": S("已经查过哪些来源"),
    "blocks_denominator": B("是否导致无法出分：代码安全指分母建不出来（结果变成「无法评分」）；链上指必需检查读不到（结果变成「评估未完成」）"),
})

CHAIN = S("链标识，格式 sui:mainnet 或 evm:<chainId>，例如 evm:1", pattern=r"^(sui:(mainnet|testnet|devnet)|evm:\d+|[a-z]+:[a-z0-9-]+)$")

TIME_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"
TIME = S("UTC 时间，ISO8601，以 Z 结尾，例如 2026-11-25T08:00:00Z", pattern=TIME_PATTERN)

# 证据引用只能是以下五种之一，export 会据此生成前端的证据字典
EV_PATTERN = r"^(https?://\S+|tx:\S+|cmd:\S.*|file:\S+|[^\s:]+(:[^\s:]+)*:\d+-\d+)$"
EV = S("证据引用：网址 https://…；交易 tx:<链>:<哈希或 digest>；命令 cmd:<完整命令>；本地文件 file:<路径>；源码位置 <路径>:<起>-<止>", pattern=EV_PATTERN)

FILES = {
    "T0-task.json": {
        "step": "T0",
        "root": O("任务单", {
            "assessment_id": S("评估 ID，格式 <项目>-<YYYYMMDD>，同一天第二次评估加 -2，例如 navi-20261125", pattern=r"^[a-z0-9][a-z0-9-]*-\d{8}(-\d+)?$"),
            "previous_assessment_id": S("上一次评估的 ID；第一次评估写 无", pattern=r"^([a-z0-9][a-z0-9-]*-\d{8}(-\d+)?|无)$"),
            "reason": E("为什么做这次评估：first 首次；scheduled 定期复评；permission_change 权限持有人或门限变了；upgrade 合约升级；parameter_change 核心参数改了；rule_change 评分规则升版；correction 纠正上次的错误",
                        ["first", "scheduled", "permission_change", "upgrade", "parameter_change", "rule_change", "correction"]),
            "project": S("项目名称"),
            "dimensions": L("本轮评估维度", E("维度", ["code_security", "onchain"]), min_items=1),
            "chains": L("涉及的链", O("链", {
                "chain_id": CHAIN,
                "name": S("链的名称，例如 Sui Mainnet"),
            }), min_items=1),
            "scope_statement": S("委托方给出的范围原文，或你记录的口径"),
            "known_entries": L("委托方或公开资料给出的入口地址或包 ID（只是线索）", S("地址或包 ID")),
            "known_repos": L("已知的源码仓库 URL（只是线索）", S("URL")),
            "out_of_scope": L("明确排除的范围", S("描述")),
            "assessor": S("评估人或 agent 名称"),
            "date": S("开始日期 YYYY-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$"),
        }),
    },
    "P1-baseline.json": {
        "step": "P1",
        "root": O("部署基线", {
            "baseline_id": S("基线 ID，固定写 B01（升级后新建基线时用 B02…）", id="baseline"),
            "snapshots": L("每条链一个快照", O("快照", {
                "chain_id": CHAIN,
                "block_or_checkpoint": S("区块号（EVM）或检查点序号（Sui）"),
                "block_hash_or_digest": S("区块哈希或检查点 digest"),
                "time_utc": TIME,
                "evidence": EV,
            }), min_items=1),
            "deployments": L("每个「入口 → 实际执行代码」一条", O("部署实例", {
                "id": S("实例 ID，格式 I01", id="deployment"),
                "chain_id": CHAIN,
                "entry": S("用户调用的入口地址或包 ID"),
                "proxy_kind": E("入口的类型", ["none", "eip1967_proxy", "beacon_proxy", "diamond", "other_proxy", "sui_package"]),
                "actual_code": S("快照时实际执行的实现地址或包 ID（没有代理时等于 entry）"),
                "version": S("实现版本：Sui 写包 version；EVM 写实现合约地址的部署交易哈希"),
                "how_found": S("你是怎么确认实际执行代码的（读了哪个槽位、哪笔交易、哪个接口）"),
                "evidence": L("证据", EV, min_items=1),
                "status": E("入口到实际代码的对应关系", ["confirmed", "unconfirmed"]),
            }), min_items=1),
        }),
    },
    "P2-sources.json": {
        "step": "P2",
        "root": O("源码核验", {
            "sources": L("每个不同的实现版本一条", O("源码记录", {
                "id": S("源码 ID，格式 S01", id="source"),
                "deployment_ids": REFS("deployment", "使用这份源码的部署实例 ID", min_items=1),
                "language": E("语言", ["move", "solidity", "vyper", "rust", "other"]),
                "repo_url": S("仓库 URL，没有写 无"),
                "commit": S("完整 40 位 commit，或源码归档的 sha256"),
                "local_path": S("你本地检出这份源码的目录（脚本要读这个目录）"),
                "in_scope_globs": L("纳入统计的文件，相对 local_path 的 glob，例如 sources/**/*.move", S("glob"), min_items=1),
                "excluded_globs": L("排除的文件（第三方库、测试、脚本）", S("glob")),
                "verify_method": E("怎么核验源码和链上代码一致", [
                    "explorer_verified", "sui_verify_source", "rebuild_and_compare",
                    "sourcify_exact", "sourcify_partial", "not_verified"]),
                "verify_result": E("核验结果", ["match", "mismatch", "not_verified"]),
                "verify_evidence": L("核验证据（链接、命令、输出文件）", EV),
            }), min_items=1),
        }),
    },
    "P3-business-modules.json": {
        "step": "P3",
        "root": O("业务与模块", {
            "businesses": L("每项用户能用的业务功能一条", O("业务", {
                "id": S("业务 ID，格式 BZ01", id="business"),
                "name": S("业务名称，例如 借贷、现货交易"),
                "specialty": E("对应的链上专项", [
                    "lending", "dex_amm", "dex_aggregator", "dex_rfq", "yield_vault", "margin",
                    "order_limit", "order_dca", "farm", "staking_redemption", "launchpad",
                    "lp_burn", "compensation", "perpetuals", "token", "cdp", "liquid_staking", "bridge", "other"]),
                "user_entries": L("用户入口函数，格式 模块::函数", S("函数"), min_items=1),
                "assets_or_state": L("涉及的资产或关键状态", S("描述"), min_items=1),
            }), min_items=1),
            "modules": L("每个源码模块（Move module / Solidity contract）一条", O("模块", {
                "id": S("模块 ID，格式 M01", id="module"),
                "name": S("模块名，例如 lending_core::lending"),
                "source_id": REF("source", "所属源码记录 ID（P2）；外部依赖写 外部"),
                "file": S("文件路径；外部依赖写 外部"),
                "is_external": B("是否外部依赖（第三方合约或库）"),
                "business_ids": REFS("business", "使用它的业务 ID", min_items=1),
                "purpose": S("一句话说明它干什么"),
                "calls_module_ids": REFS("module", "它调用的其他模块 ID"),
            }), min_items=1),
        }),
    },
    "P4-responsibilities.json": {
        "step": "P4",
        "root": O("代码职责与档位", {
            "responsibilities": L("每个可独立核查的结果一条", O("职责", {
                "id": S("职责 ID，格式 D01", id="responsibility"),
                "result": S("这段代码负责的结果，例如 新增借款债务并从池中划款"),
                "business_ids": REFS("business", "相关业务 ID", min_items=1),
                "module_ids": REFS("module", "相关模块 ID", min_items=1),
                "ranges": L("实现这个结果的全部源码区间", RANGE, min_items=1),
                "q1_assets_or_authority": E("问题 1：这段代码是否直接改变资产、余额、价值计算或授权边界，或决定核心实现及其升级？", ["yes", "no"]),
                "q1_evidence": S("问题 1 的依据说明：这几行做了什么；答 no 写 无"),
                "q1_locations": L("问题 1 的源码位置，格式 路径:起-止；答 no 留空 []", EV),
                "q2_preconditions_or_availability": E("问题 2：这段代码是否影响关键调用的前提、执行限制、时机或可用性（包括暂停开关）？", ["yes", "no"]),
                "q2_evidence": S("问题 2 的依据说明；答 no 写 无"),
                "q2_locations": L("问题 2 的源码位置，格式 路径:起-止；答 no 留空 []", EV),
                "impact_object": S("影响的具体资产、状态、权限或入口"),
                "failure_consequence": S("这段代码出错时，哪项业务结果会怎样"),
            }), min_items=1),
        }),
    },
    "P5-roles-controls.json": {
        "step": "P5",
        "root": O("特权角色与关键控制", {
            "roles": L("代码里定义的每个角色或权限凭证一条", O("角色", {
                "id": S("角色 ID，格式 R01", id="role"),
                "credential": S("源码里的名字或凭证类型，例如 storage::OwnerCap、onlyOwner"),
                "check_locations": L("做权限检查的源码位置", LOC, min_items=1),
                "how_obtained": S("这个权限怎么来的：初始化时给谁、谁能再授予、能不能转移"),
                "granted_by_role_ids": REFS("role", "能授予或替换它的上级角色 ID"),
            })),
            "controls": L("每个特权操作一条", O("控制", {
                "id": S("控制 ID，格式 K01", id="control"),
                "role_ids": REFS("role", "需要哪些角色", min_items=1),
                "entry": S("特权函数，格式 模块::函数"),
                "conditions": S("代码强制的执行条件（版本检查、对象范围、延时）；没有写 无"),
                "what_changes": S("改了什么：哪个对象的哪个字段，或转移了什么资产"),
                "effect_locations": L("生效位置：直接执行点，或写入点加读取点", LOC, min_items=1),
                "affected_responsibility_ids": REFS("responsibility", "受影响的职责 ID", min_items=1),
                "consequence": E("对用户的最坏后果（链上权限评分会用）：H1 处分资产或改写权益，H2 有限度改变存量条件，H3 阻断必要操作，none 都不是", ["H1", "H2", "H3", "none"]),
                "reachability": E("这条控制路径能不能走通", ["source_closed", "config_dependent", "disabled_in_code", "unknown"]),
            })),
        }),
    },
    "gaps.json": {
        "step": "*",
        "root": O("证据缺口（所有步骤共用）", {
            "gaps": L("证据缺口", GAP),
        }),
    },
    "C2-reports.json": {
        "step": "C2",
        "root": O("审计报告登记", {
            "reports": L("每份报告一条", O("报告", {
                "id": S("报告 ID，格式 AR01", id="report"),
                "firm": S("审计机构"),
                "type": E("报告类型", ["audit", "incremental_audit", "formal_verification"]),
                "date": S("报告日期 YYYY-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$"),
                "url": S("报告原文链接"),
                "audited_source": O("受审版本在本地的位置", {
                    "kind": E("受审源码的形式", ["git", "dir", "unavailable"]),
                    "repo_path": S("kind=git 时：本地仓库目录；否则写 无"),
                    "commit": S("kind=git 时：受审的完整 commit；否则写 无"),
                    "dir_path": S("kind=dir 时：受审源码目录；否则写 无"),
                }),
                "scope_evidence": S("报告里列出范围的位置，例如 第 3 页 Scope 表"),
                "scope": L("报告正式范围里的每个文件一条", O("范围文件", {
                    "audited_path": S("受审版本中的文件路径"),
                    "production_source_id": REF("source", "对应的生产源码 ID（P2）"),
                    "production_path": S("生产版本中的文件路径（没改名就和 audited_path 一样）"),
                    "only_line_ranges": L("报告只审了部分行时填受审版本的行区间 [起, 止]；审整个文件就留空 []", L("区间", I("行号"), min_items=2)),
                    "excluded_line_ranges": L("报告明确排除的受审版本行区间 [起, 止]；没有就留空 []", L("区间", I("行号"), min_items=2)),
                }), min_items=1),
            })),
            "search_log": L("查找报告的记录（找到和没找到都要记）", O("查找记录", {
                "target": S("在找哪个模块或范围的报告"),
                "channels": L("查过的渠道", S("URL 或渠道名"), min_items=1),
                "date": S("查找日期 YYYY-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$"),
                "found_report_ids": REFS("report", "找到的报告 ID；没找到留空 []"),
            }), min_items=1),
        }),
    },
    "C3-semantic-changes.json": {
        "step": "C3",
        "generated": True,
        "root": O("改动的语义判定（脚本生成，agent 只填 semantic_change、identifiers、reason）", {
            "changes": L("受审版本到生产版本的每一处改动", O("改动", {
                "change_id": S("脚本生成，不要改"),
                "report_id": REF("report", "脚本生成，不要改"),
                "production_path": S("脚本生成，不要改"),
                "audited_lines": S("脚本生成，不要改"),
                "production_lines": S("脚本生成，不要改"),
                "enclosing_symbol": S("脚本猜的所在函数或结构体，不要改"),
                "diff_preview": S("脚本生成，不要改"),
                "semantic_change": E("这处改动有没有改变行为？只改注释、格式、日志、事件、错误码数字写 no；其余写 yes", ["yes", "no"]),
                "identifiers": L("semantic_change=yes 时：行为变了的函数名或结构体字段名（脚本会把引用它们的未改动行判为未覆盖）；no 时留空 []", S("标识符")),
                "reason": S("一句话理由"),
            })),
        }),
    },
    "C4-findings.json": {
        "step": "C4",
        "root": O("报告发现", {
            "findings": L("所有报告里的每一条发现", O("发现", {
                "report_id": REF("report", "报告 ID"),
                "finding_id": S("报告里的编号"),
                "title": S("标题"),
                "severity": E("报告给的等级", ["critical", "high", "medium", "low", "informational", "unrated"]),
                "assessor_severity": E("报告未定级（unrated）时你给的等级；报告已定级就写 same", ["same", "critical", "high", "medium", "low", "informational"]),
                "assessor_severity_reason": S("你定级的理由；same 写 无"),
                "production_applicable": E("这个问题在当前生产代码里是否还存在", ["yes", "no", "unknown"]),
                "applicability_evidence": S("依据说明：生产代码里那段逻辑现在是什么样"),
                "applicability_refs": L("依据引用：生产代码位置、改动链接", EV, min_items=1),
                "fix_status": E("修复状态", ["fixed_and_reviewed", "fix_deployed_not_reviewed", "claimed_fixed", "acknowledged", "not_fixed"]),
                "fix_evidence": S("修复情况说明；没有写 无"),
                "fix_refs": L("修复引用：修复提交链接、部署交易、复核报告链接；没有留空 []", EV),
                "centralization_only": B("是否纯中心化问题（例如 owner 权限过大）；是的话不参与封顶，交给链上权限评价"),
                "root_cause_group": S("同一根因的多条发现填同一个组名；没有写 无"),
            })),
        }),
    },
    "C5-overall.json": {
        "step": "C5",
        "root": O("总体评价（基准 5 分；A4、B2 由脚本自动判，不在这里填）", {
            "a1_multi_firm": E("A1 找补：核心模块是否被 2 家及以上不同机构审计过", ["yes", "no"]),
            "a1_evidence": S("A1 依据说明：哪几家机构审了哪些核心文件；答 no 写 无"),
            "a1_report_ids": REFS("report", "A1 依据的报告 ID；答 no 留空 []"),
            "a2_incremental_review": E("A2 找补：是否有针对升级的增量审计或复审", ["yes", "no"]),
            "a2_evidence": S("A2 依据说明：复审的是哪次升级；答 no 写 无"),
            "a2_report_ids": REFS("report", "A2 依据的报告 ID；答 no 留空 []"),
            "a3_formal_verification": E("A3 找补：核心逻辑是否有形式化验证", ["yes", "no"]),
            "a3_evidence": S("A3 依据说明：验证了哪些核心函数；答 no 写 无"),
            "a3_report_ids": REFS("report", "A3 依据的报告 ID；答 no 留空 []"),
            "b1_observations": L("B1 线索：观察到的反常写法，每处一条；没有就留空 []", O("线索", {
                "signal": E("线索类型", ["custom_math", "custom_auth", "bypass_framework", "unexplained_branch", "other"]),
                "location": LOC,
                "description": S("具体是什么、为什么觉得反常"),
            })),
            "b1_human_decision": E("B1 由人确认：有线索时由人填 deduct（扣 2 分）或 no_deduct；agent 一律填 pending；没有线索填 not_applicable", ["pending", "deduct", "no_deduct", "not_applicable"]),
            "b1_human_reviewer": S("确认人姓名；pending 或 not_applicable 时写 无"),
            "b3_unaudited_cross_module": E("B3 扣分：是否有核心业务的跨模块调用链没有被任何一份报告完整审过", ["yes", "no"]),
            "b3_evidence": S("B3 依据：哪个业务、哪几个模块、各报告分别审了哪些；答 no 写 无"),
        }),
    },
}

STEP_ORDER = ["T0", "P1", "P2", "P3", "P4", "P5", "C2", "C3", "C4", "C5"]


# ================================================================ 链上（O1–O8）

YN = ["yes", "no"]
YNA = ["yes", "no", "na"]

INPUT = O("公式的一个输入", {
    "name": S("输入名，必须是这个检查项的公式要求的名字（见 O5 卡的公式表）"),
    "reading_id": S("取自哪条读数（O3 的 RD 编号）；用常量时写 无"),
    "constant": S("不取读数时填常量值（例如代码里写死的数，或 yes／no、pull／push）；用读数时写 无"),
    "divide_by": F("把原始读数换算成公式单位要除以多少。例如读数 8000、单位是 bps，公式要小数，就填 10000；不用换算填 1", min=0.000000001),
    "note": S("换算或取值依据，例如 代码 sources/config.move:42 定义分母为 10000"),
    "group": S("同一检查项要算多个组合时（例如每个 E-mode 抵押×借款组合），给同一组的输入写相同的组名，例如 emode-6；只有一组写 无。脚本逐组计算，取最差的结果"),
})

CHECK = O("一个检查项在一个市场上的结果", {
    "id": S("检查 ID，格式 CK01（O5、O6 连续编号，不要重复）", id="check"),
    "business_id": REF("business", "业务 ID（P3）"),
    "market_id": S("市场或池子 ID（O1 的 MK 编号）；全业务共用的检查写 ALL"),
    "check_id": S("专项表里的编号，例如 L-C2.1；通用预言机检查写 OR-1 到 OR-4"),
    "inputs": L("公式输入。这个检查项没有公式时留空 []", INPUT),
    "q_not_applicable": E("这个机制在本市场确认不存在吗？（是 → N/A，要写依据）", YN),
    "q_aggregate_not_stored": E("计算要用的汇总值协议没有存储、只能扫历史或枚举用户才能得到吗？（是 → 只披露）", YN),
    "q_hard": E("违反专项这一行的硬约束，或必要操作完全受阻且没有替代吗？有公式的检查项填 by_formula", ["yes", "no", "by_formula"]),
    "q_warn": E("触发专项这一行的警戒，或必要操作部分受阻但仍有可用路径吗？有公式的检查项填 by_formula", ["yes", "no", "by_formula"]),
    "q_weakened": E("已证实某个次要保护、备用路径或便捷入口失效，但主路径仍能完整承接吗？", YN),
    "refers_to": S("这个事实已在别的检查里计分、这里只引用时，填那个检查的 CK 编号；否则写 无"),
    "reading_ids": REFS("reading", "这个判断用到的全部读数 ID（包括公式输入）"),
    "reason": S("一句话写明判断依据，答 yes 的问题都要在这里说清楚"),
    "evidence": L("证据", EV, min_items=1),
})

FILES.update({
    "O1-scope.json": {
        "step": "O1",
        "root": O("链上范围与快照", {
            "snapshots": L("每条链一个链上快照", O("快照", {
                "chain_id": CHAIN,
                "block_or_checkpoint": S("区块号（EVM）或检查点序号（Sui）"),
                "block_hash_or_digest": S("区块哈希或检查点 digest"),
                "time_utc": TIME,
                "evidence": EV,
            }), min_items=1),
            "baseline_check": L("P1 的每个部署实例，在链上快照时是否还指向同一份代码", O("基线复核", {
                "deployment_id": REF("deployment", "部署实例 ID（P1）"),
                "unchanged": E("快照时实际执行的代码是否仍是 P1 记录的版本", YN),
                "evidence": EV,
            }), min_items=1),
            "businesses": L("每个纳入链上评估的业务一条", O("业务范围", {
                "business_id": REF("business", "业务 ID（P3）"),
                "necessary_ops": L("必要操作：用户为保住权益必须能完成的操作（从专项第 1 节抄）", O("必要操作", {
                    "op": S("操作名，例如 还款"),
                    "entry": S("入口函数，格式 模块::函数"),
                }), min_items=1),
                "markets": L("业务内的市场或池子；只有一个整体时留空 []", O("市场", {
                    "id": S("市场 ID，格式 MK01", id="market"),
                    "name": S("市场名，例如 USDC 储备"),
                    "object": S("市场或池子的对象 ID（小写，Sui 写完整 64 位）；市场是表中的一个条目、没有独立对象时，写所在表的 ID"),
                    "key": S("市场是表中的条目时，写条目的键（例如资产编号 10）；有独立对象时写 无"),
                    "discovered_by": E("这个市场是怎么找到的：onchain_registry 从链上的市场列表读到；official_list 链上无法枚举，取自官方文档或前端", ["onchain_registry", "official_list"]),
                    "discovery_evidence": EV,
                })),
            }), min_items=1),
            "module_objects": L("前期准备关系图里每个模块对应的顶层链上对象（包、全局配置、注册表、权限凭证、金库）；不逐个列池子或用户对象", O("模块对象", {
                "module_id": REF("module", "模块 ID（P3）"),
                "chain_id": CHAIN,
                "object": S("链上地址或对象 ID（小写；Sui 写完整 64 位）"),
                "object_kind": E("对象类型", ["package", "contract", "global_config", "registry", "capability", "treasury", "other"]),
                "evidence": EV,
            }), min_items=1),
            "out_of_scope": L("没有纳入链上评估的业务或市场，以及原因", S("描述")),
        }),
    },
    "O2-targets.json": {
        "step": "O2",
        "root": O("读取清单：这次要读哪些链上对象和字段", {
            "targets": L("每个要读的链上对象一条", O("读取目标", {
                "id": S("目标 ID，格式 OT01", id="target"),
                "chain_id": CHAIN,
                "address": S("地址或对象 ID（小写；Sui 写完整 64 位，EVM 写 40 位）"),
                "kind": E("对象类型", ["package", "contract", "proxy_admin", "eoa", "multisig", "timelock",
                                   "capability", "config", "market_or_pool", "oracle_feed", "vault_or_reserve", "other"]),
                "fields": L("要读的字段", O("字段", {
                    "name": S("字段名或调用，例如 reserves[3].ltv、getThreshold()"),
                    "meaning": S("这个字段是什么意思，单位是什么"),
                }), min_items=1),
                "serves": L("服务于哪些检查，格式 检查编号@业务或市场，例如 L-C2.1@MK01、H1@BZ01", S("检查"), min_items=1),
                "priority": E("required：必需检查要用；optional：可选；disclosure：只用于披露", ["required", "optional", "disclosure"]),
                "reason": S("为什么要读它；不是专项表直接列出的对象，必须写清它服务于哪个检查"),
            }), min_items=1),
        }),
    },
    "O3-readings.json": {
        "step": "O3",
        "root": O("读数回填", {
            "readings": L("每个字段的读数一条", O("读数", {
                "id": S("读数 ID，格式 RD01", id="reading"),
                "target_id": REF("target", "读取目标 ID（O2）"),
                "field": S("字段名，和 O2 中写的一致"),
                "status": E("read：读到了；unreadable：读不到", ["read", "unreadable"]),
                "value": S("原始值，原样照抄（不要换算单位）；读不到写 无"),
                "unit": S("原始单位，例如 bps、1e18、秒、地址"),
                "chain_id": CHAIN,
                "method": E("读取方式：getter 查询函数；object_field Sui 对象字段；dynamic_field Sui 表条目或动态字段；type_query 按类型在快照上查找对象（只用于找权限凭证）；storage_slot EVM 存储槽；code_constant 代码常量；targeted_tx 定向读一笔交易（只用于 Sui 原生多签成员）",
                            ["getter", "object_field", "dynamic_field", "type_query", "storage_slot", "code_constant", "targeted_tx"]),
                "method_detail": S("getter 写函数签名；object_field／dynamic_field 写字段路径；storage_slot 写槽位和依据（源码存储布局）；code_constant 写常量名；targeted_tx 写交易 digest 和选它的理由"),
                "at_snapshot": E("exact：在 O1 的快照上读的；bracketed：节点不支持按快照读，在快照前后各读一次且结果一致；code_constant 和 targeted_tx 写 not_applicable", ["exact", "bracketed", "not_applicable"]),
                "source": E("读数是用什么工具拿到的：collector 采集工具或脚本；rpc 手工调用节点；explorer 区块浏览器；source_code 源码常量。只作记录，不影响计分", ["collector", "rpc", "explorer", "source_code"]),
                "evidence": EV,
            }), min_items=1),
        }),
    },
    "O4-permissions.json": {
        "step": "O4",
        "root": O("角色关系与权限路径", {
            "principals": L("每个链上实体一条：EOA、多签、时间锁，或无法归类的控制者；同一实体只登记一次", O("控制者", {
                "id": S("控制者 ID，格式 PR01", id="principal"),
                "chain_id": CHAIN,
                "address": S("地址（Sui 多签的成员写成员公钥对应的地址）"),
                "kind": E("eoa：单个密钥；multisig：多签；timelock：时间锁合约；other：治理合约、无法确认的合约等（会使相关路径记评估未完成，交人处理）", ["eoa", "multisig", "timelock", "other"]),
                "threshold": I("多签门限（按权重计时写权重门限）；时间锁写需要几个提议者同意（通常 1）；eoa 和 other 写 0", min=0),
                "members": L("多签的成员，或时间锁的提议者；eoa 和 other 留空 []", O("成员", {
                    "principal_id": REF("principal", "成员的控制者 ID（成员是多签时写那个多签的 ID）"),
                    "weight": I("权重；不按权重的多签写 1", min=1),
                })),
                "delay_seconds": I("时间锁当前的最短等待时间（秒）；不是时间锁写 0", min=0),
                "reading_ids": REFS("reading", "门限和成员的读数 ID"),
            }), min_items=1),
            "role_holders": L("P5 每个特权角色在链上由谁持有（关系图从角色节点连到链上实体）", O("角色持有人", {
                "role_id": REF("role", "角色 ID（P5）"),
                "chain_id": CHAIN,
                "credential": S("链上凭证：Sui 写 Cap 对象 ID；EVM 写 合约地址 加角色名，例如 0xabc…#DEFAULT_ADMIN_ROLE"),
                "holder_status": E("held：有持有人；burned：凭证已销毁或权限已放弃；unassigned：查不到持有人", ["held", "burned", "unassigned"]),
                "holder_principal_ids": REFS("principal", "持有人的控制者 ID（可以多个，例如一个角色授予了多个地址）；不是 held 留空 []"),
                "reading_ids": REFS("reading", "持有人的读数 ID"),
                "evidence": L("证据", EV, min_items=1),
            }), min_items=1),
            "paths": L("每条能达到 H1／H2／H3 后果的完整路径一条", O("权限路径", {
                "id": S("路径 ID，格式 PA01", id="path"),
                "business_ids": REFS("business", "受影响的业务 ID", min_items=1),
                "consequence": E("后果", ["H1", "H2", "H3"]),
                "control_ids": REFS("control", "走的是 P5 里的哪些控制", min_items=1),
                "description": S("一句话描述路径，例如 OwnerCap 持有人 → 升级包"),
                "approver_ids": REFS("principal", "这条路径上必须批准的全部控制者 ID（全部都要签才能走通）", min_items=1),
                "delay_seconds": I("这条路径上代码强制的等待时间（秒）；没有写 0", min=0),
                "delay_public": E("等待期间待执行的内容是否公开可查；没有等待写 na", YNA),
                "delay_bypass": E("是否存在能跳过等待的路径；没有等待写 na", YNA),
                "exit_closable_in_delay": E("等待期间，控制者能否先关掉用户的退出入口；没有等待写 na", YNA),
                "h1_rate_limited": E("仅 H1：是否受代码强制的出金限速约束，且同一控制者关不掉、调不大；不是 H1 写 na", YNA),
                "h1_covers_all_assets": E("仅 H1：这条路径能否处分该业务全部用户资产；不是 H1 写 na", YNA),
                "h3_auto_expire": E("仅 H3：暂停是否会自动到期、且不能连续续期；不是 H3 写 na", YNA),
                "reading_ids": REFS("reading", "用到的读数 ID（持有人、延时等）"),
                "evidence": L("证据", EV, min_items=1),
            })),
            "absent": L("某个业务确认不存在某类后果时登记（每个业务的 H1、H2、H3 要么有路径，要么在这里登记）", O("能力不存在", {
                "business_id": REF("business", "业务 ID"),
                "consequence": E("后果", ["H1", "H2", "H3"]),
                "verified": E("是否完成了全部追踪、确认不存在（no 会使结果变成评估未完成）", YN),
                "reason": S("依据，例如 UpgradeCap 已销毁、代码中不存在暂停开关"),
                "evidence": L("证据", EV, min_items=1),
            })),
        }),
    },
    "O5-config.json": {
        "step": "O5",
        "root": O("参数配置检查", {
            "checks": L("专项第 3 节每一行，在每个市场（或 ALL）上各一条", CHECK, min_items=1),
        }),
    },
    "O6-funds.json": {
        "step": "O6",
        "root": O("资金与外部依赖检查", {
            "checks": L("专项第 4 节每一行，以及通用预言机检查，在每个市场（或 ALL）上各一条", CHECK, min_items=1),
        }),
    },
    "O7-fatal.json": {
        "step": "O7",
        "root": O("致命项", {
            "fatal": L("每个致命项候选一条；脚本提示的 X1 候选必须登记；没有候选就留空 []", O("致命项候选", {
                "id": S("候选 ID，格式 XF01", id="fatal"),
                "kind": E("类型", ["X1", "X2", "X3"]),
                "business_ids": REFS("business", "受影响的业务 ID", min_items=1),
                "path_id": S("X1 写对应的 O4 路径 ID；其他写 无"),
                "fact": S("已证实的事实，一两句话"),
                "evidence": L("证据", EV, min_items=1),
                "human_decision": E("由人确认：agent 一律填 pending；人填 confirmed（触发，业务记 0）或 rejected（不触发）", ["pending", "confirmed", "rejected"]),
                "human_reviewer": S("确认人姓名；pending 时写 无"),
            })),
        }),
    },
    "O8-tvl.json": {
        "step": "O8",
        "root": O("TVL", {
            "tvl_available": E("能否拿到各业务的 TVL（no 时所有业务等权）", YN),
            "tvl_source": E("业务 TVL 的口径，同一次评估的所有业务用同一个：defillama；official_dapp 官方 dapp 的统计；onchain_balances 链上模块余额 × 价格；拿不到写 none",
                            ["defillama", "official_dapp", "onchain_balances", "none"]),
            "market_tvl_source": E("市场 TVL 的口径（没有市场写 none）", ["defillama", "official_dapp", "onchain_balances", "none"]),
            "price_source": S("onchain_balances 口径用的美元价格来源，例如 Pyth、CoinGecko；其他口径写 无"),
            "tvl_time_utc": S("TVL 数据的时间，UTC ISO8601；拿不到写 无", pattern=r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z|无)$"),
            "businesses": L("每个纳入的业务一条", O("业务 TVL", {
                "business_id": REF("business", "业务 ID"),
                "tvl_usd": F("快照时该业务托管的用户资产（美元）；不托管资产写 0", min=0),
                "basis": S("怎么得到的：defillama／official_dapp 写取的是哪一项；onchain_balances 写哪些余额乘以哪些价格"),
                "reading_ids": REFS("reading", "onchain_balances 口径用到的余额读数 ID；其他口径留空 []"),
                "evidence": L("证据：DefiLlama 或官方 dapp 的页面链接；onchain_balances 可留空 []", EV),
            }), min_items=1),
            "markets": L("O1 里登记的每个市场一条", O("市场 TVL", {
                "market_id": S("市场 ID（O1 的 MK 编号）"),
                "tvl_usd": F("快照时该市场托管的用户资产（美元）", min=0),
                "basis": S("怎么得到的"),
                "reading_ids": REFS("reading", "onchain_balances 口径用到的余额读数 ID；其他口径留空 []"),
                "evidence": L("证据：页面链接；onchain_balances 可留空 []", EV),
            })),
        }),
    },
})

ONCHAIN_ORDER = ["O1", "O2", "O3", "O4", "O5", "O6", "O7", "O8"]
