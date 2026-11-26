# -*- coding: utf-8 -*-
"""BitsScore 链上评估（O1–O8）的检查与计分。

规则依据：评分骨架 v1.1 第 3 节、链上安全评估标准 v1.1、各专项现行版本。
专项检查表直接从 onchain/ 下的专项文件解析，不在这里重复抄写。
"""
import itertools
import os
import re
from decimal import Decimal, InvalidOperation

HERE = os.path.dirname(os.path.abspath(__file__))
ONCHAIN_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "onchain"))
RULE_VERSION = "onchain-v1.1 / skeleton-v1.1 / workflow-v1.0"

WEIGHTS = {"permissions": 0.4, "configuration": 0.3, "funds_dependencies": 0.3}
DIM_NAME = {"permissions": "权限管理", "configuration": "参数配置", "funds_dependencies": "资金与外部依赖"}
MIN_BUSINESS_WEIGHT = 0.05
DAY = 24 * 3600
MAX_LEAVES = 22

SPECIALTY_FILE = {
    "lending": "lending", "dex_amm": "dex", "dex_aggregator": "dex", "dex_rfq": "dex",
    "yield_vault": "yield-vault", "margin": "margin", "order_limit": "order-execution",
    "order_dca": "order-execution", "farm": "farm-incentives", "staking_redemption": "staking-redemption",
    "launchpad": "launchpad", "lp_burn": "lp-burn", "compensation": "lp-burn", "perpetuals": "perpetuals",
    "token": "fungible-token", "cdp": "cdp-stablecoin", "liquid_staking": "liquid-staking", "bridge": "bridge",
}
ORACLE_REQUIRED = {"lending", "margin", "perpetuals", "cdp"}
OR_CHECKS = {"OR-1": "funds_dependencies", "OR-2": "funds_dependencies",
             "OR-3": "funds_dependencies", "OR-4": "funds_dependencies"}
OR_DISCLOSURE = {"OR-3"}

# 有公式的检查项：check_id -> (公式名, 必填输入)
FORMULA_FOR = {
    "L-C2.1": "lending_buffer", "L-C2.3": "lending_buffer", "M-C2.1": "lending_buffer",
    "L-C2.2": "rate_curve", "M-C2.2": "margin_h", "P-C2.1": "im_mm", "OR-2": "oracle_age",
    "CD-C2.1": "cdp_buffer", "CD-F1.1": "cdp_tcr", "LS-C2.1": "lst_rate", "LS-F1.2": "concentration",
    "BR-F1.1": "coverage",
    "L-F1.1": "interval_cover", "V-F1.1": "interval_cover", "M-F1.1": "interval_cover",
    "P-F1.1": "interval_cover", "LS-F1.1": "interval_cover", "FA-F1.1": "interval_cover",
    "BR-F1.2": "interval_cover", "LB-F1.2": "interval_cover",
    "DX-F1.1": "amm_cover",
}
# 公式说明：交付物字段表里的公式表由这里生成，步骤卡只链接过去，不另抄一份
FORMULA_DOC = {
    "lending_buffer": ("抵押缓冲", "D_open = 1 − b/λ；M = 1 − λ·β；B_buf = min(D_open, M)（单一 LLTV 机制 B_buf = M）",
                       "违反 0 < b ≤ λ ≤ 1、β < 1，或 M < 0 → 0；B_buf < 5%（同底层 1%）→ 60",
                       {"b": "开仓上限（小数）；单一 LLTV 机制填常量 none；为 0 时这一行应填不适用", "lambda": "有效清算线（小数）",
                        "beta": "清算扣押倍率，例如 1.05（与 bonus 二选一）", "bonus": "清算奖励比例，例如 0.05；脚本按 β = 1 + bonus 计算（与 beta 二选一）",
                        "same_underlying": "yes／no：是否同底层组合（按 Lending 专项第 6 节证明；属于人工复核重点）"}),
    "rate_curve": ("利率曲线", "k_low = (r_kink − r0) / u_kink；k_high = (r1 − r_kink) / (1 − u_kink)",
                   "有负利率，或利率随利用率上升而下降 → 0；k_high = 0 → 60",
                   {"r0": "写法一：利用率 0 时的年利率", "r_kink": "写法一：拐点处的年利率；没有拐点填 r(0.8)",
                    "r1": "写法一：利用率 100% 时的年利率", "u_kink": "拐点利用率；没有拐点填 0.8",
                    "base_rate": "写法二（标准拐点模型）：基础利率", "slope_low": "写法二：拐点前斜率",
                    "slope_high": "写法二：拐点后斜率"}),
    "margin_h": ("价格不确定性", "H情景 = (λ / b) × (1 − εc) / (1 + εd)", "H情景 < 1 → 60",
                 {"lambda": "有效清算线", "b": "开仓上限", "eps_c": "抵押侧允许的最大价格不确定性", "eps_d": "债务侧允许的最大价格不确定性"}),
    "im_mm": ("保证金", "比较 IM 与 MM", "IM ≤ MM → 0", {"im": "初始保证金率", "mm": "维持保证金率"}),
    "oracle_age": ("价格年龄", "比较允许的最大价格年龄与上限", "拉取型 > 300 秒，或推送型 > 心跳 × 2 → 60",
                   {"oracle_type": "常量 pull（使用方按需更新）或 push（预言机定时推送）", "max_age_s": "允许的最大价格年龄（秒）",
                    "heartbeat_s": "推送型的心跳（秒）；拉取型填常量 none"}),
    "cdp_buffer": ("CDP 清算缓冲", "清算缓冲 = MCR − 1 − p", "清算缓冲 < 0 → 0；< 5%（同底层 1%）→ 60",
                   {"mcr": "最低抵押率，例如 1.10", "p": "清算罚金或奖励比例，例如 0.10", "same_underlying": "yes／no"}),
    "cdp_tcr": ("系统抵押率", "TCR = 抵押总价值 ÷ 总债务", "TCR < 1 → 0；TCR < CCR → 60",
                {"collateral_value": "全系统抵押总价值", "debt": "稳定币总债务", "ccr": "协议定义的临界抵押率；没有定义填常量 none"}),
    "lst_rate": ("LST 兑换率", "R_backing = (已质押 + 待领取 + 闲置 − 待兑付赎回) ÷ 供应量；偏离 = (R_stored − R_backing) ÷ R_backing",
                 "偏离 > 一个 epoch 的应计奖励率 → 0；|偏离| > 0.5% → 60",
                 {"r_stored": "合约存储的兑换率", "staked": "已质押总量", "pending_claim": "待领取", "idle": "闲置缓冲",
                  "pending_redeem": "待兑付赎回", "supply": "LST 总供应", "epoch_tolerance": "一个 epoch 的应计奖励率"}),
    "concentration": ("验证者集中度", "最大集中度 = 单一验证者质押量 ÷ 总质押量", "> 50% → 60",
                      {"max_stake": "质押量最大的验证者的质押量", "total_stake": "总质押量"}),
    "coverage": ("锁定覆盖", "覆盖 = 源链锁定量 ÷ 目标链流通量", "覆盖 < 1 → 0",
                 {"locked": "源链锁定量", "circulating": "目标链流通量"}),
    "interval_cover": ("区间覆盖", "比较应付区间与可用资金区间",
                       "应付下界 > 可用资金上界 → 0；两区间重叠 → 60；可用资金下界 ≥ 应付上界 → 通过",
                       {"due_low": "应付下界", "due_high": "应付上界", "avail_low": "可用资金下界", "avail_high": "可用资金上界（确定值时上下界填同一个读数）"}),
    "amm_cover": ("池子本金覆盖", "可用 = 真实余额 − 不属于 LP 的余额；余量 = 可用 − 全部头寸本金应得（每个币种一组）",
                  "可用 < 应得 → 0",
                  {"due": "全部头寸的本金应得（读取工具从 tick 表或 bin 表重建的读数，method 为 derived）",
                   "balance": "池子该币种的真实余额", "reserved": "不属于 LP 的余额，例如协议费；没有填常量 0"}),
}

