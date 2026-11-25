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
    "step": E("在哪一步发现", ["P1", "P2", "P3", "P4", "P5", "C2", "C3", "C4"]),
    "object_ids": L("受影响的对象 ID", S("ID")),
    "missing": S("缺什么证据（具体到文件、地址或报告）"),
    "searched": S("已经查过哪些来源"),
    "blocks_denominator": B("是否导致代码安全的分母建不出来（true 会使结果变成「无法评分」）"),
})

CHAIN = S("链标识，格式 sui:mainnet 或 evm:<chainId>，例如 evm:1")

FILES = {
    "T0-task.json": {
        "step": "T0",
        "root": O("任务单", {
            "assessment_id": S("评估 ID，例如 navi-2026-11"),
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
                "time_utc": S("快照时间 ISO8601，例如 2026-11-25T08:00:00Z"),
                "evidence": S("能复查这个快照的链接或命令"),
            }), min_items=1),
            "deployments": L("每个「入口 → 实际执行代码」一条", O("部署实例", {
                "id": S("实例 ID，格式 I01", id="deployment"),
                "chain_id": CHAIN,
                "entry": S("用户调用的入口地址或包 ID"),
                "proxy_kind": E("入口的类型", ["none", "eip1967_proxy", "beacon_proxy", "diamond", "other_proxy", "sui_package"]),
                "actual_code": S("快照时实际执行的实现地址或包 ID（没有代理时等于 entry）"),
                "version": S("实现版本：Sui 写包 version；EVM 写实现合约地址的部署交易哈希"),
                "how_found": S("你是怎么确认实际执行代码的（读了哪个槽位、哪笔交易、哪个接口）"),
                "evidence": L("证据链接", S("URL 或命令"), min_items=1),
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
                "verify_evidence": L("核验证据（链接、命令输出文件）", S("URL 或路径")),
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
                    "lp_burn", "compensation", "perpetuals", "token", "other"]),
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
                "q1_evidence": S("问题 1 的依据：指出哪一行做了这件事；答 no 写 无"),
                "q2_preconditions_or_availability": E("问题 2：这段代码是否影响关键调用的前提、执行限制、时机或可用性（包括暂停开关）？", ["yes", "no"]),
                "q2_evidence": S("问题 2 的依据；答 no 写 无"),
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
                "applicability_evidence": S("依据：生产代码哪一行，或改动链接"),
                "fix_status": E("修复状态", ["fixed_and_reviewed", "fix_deployed_not_reviewed", "claimed_fixed", "acknowledged", "not_fixed"]),
                "fix_evidence": S("修复提交、部署交易、复核报告链接；没有写 无"),
                "centralization_only": B("是否纯中心化问题（例如 owner 权限过大）；是的话不参与封顶，交给链上权限评价"),
                "root_cause_group": S("同一根因的多条发现填同一个组名；没有写 无"),
            })),
        }),
    },
    "C5-overall.json": {
        "step": "C5",
        "root": O("总体评价（基准 5 分；A4、B2 由脚本自动判，不在这里填）", {
            "a1_multi_firm": E("A1 找补：核心模块是否被 2 家及以上不同机构审计过", ["yes", "no"]),
            "a1_evidence": S("A1 依据：列出机构和报告 ID；答 no 写 无"),
            "a2_incremental_review": E("A2 找补：是否有针对升级的增量审计或复审", ["yes", "no"]),
            "a2_evidence": S("A2 依据：报告 ID 和它复审的升级；答 no 写 无"),
            "a3_formal_verification": E("A3 找补：核心逻辑是否有形式化验证", ["yes", "no"]),
            "a3_evidence": S("A3 依据：报告 ID 和验证的函数；答 no 写 无"),
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
