# -*- coding: utf-8 -*-
"""由 schema.py 生成《交付物字段表》，保证文档和校验用的是同一份定义。"""
from schema import FILES

PHASES = [
    ("前期准备", ["T0-task.json", "P1-baseline.json", "P2-sources.json", "P3-business-modules.json",
              "P4-responsibilities.json", "P5-roles-controls.json", "gaps.json"]),
    ("代码安全", ["C2-reports.json", "C3-semantic-changes.json", "C4-findings.json", "C5-overall.json"]),
    ("链上", ["O1-scope.json", "O2-targets.json", "O3-readings.json", "O4-permissions.json", "O5-config.json",
            "O6-funds.json", "O7-fatal.json", "O8-tvl.json"]),
]
STEP_NAME = {"T0": "任务单", "P1": "锁定生产部署", "P2": "核验源码", "P3": "业务与模块", "P4": "职责与档位",
             "P5": "角色与控制", "*": "各步共用", "C2": "登记审计报告", "C3": "判定覆盖", "C4": "登记发现",
             "C5": "总体评价", "O1": "范围与快照", "O2": "读取清单", "O3": "读数回填", "O4": "角色关系与权限路径",
             "O5": "参数配置", "O6": "资金与依赖", "O7": "致命项", "O8": "TVL 与计分"}

GENERATED = [
    ("前期准备", "P6-graph.md", "P6", "`graph`", "模块与角色关系图（Mermaid）：业务、模块、职责（带档位）、角色、控制、缺口，以及它们之间的使用、调用、实现、授予、可调用、作用于关系"),
    ("代码安全", "C1-lines.json", "C1", "`lines`", "每个源码文件的有效行、每行的档位和所属职责；每档行数；未归入职责的行；可疑定档报警"),
    ("代码安全", "C3-semantic-changes.json", "C3", "`coverage`", "受审版本到生产版本的每处改动（脚本生成，agent 只填 `semantic_change`、`identifiers`、`reason`，字段见下文）"),
    ("代码安全", "C3-coverage.json", "C3", "`coverage`", "`by_tier`：每档行数、覆盖数（直接、沿用）、未覆盖原因计数；`detail`：逐段的覆盖状态、未覆盖原因、覆盖它的报告；`a4_small_changes_only` 及不满足的原因"),
    ("代码安全", "C6-score.json / .md", "C6", "`score`", "状态（已评分／无法评分／待人工确认／不适用）、各档覆盖、覆盖分、总体评价及加减分项、封顶及参与封顶的发现、最终分"),
    ("链上", "O4-role-graph.md", "O4", "`role-graph`", "在 P6 关系图上补齐链上实体：模块对应的顶层对象、角色持有人、多签签名人、时间锁提议者（Mermaid）"),
    ("链上", "O8-score.json / .md", "O8", "`onchain-score`", "快照、状态、项目链上分、各业务分和权重、每条权限路径的密钥数和延时、每个检查项的结果和计算过程、0 分市场、致命项、未完成原因、有效期"),
    ("最终交付", "deliverable.json", "—", "`export`", "前端唯一数据源：证据树、链上角色关系图、快照、规则版本、报告、缺口、证据字典。格式见[交付格式](./交付格式.md)"),
]


def type_text(spec):
    t = spec["type"]
    if t == "enum":
        return "枚举", " ／ ".join("`%s`" % x for x in spec["enum"])
    if t == "int":
        rng = []
        if "min" in spec:
            rng.append("≥ %s" % spec["min"])
        return "整数", "，".join(rng)
    if t == "float":
        return "数字", ("≥ %s" % spec["min"]) if "min" in spec else ""
    if t == "bool":
        return "布尔", "`true` ／ `false`"
    if t == "str":
        extra = []
        if "ref" in spec:
            extra.append("引用 %s ID" % spec["ref"])
        if "id" in spec:
            extra.append("本文件的 ID")
        if "pattern" in spec:
            extra.append("有格式要求")
        return "文本", "，".join(extra)
    return t, ""