# 每个公式可接受的输入写法：列表里任选一种，名字必须完全一致
FORMULA_INPUTS = {
    "lending_buffer": [["b", "lambda", "beta", "same_underlying"], ["b", "lambda", "bonus", "same_underlying"]],
    "rate_curve": [["r0", "u_kink", "r_kink", "r1"], ["base_rate", "slope_low", "slope_high", "u_kink"]],
    "margin_h": [["lambda", "b", "eps_c", "eps_d"]],
    "im_mm": [["im", "mm"]],
    "oracle_age": [["oracle_type", "max_age_s", "heartbeat_s"]],
    "cdp_buffer": [["mcr", "p", "same_underlying"]],
    "cdp_tcr": [["collateral_value", "debt", "ccr"]],
    "lst_rate": [["r_stored", "staked", "pending_claim", "idle", "pending_redeem", "supply", "epoch_tolerance"]],
    "concentration": [["max_stake", "total_stake"]],
    "coverage": [["locked", "circulating"]],
    "interval_cover": [["due_low", "due_high", "avail_low", "avail_high"]],
    "amm_cover": [["due", "balance", "reserved"]],
}


def input_set_ok(fname, names):
    """返回 (是否齐全, 缺少的名字)。"""
    best = None
    for alt in FORMULA_INPUTS[fname]:
        miss = [n for n in alt if n not in names]
        if not miss:
            return True, []
        if best is None or len(miss) < len(best):
            best = miss
    return False, best


# ---------------------------------------------------------------- 专项表解析

_ROW = re.compile(r"^\|\s*([A-Z]{1,2}-[CFD]\d\.\d+[a-z]?)\s*\|\s*([CFD]\d)\s*\|(.*)$")


def specialty_rows(specialty):
    """返回 {check_id: {"dim":..., "disclosure": bool, "file": ...}}。"""
    stem = SPECIALTY_FILE.get(specialty)
    if not stem:
        return None
    path = os.path.join(ONCHAIN_DIR, stem + "-onchain-security-rating-standard.md")
    rows = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = _ROW.match(line.strip())
            if not m:
                continue
            cid, belong, rest = m.groups()
            cols = [c.strip() for c in rest.split("|")]
            hard = cols[2] if len(cols) > 2 else ""
            warn = cols[3] if len(cols) > 3 else ""
            dim = "configuration" if belong.startswith("C") else "funds_dependencies"
            rows[cid] = {"dim": dim, "disclosure": hard in ("—", "-", "") and "只披露" in warn,
                         "file": os.path.basename(path)}
    return rows


_APPLIES = re.compile(r"^\|\s*([a-z_]+)\s*\|(.*)\|\s*$")
_CHECK_ID = re.compile(r"[A-Z]{1,2}-[CFD]\d\.\d+[a-z]?")


def applicable_ids(specialty):
    """专项里有「各业务适用的检查项」表时，返回这种业务适用的编号集合；没有这张表返回 None（全部适用）。"""
    stem = SPECIALTY_FILE.get(specialty)
    if not stem:
        return None
    path = os.path.join(ONCHAIN_DIR, stem + "-onchain-security-rating-standard.md")
    table = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = _APPLIES.match(line.strip())
            if m and m.group(1) in SPECIALTY_FILE:
                table[m.group(1)] = set(_CHECK_ID.findall(m.group(2)))
    if not table:
        return None
    if specialty not in table:
        raise ValueError("专项文件 %s 有「各业务适用的检查项」表，但没有列出 %s" % (os.path.basename(path), specialty))
    return table[specialty]


def specialty_rows_for(specialty):
    rows = specialty_rows(specialty) or {}
    ids = applicable_ids(specialty)
    return rows if ids is None else {k: v for k, v in rows.items() if k in ids}


def required_checks(specialty):
    out = dict(specialty_rows_for(specialty))
    if specialty in ORACLE_REQUIRED:
        for k, dim in OR_CHECKS.items():
            out[k] = {"dim": dim, "disclosure": k in OR_DISCLOSURE, "file": "链上安全评估标准.md"}
    return out


def allowed_check(specialty, cid):
    if cid in OR_CHECKS:
        return {"dim": OR_CHECKS[cid], "disclosure": cid in OR_DISCLOSURE}
    return specialty_rows_for(specialty).get(cid)


# ---------------------------------------------------------------- 最少密钥数

def leaves_of(pid, principals, seen=()):
    p = principals[pid]
    if pid in seen:
        raise ValueError("多签嵌套出现循环：%s" % " → ".join(seen + (pid,)))
    if p["kind"] == "eoa":
        return {"%s|%s" % (p["chain_id"], p["address"].lower())}
    if p["kind"] in ("multisig", "timelock"):
        out = set()
        for m in p["members"]:
            out |= leaves_of(m["principal_id"], principals, seen + (pid,))
        return out
    raise ValueError("控制者 %s 类型为 other，无法计算密钥数" % pid)


def satisfied(pid, chosen, principals):
    p = principals[pid]
    if p["kind"] == "eoa":
        return "%s|%s" % (p["chain_id"], p["address"].lower()) in chosen
    w = sum(m["weight"] for m in p["members"] if satisfied(m["principal_id"], chosen, principals))
    return w >= p["threshold"]


def min_keys(approver_ids, principals):
    leaves = set()
    for a in approver_ids:
        leaves |= leaves_of(a, principals)
    leaves = sorted(leaves)
    if len(leaves) > MAX_LEAVES:
        raise ValueError("涉及 %d 个签名地址，超过脚本可穷举的 %d 个，请交人计算" % (len(leaves), MAX_LEAVES))
    for k in range(1, len(leaves) + 1):
        for combo in itertools.combinations(leaves, k):
            chosen = set(combo)
            if all(satisfied(a, chosen, principals) for a in approver_ids):
                return k
    raise ValueError("门限无法被满足，请检查门限和权重")


def key_concentration(o4, business_id):
    """密钥集中度（只披露，不计分）：最少几把密钥就能走通这个业务的全部 H1–H3 路径，
    以及每多一把密钥能多控制哪些路径。同一个签名地址出现在多个多签里时只算一次。"""
    principals = {p["id"]: p for p in o4["principals"]}
    paths = [p for p in o4["paths"] if business_id in p["business_ids"]
             and not (p["consequence"] == "H3" and p["h3_auto_expire"] == "yes")]
    usable, leaves = [], set()
    for p in paths:
        try:
            ls = set()
            for a in p["approver_ids"]:
                ls |= leaves_of(a, principals)
        except ValueError:
            continue
        usable.append(p)
        leaves |= ls
    leaves = sorted(leaves)
    if not usable:
        return None
    if len(leaves) > MAX_LEAVES:
        return {"note": "涉及 %d 个签名地址，超过脚本可穷举的 %d 个，未计算" % (len(leaves), MAX_LEAVES)}

    def controlled(chosen):
        return [p["id"] for p in usable if all(satisfied(a, chosen, principals) for a in p["approver_ids"])]

    levels = []
    prev = set()
    for k in range(1, len(leaves) + 1):
        best = None
        for combo in itertools.combinations(leaves, k):
            got = controlled(set(combo))
            # 同样多的路径时，优先选包含上一层密钥的组合，读者可以看出「再加哪一把」
            better = best is None or len(got) > len(best[1]) or (
                len(got) == len(best[1]) and prev <= set(combo) and not prev <= set(best[0]))
            if better:
                best = (combo, got)
        prev = set(best[0])
        if best[1] and (not levels or len(best[1]) > len(levels[-1]["controlled_paths"])):
            levels.append({"keys": len(best[0]), "addresses": [x.split("|", 1)[1] for x in best[0]],
                           "controlled_paths": best[1],
                           "uncontrolled_paths": [p["id"] for p in usable if p["id"] not in best[1]]})
        if len(best[1]) == len(usable):
            break
    member_of = {}
    for pid_, p in principals.items():
        if p["kind"] in ("multisig", "timelock"):
            for m in p["members"]:
                mp = principals[m["principal_id"]]
                if mp["kind"] == "eoa":
                    member_of.setdefault(mp["address"].lower(), []).append(pid_)
    label = {pid_: "%s %d/%d" % (pid_, p["threshold"], sum(m["weight"] for m in p["members"]))
             for pid_, p in principals.items() if p["kind"] in ("multisig", "timelock")}
    for lv in levels:
        lv["member_of"] = {a: [label[x] for x in sorted(member_of.get(a, []))] for a in lv["addresses"]}
    return {"paths_considered": len(usable), "levels": levels,
            "all_paths_keys": levels[-1]["keys"] if levels and not levels[-1]["uncontrolled_paths"] else None}


