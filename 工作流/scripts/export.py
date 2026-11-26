# -*- coding: utf-8 -*-
"""把各步骤的结果汇总成交付 JSON（前端唯一数据源），并按 deliverable.schema.json 自检。

格式说明见 工作流/交付格式.md。这里只做搬运和格式统一，不重新计分。
"""
import datetime
import hashlib
import json
import os
import re

import onchain

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(HERE, "deliverable.schema.json")
VERSIONS = {"skeleton": "1.1", "codeSecurity": "1.1", "onchain": "1.1", "workflow": "1.0"}
DIM_KEY = {"permissions": "permissions", "configuration": "configuration", "funds_dependencies": "fundsDependencies"}
VALIDITY = ["权限持有人或门限变更", "合约升级", "核心参数改动"]

CODE_STATUS = {"已评分": "rated", "无法评分": "incomplete", "待人工确认": "pending_review", "不适用": "not_applicable"}
ONCHAIN_STATUS = {"已评分": "rated", "已评分（致命项）": "rated", "评估未完成": "incomplete", "待人工确认": "pending_review"}
CHECK_STATUS = {"N/A": "not_applicable", "disclosure": "disclosure", "reference": "reference", "incomplete": "incomplete"}


def r2(x):
    return None if x is None else round(float(x), 2)


# ---------------------------------------------------------------- 证据字典

class Evidence:
    def __init__(self):
        self.items = {}

    def add(self, ref):
        ref = str(ref).strip()
        if not ref or ref == "无":
            return None
        eid = "EV-" + hashlib.sha1(ref.encode("utf-8")).hexdigest()[:10]
        if eid not in self.items:
            if re.match(r"^https?://", ref):
                kind, url = "url", ref
            elif ref.startswith("tx:"):
                kind, url = "tx", tx_url(ref)
            elif ref.startswith("cmd:"):
                kind, url = "command", None
            elif ref.startswith("file:"):
                kind, url = "file", None
            else:
                kind, url = "code", None
            self.items[eid] = {"kind": kind, "ref": ref, "url": url}
        return eid

    def ids(self, refs):
        out = []
        for r in refs if isinstance(refs, list) else [refs]:
            e = self.add(r)
            if e and e not in out:
                out.append(e)
        return out


def tx_url(ref):
    m = re.match(r"^tx:sui:(mainnet|testnet):(\S+)$", ref)
    if m:
        return "https://suiscan.xyz/%s/tx/%s" % (m.group(1), m.group(2))
    m = re.match(r"^tx:evm:1:(0x[0-9a-fA-F]{64})$", ref)
    if m:
        return "https://etherscan.io/tx/" + m.group(1)
    return None


# ---------------------------------------------------------------- 专项版本

def specialty_version(specialty):
    stem = onchain.SPECIALTY_FILE.get(specialty)
    if not stem:
        return None
    path = os.path.join(onchain.ONCHAIN_DIR, stem + "-onchain-security-rating-standard.md")
    with open(path, encoding="utf-8") as f:
        m = re.search(r"^- 版本 v(\d+\.\d+)", f.read(), re.M)
    return m.group(1) if m else None


# ---------------------------------------------------------------- 节点

TIER_W = {5: 5, 3: 3, 1: 1}
STATUS_CN = {"rated": "已评分", "incomplete": "评估未完成", "pending_review": "待人工确认",
             "not_applicable": "不适用", "not_assessed": "未评估", "reference": "参见其他检查",
             "disclosure": "只披露", "excluded": "不构成该后果", "info": "事实"}
DIM_CN = {"permissions": "权限管理", "configuration": "参数配置", "funds_dependencies": "资金与外部依赖"}


def node(nid, kind, label, status, score=None, weight=None, method="none", text="", summary=None,
         data=None, evidence_ids=None, children=None, ref=None):
    return {"id": nid, "kind": kind, "label": label, "status": status,
            "score": r2(score) if status == "rated" and score is not None else None,
            "weight": None if weight is None else round(float(weight), 6),
            "rule": {"method": method, "text": text}, "summary": summary, "refId": ref,
            "data": data or {}, "evidenceIds": evidence_ids or [], "children": children or []}


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def st(x):
    if is_num(x):
        return "rated"
    return {"incomplete": "incomplete", "N/A": "not_applicable", "reference": "reference",
            "disclosure": "disclosure"}.get(x, "incomplete")


def share(items):
    """items: [(key, weight)] -> {key: 归一权重}；全为 0 时等权。"""
    tot = sum(w for _, w in items)
    if not items:
        return {}
    if tot <= 0:
        return {k: 1.0 / len(items) for k, _ in items}
    return {k: w / tot for k, w in items}


