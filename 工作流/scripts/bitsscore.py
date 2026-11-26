#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BitsScore 工作流脚本：前期准备、代码安全、链上。

用法（<目录> 是这一轮评估的工作目录）：
  python3 bitsscore.py init <目录>        生成空白模板
  python3 bitsscore.py validate <目录> [--step P3]
                                          检查漏填、格式和引用；--step 表示要求做到这一步
  python3 bitsscore.py graph <目录>       由 P3–P5 生成关系图 P6-graph.md
  python3 bitsscore.py lines <目录>       统计有效行并按职责定档，输出 C1-lines.json
  python3 bitsscore.py coverage <目录>    逐行判定覆盖，输出 C3-coverage.json
                                          （第一次运行会生成 C3-semantic-changes.json 让你填）
  python3 bitsscore.py score <目录>       计算代码安全分，输出 C6-score.json 和 C6-score.md
  python3 bitsscore.py onchain-score <目录>
                                          计算链上分，输出 O8-score.json 和 O8-score.md
  python3 bitsscore.py role-graph <目录>  在前期准备关系图上补齐链上实体，输出 O4-role-graph.md
  python3 bitsscore.py field-table        由 schema.py 重新生成 工作流/交付物字段表.md
  python3 bitsscore.py review <目录> <步骤> --reviewer 名字 --verdict pass|needs_fix [--comment 意见]
                                          人工复核某一步的产出（记录文件指纹，文件改过后复核自动过期）
  python3 bitsscore.py review-status <目录>
                                          列出每一步的复核状态
  python3 bitsscore.py history <项目目录> 扫描项目下的各次评估，生成 index.json 和 index.md
  python3 bitsscore.py export <目录>      重新计分并生成交付 JSON deliverable.json（前端数据源）