def perm_score(keys, delay):
    if keys <= 1:
        return 0 if delay < DAY else (40 if delay < 2 * DAY else 50)
    return 80 if delay < DAY else (85 if delay < 2 * DAY else 95)


def effective_delay(p):
    if p["delay_seconds"] <= 0:
        return 0
    if p["delay_public"] != "yes" or p["delay_bypass"] != "no" or p["exit_closable_in_delay"] != "no":
        return 0
    return p["delay_seconds"]


def evaluate_paths(o4):
    principals = {p["id"]: p for p in o4["principals"]}
    out = []
    for p in o4["paths"]:
        r = {"path_id": p["id"], "business_ids": p["business_ids"], "declared": p["consequence"],
             "consequence": p["consequence"], "description": p["description"]}
        if p["consequence"] == "H1" and p["h1_rate_limited"] == "yes":
            r["consequence"] = "H2"
            r["note"] = "受代码强制限速约束，按 H2 计"
        if p["consequence"] == "H3" and p["h3_auto_expire"] == "yes":
            r["excluded"] = True
            r["note"] = "暂停会自动到期且不能续期，不构成 H3"
            out.append(r)
            continue
        try:
            r["keys"] = min_keys(p["approver_ids"], principals)
        except ValueError as e:
            r["incomplete"] = str(e)
            out.append(r)
            continue
        r["effective_delay_s"] = effective_delay(p)
        r["score"] = perm_score(r["keys"], r["effective_delay_s"])
        inits = p.get("initiator_ids") or []
        if inits:
            try:
                r["initiator_keys"] = min(min_keys([i], principals) for i in inits)
                r["initiator_ids"] = list(inits)
            except ValueError as e:
                r["initiator_note"] = "无法计算发起阻断的密钥数：%s" % e
        r["x1_candidate"] = (r["consequence"] == "H1" and r["keys"] <= 1 and r["effective_delay_s"] < DAY
                             and p["h1_covers_all_assets"] == "yes")
        out.append(r)
    return out


# ---------------------------------------------------------------- 公式

def D(x):
    return Decimal(str(x))


def input_groups(chk):
    groups = {}
    for i in chk["inputs"]:
        groups.setdefault(i.get("group", "无"), []).append(i)
    return groups


def input_values(inputs, readings):
    vals = {}
    for i in inputs:
        if i["reading_id"] != "无":
            rd = readings.get(i["reading_id"])
            if not rd or rd["status"] != "read":
                raise LookupError("输入 %s 的读数 %s 没读到" % (i["name"], i["reading_id"]))
            raw = rd["value"]
        else:
            raw = i["constant"]
        raw = str(raw).strip()
        try:
            vals[i["name"]] = D(raw) / D(i["divide_by"])
        except InvalidOperation:
            vals[i["name"]] = raw.lower()
    return vals


def num(v, name):
    if not isinstance(v, Decimal):
        raise ValueError("输入 %s 应为数字，现在是 %r" % (name, v))
    return v


def run_formula(fname, v):
    """返回 (hard: bool, warn: bool, 计算过程 dict)。"""
    g = lambda k: num(v[k], k)  # noqa: E731
    if fname == "lending_buffer":
        lam = g("lambda")
        beta = g("beta") if "beta" in v else 1 + g("bonus")
        single = v["b"] == "none"
        b = None if single else g("b")
        if not single and b == 0:
            raise ValueError("b = 0：该资产不能作抵押，没有可检查的组合，这一行应填 q_not_applicable: yes")
        m = 1 - lam * beta
        d_open = None if single else 1 - b / lam
        buf = m if single else min(d_open, m)
        hard = beta < 1 or m < 0 or lam > 1 or lam <= 0 or (not single and not (0 < b <= lam))
        d1 = D("0.01") if v["same_underlying"] == "yes" else D("0.05")
        return hard, buf < d1, {"D_open": d_open, "M": m, "B_buf": buf, "d1": d1}
    if fname == "rate_curve":
        uk = g("u_kink")
        if "r0" in v:
            r0, rk, r1 = g("r0"), g("r_kink"), g("r1")
        else:   # 标准拐点模型：r(u) = base + slope_low·u（u < 拐点），之后加 slope_high·(u − 拐点)
            r0 = g("base_rate")
            rk = r0 + g("slope_low") * uk
            r1 = rk + g("slope_high") * (1 - uk)
        k_low = (rk - r0) / uk if uk > 0 else None
        k_high = (r1 - rk) / (1 - uk) if uk < 1 else None
        hard = min(r0, rk, r1) < 0 or rk < r0 or r1 < rk
        return hard, k_high == 0, {"r0": r0, "r_kink": rk, "r1": r1, "k_low": k_low, "k_high": k_high}
    if fname == "margin_h":
        h = (g("lambda") / g("b")) * (1 - g("eps_c")) / (1 + g("eps_d"))
        return False, h < 1, {"H_scenario": h}
    if fname == "im_mm":
        im, mm = g("im"), g("mm")
        return im <= mm, False, {"IM_minus_MM": im - mm}
    if fname == "oracle_age":
        t = v["oracle_type"]
        age = g("max_age_s")
        if t == "pull":
            return False, age > 300, {"limit_s": 300}
        if t == "push":
            hb = g("heartbeat_s")
            return False, age > 2 * hb, {"limit_s": 2 * hb}
        raise ValueError("oracle_type 只能是 pull 或 push")
    if fname == "cdp_buffer":
        buf = g("mcr") - 1 - g("p")
        d1 = D("0.01") if v["same_underlying"] == "yes" else D("0.05")
        return buf < 0, buf < d1, {"buffer": buf, "d1": d1}
    if fname == "cdp_tcr":
        tcr = g("collateral_value") / g("debt")
        ccr = None if v["ccr"] == "none" else g("ccr")
        return tcr < 1, (ccr is not None and tcr < ccr), {"TCR": tcr, "CCR": ccr}
    if fname == "lst_rate":
        backing = (g("staked") + g("pending_claim") + g("idle") - g("pending_redeem")) / g("supply")
        dev = (g("r_stored") - backing) / backing
        return dev > g("epoch_tolerance"), abs(dev) > D("0.005"), {"R_backing": backing, "deviation": dev}
    if fname == "concentration":
        c = g("max_stake") / g("total_stake")
        return False, c > D("0.5"), {"concentration": c}
    if fname == "coverage":
        c = g("locked") / g("circulating")
        return c < 1, False, {"coverage": c}
    if fname == "interval_cover":
        dl, dh, al, ah = g("due_low"), g("due_high"), g("avail_low"), g("avail_high")
        if al >= dh:
            return False, False, {"result": "覆盖"}
        if dl > ah:
            return True, False, {"result": "有缺口"}
        return False, True, {"result": "区间重叠，无法确认足额"}
    if fname == "amm_cover":
        avail = g("balance") - g("reserved")
        return avail < g("due"), False, {"available": avail, "surplus": avail - g("due")}
    raise ValueError("未知公式 %s" % fname)