def fmt_h(sec):
    return "%.1f" % (sec / 3600.0)


# ---------------------------------------------------------------- 代码安全树

def build_code_tree(c6, data, code_lines, cov, ev):
    status = {"已评分": "rated", "无法评分": "incomplete", "待人工确认": "pending_review", "不适用": "not_applicable"}[c6["status"]]
    reports = (data.get("C2-reports.json") or {}).get("reports", [])
    report_url = {r["id"]: r["url"] for r in reports}
    prod_src = {s_["id"]: s_ for s_ in data["P2-sources.json"]["sources"]}
    audited_path = {}
    for r in reports:
        for sc in r["scope"]:
            audited_path[(r["id"], sc["production_source_id"], sc["production_path"])] = sc["audited_path"]

    def carried_from(sid, f, reps):
        """沿用覆盖：写明受审版本和生产版本，并给出 diff 的链接或命令。"""
        out, refs = [], []
        src = prod_src.get(sid, {})
        for rid in reps:
            r = next((x for x in reports if x["id"] == rid), None)
            if not r:
                continue
            a = r["audited_source"]
            ap = audited_path.get((rid, sid, f), f)
            item = {"reportId": rid, "auditedCommit": a.get("commit"), "auditedPath": ap,
                    "productionCommit": src.get("commit"), "productionPath": f}
            out.append(item)
            repo = str(src.get("repo_url", ""))
            if repo.startswith("https://github.com/") and a.get("kind") == "git":
                refs.append("%s/compare/%s...%s" % (repo.rstrip("/").removesuffix(".git"), a["commit"], src.get("commit")))
            elif a.get("kind") == "git":
                refs.append("cmd:git diff --no-index <(git -C %s show %s:%s) %s/%s" % (
                    a["repo_path"], a["commit"], ap, src.get("local_path", ""), f))
            else:
                refs.append("cmd:diff -u %s/%s %s/%s" % (a.get("dir_path", ""), ap, src.get("local_path", ""), f))
        return out, refs
    resp_info = {r["id"]: r for r in data["P4-responsibilities.json"]["responsibilities"]}

    # 每一行的覆盖状态（来自 C3）和归属职责（决定其档位的第一个职责）
    line_state = {}
    for row in cov.get("detail", []):
        for ln in range(row["start"], row["end"] + 1):
            line_state[(row["source_id"], row["file"], ln)] = (row["status"], row["reason"], tuple(row["report_ids"]))
    owned = {}
    for k, e in code_lines.items():
        if e["tier"] is None:
            continue
        owner = next((r for r in e["resps"] if onchain_tier(resp_info[r]) == e["tier"]), e["resps"][0])
        owned.setdefault((e["tier"], owner), []).append(k)

    nxt = {}
    by_file = {}
    for (sid, f, ln) in code_lines:
        by_file.setdefault((sid, f), []).append(ln)
    for key, lns in by_file.items():
        lns.sort()
        for a, b in zip(lns, lns[1:]):
            nxt[(key[0], key[1], a)] = b
    applicable = [t for t in c6["tiers"] if t["status"] == "适用"]
    wsum = sum(TIER_W[t["tier"]] for t in applicable) or 1
    tier_nodes = []
    for t in c6["tiers"]:
        tid = "code/coverage/tier%d" % t["tier"]
        if t["status"] != "适用":
            tier_nodes.append(node(tid, "tier", "%s档" % t["name"], "not_applicable",
                                   text="没有这一档的代码", data={"tier": t["tier"]}))
            continue
        resp_nodes = []
        keys_by_resp = {r: ks for (tier, r), ks in owned.items() if tier == t["tier"]}
        for rid in sorted(keys_by_resp):
            ks = sorted(keys_by_resp[rid])
            covered = sum(1 for k in ks if line_state.get(k, ("uncovered",))[0].startswith("covered"))
            ranges = []
            for (sid, f, a, b, n), (s_, reason, reps) in group_lines(ks, line_state, nxt):
                loc = "%s:%d-%d" % (f, a, b)
                carried, diff_refs = carried_from(sid, f, reps) if s_ == "covered-carried" else ([], [])
                eids = ev.ids([loc] + [report_url[x] for x in reps if x in report_url] + diff_refs)
                ranges.append(node("%s/%s/%s:%d-%d" % (tid, rid, f, a, b), "code_range", loc, "rated",
                                   score=100 if s_.startswith("covered") else 0, weight=n / len(ks),
                                   method="none", text="覆盖" if s_.startswith("covered") else "未覆盖：%s" % reason,
                                   data={"sourceId": sid, "file": f, "start": a, "end": b, "effectiveLines": n,
                                         "coverage": s_, "uncoveredReason": reason, "reportIds": list(reps),
                                         "carriedFrom": carried},
                                   evidence_ids=eids))
            r = resp_info[rid]
            resp_nodes.append(node("%s/%s" % (tid, rid), "responsibility", "%s %s" % (rid, r["result"]), "rated",
                                   score=100.0 * covered / len(ks), weight=len(ks) / t["lines"],
                                   method="weighted_mean", text="覆盖行数 %d ÷ 有效行数 %d" % (covered, len(ks)),
                                   data={"lines": len(ks), "covered": covered,
                                         "q1": r["q1_assets_or_authority"], "q1Evidence": r["q1_evidence"],
                                         "q2": r["q2_preconditions_or_availability"], "q2Evidence": r["q2_evidence"]},
                                   evidence_ids=ev.ids(["%s:%d-%d" % (g["file"], g["start"], g["end"]) for g in r["ranges"]]
                                                       + r["q1_locations"] + r["q2_locations"]),
                                   children=ranges, ref=rid))
        tier_nodes.append(node(tid, "tier", "%s档" % t["name"], "rated", score=100.0 * t["rate"],
                               weight=TIER_W[t["tier"]] / wsum, method="weighted_mean",
                               text="覆盖行数 %d ÷ 有效行数 %d（直接 %d，沿用 %d）" % (
                                   t["covered"], t["lines"], t["covered_direct"], t["covered_carried"]),
                               data={"tier": t["tier"], "lines": t["lines"], "covered": t["covered"],
                                     "coveredDirect": t["covered_direct"], "coveredCarried": t["covered_carried"],
                                     "uncoveredByReason": t["uncovered_by_reason"]},
                               children=resp_nodes))
    coverage = node("code/coverage", "coverage", "审计覆盖", "rated", score=c6["coverage_score"],
                    method="weighted_mean", text="90 × Σ(档权重 × 覆盖率) ÷ Σ档权重，档权重 核心 5、重要 3、辅助 1",
                    data={"max": 90}, children=tier_nodes)
    items = [node("code/overall/base", "adjustment", "基准", "info", text="基准 5 分", data={"points": 5})]
    c5 = data.get("C5-overall.json") or {}
    adj_reports = {"A1": c5.get("a1_report_ids", []), "A2": c5.get("a2_report_ids", []), "A3": c5.get("a3_report_ids", [])}
    for it in c6["overall_items"]:
        items.append(node("code/overall/%s" % it["code"], "adjustment", it["code"], "info",
                          text="%+d" % it["points"], data={"code": it["code"], "points": it["points"], "fact": it["fact"],
                                                           "reportIds": adj_reports.get(it["code"], [])},
                          evidence_ids=ev.ids([report_url[x] for x in adj_reports.get(it["code"], []) if x in report_url])))
    pending_b1 = bool(c6["b1_observations"]) and status == "pending_review"
    for i, o in enumerate(c6["b1_observations"]):
        items.append(node("code/overall/B1-obs%d" % (i + 1), "observation", "B1 线索：%s" % o["signal"],
                          "pending_review" if pending_b1 else "info", text=o["description"],
                          data=o, evidence_ids=ev.ids(o["location"])))
    overall = node("code/overall", "overall", "总体评价", "rated", score=c6["overall_score"], method="sum",
                   text="5 + min(5, 加分合计) − 扣分合计，限制在 0–10", data={"max": 10}, children=items)
    c4 = {(x["report_id"], x["finding_id"]): x for x in (data.get("C4-findings.json") or {}).get("findings", [])}

    def fev(f):
        x = c4.get((f["report_id"], f["finding_id"]), {})
        return ev.ids([report_url.get(f["report_id"], "")] + x.get("applicability_refs", []) + x.get("fix_refs", []))

    def fdata(f, capping):
        x = c4.get((f["report_id"], f["finding_id"]), {})
        return {"reportId": f["report_id"], "findingId": f["finding_id"], "severity": f["severity"],
                "fixStatus": x.get("fix_status"), "capping": capping,
                "productionApplicable": x.get("production_applicable"),
                "applicability": x.get("applicability_evidence"), "fix": x.get("fix_evidence")}
    finds = []
    for f in c6["capping_findings"]:
        finds.append(node("code/cap/%s-%s" % (f["report_id"], f["finding_id"]), "finding", f["title"], "info",
                          text="%s，%s" % (f["severity"], f["fix_status"]),
                          data=fdata(f, True), evidence_ids=fev(f)))
    for f in c6["applicability_unknown_findings"]:
        finds.append(node("code/cap/%s-%s" % (f["report_id"], f["finding_id"]), "finding", f["title"], "disclosure",
                          text="生产适用性无法确认，不参与封顶",
                          data=fdata(f, False), evidence_ids=fev(f)))
    cap = node("code/cap", "cap", "风险封顶", "rated", score=c6["cap"], method="cap",
               text="仍存在且未完成修复复核的发现：严重 0、高 49、中 79、低 94；没有则 100", children=finds)
    if status == "rated":
        text = "min(覆盖 %.2f + 总体评价 %d, 封顶 %d)" % (c6["coverage_score"], c6["overall_score"], c6["cap"])
        summary = "%.2f 分：审计覆盖 %.2f / 90，总体评价 %d / 10，风险封顶 %d。" % (
            c6["final_score"], c6["coverage_score"], c6["overall_score"], c6["cap"])
    else:
        text = "min(覆盖分 + 总体评价, 封顶)"
        summary = "%s。%s" % (STATUS_CN[status], "；".join(c6["blockers"][:3]))
    return node("code_security", "dimension", "代码安全", status, score=c6["final_score"], method="cap", text=text,
                summary=summary, data={"blockers": c6["blockers"], "ruleVersion": VERSIONS["codeSecurity"]},
                children=[coverage, overall, cap])