规则依据：评分骨架 v1.1 第 2、3 节，代码安全评分标准 v1.1，链上安全评估标准 v1.1。
计分只在本脚本和 onchain.py 中实现。
"""
import fnmatch
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema import BLANK, FILES, ID_PATTERNS, ONCHAIN_ORDER, STEP_ORDER  # noqa: E402
import onchain  # noqa: E402

RULE_VERSION = "code-security-v1.1 / skeleton-v1.1 / workflow-v1.0"
TIER_WEIGHT = {5: 5, 3: 3, 1: 1}
TIER_NAME = {5: "核心", 3: "重要", 1: "辅助"}
CAP = {"critical": 0, "high": 49, "medium": 79, "low": 94}
SEV_ORDER = ["critical", "high", "medium", "low", "informational"]
SUSPECT_RE = re.compile(
    r"(balance::(split|join|withdraw|increase|decrease)|coin::(take|put|split|join|mint|burn|from_balance|into_balance)"
    r"|transfer::(public_)?transfer|package::|UpgradeCap|\.transfer\(|\.call\{|safeTransfer|_mint\(|_burn\("
    r"|delegatecall|upgradeTo|selfdestruct)")
REASON_PRIORITY = ["dependency-changed", "changed", "no-diff", "out-of-scope", "no-report"]


# ---------------------------------------------------------------- 基础工具

def die(msg, code=1):
    print(msg)
    sys.exit(code)


def jload(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def jsave(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def is_blank(v):
    return isinstance(v, str) and v.startswith(BLANK)


def fp(d, name):
    return os.path.join(d, name)


# ---------------------------------------------------------------- init

def template(spec):
    t = spec["type"]
    if t == "obj":
        return {k: template(v) for k, v in spec["fields"].items()}
    if t == "list":
        if spec.get("min", 0) >= 1 or spec["item"]["type"] == "obj":
            return [template(spec["item"])]
        return []
    if t == "enum":
        return "%s: %s" % (BLANK, " | ".join(str(x) for x in spec["enum"]))
    if t == "int":
        return "%s: 整数" % BLANK
    if t == "float":
        return "%s: 数字" % BLANK
    if t == "bool":
        return "%s: true | false" % BLANK
    return "%s: %s" % (BLANK, spec["desc"])


def cmd_init(d):
    os.makedirs(d, exist_ok=True)
    made = []
    for name, f in FILES.items():
        if f.get("generated"):
            continue
        p = fp(d, name)
        if os.path.exists(p):
            continue
        data = template(f["root"])
        if name == "gaps.json":
            data = {"gaps": []}
        jsave(p, data)
        made.append(name)
    print("已生成模板：" + (", ".join(made) if made else "（全部已存在，未覆盖）"))
    print("下一步：按 工作流/README.md 从 T0 开始逐步填写。")


# ---------------------------------------------------------------- validate

class Ctx:
    def __init__(self):
        self.errors = []
        self.ids = {}       # kind -> {id: (file, path)}
        self.refs = []      # (kind, value, file, path)

    def err(self, file, path, msg):
        self.errors.append("%s %s：%s" % (file, path, msg))


def check(spec, v, file, path, ctx):
    t = spec["type"]
    if is_blank(v):
        ctx.err(file, path, "还没填")
        return
    if t == "obj":
        if not isinstance(v, dict):
            ctx.err(file, path, "应为对象")
            return
        for k, fs in spec["fields"].items():
            if k not in v:
                ctx.err(file, path + "." + k, "缺少字段")
            else:
                check(fs, v[k], file, path + "." + k, ctx)
        for k in v:
            if k not in spec["fields"]:
                ctx.err(file, path + "." + k, "多余字段（模板里没有）")
        return
    if t == "list":
        if not isinstance(v, list):
            ctx.err(file, path, "应为列表")
            return
        if len(v) < spec.get("min", 0):
            ctx.err(file, path, "至少要有 %d 项" % spec["min"])
        for i, x in enumerate(v):
            check(spec["item"], x, file, "%s[%d]" % (path, i), ctx)
        return
    if t == "enum":
        if v not in spec["enum"]:
            ctx.err(file, path, "只能填 %s 之一，现在是 %r" % (spec["enum"], v))
        return
    if t == "int":
        if not isinstance(v, int) or isinstance(v, bool):
            ctx.err(file, path, "应为整数")
            return
    if t == "float":
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            ctx.err(file, path, "应为数字")
            return
    if t in ("int", "float"):
        if "min" in spec and v < spec["min"]:
            ctx.err(file, path, "不能小于 %s" % spec["min"])
        if "max" in spec and v > spec["max"]:
            ctx.err(file, path, "不能大于 %s" % spec["max"])
        return
    if t == "bool":
        if not isinstance(v, bool):
            ctx.err(file, path, "应为 true 或 false")
        return
    if t == "str":
        if not isinstance(v, str) or not v.strip():
            ctx.err(file, path, "应为非空文本")
            return
        if "pattern" in spec and not re.match(spec["pattern"], v):
            ctx.err(file, path, "格式不对（现在是 %r）。要求：%s" % (v[:60], spec["desc"]))
        if "id" in spec:
            kind = spec["id"]
            if not re.match(ID_PATTERNS[kind], v):
                ctx.err(file, path, "ID 格式不对，应匹配 %s" % ID_PATTERNS[kind])
            if v in ctx.ids.setdefault(kind, {}):
                ctx.err(file, path, "ID %s 重复" % v)
            ctx.ids[kind][v] = (file, path)
        if "ref" in spec:
            ctx.refs.append((spec["ref"], v, file, path))


def parse_ranges(rs):
    out = []
    for r in rs or []:
        if isinstance(r, list) and len(r) == 2:
            out.append((r[0], r[1]))
    return out


def file_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().split("\n")


def validate(d, upto=None, quiet=False, skip=()):
    ctx = Ctx()
    data = {}
    required = []
    if upto:
        if upto in STEP_ORDER:
            required = STEP_ORDER[: STEP_ORDER.index(upto) + 1]
        elif upto in ONCHAIN_ORDER:
            required = STEP_ORDER[: STEP_ORDER.index("P5") + 1] + ONCHAIN_ORDER[: ONCHAIN_ORDER.index(upto) + 1]
        else:
            die("--step 只能是 %s" % (STEP_ORDER + ONCHAIN_ORDER))
    for name, f in FILES.items():
        if name in skip:
            continue
        if upto and f["step"] != "*" and f["step"] not in required:
            continue
        p = fp(d, name)
        if not os.path.exists(p):
            if f["step"] in required and not f.get("generated"):
                ctx.err(name, "", "文件不存在（这一步还没做）")
            continue
        try:
            data[name] = jload(p)
        except Exception as e:  # noqa: BLE001
            ctx.err(name, "", "不是合法的 JSON：%s" % e)
            continue
        check(f["root"], data[name], name, "$", ctx)

    # 引用检查
    for kind, v, file, path in ctx.refs:
        if kind == "source" and v == "外部":
            continue
        if v not in ctx.ids.get(kind, {}):
            ctx.err(file, path, "引用的 %s ID %s 不存在" % (kind, v))

    # 跨文件规则
    t0 = data.get("T0-task.json")
    chains = {c.get("chain_id") for c in (t0 or {}).get("chains", []) if isinstance(c, dict)}
    if t0:
        prev, why = t0.get("previous_assessment_id"), t0.get("reason")
        if (prev == "无") != (why == "first"):
            ctx.err("T0-task.json", "$.reason", "第一次评估：reason 填 first，previous_assessment_id 写 无；重评：两者都要填")
        aid = str(t0.get("assessment_id", ""))
        if prev not in (None, "无") and not is_blank(str(prev)) and prev == aid:
            ctx.err("T0-task.json", "$.previous_assessment_id", "不能指向自己")
        parent = os.path.dirname(os.path.abspath(d))
        if prev not in (None, "无") and not is_blank(str(prev)) and not os.path.isdir(os.path.join(parent, str(prev))):
            ctx.err("T0-task.json", "$.previous_assessment_id", "同一项目目录下找不到上一次评估 %s（应在 %s）" % (prev, parent))
        if not is_blank(aid) and os.path.basename(os.path.abspath(d)) != aid:
            ctx.err("T0-task.json", "$.assessment_id", "评估目录名要和评估 ID 一致：目录是 %s" % os.path.basename(os.path.abspath(d)))
    p1 = data.get("P1-baseline.json")
    if p1 and t0:
        for i, s in enumerate(p1.get("snapshots", [])):
            if isinstance(s, dict) and s.get("chain_id") not in chains:
                ctx.err("P1-baseline.json", "$.snapshots[%d].chain_id" % i, "不在 T0 的 chains 里")
        snap_chains = {s.get("chain_id") for s in p1.get("snapshots", []) if isinstance(s, dict)}
        for i, x in enumerate(p1.get("deployments", [])):
            if isinstance(x, dict) and x.get("chain_id") not in snap_chains:
                ctx.err("P1-baseline.json", "$.deployments[%d].chain_id" % i, "这条链没有快照")
    p2 = data.get("P2-sources.json")
    srcs = {}
    if p2:
        used = set()
        for i, s in enumerate(p2.get("sources", [])):
            if not isinstance(s, dict):
                continue
            srcs[s.get("id")] = s
            used.update(s.get("deployment_ids") or [])
            c = s.get("commit", "")
            if isinstance(c, str) and not is_blank(c) and not re.match(r"^([0-9a-f]{40}|[0-9a-f]{64})$", c):
                ctx.err("P2-sources.json", "$.sources[%d].commit" % i, "应为 40 位 commit 或 64 位 sha256（小写十六进制）")
            lp = s.get("local_path", "")
            if isinstance(lp, str) and not is_blank(lp) and not os.path.isdir(lp):
                ctx.err("P2-sources.json", "$.sources[%d].local_path" % i, "目录不存在：%s" % lp)
        if p1:
            for x in p1.get("deployments", []):
                if isinstance(x, dict) and x.get("id") not in used:
                    ctx.err("P2-sources.json", "$.sources", "部署实例 %s 没有对应的源码记录" % x.get("id"))
    p3 = data.get("P3-business-modules.json")
    if p3:
        for i, m in enumerate(p3.get("modules", [])):
            if isinstance(m, dict) and m.get("source_id") == "外部" and m.get("is_external") is not True:
                ctx.err("P3-business-modules.json", "$.modules[%d]" % i, "source_id 写了 外部，is_external 必须是 true")
    p4 = data.get("P4-responsibilities.json")
    if p4 and srcs:
        for i, r in enumerate(p4.get("responsibilities", [])):
            if not isinstance(r, dict):
                continue
            for j, rg in enumerate(r.get("ranges") or []):
                if not isinstance(rg, dict):
                    continue
                s = srcs.get(rg.get("source_id"))
                if not s or is_blank(s.get("local_path", "")):
                    continue
                pth = os.path.join(s["local_path"], str(rg.get("file")))
                where = "$.responsibilities[%d].ranges[%d]" % (i, j)
                if not os.path.isfile(pth):
                    ctx.err("P4-responsibilities.json", where, "文件不存在：%s" % pth)
                    continue
                n = len(file_lines(pth))
                st, en = rg.get("start"), rg.get("end")
                if isinstance(st, int) and isinstance(en, int) and not (1 <= st <= en <= n):
                    ctx.err("P4-responsibilities.json", where, "行号超出范围（文件共 %d 行，且起始不能大于结束）" % n)
            for q, ev in (("q1_assets_or_authority", "q1_locations"), ("q2_preconditions_or_availability", "q2_locations")):
                if r.get(q) == "yes" and not r.get(ev):
                    ctx.err("P4-responsibilities.json", "$.responsibilities[%d].%s" % (i, ev), "答了 yes 就要写源码位置")
                if r.get(q) == "no" and r.get(ev):
                    ctx.err("P4-responsibilities.json", "$.responsibilities[%d].%s" % (i, ev), "答 no 时留空 []")
            for q, ev in (("q1_assets_or_authority", "q1_evidence"), ("q2_preconditions_or_availability", "q2_evidence")):
                if r.get(q) == "yes" and str(r.get(ev, "")).strip() in ("无", ""):
                    ctx.err("P4-responsibilities.json", "$.responsibilities[%d].%s" % (i, ev), "答了 yes 就要写依据")
    c2 = data.get("C2-reports.json")
    if c2:
        for i, r in enumerate(c2.get("reports", [])):
            if not isinstance(r, dict):
                continue
            a = r.get("audited_source") or {}
            where = "$.reports[%d].audited_source" % i
            if a.get("kind") == "git":
                rp, cm = a.get("repo_path", ""), a.get("commit", "")
                if not os.path.isdir(str(rp)):
                    ctx.err("C2-reports.json", where + ".repo_path", "目录不存在：%s" % rp)
                elif subprocess.run(["git", "-C", rp, "cat-file", "-e", str(cm) + "^{commit}"],
                                    capture_output=True).returncode != 0:
                    ctx.err("C2-reports.json", where + ".commit", "仓库里找不到这个 commit：%s" % cm)
            if a.get("kind") == "dir" and not os.path.isdir(str(a.get("dir_path", ""))):
                ctx.err("C2-reports.json", where + ".dir_path", "目录不存在")
            for j, sc in enumerate(r.get("scope") or []):
                if not isinstance(sc, dict):
                    continue
                s = srcs.get(sc.get("production_source_id"))
                if s and not is_blank(s.get("local_path", "")):
                    pth = os.path.join(s["local_path"], str(sc.get("production_path")))
                    if not os.path.isfile(pth):
                        ctx.err("C2-reports.json", "$.reports[%d].scope[%d].production_path" % (i, j),
                                "生产版本里没有这个文件：%s（文件已删除就不用登记）" % pth)
    c4 = data.get("C4-findings.json")
    if c4:
        for i, x in enumerate(c4.get("findings", [])):
            if not isinstance(x, dict):
                continue
            if x.get("severity") == "unrated" and x.get("assessor_severity") == "same":
                ctx.err("C4-findings.json", "$.findings[%d].assessor_severity" % i, "报告未定级，必须由你定级")
            if x.get("severity") != "unrated" and x.get("assessor_severity") not in ("same", None):
                ctx.err("C4-findings.json", "$.findings[%d].assessor_severity" % i, "报告已定级，这里写 same")
    if c4:
        for i, x in enumerate(c4.get("findings", [])):
            if isinstance(x, dict) and x.get("fix_status") in ("fixed_and_reviewed", "fix_deployed_not_reviewed") and not x.get("fix_refs"):
                ctx.err("C4-findings.json", "$.findings[%d].fix_refs" % i, "修复状态是已修复，要给出修复提交、部署交易或复核报告的引用")
    c5 = data.get("C5-overall.json")
    if c5:
        for q, ids in (("a1_multi_firm", "a1_report_ids"), ("a2_incremental_review", "a2_report_ids"),
                       ("a3_formal_verification", "a3_report_ids")):
            if c5.get(q) == "yes" and not c5.get(ids):
                ctx.err("C5-overall.json", "$." + ids, "答了 yes 就要列出依据的报告 ID")
            if c5.get(q) == "no" and c5.get(ids):
                ctx.err("C5-overall.json", "$." + ids, "答 no 时留空 []")
        if c5.get("a1_multi_firm") == "yes" and c2:
            firms = {r.get("firm") for r in c2.get("reports", []) if r.get("id") in (c5.get("a1_report_ids") or [])}
            if len(firms) < 2:
                ctx.err("C5-overall.json", "$.a1_report_ids", "A1 要求至少两家不同机构，这里列出的报告只来自 %d 家" % len(firms))
        for q, ev in (("a1_multi_firm", "a1_evidence"), ("a2_incremental_review", "a2_evidence"),
                      ("a3_formal_verification", "a3_evidence"), ("b3_unaudited_cross_module", "b3_evidence")):
            if c5.get(q) == "yes" and str(c5.get(ev, "")).strip() in ("无", ""):
                ctx.err("C5-overall.json", "$." + ev, "答了 yes 就要写依据")
        obs = c5.get("b1_observations") or []
        dec = c5.get("b1_human_decision")
        if not obs and dec not in ("not_applicable", None) and not is_blank(dec or ""):
            ctx.err("C5-overall.json", "$.b1_human_decision", "没有 B1 线索时填 not_applicable")
        if obs and dec == "not_applicable":
            ctx.err("C5-overall.json", "$.b1_human_decision", "有 B1 线索时，agent 填 pending，等人确认")
        if dec in ("deduct", "no_deduct") and str(c5.get("b1_human_reviewer", "")).strip() in ("无", ""):
            ctx.err("C5-overall.json", "$.b1_human_reviewer", "人确认后要写确认人")

    onchain.validate_onchain(data, ctx, is_blank)
    if not quiet and data.get("O2-targets.json") and data.get("O1-scope.json"):
        n = len({"%s|%s" % (t.get("chain_id"), str(t.get("address", "")).lower())
                 for t in data["O2-targets.json"].get("targets", []) if isinstance(t, dict)})
        print("取证预算：已列 %d 个目标，预算 %d" % (n, onchain.budget_of(data)))

    if not quiet:
        if ctx.errors:
            print("发现 %d 个问题：" % len(ctx.errors))
            for e in ctx.errors:
                print("  - " + e)
        else:
            print("检查通过" + ("（已做到 %s）" % upto if upto else ""))
    return ctx.errors, data


def need_valid(d, upto, skip=()):
    errs, data = validate(d, upto, quiet=True, skip=skip)
    if errs:
        print("先修好以下问题再继续（也可以运行 validate 查看）：")
        for e in errs[:40]:
            print("  - " + e)
        if len(errs) > 40:
            print("  …… 共 %d 个" % len(errs))
        sys.exit(1)
    return data


# ---------------------------------------------------------------- 有效行

def effective_lines(text, language):
    """返回 [(行号, 去掉注释后的代码文本)]，只含有效行。"""
    lines = text.split("\n")
    out = []
    if language == "vyper":
        for i, ln in enumerate(lines, 1):
            code = re.sub(r"#.*$", "", ln)
            if code.strip():
                out.append((i, code))
        return out
    quotes = ("\"", "'") if language == "solidity" else ("\"",)
    in_block = False
    for i, ln in enumerate(lines, 1):
        code = []
        j = 0
        in_str = None
        while j < len(ln):
            c = ln[j]
            nxt = ln[j:j + 2]
            if in_block:
                if nxt == "*/":
                    in_block = False
                    j += 2
                    continue
                j += 1
                continue
            if in_str:
                code.append(c)
                if c == "\\":
                    code.append(ln[j + 1:j + 2])
                    j += 2
                    continue
                if c == in_str:
                    in_str = None
                j += 1
                continue
            if nxt == "//":
                break
            if nxt == "/*":
                in_block = True
                j += 2
                continue
            if c in quotes:
                in_str = c
            code.append(c)
            j += 1
        s = "".join(code)
        if s.strip():
            out.append((i, s))
    return out


def norm(s):
    return re.sub(r"\s+", "", s)


def scope_files(src):
    root = src["local_path"]
    files = set()
    for g in src["in_scope_globs"]:
        for p in glob.glob(os.path.join(root, g), recursive=True):
            if os.path.isfile(p):
                files.add(os.path.relpath(p, root))
    out = []
    for f in sorted(files):
        if any(fnmatch.fnmatch(f, x) for x in src.get("excluded_globs") or []):
            continue
        out.append(f)
    return out


def tier_of(resp):
    if resp["q1_assets_or_authority"] == "yes":
        return 5
    if resp["q2_preconditions_or_availability"] == "yes":
        return 3
    return 1


def compute_lines(d, data):
    srcs = {s["id"]: s for s in data["P2-sources.json"]["sources"]}
    resps = data["P4-responsibilities.json"]["responsibilities"]
    lines = {}   # (sid, file, ln) -> {"text":..., "tier":..., "resps":[...]}
    texts = {}
    for sid, s in srcs.items():
        for f in scope_files(s):
            with open(os.path.join(s["local_path"], f), encoding="utf-8", errors="replace") as h:
                t = h.read()
            texts[(sid, f)] = t
            for ln, code in effective_lines(t, s["language"]):
                lines[(sid, f, ln)] = {"text": code, "tier": None, "resps": []}
    outside = []
    for r in resps:
        tr = tier_of(r)
        for rg in r["ranges"]:
            hit = False
            for ln in range(rg["start"], rg["end"] + 1):
                k = (rg["source_id"], rg["file"], ln)
                if k in lines:
                    hit = True
                    e = lines[k]
                    e["resps"].append(r["id"])
                    if e["tier"] is None or tr > e["tier"]:
                        e["tier"] = tr
            if not hit:
                outside.append("%s 的区间 %s:%s-%s 不在纳入统计的文件里，或者全是空行和注释" % (
                    r["id"], rg["file"], rg["start"], rg["end"]))
    return lines, texts, outside


def to_ranges(nums):
    nums = sorted(nums)
    out = []
    for n in nums:
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return out


def group_ranges(keys):
    by = {}
    for sid, f, ln in keys:
        by.setdefault((sid, f), []).append(ln)
    return [{"source_id": sid, "file": f, "ranges": to_ranges(v)} for (sid, f), v in sorted(by.items())]


def cmd_lines(d, write=True):
    data = need_valid(d, "P4")
    lines, _, outside = compute_lines(d, data)
    unassigned = [k for k, v in lines.items() if v["tier"] is None]
    per_tier = {5: 0, 3: 0, 1: 0}
    for v in lines.values():
        if v["tier"]:
            per_tier[v["tier"]] += 1
    suspicious = [k for k, v in lines.items() if v["tier"] == 1 and SUSPECT_RE.search(v["text"])]
    res = {
        "rule_version": RULE_VERSION,
        "suspicious_tier1_lines": group_ranges(suspicious),
        "total_effective_lines": len(lines),
        "lines_by_tier": {"5": per_tier[5], "3": per_tier[3], "1": per_tier[1]},
        "unassigned_lines": len(unassigned),
        "unassigned_detail": group_ranges(unassigned),
        "ranges_outside_scope": outside,
    }
    if write:
        jsave(fp(d, "C1-lines.json"), res)
        print("有效行 %d：核心 %d，重要 %d，辅助 %d；未归档 %d" % (
            len(lines), per_tier[5], per_tier[3], per_tier[1], len(unassigned)))
        if unassigned:
            print("有未归档的有效行（明细见 C1-lines.json 的 unassigned_detail）。回到 P4，把它们归入某个职责，或者在 P2 的 excluded_globs 里排除。")
        if suspicious:
            print("警告：有 %d 行看起来在操作资产或权限，却被定成了辅助档（明细见 suspicious_tier1_lines）。回到 P4 复核这些行所属职责的问题 1。" % len(suspicious))
        if outside:
            print("注意：有职责区间没有落在统计范围内：")
            for o in outside:
                print("  - " + o)
        print("已写入 C1-lines.json")
    return lines, unassigned, outside


# ---------------------------------------------------------------- 覆盖

SYM_RE = re.compile(r"\b(fun|function|struct|modifier|event|contract|module|fn|interface|library)\s+([A-Za-z_]\w*)")


def enclosing(raw_lines, ln):
    for i in range(min(ln, len(raw_lines)) - 1, -1, -1):
        m = SYM_RE.search(raw_lines[i])
        if m:
            return "%s %s" % (m.group(1), m.group(2))
    return "未知"


def audited_text(rep, path):
    a = rep["audited_source"]
    if a["kind"] == "git":
        r = subprocess.run(["git", "-C", a["repo_path"], "show", "%s:%s" % (a["commit"], path)],
                           capture_output=True)
        if r.returncode != 0:
            return None
        return r.stdout.decode("utf-8", errors="replace")
    if a["kind"] == "dir":
        p = os.path.join(a["dir_path"], path)
        if os.path.isfile(p):
            with open(p, encoding="utf-8", errors="replace") as h:
                return h.read()
    return None


def in_ranges(n, rs):
    return any(a <= n <= b for a, b in rs)


def analyse(d, data):
    """对每份报告的每个范围文件做比对。返回 (逐行结果, 改动清单)。"""
    srcs = {s["id"]: s for s in data["P2-sources.json"]["sources"]}
    reports = data["C2-reports.json"]["reports"]
    per_line = {}   # (sid, file, ln) -> {report_id: status}
    changes = []
    report_files = {}
    for rep in reports:
        prod_commit = None
        for sc in rep["scope"]:
            sid = sc["production_source_id"]
            s = srcs[sid]
            prod_commit = s["commit"]
            ppath = sc["production_path"]
            report_files.setdefault(rep["id"], set()).add((sid, ppath))
            with open(os.path.join(s["local_path"], ppath), encoding="utf-8", errors="replace") as h:
                ptext = h.read()
            p_eff = effective_lines(ptext, s["language"])
            atext = audited_text(rep, sc["audited_path"]) if rep["audited_source"]["kind"] != "unavailable" else None
            if atext is None:
                for ln, _ in p_eff:
                    per_line.setdefault((sid, ppath, ln), {})[rep["id"]] = "no-diff"
                continue
            a_eff = effective_lines(atext, s["language"])
            only = parse_ranges(sc.get("only_line_ranges"))
            excl = parse_ranges(sc.get("excluded_line_ranges"))

            def a_in_scope(n):
                return (not only or in_ranges(n, only)) and not in_ranges(n, excl)

            an = [norm(x) for _, x in a_eff]
            pn = [norm(x) for _, x in p_eff]
            same_commit = (rep["audited_source"]["kind"] == "git" and rep["audited_source"]["commit"] == prod_commit)
            identical = same_commit or an == pn
            label = "covered-direct" if identical else "covered-carried"
            sm = SequenceMatcher(None, an, pn, autojunk=False)
            araw, praw = atext.split("\n"), ptext.split("\n")
            a_syms = {m.group(2) for m in SYM_RE.finditer(atext)}
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == "equal":
                    for k in range(i2 - i1):
                        aln = a_eff[i1 + k][0]
                        pln = p_eff[j1 + k][0]
                        st = label if a_in_scope(aln) else "out-of-scope"
                        per_line.setdefault((sid, ppath, pln), {})[rep["id"]] = st
                    continue
                for k in range(j1, j2):
                    per_line.setdefault((sid, ppath, p_eff[k][0]), {})[rep["id"]] = "changed"
                alns = [a_eff[k][0] for k in range(i1, i2)]
                plns = [p_eff[k][0] for k in range(j1, j2)]
                if plns:
                    sym = enclosing(praw, plns[0])
                else:
                    sym = enclosing(araw, alns[0])
                preview = ["- " + araw[n - 1].strip() for n in alns[:4]] + ["+ " + praw[n - 1].strip() for n in plns[:4]]
                key = "%s|%s|%s|%s" % (rep["id"], ppath, alns[:1] + alns[-1:], plns[:1] + plns[-1:])
                changes.append({
                    "change_id": "CH-" + hashlib.sha1(key.encode()).hexdigest()[:10],
                    "report_id": rep["id"],
                    "production_path": ppath,
                    "audited_lines": "%d-%d" % (alns[0], alns[-1]) if alns else "无（新增）",
                    "production_lines": "%d-%d" % (plns[0], plns[-1]) if plns else "无（删除）",
                    "enclosing_symbol": sym,
                    "diff_preview": " / ".join(preview)[:600],
                    "semantic_change": "%s: yes | no" % BLANK,
                    "identifiers": [],
                    "reason": "%s: 一句话理由" % BLANK,
                    "_sid": sid,
                    "_plns": plns,
                    "_new_symbol": any(m.group(2) not in a_syms for n in plns for m in SYM_RE.finditer(praw[n - 1])),
                })
    return per_line, changes, report_files


def cmd_coverage(d, write=True):
    data = need_valid(d, "C2")
    lines, unassigned, _ = cmd_lines(d, write=False)
    per_line, changes, report_files = analyse(d, data)
    sem_path = fp(d, "C3-semantic-changes.json")
    old = {}
    if os.path.exists(sem_path):
        for c in jload(sem_path).get("changes", []):
            old[c.get("change_id")] = c
    merged = []
    for c in changes:
        o = old.get(c["change_id"])
        if o:
            for k in ("semantic_change", "identifiers", "reason"):
                c[k] = o.get(k, c[k])
        merged.append(c)
    jsave(sem_path, {"changes": [{k: v for k, v in c.items() if not k.startswith("_")} for c in merged]})
    pending = [c for c in merged if is_blank(c["semantic_change"]) or is_blank(c["reason"])
               or (c["semantic_change"] == "yes" and not c["identifiers"])]
    if pending:
        print("C3-semantic-changes.json 里有 %d 处改动需要你判断（共 %d 处）。" % (len(pending), len(merged)))
        print("对每一处填 semantic_change（yes/no）、identifiers（yes 时必填）和 reason，然后再运行一次 coverage。")
        sys.exit(2)
    need_valid(d, "C3")

    dep = {}
    for c in merged:
        if c["semantic_change"] == "yes":
            dep.setdefault(c["report_id"], set()).update(c["identifiers"])
    for rid, idents in dep.items():
        if not idents:
            continue
        pat = re.compile(r"\b(" + "|".join(re.escape(x) for x in sorted(idents)) + r")\b")
        files = report_files.get(rid, set())
        for (sid, f, ln), st in per_line.items():
            if (sid, f) in files and st.get(rid, "").startswith("covered") and (sid, f, ln) in lines:
                if pat.search(lines[(sid, f, ln)]["text"]):
                    st[rid] = "dependency-changed"

    final = {}
    for k in lines:
        st = per_line.get(k)
        if not st:
            final[k] = ("uncovered", "no-report", [])
            continue
        cov = [r for r, x in st.items() if x.startswith("covered")]
        if cov:
            kind = "covered-direct" if any(st[r] == "covered-direct" for r in cov) else "covered-carried"
            final[k] = (kind, None, sorted(cov))
        else:
            reason = min(st.values(), key=lambda x: REASON_PRIORITY.index(x))
            final[k] = ("uncovered", reason, sorted(st))
    by_tier = {}
    for k, (status, reason, reps) in final.items():
        t = lines[k]["tier"]
        b = by_tier.setdefault(str(t), {"lines": 0, "covered": 0, "covered_direct": 0, "covered_carried": 0, "uncovered_by_reason": {}})
        b["lines"] += 1
        if status.startswith("covered"):
            b["covered"] += 1
            b["covered_direct" if status == "covered-direct" else "covered_carried"] += 1
        else:
            b["uncovered_by_reason"][reason] = b["uncovered_by_reason"].get(reason, 0) + 1
    detail = {}
    for k, (status, reason, reps) in final.items():
        tag = (status, reason, ",".join(reps), lines[k]["tier"])
        detail.setdefault(tag, []).append(k)
    rows = []
    for (status, reason, reps, tier), keys in sorted(detail.items(), key=lambda x: str(x[0])):
        for g in group_ranges(keys):
            for a, b in g["ranges"]:
                rows.append({"source_id": g["source_id"], "file": g["file"], "start": a, "end": b,
                             "tier": tier, "status": status, "reason": reason, "report_ids": reps.split(",") if reps else []})
    rows.sort(key=lambda r: (r["source_id"], r["file"], r["start"]))
    # A4：核心档未覆盖的行是否全部来自审计后的小改动
    core_unc = {k for k, v in final.items() if lines[k]["tier"] == 5 and v[0] == "uncovered"}
    a4_reasons = []
    bad = {final[k][1] for k in core_unc} - {"changed", "dependency-changed"}
    if bad:
        a4_reasons.append("核心档有未覆盖行的原因不是改动：%s" % sorted(bad))
    for c in merged:
        hit = [n for n in c["_plns"] if (c["_sid"], c["production_path"], n) in core_unc]
        if not hit:
            continue
        if len(c["_plns"]) > 20:
            a4_reasons.append("%s %s 第 %s 行：单处改动超过 20 行" % (c["change_id"], c["production_path"], c["production_lines"]))
        if c["_new_symbol"]:
            a4_reasons.append("%s %s 第 %s 行：新增了受审版本中没有的函数或结构体" % (c["change_id"], c["production_path"], c["production_lines"]))
    res = {"rule_version": RULE_VERSION, "by_tier": by_tier, "unassigned_lines": len(unassigned),
           "a4_small_changes_only": not a4_reasons, "a4_failed_because": a4_reasons, "detail": rows}
    if write:
        jsave(fp(d, "C3-coverage.json"), res)
        for t in ("5", "3", "1"):
            if t in by_tier:
                b = by_tier[t]
                print("%s档：%d 行，覆盖 %d（直接 %d，沿用 %d），未覆盖原因 %s" % (
                    TIER_NAME[int(t)], b["lines"], b["covered"], b["covered_direct"], b["covered_carried"], b["uncovered_by_reason"]))
        print("已写入 C3-coverage.json")
    return res


# ---------------------------------------------------------------- 计分

FUNC_RE = re.compile(r"\b(fun|function|fn)\s+([A-Za-z_]\w*)")
LONG_FUNC = 200


def long_core_functions(data, lines):
    """B2：找出包含核心档代码、且超过 200 有效行的函数。"""
    found = []
    for s in data["P2-sources.json"]["sources"]:
        for f in scope_files(s):
            with open(os.path.join(s["local_path"], f), encoding="utf-8", errors="replace") as h:
                eff = effective_lines(h.read(), s["language"])
            i = 0
            while i < len(eff):
                ln, code = eff[i]
                m = FUNC_RE.search(code)
                if not m:
                    i += 1
                    continue
                depth, started, j = 0, False, i
                while j < len(eff):
                    c = eff[j][1]
                    if not started and ";" in c and "{" not in c:
                        break
                    depth += c.count("{") - c.count("}")
                    if "{" in c:
                        started = True
                    if started and depth <= 0:
                        break
                    j += 1
                if started:
                    span = eff[i:j + 1]
                    if len(span) > LONG_FUNC and any(lines.get((s["id"], f, x[0]), {}).get("tier") == 5 for x in span):
                        found.append("%s:%d-%d %s（%d 有效行）" % (f, span[0][0], span[-1][0], m.group(2), len(span)))
                    i = j + 1
                else:
                    i += 1
    return found


def overall_score(c5, cov, long_funcs):
    items = []
    if c5["a1_multi_firm"] == "yes":
        items.append(("A1", 1, c5["a1_evidence"]))
    if c5["a2_incremental_review"] == "yes":
        items.append(("A2", 1, c5["a2_evidence"]))
    if c5["a3_formal_verification"] == "yes":
        items.append(("A3", 1, c5["a3_evidence"]))
    if cov["a4_small_changes_only"]:
        items.append(("A4", 2, "核心档未覆盖的行全部来自审计后的小改动（脚本判定）"))
    if c5["b1_human_decision"] == "deduct":
        items.append(("B1", -2, "人工确认代码逻辑反常（%s）" % c5["b1_human_reviewer"]))
    if long_funcs:
        items.append(("B2", -1, "核心函数过长：" + "；".join(long_funcs[:5])))
    if c5["b3_unaudited_cross_module"] == "yes":
        items.append(("B3", -2, c5["b3_evidence"]))
    bonus = min(5, sum(p for _, p, _ in items if p > 0))
    minus = sum(p for _, p, _ in items if p < 0)
    return max(0, min(10, 5 + bonus + minus)), items


def cmd_score(d):
    cov = cmd_coverage(d, write=False)
    data = need_valid(d, "C5")
    blockers = []
    for x in data["P1-baseline.json"]["deployments"]:
        if x["status"] != "confirmed":
            blockers.append("部署实例 %s 的入口与实际代码对应关系未确认" % x["id"])
    for s in data["P2-sources.json"]["sources"]:
        if s["verify_result"] != "match":
            blockers.append("源码 %s 未核验为与链上一致（%s）" % (s["id"], s["verify_result"]))
    for g in data.get("gaps.json", {}).get("gaps", []):
        if g.get("blocks_denominator") is True:
            blockers.append("缺口 %s：%s" % (g["id"], g["missing"]))
    if cov["unassigned_lines"]:
        blockers.append("有 %d 行有效代码没有归入任何职责" % cov["unassigned_lines"])

    bt = cov["by_tier"]
    applicable = [int(t) for t in ("5", "3", "1") if t in bt and bt[t]["lines"] > 0]
    wsum = sum(TIER_WEIGHT[t] for t in applicable)
    tiers = []
    coverage_score = 0.0
    for t in (5, 3, 1):
        b = bt.get(str(t))
        if t not in applicable:
            tiers.append({"tier": t, "name": TIER_NAME[t], "status": "不适用"})
            continue
        full = 90.0 * TIER_WEIGHT[t] / wsum
        rate = b["covered"] / b["lines"]
        sc = rate * full
        coverage_score += sc
        tiers.append({"tier": t, "name": TIER_NAME[t], "status": "适用", "lines": b["lines"], "covered": b["covered"],
                      "covered_direct": b["covered_direct"], "covered_carried": b["covered_carried"],
                      "uncovered_by_reason": b["uncovered_by_reason"], "rate": rate, "full": full, "score": sc})

    lines, _, _ = compute_lines(d, data)
    long_funcs = long_core_functions(data, lines)
    c5 = data["C5-overall.json"]
    overall, overall_items = overall_score(c5, cov, long_funcs)
    pending_human = c5["b1_human_decision"] == "pending"
    capping, unknown = [], []
    cap = 100
    for f in data["C4-findings.json"]["findings"]:
        sev = f["severity"] if f["severity"] != "unrated" else f["assessor_severity"]
        if f["centralization_only"]:
            continue
        if f["production_applicable"] == "unknown":
            unknown.append(f)
            continue
        if f["production_applicable"] != "yes" or f["fix_status"] == "fixed_and_reviewed":
            continue
        if sev in CAP:
            capping.append(dict(f, effective_severity=sev))
            cap = min(cap, CAP[sev])

    if not applicable and not blockers:
        status, final = "不适用", None
    elif blockers:
        status, final = "无法评分", None
    elif pending_human:
        status, final = "待人工确认", None
    else:
        status, final = "已评分", min(coverage_score + overall, cap)
    res = {
        "rule_version": RULE_VERSION,
        "assessment_id": data["T0-task.json"]["assessment_id"],
        "project": data["T0-task.json"]["project"],
        "baseline_id": data["P1-baseline.json"]["baseline_id"],
        "status": status,
        "blockers": blockers,
        "tiers": tiers,
        "coverage_score": round(coverage_score, 6),
        "overall_score": overall,
        "overall_items": [{"code": c, "points": p, "fact": f} for c, p, f in overall_items],
        "a4_failed_because": cov["a4_failed_because"],
        "b1_observations": c5["b1_observations"],
        "cap": cap,
        "capping_findings": [{"report_id": f["report_id"], "finding_id": f["finding_id"], "title": f["title"],
                              "severity": f["effective_severity"], "fix_status": f["fix_status"]} for f in capping],
        "applicability_unknown_findings": [{"report_id": f["report_id"], "finding_id": f["finding_id"], "title": f["title"],
                                            "severity": f["severity"]} for f in unknown],
        "final_score": None if final is None else round(final, 6),
    }
    jsave(fp(d, "C6-score.json"), res)
    md = ["# 代码安全评分结果：%s" % res["project"], "",
          "- 评估 ID：%s；部署基线：%s；规则：%s" % (res["assessment_id"], res["baseline_id"], RULE_VERSION),
          "- **结果：%s%s**" % (status, "" if final is None else "，%.2f 分" % final), ""]
    if blockers:
        md += ["## 无法评分的原因", ""] + ["- " + b for b in blockers] + [""]
    md += ["## 覆盖", "", "| 档 | 有效行 | 覆盖 | 直接 | 沿用 | 覆盖率 | 满分 | 得分 | 未覆盖原因 |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for t in tiers:
        if t["status"] != "适用":
            md.append("| %s | 不适用 | | | | | | | |" % t["name"])
        else:
            md.append("| %s | %d | %d | %d | %d | %.2f%% | %.2f | %.2f | %s |" % (
                t["name"], t["lines"], t["covered"], t["covered_direct"], t["covered_carried"], t["rate"] * 100,
                t["full"], t["score"], ", ".join("%s %d" % kv for kv in t["uncovered_by_reason"].items()) or "—"))
    md += ["", "- 覆盖分：%.2f / 90" % coverage_score, "- 总体评价：%d / 10（基准 5）" % overall]
    md += ["  - %s %+d：%s" % (c, p, f) for c, p, f in overall_items]
    if pending_human:
        md += ["  - B1 待人工确认：agent 记录了 %d 条反常写法线索，确认前不出最终分" % len(c5["b1_observations"])]
    md += ["- 风险封顶：%d" % cap, ""]
    if c5["b1_observations"]:
        md += ["## B1 反常写法线索", "", "| 类型 | 位置 | 说明 |", "| --- | --- | --- |"]
        md += ["| %s | %s | %s |" % (o["signal"], o["location"], o["description"]) for o in c5["b1_observations"]]
        md.append("")
    if capping:
        md += ["## 参与封顶的发现", "", "| 报告 | 编号 | 标题 | 等级 | 修复状态 |", "| --- | --- | --- | --- | --- |"]
        md += ["| %s | %s | %s | %s | %s |" % (f["report_id"], f["finding_id"], f["title"], f["severity"], f["fix_status"]) for f in res["capping_findings"]]
        md.append("")
    if unknown:
        md += ["## 生产适用性无法确认的发现（不参与封顶，单独披露）", ""]
        md += ["- %s %s %s（%s）" % (f["report_id"], f["finding_id"], f["title"], f["severity"]) for f in res["applicability_unknown_findings"]]
        md.append("")
    with open(fp(d, "C6-score.md"), "w", encoding="utf-8") as h:
        h.write("\n".join(md) + "\n")
    print("结果：%s%s" % (status, "" if final is None else "，%.2f 分" % final))
    print("已写入 C6-score.json 和 C6-score.md")


# ---------------------------------------------------------------- 关系图

def q(s):
    return str(s).replace("\"", "'")


def cmd_graph(d):
    data = need_valid(d, "P5")
    p3, p4, p5 = data["P3-business-modules.json"], data["P4-responsibilities.json"], data["P5-roles-controls.json"]
    gaps = data.get("gaps.json", {}).get("gaps", [])
    out = ["# 全量关系图（脚本生成，不要手改）", "", "```mermaid", "flowchart LR"]
    for b in p3["businesses"]:
        out.append("  subgraph %s[\"%s · %s\"]" % (b["id"], b["id"], q(b["name"])))
        for m in p3["modules"]:
            if b["id"] == m["business_ids"][0]:
                shape = ("[/\"%s · %s（外部）\"/]" if m["is_external"] else "[\"%s · %s\"]") % (m["id"], q(m["name"]))
                out.append("    %s%s" % (m["id"], shape))
        out.append("  end")
    for m in p3["modules"]:
        for c in m["calls_module_ids"]:
            out.append("  %s -->|调用| %s" % (m["id"], c))
        for b in m["business_ids"][1:]:
            out.append("  %s -.->|共用| %s" % (b, m["id"]))
    for r in p4["responsibilities"]:
        out.append("  %s{{\"%s · %s档 · %s\"}}" % (r["id"], r["id"], tier_of(r), q(r["result"])[:40]))
        for m in r["module_ids"]:
            out.append("  %s -->|实现| %s" % (m, r["id"]))
    for r in p5["roles"]:
        out.append("  %s([\"%s · %s\"])" % (r["id"], r["id"], q(r["credential"])))
        for g in r["granted_by_role_ids"]:
            out.append("  %s -->|授予| %s" % (g, r["id"]))
    for k in p5["controls"]:
        out.append("  %s[[\"%s · %s · %s\"]]" % (k["id"], k["id"], q(k["entry"]), k["consequence"]))
        for r in k["role_ids"]:
            out.append("  %s -->|可调用| %s" % (r, k["id"]))
        for t in k["affected_responsibility_ids"]:
            out.append("  %s -->|作用于| %s" % (k["id"], t))
    for g in gaps:
        out.append("  %s>\"缺口 %s：%s\"]" % (g["id"], g["id"], q(g["missing"])[:40]))
        for o in g["object_ids"]:
            out.append("  %s -.- %s" % (g["id"], o))
    out += ["```", ""]
    with open(fp(d, "P6-graph.md"), "w", encoding="utf-8") as h:
        h.write("\n".join(out))
    print("已写入 P6-graph.md")


# ---------------------------------------------------------------- 链上角色关系图

def cmd_role_graph(d):
    data = need_valid(d, "O4")
    g = onchain.role_graph(data)
    shape = {"business": '(["%s"])', "module": '["%s"]', "role": '(["%s"])', "control": '[["%s"]]',
             "object": '[/"%s"/]', "eoa": '(("%s"))', "multisig": '{{"%s"}}', "timelock": '[("%s")]',
             "other": '>"%s"]', "no_holder": '>"%s"]'}
    out = ["# 链上角色关系图（脚本生成，不要手改）", "",
           "在前期准备的模块—角色—控制关系上，补充了链上实体：模块对应的顶层对象、角色的持有人、多签和时间锁的成员。"
           "同一个链上实体只有一个节点。", "", "```mermaid", "flowchart LR"]
    ids = {}
    for i, n in enumerate(g["nodes"]):
        ids[n["id"]] = "N%d" % i
        label = n["label"]
        if n["kind"] in ("eoa", "multisig", "timelock", "object"):
            label = label[:10] + "…" + label[-4:] if len(label) > 18 else label
        extra = {"multisig": " · 多签 %s" % n.get("threshold"), "timelock": " · 时间锁 %sh" % round(n.get("delaySeconds", 0) / 3600, 1),
                 "eoa": " · EOA", "control": " · %s" % n.get("consequence", "")}.get(n["kind"], "")
        out.append("  %s%s" % (ids[n["id"]], shape.get(n["kind"], '["%s"]') % q("%s · %s%s" % (n["id"] if not n["id"].startswith(("OBJ:", "NOHOLDER:")) else n["kind"], label, extra))))
    name = {"uses": "使用", "calls": "调用", "grants": "授予", "can_call": "可调用", "affects": "作用于",
            "deployed_as": "链上对象", "held_by": "持有人", "signer": "签名人", "proposer": "提议者"}
    for e in g["edges"]:
        if e["from"] in ids and e["to"] in ids:
            lab = name[e["kind"]] + (" w%d" % e["weight"] if e.get("weight", 1) != 1 else "")
            out.append("  %s -->|%s| %s" % (ids[e["from"]], lab, ids[e["to"]]))
    out += ["```", ""]
    with open(fp(d, "O4-role-graph.md"), "w", encoding="utf-8") as h:
        h.write("\n".join(out))
    print("已写入 O4-role-graph.md（%d 个节点，%d 条边）" % (len(g["nodes"]), len(g["edges"])))


# ---------------------------------------------------------------- 链上计分

def fmt(x):
    if isinstance(x, bool) or x is None:
        return "—"
    if isinstance(x, (int, float)):
        return "%.2f" % x
    return {"incomplete": "评估未完成", "reference": "参见其他大项", "N/A": "N/A",
            "disclosure": "只披露"}.get(x, str(x))


def cmd_onchain_score(d):
    data = need_valid(d, "O8")
    res = onchain.score_onchain(data)
    res["snapshots"] = data["O1-scope.json"]["snapshots"]
    res["validity"] = "分数只代表快照时点的状态。权限持有人或门限变更、合约升级、核心参数改动后，结果过期，需要重评。"
    res["budget"] = onchain.budget_of(data)
    jsave(fp(d, "O8-score.json"), res)

    out = ["# 链上评分结果", ""]
    out += ["## 快照", "", "| 链 | 区块或检查点 | 哈希或 digest | 时间（UTC） |", "| --- | --- | --- | --- |"]
    for s in res["snapshots"]:
        out.append("| %s | %s | %s | %s |" % (s["chain_id"], s["block_or_checkpoint"], s["block_hash_or_digest"], s["time_utc"]))
    out += ["", "**有效期：** " + res["validity"], ""]
    out += ["## 结果", "", "- 状态：**%s**" % res["status"],
            "- 项目链上分：**%s**" % fmt(res["project_score"]),
            "- 业务权重：%s" % res["weight_note"],
            "- 规则版本：%s" % res["rule_version"], ""]
    out += ["| 大项（按业务权重加权，仅展示） | 分数 |", "| --- | ---: |"]
    for k, v in res["dimension_view"].items():
        out.append("| %s | %s |" % (onchain.DIM_NAME[k], fmt(v)))
    for g in res["blocking_gaps"]:
        out.append("- 阻断缺口 %s：%s" % (g["id"], g["missing"]))
    for br in res["businesses"]:
        out += ["", "## 业务 %s（%s）" % (br["business_id"], br["specialty"]), "",
                "- 状态：**%s**；业务分 **%s**；权重 %.2f%%；TVL %s 美元" % (
                    br["status"], fmt(br["score"]), br["weight"] * 100, fmt(br["tvl_usd"])), ""]
        out += ["| 大项 | 分数 |", "| --- | ---: |"]
        for k, v in br["dimensions"].items():
            out.append("| %s | %s |" % (onchain.DIM_NAME[k], fmt(v["score"])))
        perm = br["dimensions"]["permissions"]
        out += ["", "**权限路径**", "", "| 路径 | 后果 | 最少密钥数 | 有效延时（小时） | 得分 | 说明 |", "| --- | --- | ---: | ---: | ---: | --- |"]
        for p in perm["paths"]:
            out.append("| %s | %s | %s | %s | %s | %s |" % (
                p["path_id"], p["consequence"], p.get("keys", "—"),
                fmt(p["effective_delay_s"] / 3600) if "effective_delay_s" in p else "—",
                fmt(p.get("score")) if "score" in p else ("不计" if p.get("excluded") else "评估未完成"),
                p.get("note", p.get("incomplete", p["description"]))))
        out.append("")
        out.append("H1／H2／H3：" + "、".join("%s %s" % (k, fmt(v)) for k, v in perm["by_consequence"].items()))
        kc = perm.get("key_concentration")
        if kc and kc.get("levels"):
            out += ["", "**密钥集中度（只披露，不计分）**", "",
                    "| 密钥数 | 签名地址（所在多签） | 能走通的路径 | 走不通的路径 |", "| ---: | --- | --- | --- |"]
            for lv in kc["levels"]:
                out.append("| %d | %s | %s | %s |" % (lv["keys"], "；".join(
                    "%s（%s）" % (a, "、".join(lv["member_of"][a]) or "单独持有") for a in lv["addresses"]),
                    "、".join(lv["controlled_paths"]), "、".join(lv["uncontrolled_paths"]) or "—"))
        elif kc and kc.get("note"):
            out += ["", "密钥集中度：" + kc["note"]]
        for dim in ("configuration", "funds_dependencies"):
            v = br["dimensions"][dim]
            out += ["", "**%s**" % onchain.DIM_NAME[dim], "", "| 检查 | 编号 | 市场 | 结果 | 计算 | 理由 |", "| --- | --- | --- | --- | --- | --- |"]
            for c in v["checks"]:
                calc = "；".join("%s=%s" % kv for kv in (c.get("calc") or {}).items())
                out.append("| %s | %s | %s | %s | %s | %s |" % (c["check"], c["check_id"], c["market_id"],
                           fmt(c["result"]), calc or "—", c["reason"].replace("|", "/")))
            if len(v["markets"]) > 1:
                out.append("")
                out.append("各市场：" + "、".join("%s %s" % (m["market_id"], fmt(m["score"])) for m in v["markets"]))
        if br["zero_markets"]:
            out += ["", "**得 0 分的市场：** " + "、".join("%s（%s）" % (z["market_id"], onchain.DIM_NAME[z["dimension"]]) for z in br["zero_markets"])]
        if br["fatal"]:
            out += ["", "**致命项：** " + "；".join("%s %s（%s）：%s" % (x["id"], x["kind"], x["decision"], x["fact"]) for x in br["fatal"])]
        if br["incomplete"]:
            out += ["", "**未完成的原因：**"] + ["- " + x for x in br["incomplete"]]
    out.append("")
    with open(fp(d, "O8-score.md"), "w", encoding="utf-8") as h:
        h.write("\n".join(out))
    print("状态：%s；项目链上分：%s" % (res["status"], fmt(res["project_score"])))
    print("已写入 O8-score.json、O8-score.md")


# ---------------------------------------------------------------- 交付 JSON

def cmd_export(d):
    import export
    t0 = jload(fp(d, "T0-task.json"))
    dims = t0.get("dimensions") or []
    c6 = o8 = None
    if "code_security" in dims:
        cmd_score(d)
        c6 = jload(fp(d, "C6-score.json"))
    if "onchain" in dims:
        cmd_onchain_score(d)
        o8 = jload(fp(d, "O8-score.json"))
    if not c6 and not o8:
        die("T0 的 dimensions 里没有 code_security 或 onchain，没有可交付的结果")
    data = {}
    for name in FILES:
        p = fp(d, name)
        if os.path.exists(p):
            data[name] = jload(p)
    code_lines = cov = None
    if c6:
        code_lines = compute_lines(d, data)[0]
        cov = jload(fp(d, "C3-coverage.json"))
    doc = export.build(data, c6, o8, code_lines, cov)
    errs = export.self_check(doc)
    if errs:
        print("交付 JSON 不符合格式，没有写出（这是脚本的问题，请交给人处理）：")
        for e in errs[:40]:
            print("  - " + e)
        sys.exit(1)
    jsave(fp(d, "deliverable.json"), doc)
    print("已写入 deliverable.json（格式自检通过）")


# ---------------------------------------------------------------- 入口

def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "field-table":
        import fields_doc
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "交付物字段表.md")
        with open(out, "w", encoding="utf-8") as h:
            h.write(fields_doc.render())
        print("已写入 工作流/交付物字段表.md")
        return
    if len(sys.argv) < 3:
        die(__doc__)
    if sys.argv[1] in ("review", "review-status", "history"):
        import records
        if sys.argv[1] == "review":
            if len(sys.argv) < 4:
                die("用法：review <目录> <步骤> --reviewer 名字 --verdict pass|needs_fix [--comment 意见]…")
            args = sys.argv[4:]
            opt = lambda k: args[args.index(k) + 1] if k in args else None  # noqa: E731
            comments = [args[i + 1] for i, a in enumerate(args) if a == "--comment"]
            records.add_review(sys.argv[2], sys.argv[3], opt("--reviewer"), opt("--verdict"), comments)
        elif sys.argv[1] == "review-status":
            records.print_status(sys.argv[2])
        else:
            records.history(sys.argv[2])
        return
    cmd, d = sys.argv[1], sys.argv[2]
    if cmd == "init":
        cmd_init(d)
    elif cmd == "validate":
        upto = None
        if "--step" in sys.argv:
            upto = sys.argv[sys.argv.index("--step") + 1]
        errs, _ = validate(d, upto)
        sys.exit(1 if errs else 0)
    elif cmd == "lines":
        cmd_lines(d)
    elif cmd == "coverage":
        cmd_coverage(d)
    elif cmd == "score":
        cmd_score(d)
    elif cmd == "graph":
        cmd_graph(d)
    elif cmd == "onchain-score":
        cmd_onchain_score(d)
    elif cmd == "role-graph":
        cmd_role_graph(d)
    elif cmd == "export":
        cmd_export(d)
    else:
        die(__doc__)


if __name__ == "__main__":
    main()