def short(x):
    if isinstance(x, Decimal):
        t = "{:.6f}".format(x).rstrip("0").rstrip(".")
        return t if t not in ("", "-0") else "0"
    return str(x)


def evaluate_check(chk, meta, readings):
    """返回 dict：result in 100/90/60/0/'N/A'/'disclosure'/'reference'/'incomplete'。"""
    r = {"check": chk["id"], "check_id": chk["check_id"], "business_id": chk["business_id"],
         "market_id": chk["market_id"], "reason": chk["reason"]}
    if chk["refers_to"] != "无":
        r["result"] = "reference"
        r["refers_to"] = chk["refers_to"]
        return r
    if chk["q_not_applicable"] == "yes":
        r["result"] = "N/A"
        return r
    if meta.get("disclosure") or chk["q_aggregate_not_stored"] == "yes":
        r["result"] = "disclosure"
        return r
    for rid in chk["reading_ids"]:
        rd = readings.get(rid)
        if rd and rd["status"] != "read":
            r["result"] = "incomplete"
            r["missing"] = "读数 %s 没读到" % rid
            return r
    hard = chk["q_hard"] == "yes"
    warn = chk["q_warn"] == "yes"
    fname = FORMULA_FOR.get(chk["check_id"])
    if fname:
        hard = warn = False
        calc = {}
        groups = input_groups(chk)
        for gname, inputs in groups.items():
            try:
                fh, fw, c = run_formula(fname, input_values(inputs, readings))
            except (LookupError, ValueError, ZeroDivisionError, InvalidOperation) as e:
                r["result"] = "incomplete"
                r["missing"] = "公式无法计算%s：%s" % ("" if gname == "无" else "（组合 %s）" % gname, e)
                return r
            hard, warn = hard or fh, warn or fw
            for k, x in c.items():
                calc[k if len(groups) == 1 else "%s[%s]" % (k, gname)] = x
            if len(groups) > 1:
                calc["结果[%s]" % gname] = "0" if fh else ("60" if fw else "通过")
        r["formula"] = fname
        r["calc"] = {k: (None if x is None else short(x)) for k, x in calc.items()}
    if hard:
        r["result"] = 0
    elif warn:
        r["result"] = 60
    elif chk["q_weakened"] == "yes":
        r["result"] = 90
    else:
        r["result"] = 100
    return r


# ---------------------------------------------------------------- 校验

CODE_LOC = re.compile(r"^[^\s:]+(:[^\s:]+)*:\d+-\d+$")


def address_problem(chain, addr):
    a = str(addr)
    if a != a.lower():
        return "地址要写小写"
    if str(chain).startswith("sui:") and not re.match(r"^0x[0-9a-f]{64}$", a):
        return "Sui 地址或对象 ID 要写完整的 0x 加 64 位十六进制（短地址要补零）"
    if str(chain).startswith("evm:") and not re.match(r"^0x[0-9a-f]{40}$", a):
        return "EVM 地址要写 0x 加 40 位十六进制"
    return None


def scope_businesses(data):
    o1 = data.get("O1-scope.json") or {}
    return {b.get("business_id"): b for b in o1.get("businesses", []) if isinstance(b, dict)}


def specialty_of(data):
    p3 = data.get("P3-business-modules.json") or {}
    return {b.get("id"): b.get("specialty") for b in p3.get("businesses", []) if isinstance(b, dict)}


def budget_of(data):
    return 30 + 15 * len(scope_businesses(data))


def x1_candidates(o4):
    try:
        return [r for r in evaluate_paths(o4) if r.get("x1_candidate")]
    except Exception:  # noqa: BLE001
        return []