def onchain_tier(resp):
    if resp["q1_assets_or_authority"] == "yes":
        return 5
    if resp["q2_preconditions_or_availability"] == "yes":
        return 3
    return 1


def group_lines(keys, line_state, nxt):
    """把同一文件中相邻的有效行（中间只隔空行或注释）、且覆盖状态相同的合成一个区间。"""
    out = []
    for k in sorted(keys):
        sid, f, ln = k
        sv = line_state.get(k, ("uncovered", "no-report", ()))
        if out:
            (psid, pf, a, b, n), psv = out[-1]
            if psid == sid and pf == f and psv == sv and nxt.get((sid, f, b)) == ln:
                out[-1] = ((psid, pf, a, ln, n + 1), psv)
                continue
        out.append(((sid, f, ln, ln, 1), sv))
    return out


# ---------------------------------------------------------------- 链上树

class OnchainTree:
    def __init__(self, o8, data, ev):
        self.o8, self.data, self.ev = o8, data, ev
        self.readings = {r["id"]: r for r in data["O3-readings.json"]["readings"]}
        self.targets = {t["id"]: t for t in data["O2-targets.json"]["targets"]}
        o4 = data["O4-permissions.json"]
        self.principals = {p["id"]: p for p in o4["principals"]}
        self.path_src = {p["id"]: p for p in o4["paths"]}
        self.absent = o4.get("absent", [])
        self.checks_src = {c["id"]: c for n in ("O5-config.json", "O6-funds.json") for c in data[n]["checks"]}
        self.fatal_src = {x["id"]: x for x in data["O7-fatal.json"]["fatal"]}
        self.o1 = {b["business_id"]: b for b in data["O1-scope.json"]["businesses"]}
        self.p3 = {b["id"]: b for b in data["P3-business-modules.json"]["businesses"]}
        self.mtvl = {m["market_id"]: m["tvl_usd"] for m in data["O8-tvl.json"].get("markets", [])}

    def reading(self, pid, rid, label=None, extra=None):
        r = self.readings[rid]
        t = self.targets.get(r["target_id"], {})
        d = {"object": t.get("address", ""), "field": r["field"], "value": r["value"] if r["status"] == "read" else None,
             "unit": r["unit"], "method": r["method"], "methodDetail": r["method_detail"],
             "atSnapshot": r["at_snapshot"], "chainId": r["chain_id"]}
        d.update(extra or {})
        return node("%s/%s" % (pid, rid), "reading", label or "%s.%s" % (t.get("id", ""), r["field"]),
                    "info" if r["status"] == "read" else "incomplete",
                    text="%s %s" % (d["value"], r["unit"]) if r["status"] == "read" else "读不到",
                    data=d, evidence_ids=self.ev.ids(r["evidence"]), ref=rid)

    def controller(self, pid, cid, weight=None, seen=()):
        p = self.principals[cid]
        nid = "%s/%s" % (pid, cid)
        kids = [self.reading(nid, r) for r in p["reading_ids"]]
        if p["kind"] == "multisig" and cid not in seen:
            tw = sum(m["weight"] for m in p["members"])
            for m in p["members"]:
                kids.append(self.controller(nid, m["principal_id"], m["weight"], seen + (cid,)))
            text = "多签，门限 %d / 总权重 %d" % (p["threshold"], tw)
        elif p["kind"] == "eoa":
            text = "单个密钥"
        else:
            text = "无法归类的控制者"
        return node(nid, "controller", p["address"], "info", text=text,
                    data={"kind": p["kind"], "address": p["address"], "chainId": p["chain_id"],
                          "threshold": p["threshold"], "memberWeight": weight}, children=kids, ref=cid)

    def path(self, pid, p):
        src = self.path_src[p["path_id"]]
        nid = "%s/%s" % (pid, p["path_id"])
        kids = [self.controller(nid, a) for a in src["approver_ids"]] + [self.reading(nid, r) for r in src["reading_ids"]]
        data = {"description": p["description"], "declaredConsequence": p["declared"], "minKeys": p.get("keys"),
                "effectiveDelaySeconds": p.get("effective_delay_s"), "delaySeconds": src["delay_seconds"],
                "delayPublic": src["delay_public"], "delayBypass": src["delay_bypass"],
                "exitClosableInDelay": src["exit_closable_in_delay"], "note": p.get("note")}
        if p.get("excluded"):
            return node(nid, "path", p["description"], "excluded", method="none", text=p["note"], data=data,
                        evidence_ids=self.ev.ids(src["evidence"]), children=kids, ref=p["path_id"])
        if "score" not in p:
            return node(nid, "path", p["description"], "incomplete", text=p.get("incomplete", ""), data=data,
                        evidence_ids=self.ev.ids(src["evidence"]), children=kids, ref=p["path_id"])
        text = "最少 %d 把密钥，有效延时 %s 小时 → %d 分" % (p["keys"], fmt_h(p["effective_delay_s"]), p["score"])
        if p.get("note"):
            text += "（%s）" % p["note"]
        return node(nid, "path", p["description"], "rated", score=p["score"], method="lookup", text=text, data=data,
                    evidence_ids=self.ev.ids(src["evidence"]), children=kids, ref=p["path_id"])

    def permissions(self, pid, bid, perm):
        nid = "%s/permissions" % pid
        cons = []
        for c in ("H1", "H2", "H3"):
            cid = "%s/%s" % (nid, c)
            v = perm["by_consequence"][c]
            ps = [self.path(cid, p) for p in perm["paths"]
                  if p["consequence"] == c or (p.get("excluded") and p["declared"] == c)]
            for a in self.absent:
                if a["business_id"] == bid and a["consequence"] == c:
                    ps.append(node("%s/absent" % cid, "absent", "确认不存在", "info" if a["verified"] == "yes" else "incomplete",
                                   text=a["reason"], data={"verified": a["verified"] == "yes"},
                                   evidence_ids=self.ev.ids(a["evidence"])))
            text = "各路径取最低" if any(k["kind"] == "path" and k["status"] == "rated" for k in ps) else \
                "没有构成该后果的路径，记 100"
            cons.append(node(cid, "consequence", c, st(v), score=v if is_num(v) else None, method="min",
                             text=text, children=ps))
        s = perm["score"]
        return node(nid, "aspect", DIM_CN["permissions"], st(s), score=s if is_num(s) else None, weight=0.4,
                    method="min", text="H1、H2、H3 取最低", children=cons)

    def check(self, pid, c):
        src = self.checks_src[c["check"]]
        nid = "%s/%s" % (pid, c["check_id"])
        kids, used = [], set()
        for i in src["inputs"]:
            if i["reading_id"] != "无":
                used.add(i["reading_id"])
                kids.append(self.reading("%s/in-%s" % (nid, i["name"]), i["reading_id"], label="%s ← %s" % (i["name"], i["reading_id"]),
                                         extra={"input": i["name"], "divideBy": i["divide_by"], "note": i["note"]}))
            else:
                kids.append(node("%s/const-%s" % (nid, i["name"]), "constant", "%s = %s" % (i["name"], i["constant"]),
                                 "info", text=i["note"], data={"input": i["name"], "value": i["constant"]}))
        for rid in src["reading_ids"]:
            if rid not in used:
                kids.append(self.reading(nid, rid))
        res = c["result"]
        if c.get("formula"):
            method = "formula"
            text = "%s：%s" % (c["formula"], "；".join("%s=%s" % kv for kv in (c.get("calc") or {}).items()))
        elif res == "reference":
            method, text = "none", "引用 %s，这里不计分" % c.get("refers_to")
        elif res in ("N/A", "disclosure", "incomplete"):
            method, text = "none", {"N/A": "机制不存在", "disclosure": "只披露，不计分",
                                    "incomplete": c.get("missing", "")}[res]
        else:
            method = "answer"
            text = {0: "违反硬约束或必要操作完全受阻", 60: "触发警戒或必要操作部分受阻",
                    90: "次要保护失效，主路径完整", 100: "均未触发"}[res]
        return node(nid, "check", c["check_id"], st(res), score=res if is_num(res) else None, method=method,
                    text=text, data={"checkId": c["check_id"], "marketId": c["market_id"], "reason": c["reason"]},
                    evidence_ids=self.ev.ids(src["evidence"]), children=kids, ref=c["check"])

    def checks_aspect(self, pid, bid, key, d, weight):
        nid = "%s/%s" % (pid, DIM_KEY[key])
        mks = [m for m in self.o1[bid].get("markets", [])]
        s = d["score"]
        if not mks:
            kids = [self.check(nid, c) for c in d["checks"]]
            return node(nid, "aspect", DIM_CN[key], st(s), score=s if is_num(s) else None, weight=weight,
                        method="min", text="各检查取最低（N/A、只披露、引用不参与）", children=kids)
        scored = {m["market_id"]: m for m in d["markets"]}
        w = share([(m["market_id"], self.mtvl.get(m["market_id"], 0)) for m in d["markets"] if is_num(m["score"])])
        kids = []
        for m in mks:
            mm = scored.get(m["id"], {"score": "N/A"})
            mid = "%s/%s" % (nid, m["id"])
            cks = [self.check(mid, c) for c in d["checks"] if c["market_id"] in ("ALL", m["id"])]
            kids.append(node(mid, "market", m["name"], st(mm["score"]), score=mm["score"] if is_num(mm["score"]) else None,
                             weight=w.get(m["id"]), method="min", text="各检查取最低（N/A、只披露、引用不参与）",
                             data={"object": m["object"], "tvlUsd": self.mtvl.get(m["id"]), "discoveredBy": m["discovered_by"]},
                             evidence_ids=self.ev.ids(m["discovery_evidence"]), children=cks, ref=m["id"]))
        return node(nid, "aspect", DIM_CN[key], st(s), score=s if is_num(s) else None, weight=weight,
                    method="weighted_mean", text="各市场按 TVL 加权", children=kids)

    def business(self, br):
        bid = br["business_id"]
        nid = "onchain/%s" % bid
        dims = br["dimensions"]
        aspects = [self.permissions(nid, bid, dims["permissions"]),
                   self.checks_aspect(nid, bid, "configuration", dims["configuration"], 0.3),
                   self.checks_aspect(nid, bid, "funds_dependencies", dims["funds_dependencies"], 0.3)]
        fatal = []
        for x in br["fatal"]:
            fs = self.fatal_src[x["id"]]
            fatal.append(node("%s/%s" % (nid, x["id"]), "fatal", "致命项 %s" % x["kind"],
                              "pending_review" if x["decision"] == "pending" else "info",
                              method="override" if x["decision"] == "confirmed" else "none",
                              text={"confirmed": "已确认，业务分记 0", "rejected": "人工确认不触发",
                                    "pending": "待人工确认"}[x["decision"]],
                              data={"kind": x["kind"], "decision": x["decision"], "fact": x["fact"]},
                              evidence_ids=self.ev.ids(fs["evidence"]), ref=x["id"]))
        status = ONCHAIN_STATUS[br["status"]]
        if any(x["decision"] == "confirmed" for x in br["fatal"]):
            method, text = "override", "致命项已确认，业务分记 0（三个大项照常展示）"
        else:
            method, text = "weighted_mean", "0.4 × 权限 + 0.3 × 配置 + 0.3 × 资金与依赖（N/A 或只有引用的大项去掉后重新归一）"
        return node(nid, "business", self.p3[bid]["name"], status, score=br["score"], weight=br["weight"],
                    method=method, text=text,
                    data={"specialty": br["specialty"], "specialtyVersion": specialty_version(br["specialty"]),
                          "tvlUsd": br.get("tvl_usd"), "notes": br.get("notes", []),
                          "incompleteReasons": br["incomplete"],
                          "zeroMarkets": [{"marketId": z["market_id"], "dimension": DIM_KEY[z["dimension"]]}
                                          for z in br["zero_markets"]]},
                    children=aspects + fatal, ref=bid)

    def build(self):
        o8 = self.o8
        status = {"已评分": "rated", "评估未完成": "incomplete", "待人工确认": "pending_review"}[o8["status"]]
        kids = [self.business(br) for br in o8["businesses"]]
        dv = o8["dimension_view"]
        f = lambda x: "—" if x is None else "%.2f" % x  # noqa: E731
        head = "%.2f 分" % o8["project_score"] if status == "rated" else STATUS_CN[status]
        summary = "%s：%d 个业务；权限 %s、配置 %s、资金与依赖 %s（按业务权重加权，仅展示）。" % (
            head, len(kids), f(dv["permissions"]), f(dv["configuration"]), f(dv["funds_dependencies"]))
        tvl = o8["weight_note"].startswith("max")
        targets = {"%s|%s" % (t["chain_id"], t["address"].lower()) for t in self.targets.values()}
        return node("onchain", "dimension", "链上安全", status, score=o8["project_score"], method="weighted_mean",
                    text="Σ 业务分 × 业务权重；业务权重 = %s" % ("max(TVL 占比, 5%) 后归一" if tvl else "等权（拿不到 TVL）"),
                    summary=summary,
                    data={"weighting": "tvl" if tvl else "equal", "budget": {"limit": o8["budget"], "used": len(targets)},
                          "dimensionView": {DIM_KEY[k]: r2(v) for k, v in dv.items()},
                          "blockingGapIds": [g["id"] for g in o8["blocking_gaps"]],
                          "ruleVersion": VERSIONS["onchain"]},
                    children=kids)