def rows(spec, prefix=""):
    out = []
    for k, v in spec["fields"].items():
        name = prefix + k
        if v["type"] == "obj":
            out.append((name, "对象", "", v["desc"]))
            out += rows(v, name + ".")
        elif v["type"] == "list":
            item = v["item"]
            need = "至少 %d 项" % v["min"] if v.get("min") else "可为空 `[]`"
            if item["type"] == "obj":
                out.append((name + "[]", "对象列表", need, v["desc"]))
                out += rows(item, name + "[].")
            else:
                it, iv = type_text(item)
                out.append((name + "[]", "%s列表" % it, "，".join(x for x in (need, iv) if x), v["desc"]))
        else:
            t, vals = type_text(v)
            out.append((name, t, vals, v["desc"]))
    return out


def esc(x):
    return str(x).replace("|", "\\|").replace("\n", " ")


def render():
    out = ["# 交付物字段表", "",
           "> 本文件由 `python3 工作流/scripts/bitsscore.py field-table` 从 [scripts/schema.py](./scripts/schema.py) 生成，**不要手改**。"
           "字段有变化时改 schema.py，再重新生成。", "",
           "## 一、总览", "",
           "| 阶段 | 交付物 | 步骤 | 谁写 |", "| --- | --- | --- | --- |"]
    for phase, names in PHASES:
        for n in names:
            f = FILES[n]
            who = "脚本生成，agent 填部分字段" if f.get("generated") else ("agent 填，人确认部分字段" if n in ("C5-overall.json", "O7-fatal.json") else "agent")
            out.append("| %s | `%s` | %s %s | %s |" % (phase, n, f["step"], STEP_NAME.get(f["step"], ""), who))
    for phase, n, step, cmd, _ in GENERATED:
        if n == "C3-semantic-changes.json":
            continue
        out.append("| %s | `%s` | %s | 脚本（%s） |" % (phase, n, step, cmd))
    out += ["", "所有 agent 填写的文件都由 `validate` 检查：漏填、类型、枚举、格式、ID 引用，以及跨文件的一致性。", ""]
    out += ["## 二、脚本生成的交付物", "", "| 交付物 | 命令 | 内容 |", "| --- | --- | --- |"]
    for _, n, _, cmd, desc in GENERATED:
        out.append("| `%s` | %s | %s |" % (n, cmd, desc))
    out.append("")
    sec = 3
    for phase, names in PHASES:
        out += ["## %s、%s" % ("一二三四五六七八"[sec - 1], phase), ""]
        sec += 1
        for n in names:
            f = FILES[n]
            out += ["### `%s`（%s %s）" % (n, f["step"], STEP_NAME.get(f["step"], "")), "", f["root"]["desc"], "",
                    "| 字段 | 类型 | 取值或约束 | 说明 |", "| --- | --- | --- | --- |"]
            for name, t, vals, desc in rows(f["root"]):
                out.append("| `%s` | %s | %s | %s |" % (name, t, esc(vals), esc(desc)))
            out.append("")
    import onchain
    out += ["## 六、由脚本计算的公式", "",
            "下表列出的检查项，`q_hard` 和 `q_warn` 填 `by_formula`，在 `inputs` 里按「输入」列的名字逐个填写，定档由脚本完成。"
            "其余检查项回答是非题。", ""]
    for fname, (title, formula, rule, ins) in onchain.FORMULA_DOC.items():
        checks = "、".join(sorted(k for k, v in onchain.FORMULA_FOR.items() if v == fname))
        out += ["### %s（`%s`）" % (title, fname), "",
                "- 适用检查项：%s" % checks, "- 公式：%s" % formula, "- 定档：%s" % rule, "",
                "| 输入 | 含义 |", "| --- | --- |"]
        out += ["| `%s` | %s |" % (k, esc(v)) for k, v in ins.items()]
        out.append("")
    out += ["## 七、通用格式", "",
            "| 内容 | 格式 |", "| --- | --- |",
            "| 链 | `sui:mainnet`、`evm:<chainId>` |",
            "| 地址 | 小写；Sui 写完整 `0x` 加 64 位，EVM 写 `0x` 加 40 位 |",
            "| 时间 | UTC，ISO8601，以 `Z` 结尾 |",
            "| 证据引用 | 网址 `https://…`；交易 `tx:<链>:<哈希>`；命令 `cmd:<完整命令>`；本地文件 `file:<路径>`；源码位置 `<路径>:<起>-<止>` |",
            "| 表示「没有」 | 文本字段写 `无`，列表字段留空 `[]` |", ""]
    return "\n".join(out)