def validate_onchain(data, ctx, is_blank):
    o1, o2, o3 = data.get("O1-scope.json"), data.get("O2-targets.json"), data.get("O3-readings.json")
    o4, o7, o8 = data.get("O4-permissions.json"), data.get("O7-fatal.json"), data.get("O8-tvl.json")
    t0, p1, p5 = data.get("T0-task.json"), data.get("P1-baseline.json"), data.get("P5-roles-controls.json")
    biz = scope_businesses(data)
    spec = specialty_of(data)
    snaps = set()

    if o1:
        chains = {c.get("chain_id") for c in (t0 or {}).get("chains", []) if isinstance(c, dict)}
        for i, s in enumerate(o1.get("snapshots", [])):
            if isinstance(s, dict):
                snaps.add(s.get("chain_id"))
                if t0 and s.get("chain_id") not in chains:
                    ctx.err("O1-scope.json", "$.snapshots[%d].chain_id" % i, "不在 T0 的 chains 里")
        checked = set()
        for i, b in enumerate(o1.get("baseline_check", [])):
            if not isinstance(b, dict):
                continue
            checked.add(b.get("deployment_id"))
            if b.get("unchanged") == "no":
                ctx.err("O1-scope.json", "$.baseline_check[%d]" % i, "代码已经变了：先按新代码重做 P1–P5，再做链上评估")
        for x in (p1 or {}).get("deployments", []):
            if isinstance(x, dict) and x.get("id") not in checked:
                ctx.err("O1-scope.json", "$.baseline_check", "部署实例 %s 没有复核" % x.get("id"))
        seen = set()
        sole_chain = next(iter(snaps)) if len(snaps) == 1 else None
        for j, m in enumerate(o1.get("module_objects") or []):
            if isinstance(m, dict):
                pb = address_problem(m.get("chain_id"), m.get("object", ""))
                if pb:
                    ctx.err("O1-scope.json", "$.module_objects[%d].object" % j, pb)
        for i, b in enumerate(o1.get("businesses", [])):
            if not isinstance(b, dict):
                continue
            for j, m in enumerate(b.get("markets") or []):
                if isinstance(m, dict) and sole_chain:
                    pb = address_problem(sole_chain, m.get("object", ""))
                    if pb:
                        ctx.err("O1-scope.json", "$.businesses[%d].markets[%d].object" % (i, j), pb)
            bid = b.get("business_id")
            if bid in seen:
                ctx.err("O1-scope.json", "$.businesses[%d]" % i, "业务 %s 重复" % bid)
            seen.add(bid)
            if spec.get(bid) == "other":
                ctx.err("O1-scope.json", "$.businesses[%d]" % i, "业务 %s 的专项是 other，没有检查表；交人决定用哪个专项或移出范围" % bid)

    if o2:
        uniq = set()
        for i, t in enumerate(o2.get("targets", [])):
            if not isinstance(t, dict):
                continue
            if o1 and t.get("chain_id") not in snaps:
                ctx.err("O2-targets.json", "$.targets[%d].chain_id" % i, "这条链在 O1 没有快照")
            pb = address_problem(t.get("chain_id"), t.get("address", ""))
            if pb:
                ctx.err("O2-targets.json", "$.targets[%d].address" % i, pb)
            uniq.add("%s|%s" % (t.get("chain_id"), str(t.get("address", "")).lower()))
        if o1:
            budget = budget_of(data)
            if len(uniq) > budget:
                ctx.err("O2-targets.json", "$.targets", "去重后有 %d 个目标，超过预算 %d（30 + 15 × %d 个业务）。先删掉 optional 和 disclosure 目标；必需目标仍超预算时，在 gaps.json 登记并交人处理"
                        % (len(uniq), budget, len(biz)))

    targets = {t.get("id"): t for t in (o2 or {}).get("targets", []) if isinstance(t, dict)}
    readings = {}
    if o3:
        got = set()
        for i, r in enumerate(o3.get("readings", [])):
            if not isinstance(r, dict):
                continue
            readings[r.get("id")] = r
            w = "$.readings[%d]" % i
            t = targets.get(r.get("target_id"))
            if t:
                got.add((t["id"], r.get("field")))
                if r.get("chain_id") != t.get("chain_id"):
                    ctx.err("O3-readings.json", w + ".chain_id", "和读取目标的链不一致")
            m, snap = r.get("method"), r.get("at_snapshot")
            chain = str(r.get("chain_id", ""))
            if m in ("code_constant", "targeted_tx"):
                if snap != "not_applicable":
                    ctx.err("O3-readings.json", w + ".at_snapshot", "%s 写 not_applicable" % m)
            elif snap == "not_applicable":
                ctx.err("O3-readings.json", w + ".at_snapshot", "链上读取要写 exact 或 bracketed")
            if m == "code_constant":
                if r.get("source") != "source_code":
                    ctx.err("O3-readings.json", w + ".source", "代码常量的来源写 source_code")
                if not CODE_LOC.match(str(r.get("evidence", ""))):
                    ctx.err("O3-readings.json", w + ".evidence", "代码常量的证据要写源码位置 路径:起-止")
            if m == "type_query" and t and t.get("kind") != "capability":
                ctx.err("O3-readings.json", w + ".method", "按类型查询只允许用于找权限凭证（目标类型要是 capability）")
            if m in ("type_query", "dynamic_field") and not chain.startswith("sui:"):
                ctx.err("O3-readings.json", w + ".method", "%s 只用于 Sui" % m)
            if m == "targeted_tx" and t and t.get("kind") != "multisig":
                ctx.err("O3-readings.json", w + ".method", "定向读交易只允许用于多签成员和门限（目标类型要是 multisig）")
            if m == "derived":
                if snap != "exact":
                    ctx.err("O3-readings.json", w + ".at_snapshot", "derived 读数由快照读数算出，写 exact")
                if not str(r.get("evidence", "")).startswith("file:"):
                    ctx.err("O3-readings.json", w + ".evidence", "derived 读数的证据写读取工具保存的结果文件 file:证据/raw/…")
                if "cmd:" not in str(r.get("method_detail", "")) and "sui_read" not in str(r.get("method_detail", "")):
                    ctx.err("O3-readings.json", w + ".method_detail", "derived 读数要写清是哪条命令算出的")
            if m == "storage_slot" and not chain.startswith("evm:"):
                ctx.err("O3-readings.json", w + ".method", "storage_slot 只用于 EVM；Sui 用 object_field 或 dynamic_field")
            if m == "object_field" and not chain.startswith("sui:"):
                ctx.err("O3-readings.json", w + ".method", "object_field 只用于 Sui；EVM 用 getter 或 storage_slot")
            if r.get("status") == "read" and str(r.get("value", "")).strip() in ("无", ""):
                ctx.err("O3-readings.json", w + ".value", "status 是 read 就要填值")
            if r.get("status") == "unreadable" and str(r.get("value", "")).strip() != "无":
                ctx.err("O3-readings.json", w + ".value", "读不到时 value 写 无，并在 gaps.json 登记")
        for t in targets.values():
            for fd in t.get("fields") or []:
                if isinstance(fd, dict) and (t["id"], fd.get("name")) not in got:
                    ctx.err("O3-readings.json", "$.readings", "目标 %s 的字段 %s 还没有读数" % (t["id"], fd.get("name")))

    if o4:
        principals = {}
        addr_seen = {}
        for i, p in enumerate(o4.get("principals", [])):
            if not isinstance(p, dict):
                continue
            principals[p.get("id")] = p
            w = "$.principals[%d]" % i
            k = p.get("kind")
            if k == "timelock" and not p.get("delay_seconds"):
                ctx.err("O4-permissions.json", w + ".delay_seconds", "时间锁要写当前的最短等待时间")
            if k != "timelock" and p.get("delay_seconds"):
                ctx.err("O4-permissions.json", w + ".delay_seconds", "不是时间锁写 0；等待时间写在路径的 delay_seconds 里")
            if k in ("multisig", "timelock"):
                tw = sum(m.get("weight", 0) for m in p.get("members") or [] if isinstance(m, dict))
                if not p.get("members"):
                    ctx.err("O4-permissions.json", w + ".members", "多签要列出成员，时间锁要列出提议者")
                if not isinstance(p.get("threshold"), int) or not (1 <= p.get("threshold") <= tw):
                    ctx.err("O4-permissions.json", w + ".threshold", "门限要在 1 和成员总权重 %d 之间" % tw)
            elif k in ("eoa", "other"):
                if p.get("members") or p.get("threshold") not in (0,):
                    ctx.err("O4-permissions.json", w, "eoa 和 other 的 threshold 写 0，members 留空 []")
            pb = address_problem(p.get("chain_id"), p.get("address", ""))
            if pb:
                ctx.err("O4-permissions.json", w + ".address", pb)
            if k == "eoa":
                key = "%s|%s" % (p.get("chain_id"), str(p.get("address", "")).lower())
                if key in addr_seen:
                    ctx.err("O4-permissions.json", w + ".address", "同一个地址已登记为 %s，复用那个 ID" % addr_seen[key])
                addr_seen[key] = p.get("id")
        held_roles = set()
        for i, h in enumerate(o4.get("role_holders", [])):
            if not isinstance(h, dict):
                continue
            w = "$.role_holders[%d]" % i
            held_roles.add(h.get("role_id"))
            if h.get("holder_status") == "held" and not h.get("holder_principal_ids"):
                ctx.err("O4-permissions.json", w + ".holder_principal_ids", "有持有人时要写持有人的控制者 ID")
            if h.get("holder_status") != "held" and h.get("holder_principal_ids"):
                ctx.err("O4-permissions.json", w + ".holder_principal_ids", "不是 held 时留空 []")
        p4_ = data.get("P4-responsibilities.json") or {}
        rb = {r.get("id"): set(r.get("business_ids") or []) for r in p4_.get("responsibilities", []) if isinstance(r, dict)}
        for k in (p5 or {}).get("controls", []):
            if not isinstance(k, dict) or k.get("reachability") == "disabled_in_code":
                continue
            bs = set()
            for rid in k.get("affected_responsibility_ids") or []:
                bs |= rb.get(rid, set())
            if not bs & set(biz):
                continue
            for rid in k.get("role_ids") or []:
                if rid not in held_roles:
                    ctx.err("O4-permissions.json", "$.role_holders", "P5 角色 %s（控制 %s 需要它）没有登记链上持有人" % (rid, k.get("id")))
                    held_roles.add(rid)
        covered = set()
        used_controls = set()
        for i, p in enumerate(o4.get("paths", [])):
            if not isinstance(p, dict):
                continue
            w = "$.paths[%d]" % i
            c = p.get("consequence")
            used_controls.update(p.get("control_ids") or [])
            for b in p.get("business_ids") or []:
                covered.add((b, c))
                if o1 and b not in biz:
                    ctx.err("O4-permissions.json", w + ".business_ids", "业务 %s 不在 O1 的范围里" % b)
            want = {"h1_rate_limited": c == "H1", "h1_covers_all_assets": c == "H1", "h3_auto_expire": c == "H3"}
            for f, applies in want.items():
                v = p.get(f)
                if applies and v == "na":
                    ctx.err("O4-permissions.json", w + "." + f, "%s 路径要回答 yes 或 no" % c)
                if not applies and v in ("yes", "no"):
                    ctx.err("O4-permissions.json", w + "." + f, "这一项只对 %s 路径适用，这里写 na" % ("H1" if f.startswith("h1") else "H3"))
            d = p.get("delay_seconds")
            for f in ("delay_public", "delay_bypass", "exit_closable_in_delay"):
                v = p.get(f)
                if d == 0 and v in ("yes", "no"):
                    ctx.err("O4-permissions.json", w + "." + f, "没有等待时写 na")
                if isinstance(d, int) and d > 0 and v == "na":
                    ctx.err("O4-permissions.json", w + "." + f, "有等待时要回答 yes 或 no")
            if c != "H3" and p.get("initiator_ids"):
                ctx.err("O4-permissions.json", w + ".initiator_ids", "只有 H3 路径登记发起阻断的控制者，其他写 []")
            if c == "H3" and set(p.get("initiator_ids") or []) == set(p.get("approver_ids") or []) and p.get("initiator_ids"):
                ctx.err("O4-permissions.json", w + ".initiator_ids", "发起者和 approver_ids 相同时留空 []")
            for a in p.get("approver_ids") or []:
                if principals.get(a, {}).get("kind") == "other":
                    ctx.err("O4-permissions.json", w + ".approver_ids", "控制者 %s 类型是 other，无法计算密钥数：在 gaps.json 登记并交人处理" % a)
        for i, a in enumerate(o4.get("absent", [])):
            if isinstance(a, dict):
                if (a.get("business_id"), a.get("consequence")) in covered:
                    ctx.err("O4-permissions.json", "$.absent[%d]" % i, "已经有这类后果的路径，不能再登记为不存在")
                covered.add((a.get("business_id"), a.get("consequence")))
        for b in biz:
            for c in ("H1", "H2", "H3"):
                if (b, c) not in covered:
                    ctx.err("O4-permissions.json", "$", "业务 %s 的 %s 既没有路径，也没有登记为不存在" % (b, c))
        p4 = data.get("P4-responsibilities.json") or {}
        resp_biz = {r.get("id"): set(r.get("business_ids") or []) for r in p4.get("responsibilities", []) if isinstance(r, dict)}
        for k in (p5 or {}).get("controls", []):
            if not isinstance(k, dict) or k.get("consequence") not in ("H1", "H2", "H3"):
                continue
            if k.get("reachability") == "disabled_in_code":
                continue
            bs = set()
            for rid in k.get("affected_responsibility_ids") or []:
                bs |= resp_biz.get(rid, set())
            if bs & set(biz) and k.get("id") not in used_controls:
                ctx.err("O4-permissions.json", "$.paths", "P5 控制 %s（%s）没有出现在任何路径里" % (k.get("id"), k.get("consequence")))
        try:
            for r in evaluate_paths(o4):
                if r.get("incomplete") and "other" not in r["incomplete"]:
                    ctx.err("O4-permissions.json", "$.paths", "路径 %s：%s" % (r["path_id"], r["incomplete"]))
        except Exception:  # noqa: BLE001
            pass

    ck_ids = set()
    for name in ("O5-config.json", "O6-funds.json"):
        o = data.get(name)
        if o:
            ck_ids |= {c.get("id") for c in o.get("checks", []) if isinstance(c, dict)}
    for name, dim in (("O5-config.json", "configuration"), ("O6-funds.json", "funds_dependencies")):
        o = data.get(name)
        if not o:
            continue
        have = set()
        for i, c in enumerate(o.get("checks", [])):
            if not isinstance(c, dict):
                continue
            w = "$.checks[%d]" % i
            b = c.get("business_id")
            if o1 and b not in biz:
                ctx.err(name, w + ".business_id", "业务 %s 不在 O1 的范围里" % b)
                continue
            mks = {m.get("id") for m in (biz.get(b) or {}).get("markets", []) if isinstance(m, dict)}
            mk = c.get("market_id")
            if mk != "ALL" and mk not in mks:
                ctx.err(name, w + ".market_id", "只能写 ALL 或业务 %s 的市场 %s" % (b, sorted(mks)))
            cid = c.get("check_id")
            meta = allowed_check(spec.get(b), cid)
            if not meta:
                ctx.err(name, w + ".check_id", "%s 不是业务 %s（专项 %s）适用的检查编号：要么不在检查表里，要么专项的「各业务适用的检查项」表没有为这种业务列出它（不适用的编号不用登记）" % (cid, b, spec.get(b)))
                continue
            if meta["dim"] != dim:
                ctx.err(name, w + ".check_id", "%s 属于%s，应该填在 %s" % (cid, DIM_NAME[meta["dim"]],
                        "O5-config.json" if meta["dim"] == "configuration" else "O6-funds.json"))
            if (b, mk, cid) in have:
                ctx.err(name, w, "业务 %s 的 %s 在 %s 上重复登记" % (b, cid, mk))
            have.add((b, mk, cid))
            fname = FORMULA_FOR.get(cid)
            for q in ("q_hard", "q_warn"):
                if fname and c.get(q) != "by_formula" and c.get("q_not_applicable") == "no":
                    ctx.err(name, w + "." + q, "%s 有公式，填 by_formula，由脚本判定" % cid)
                if not fname and c.get(q) == "by_formula":
                    ctx.err(name, w + "." + q, "%s 没有公式，回答 yes 或 no" % cid)
            if fname and c.get("q_not_applicable") == "no" and c.get("q_aggregate_not_stored") == "no" and c.get("refers_to") == "无":
                groups = {}
                for x in c.get("inputs") or []:
                    if isinstance(x, dict):
                        groups.setdefault(x.get("group", "无"), []).append(x.get("name"))
                if not groups:
                    groups = {"无": []}
                for gname, names in groups.items():
                    if len(names) != len(set(names)):
                        ctx.err(name, w + ".inputs", "%s 的组合 %s 里有重复的输入名" % (cid, gname))
                    ok, miss = input_set_ok(fname, names)
                    if not ok:
                        ctx.err(name, w + ".inputs", "%s%s 的公式缺少输入：%s" % (cid, "" if gname == "无" else " 组合 " + gname, ", ".join(miss)))
            for j, x in enumerate(c.get("inputs") or []):
                if not isinstance(x, dict):
                    continue
                rid, cst = x.get("reading_id"), x.get("constant")
                if (rid == "无") == (cst == "无"):
                    ctx.err(name, "%s.inputs[%d]" % (w, j), "reading_id 和 constant 必须正好一个写 无")
                if rid not in ("无", None) and rid not in readings and o3:
                    ctx.err(name, "%s.inputs[%d].reading_id" % (w, j), "读数 %s 不存在" % rid)
                if rid not in ("无", None) and rid not in (c.get("reading_ids") or []):
                    ctx.err(name, w + ".reading_ids", "公式用到的读数 %s 也要写进 reading_ids" % rid)
            ref = c.get("refers_to")
            if ref not in ("无", None) and ref not in ck_ids:
                ctx.err(name, w + ".refers_to", "检查 %s 不存在" % ref)
        for b, info in biz.items():
            mks = [m.get("id") for m in info.get("markets", []) if isinstance(m, dict)]
            for cid, meta in required_checks(spec.get(b)).items():
                if meta["dim"] != dim:
                    continue
                if (b, "ALL", cid) in have:
                    mixed = [m for m in mks if (b, m, cid) in have]
                    if mixed:
                        ctx.err(name, "$.checks", "业务 %s 的 %s 同时登记了 ALL 和市场 %s，只能二选一" % (b, cid, ", ".join(mixed)))
                    continue
                if not mks:
                    ctx.err(name, "$.checks", "业务 %s 缺少检查项 %s（market_id 写 ALL）" % (b, cid))
                    continue
                miss = [m for m in mks if (b, m, cid) not in have]
                if miss:
                    ctx.err(name, "$.checks", "业务 %s 的检查项 %s 没有覆盖市场 %s（共用就写一条 ALL）" % (b, cid, ", ".join(miss)))

    if o7 is not None and o4:
        listed = {(x.get("kind"), x.get("path_id")) for x in o7.get("fatal", []) if isinstance(x, dict)}
        for r in x1_candidates(o4):
            if ("X1", r["path_id"]) not in listed:
                ctx.err("O7-fatal.json", "$.fatal", "脚本发现 X1 候选（路径 %s：单密钥、延时不足 24 小时、能处分全部资产），必须登记" % r["path_id"])
        for i, x in enumerate(o7.get("fatal", [])):
            if not isinstance(x, dict):
                continue
            w = "$.fatal[%d]" % i
            rev = str(x.get("human_reviewer", "")).strip()
            if x.get("human_decision") in ("confirmed", "rejected") and rev in ("无", ""):
                ctx.err("O7-fatal.json", w + ".human_reviewer", "人确认后要写确认人")
            if x.get("kind") == "X1" and x.get("path_id") in ("无", None):
                ctx.err("O7-fatal.json", w + ".path_id", "X1 要写对应的 O4 路径 ID")

    if o8:
        bs = {x.get("business_id") for x in o8.get("businesses", []) if isinstance(x, dict)}
        for b in biz:
            if b not in bs:
                ctx.err("O8-tvl.json", "$.businesses", "业务 %s 没有 TVL" % b)
        ms = {x.get("market_id") for x in o8.get("markets", []) if isinstance(x, dict)}
        for b, info in biz.items():
            for m in info.get("markets", []):
                if isinstance(m, dict) and m.get("id") not in ms:
                    ctx.err("O8-tvl.json", "$.markets", "市场 %s 没有 TVL" % m.get("id"))
        if (o8.get("tvl_available") == "yes") == (o8.get("tvl_source") == "none"):
            ctx.err("O8-tvl.json", "$.tvl_source", "拿得到 TVL 时选一个口径；tvl_available 是 no 时写 none")
        has_markets = any(info.get("markets") for info in biz.values())
        if has_markets and o8.get("market_tvl_source") == "none" and o8.get("tvl_available") == "yes":
            ctx.err("O8-tvl.json", "$.market_tvl_source", "有市场时要选市场 TVL 的口径")
        if not has_markets and o8.get("market_tvl_source") != "none":
            ctx.err("O8-tvl.json", "$.market_tvl_source", "没有市场时写 none")
        if "onchain_balances" in (o8.get("tvl_source"), o8.get("market_tvl_source")) and str(o8.get("price_source", "")).strip() in ("无", ""):
            ctx.err("O8-tvl.json", "$.price_source", "onchain_balances 口径要写价格来源")
        for key, src in (("businesses", o8.get("tvl_source")), ("markets", o8.get("market_tvl_source"))):
            for i, x in enumerate(o8.get(key, [])):
                if not isinstance(x, dict):
                    continue
                w = "$.%s[%d]" % (key, i)
                if src == "onchain_balances" and not x.get("reading_ids") and x.get("tvl_usd"):
                    ctx.err("O8-tvl.json", w + ".reading_ids", "onchain_balances 口径要列出用到的余额读数")
                if src in ("defillama", "official_dapp") and not x.get("evidence"):
                    ctx.err("O8-tvl.json", w + ".evidence", "%s 口径要给出页面链接" % src)