# ---------------------------------------------------------------- 汇总

def not_assessed(nid, label):
    return node(nid, "dimension", label, "not_assessed", text="本轮未评估", summary="本轮未评估。")


def build(data, c6, o8, code_lines=None, cov=None):
    ev = Evidence()
    t0 = data["T0-task.json"]
    code = build_code_tree(c6, data, code_lines, cov, ev) if c6 else not_assessed("code_security", "代码安全")
    onc = OnchainTree(o8, data, ev).build() if o8 else not_assessed("onchain", "链上安全")
    root = node("root", "root", t0["project"], None, method="none", text="根节点不出总分，只挂四个维度",
                children=[code, onc, not_assessed("business_security", "业务攻防"),
                          not_assessed("intelligence", "盘外情报")])
    root["status"] = None
    snapshots = []
    if c6:
        snapshots += [{"dimension": "code_security", "purpose": "部署基线：代码安全评估的是这个时点实际执行的代码",
                       "chainId": s["chain_id"], "blockOrCheckpoint": str(s["block_or_checkpoint"]),
                       "hash": s["block_hash_or_digest"], "timeUtc": s["time_utc"]}
                      for s in data["P1-baseline.json"]["snapshots"]]
    if o8:
        snapshots += [{"dimension": "onchain", "purpose": "链上快照：权限、参数、资金都按这个时点读取",
                       "chainId": s["chain_id"], "blockOrCheckpoint": str(s["block_or_checkpoint"]),
                       "hash": s["block_hash_or_digest"], "timeUtc": s["time_utc"]}
                      for s in data["O1-scope.json"]["snapshots"]]
    specialties = {}
    if o8:
        for br in o8["businesses"]:
            v = specialty_version(br["specialty"])
            if v:
                specialties[br["specialty"]] = v
    return {
        "schemaVersion": "3.0",
        "assessmentId": t0["assessment_id"],
        "history": {"previousAssessmentId": None if t0["previous_assessment_id"] == "无" else t0["previous_assessment_id"],
                    "reason": t0["reason"]},
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project": {"name": t0["project"], "chains": [{"chainId": c["chain_id"], "name": c["name"]} for c in t0["chains"]]},
        "ruleVersions": {"skeleton": VERSIONS["skeleton"],
                         "codeSecurity": VERSIONS["codeSecurity"] if c6 else None,
                         "onchain": VERSIONS["onchain"] if o8 else None,
                         "workflow": VERSIONS["workflow"], "specialties": specialties},
        "snapshots": snapshots,
        "validity": {"invalidatedBy": VALIDITY},
        "tree": root,
        "roleGraph": onchain.role_graph(data) if o8 else None,
        "reports": [{"id": r["id"], "firm": r["firm"], "type": r["type"], "date": r["date"], "url": r["url"]}
                    for r in (data.get("C2-reports.json") or {}).get("reports", [])] if c6 else [],
        "gaps": [{"id": g["id"], "step": g["step"], "missing": g["missing"], "blocking": g["blocks_denominator"]}
                 for g in data.get("gaps.json", {}).get("gaps", [])],
        "evidence": dict(sorted(ev.items.items())),
    }


# ---------------------------------------------------------------- 自检（JSON Schema 子集，不依赖第三方库）

def check_schema(value, schema, root, path="$", errs=None):
    errs = [] if errs is None else errs
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        return check_schema(value, root["$defs"][name], root, path, errs)
    if "anyOf" in schema:
        for sub in schema["anyOf"]:
            if not check_schema(value, sub, root, path, []):
                return errs
        errs.append("%s：不符合任何一种允许的形式" % path)
        return errs
    if "const" in schema and value != schema["const"]:
        errs.append("%s：应为 %r" % (path, schema["const"]))
    if "enum" in schema and value not in schema["enum"]:
        errs.append("%s：只能是 %s 之一，现在是 %r" % (path, schema["enum"], value))
    t = schema.get("type")
    if t:
        types = t if isinstance(t, list) else [t]
        ok = any(type_ok(value, x) for x in types)
        if not ok:
            errs.append("%s：类型应为 %s" % (path, types))
            return errs
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                errs.append("%s：缺少 %s" % (path, k))
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for k, v in value.items():
            if k in props:
                check_schema(v, props[k], root, "%s.%s" % (path, k), errs)
            elif extra is False:
                errs.append("%s：多余字段 %s" % (path, k))
            elif isinstance(extra, dict):
                check_schema(v, extra, root, "%s.%s" % (path, k), errs)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errs.append("%s：至少 %d 项" % (path, schema["minItems"]))
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append("%s：最多 %d 项" % (path, schema["maxItems"]))
        if "items" in schema:
            for i, v in enumerate(value):
                check_schema(v, schema["items"], root, "%s[%d]" % (path, i), errs)
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append("%s：格式不对（%s）" % (path, schema["pattern"]))
        if len(value) < schema.get("minLength", 0):
            errs.append("%s：不能为空" % path)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append("%s：不能小于 %s" % (path, schema["minimum"]))
        if "maximum" in schema and value > schema["maximum"]:
            errs.append("%s：不能大于 %s" % (path, schema["maximum"]))
    return errs