# ---------------------------------------------------------------- 汇总

def is_score(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def weighted(items):
    """items: [(score, weight)]；权重全为 0 时等权。"""
    if not items:
        return None
    tw = sum(w for _, w in items)
    if tw <= 0:
        return sum(s for s, _ in items) / len(items)
    return sum(s * w for s, w in items) / tw


def score_onchain(data):
    biz = scope_businesses(data)
    spec = specialty_of(data)
    readings = {r["id"]: r for r in data["O3-readings.json"]["readings"]}
    o4, o8 = data["O4-permissions.json"], data["O8-tvl.json"]
    fatal = data["O7-fatal.json"]["fatal"]
    market_tvl = {m["market_id"]: m["tvl_usd"] for m in o8.get("markets", [])}
    paths = evaluate_paths(o4)
    absent = {(a["business_id"], a["consequence"]): a for a in o4.get("absent", [])}
    gaps = [g for g in data.get("gaps.json", {}).get("gaps", [])
            if g.get("step", "").startswith("O") and g.get("blocks_denominator") is True]

    checks = []
    for name in ("O5-config.json", "O6-funds.json"):
        for c in data[name]["checks"]:
            meta = allowed_check(spec.get(c["business_id"]), c["check_id"]) or {"dim": "configuration"}
            r = evaluate_check(c, meta, readings)
            r["dimension"] = meta["dim"]
            checks.append(r)

    results = []
    for bid, info in biz.items():
        br = {"business_id": bid, "specialty": spec.get(bid), "dimensions": {}, "incomplete": [], "zero_markets": [],
              "notes": []}
        off = [m["id"] for m in info.get("markets", []) if m.get("discovered_by") == "official_list"]
        if off:
            br["notes"].append("市场 %s 的清单取自官方列表（链上无法枚举），可能不完整" % "、".join(off))
        # 权限
        cons = {}
        for c in ("H1", "H2", "H3"):
            ps = [p for p in paths if bid in p["business_ids"] and p["consequence"] == c]
            excluded_only = [p for p in paths if bid in p["business_ids"] and p["declared"] == c]
            inc = [p for p in ps if p.get("incomplete")]
            sc = [p["score"] for p in ps if is_score(p.get("score"))]
            if inc:
                cons[c] = "incomplete"
                br["incomplete"] += ["%s 路径 %s：%s" % (c, p["path_id"], p["incomplete"]) for p in inc]
            elif sc:
                cons[c] = min(sc)
            elif excluded_only or (absent.get((bid, c)) or {}).get("verified") == "yes":
                cons[c] = 100
            else:
                cons[c] = "incomplete"
                br["incomplete"].append("%s 没有完成追踪" % c)
        perm = "incomplete" if "incomplete" in cons.values() else min(cons.values())
        mine_paths = [p for p in paths if bid in p["business_ids"]]
        tb = [p for p in mine_paths if "initiator_keys" in p and not p.get("excluded")]
        temp_block = None
        if tb:
            k = min(p["initiator_keys"] for p in tb)
            temp_block = {"min_keys": k, "paths": [p["path_id"] for p in tb if p["initiator_keys"] == k]}
        br["dimensions"]["permissions"] = {"score": perm, "by_consequence": cons, "paths": mine_paths,
                                           "key_concentration": key_concentration(o4, bid),
                                           "temporary_block": temp_block}
        # 配置、资金
        mks = [m["id"] for m in info.get("markets", [])] or ["ALL"]
        for dim in ("configuration", "funds_dependencies"):
            mine = [c for c in checks if c["business_id"] == bid and c["dimension"] == dim]
            per_market = []
            dim_inc = False
            for mk in mks:
                rel = [c for c in mine if c["market_id"] in ("ALL", mk)]
                inc = [c for c in rel if c["result"] == "incomplete"]
                sc = [c["result"] for c in rel if is_score(c["result"])]
                if inc:
                    dim_inc = True
                    br["incomplete"] += ["%s %s@%s：%s" % (DIM_NAME[dim], c["check_id"], mk, c.get("missing", "")) for c in inc]
                    per_market.append({"market_id": mk, "score": "incomplete"})
                elif sc:
                    m = min(sc)
                    per_market.append({"market_id": mk, "score": m, "tvl_usd": market_tvl.get(mk, 0)})
                    if m == 0 and mk != "ALL":
                        br["zero_markets"].append({"market_id": mk, "dimension": dim})
                else:
                    only_ref = rel and all(c["result"] == "reference" for c in rel if c["result"] not in ("N/A", "disclosure"))
                    per_market.append({"market_id": mk, "score": "reference" if only_ref and any(c["result"] == "reference" for c in rel) else "N/A"})
            scored = [m for m in per_market if is_score(m["score"])]
            if dim_inc:
                s = "incomplete"
            elif scored:
                s = weighted([(m["score"], m.get("tvl_usd", 0)) for m in scored])
            elif any(m["score"] == "reference" for m in per_market):
                s = "reference"
            else:
                s = "N/A"
            br["dimensions"][dim] = {"score": s, "markets": per_market,
                                     "checks": mine,
                                     "disclosures": [c for c in mine if c["result"] == "disclosure"]}
        # 业务分
        dims = {k: v["score"] for k, v in br["dimensions"].items()}
        if spec.get(bid) not in SPECIALTY_FILE:
            br["incomplete"].append("专项 %s 没有检查表" % spec.get(bid))
        fx = [x for x in fatal if bid in x["business_ids"]]
        br["fatal"] = [{"id": x["id"], "kind": x["kind"], "decision": x["human_decision"], "fact": x["fact"]} for x in fx]
        if br["incomplete"] or "incomplete" in dims.values():
            br["status"] = "评估未完成"
            br["score"] = None
        else:
            items = [(dims[k], WEIGHTS[k]) for k in WEIGHTS if is_score(dims[k])]
            raw = weighted(items) if items else None
            br["raw_score"] = raw
            if any(x["human_decision"] == "confirmed" for x in fx):
                br["score"] = 0.0
                br["status"] = "已评分（致命项）"
            elif any(x["human_decision"] == "pending" for x in fx):
                br["score"] = None
                br["status"] = "待人工确认"
            elif raw is None:
                br["score"] = None
                br["status"] = "评估未完成"
                br["incomplete"].append("三个大项都没有可计分的结果")
            else:
                br["score"] = raw
                br["status"] = "已评分"
        results.append(br)

    # 业务权重
    tvl = {x["business_id"]: x["tvl_usd"] for x in o8["businesses"]}
    total = sum(tvl.get(b, 0) for b in biz)
    if o8["tvl_available"] != "yes" or total <= 0:
        raw_w = {b: 1.0 for b in biz}
        weight_note = "拿不到 TVL，所有业务等权"
    else:
        raw_w = {b: max(tvl.get(b, 0) / total, MIN_BUSINESS_WEIGHT) for b in biz}
        weight_note = "max(TVL 占比, 5%) 后归一"
    sw = sum(raw_w.values())
    for br in results:
        br["tvl_usd"] = tvl.get(br["business_id"])
        br["weight"] = raw_w[br["business_id"]] / sw
        mk_ids = [m["id"] for m in biz[br["business_id"]].get("markets", [])]
        if mk_ids and o8["tvl_available"] == "yes" and br["tvl_usd"]:
            sel = sum(market_tvl.get(m, 0) for m in mk_ids)
            br["market_coverage"] = {"selected_tvl_usd": sel, "business_tvl_usd": br["tvl_usd"],
                                     "ratio": sel / br["tvl_usd"],
                                     "same_source": o8.get("market_tvl_source") == o8.get("tvl_source")}
            br["notes"].append("选定的 %d 个市场 TVL 合计 %.2f 美元，占业务 TVL 的 %.1f%%%s；配置和资金两个大项只代表这部分资金" % (
                len(mk_ids), sel, sel / br["tvl_usd"] * 100,
                "" if br["market_coverage"]["same_source"] else "（市场和业务的 TVL 口径不同，比例仅供参考）"))

    statuses = {br["status"] for br in results}
    if "评估未完成" in statuses or gaps:
        status, project = "评估未完成", None
    elif "待人工确认" in statuses:
        status, project = "待人工确认", None
    else:
        status = "已评分"
        project = sum(br["score"] * br["weight"] for br in results)
    dim_view = {}
    for k in WEIGHTS:
        items = [(br["dimensions"][k]["score"], br["weight"]) for br in results if is_score(br["dimensions"][k]["score"])]
        dim_view[k] = weighted(items)
    return {
        "rule_version": RULE_VERSION,
        "status": status,
        "project_score": project,
        "dimension_view": dim_view,
        "weight_note": weight_note,
        "blocking_gaps": [{"id": g["id"], "missing": g["missing"]} for g in gaps],
        "businesses": results,
    }


# ---------------------------------------------------------------- 链上角色关系图

def role_graph(data):
    """前期准备的模块—角色—控制关系，加上链上实体：模块对象、角色持有人、多签和时间锁的成员。

    同一个链上实体只有一个节点：两个角色由同一个多签持有时，多签节点同时连到两个角色；
    两个多签有共同签名地址时，这个地址同时连到两个多签。
    """
    p3, p5 = data["P3-business-modules.json"], data["P5-roles-controls.json"]
    o1, o4 = data.get("O1-scope.json"), data.get("O4-permissions.json")
    nodes, edges = [], []

    def add(nid, kind, label, **extra):
        nodes.append(dict({"id": nid, "kind": kind, "label": label}, **extra))

    for b in p3["businesses"]:
        add(b["id"], "business", b["name"])
    for m in p3["modules"]:
        add(m["id"], "module", m["name"], external=m["is_external"])
        for b in m["business_ids"]:
            edges.append({"from": b, "to": m["id"], "kind": "uses"})
        for c in m["calls_module_ids"]:
            edges.append({"from": m["id"], "to": c, "kind": "calls"})
    for r in p5["roles"]:
        add(r["id"], "role", r["credential"])
        for g in r["granted_by_role_ids"]:
            edges.append({"from": g, "to": r["id"], "kind": "grants"})
    resp_mod = {r["id"]: r["module_ids"] for r in data["P4-responsibilities.json"]["responsibilities"]}
    for k in p5["controls"]:
        add(k["id"], "control", k["entry"], consequence=k["consequence"])
        for r in k["role_ids"]:
            edges.append({"from": r, "to": k["id"], "kind": "can_call"})
        mods = set()
        for rid in k["affected_responsibility_ids"]:
            mods |= set(resp_mod.get(rid, []))
        for m in sorted(mods):
            edges.append({"from": k["id"], "to": m, "kind": "affects"})
    if o1:
        for i, mo in enumerate(o1.get("module_objects", [])):
            oid = "OBJ:%s:%s" % (mo["chain_id"], mo["object"])
            if not any(n["id"] == oid for n in nodes):
                add(oid, "object", mo["object"], objectKind=mo["object_kind"], chainId=mo["chain_id"])
            edges.append({"from": mo["module_id"], "to": oid, "kind": "deployed_as"})
    if o4:
        for p in o4["principals"]:
            add(p["id"], p["kind"], p["address"], chainId=p["chain_id"], threshold=p["threshold"],
                delaySeconds=p.get("delay_seconds", 0))
            for m in p["members"]:
                edges.append({"from": p["id"], "to": m["principal_id"],
                              "kind": "proposer" if p["kind"] == "timelock" else "signer", "weight": m["weight"]})
        for h in o4["role_holders"]:
            if h["holder_status"] == "held":
                for pid in h["holder_principal_ids"]:
                    edges.append({"from": h["role_id"], "to": pid, "kind": "held_by", "credential": h["credential"]})
            else:
                nid = "NOHOLDER:%s" % h["role_id"]
                add(nid, "no_holder", {"burned": "凭证已销毁", "unassigned": "查不到持有人"}[h["holder_status"]])
                edges.append({"from": h["role_id"], "to": nid, "kind": "held_by", "credential": h["credential"]})
    return {"nodes": nodes, "edges": edges}


def _check_formula_doc():
    for k, alts in FORMULA_INPUTS.items():
        assert set(FORMULA_DOC[k][3]) == {n for alt in alts for n in alt}, k


_check_formula_doc()