def recompute(n, p, errs, tol=0.02):
    """按节点写明的规则，用子节点复算分数，确认树上的每一步都对得上。"""
    for i, c in enumerate(n["children"]):
        recompute(c, "%s.children[%d]" % (p, i), errs, tol)
    if n["status"] != "rated":
        return
    m = n["rule"]["method"]
    kids = [c for c in n["children"] if c["status"] == "rated" and c["score"] is not None]
    want = None
    if n["kind"] == "dimension" and n["id"] == "code_security":
        k = {c["kind"]: c["score"] for c in n["children"]}
        want = min(k["coverage"] + k["overall"], k["cap"])
    elif m == "override":
        want = 0
    elif m == "min" and kids:
        want = min(c["score"] for c in kids)
    elif m == "weighted_mean" and kids:
        tw = sum(c["weight"] or 0 for c in kids)
        if tw > 0:
            want = sum(c["score"] * (c["weight"] or 0) for c in kids) / tw
            if n["kind"] == "coverage":
                want *= 0.9
    if want is not None and abs(want - n["score"]) > tol:
        errs.append("%s：按规则「%s」复算得 %.4f，节点写的是 %s" % (p, n["rule"]["text"], want, n["score"]))


def type_ok(v, t):
    if t == "null":
        return v is None
    if t == "boolean":
        return isinstance(v, bool)
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "string":
        return isinstance(v, str)
    if t == "array":
        return isinstance(v, list)
    if t == "object":
        return isinstance(v, dict)
    return False


def self_check(doc):
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    errs = check_schema(doc, schema, schema)
    ids = set(doc["evidence"])

    def walk(x, p):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "evidenceIds":
                    for e in v:
                        if e not in ids:
                            errs.append("%s.%s：证据 %s 不在证据字典里" % (p, k, e))
                else:
                    walk(v, p + "." + k)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, "%s[%d]" % (p, i))
    walk(doc, "$")
    seen = set()

    def tree(n, p):
        if n["id"] in seen:
            errs.append("%s：节点 ID %s 重复" % (p, n["id"]))
        seen.add(n["id"])
        if (n["score"] is not None) and n["status"] != "rated":
            errs.append("%s：只有 rated 的节点才有分数" % p)
        if n["status"] == "rated" and n["score"] is None and n["kind"] not in ("root",):
            errs.append("%s：rated 的节点必须有分数" % p)
        for i, c in enumerate(n["children"]):
            tree(c, "%s.children[%d]" % (p, i))
    tree(doc["tree"], "$.tree")
    recompute(doc["tree"], "$.tree", errs)
    dims = [c["id"] for c in doc["tree"]["children"]]
    if dims != ["code_security", "onchain", "business_security", "intelligence"]:
        errs.append("$.tree.children：必须依次是四个维度，现在是 %s" % dims)
    return errs
