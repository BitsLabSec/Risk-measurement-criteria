# 把 NAVI 的链上读数整理成工作流的 T0–P5、O1–O8 文件。
# 只做「整理」：每个答案的依据写在 reason / note 里；需要人判断的地方单独标出。
import json, os, sys, glob, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "工作流", "scripts"))
from bitsscore import src_root  # noqa: E402
SRC = src_root({"repo_url": "https://github.com/naviprotocol/navi-smart-contracts", "commit": "db60087a454c84279c285bbd29c8e0e2543e1c07", "local_path": "cache"})  # 先运行 fetch-sources
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
C = "sui:mainnet"
L = "0xd899cf7d2b5db716bd2cf55599fb0d5ee38a3061e7b6bb6eebf73fa5bc4c81ca"
LV = "0x512f28261c1a293f49416d8885b8d5d32bde6dd68a99a0be36fe42b248e6833a"
OR = "0xca441b44943c16be0e6e23c5a955bb971537ea3289ae8016fbf33fffe1fd210f"
ORV = "0x4837ae94425107554c8847721cf9954c1ad8e10520433b9e37dc11c507148bea"
STORAGE = "0xbb4e2f4b6205c2e2a2db47aeb4f830796ec7c005f88537ee775986639bc442fe"
RESERVES = "0xe6d4c6610b86ce7735ea754596d71d72d10c7980b5052fc3c8cdf8d09fea9b4b"
EMODES = "0x6ca4ad7689f6fd3f3860c8144190085ef26d425e912afaeab2dadac6bfb8bd16"
PRICEORACLE = "0x1568865ed9a0b5ec414220e8f79b3d04c77acc82358f6e5ae4635687392ffbef"
PRICES = "0xc0601facd3b98d1e82905e660bf9f5998097dedcf86ed802cf485865e3e3667c"
UPCAP_L = "0xdba1b40f3537441b51d2848fc0a149610e48e67c1cc48c6ad641767622000623"
UPCAP_O = "0x436d774dedebb6300c35ef99307a315e4c313fe79cdec326678a5c5ef574f0e0"
MS35 = "0x25549f15b144032b4a61921552f6ecbfea13556615f7b45576b12f10d67955e7"
MSA = "0x39c70d4ce3ce769a46f46ad80184a88bc25be9b49545751f5425796ef0c3d9ba"
MSB = "0x408aab3117dc95445f7564028d2b6d2b65f6d005936f2f9a44c1f27f57a8cac6"
GQ = "cmd:curl https://graphql.mainnet.sui.io/graphql（查询与响应见 证据/raw/%s.json）"
snap = json.load(open(os.path.join(HERE, "snapshot.txt")))
CP = snap["sequenceNumber"]
COMMIT = "db60087a454c84279c285bbd29c8e0e2543e1c07"
REPO = "https://github.com/naviprotocol/navi-smart-contracts"


def raw(name):
    return json.load(open(os.path.join(RAW, name + ".json")))["response"]["data"]


def w(name, data):
    json.dump(data, open(os.path.join(OUT, name), "w"), ensure_ascii=False, indent=2)


def ev(name):
    return GQ % name


def code(path, a, b):
    return "%s:%d-%d" % (path, a, b)


def nlines(rel):
    return len(open(os.path.join(SRC, rel), encoding="utf-8").read().split("\n"))


# ---------------------------------------------------------------- T0
w("T0-task.json", {
    "assessment_id": os.path.basename(OUT), "previous_assessment_id": "无", "reason": "first",
    "project": "NAVI Protocol", "dimensions": ["onchain"],
    "chains": [{"chain_id": C, "name": "Sui Mainnet"}],
    "scope_statement": "工作流试跑：NAVI Lending 主市场（lending_core + oracle）的链上安全",
    "known_entries": [L, OR], "known_repos": [REPO],
    "out_of_scope": ["激励（incentive_v2/v3）奖励业务：本次试跑只评借贷", "NAVI 的 9 个非主市场 Storage（market_id 1–12）", "Volo 流动性质押", "前端与聚合器"],
    "assessor": "claude（试跑）", "date": "2026-11-26"})

# ---------------------------------------------------------------- P1
snap_rec = {"chain_id": C, "block_or_checkpoint": str(CP), "block_hash_or_digest": snap["digest"],
            "time_utc": snap["timestamp"], "evidence": ev("snapshot")}
w("P1-baseline.json", {"baseline_id": "B01", "snapshots": [snap_rec], "deployments": [
    {"id": "I01", "chain_id": C, "entry": L, "proxy_kind": "sui_package", "actual_code": LV, "version": "26",
     "how_found": "读 lending_core 的 UpgradeCap：package 字段指向 0x512f…，version=26；packageVersions 的最新版本也是 26",
     "evidence": [ev("upgradecap-lending"), ev("pkgversions-lending")], "status": "confirmed"},
    {"id": "I02", "chain_id": C, "entry": OR, "proxy_kind": "sui_package", "actual_code": ORV, "version": "5",
     "how_found": "读 oracle 的 UpgradeCap：package 字段指向 0x4837…，version=5；packageVersions 的最新版本也是 5",
     "evidence": [ev("upgradecap-oracle"), ev("pkgversions-oracle")], "status": "confirmed"}]})

# ---------------------------------------------------------------- P2
w("P2-sources.json", {"sources": [
    {"id": "S01", "deployment_ids": ["I01", "I02"], "language": "move", "repo_url": REPO, "commit": COMMIT,
     "local_path": "cache", "in_scope_globs": ["lending_core/sources/*.move", "oracle/sources/*.move"],
     "excluded_globs": ["**/tests/**"], "verify_method": "not_verified", "verify_result": "not_verified",
     "verify_evidence": [REPO + "/blob/" + COMMIT + "/lending_core/Published.toml"]}]})

# ---------------------------------------------------------------- P3
lmods = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(SRC, "lending_core/sources/*.move")))
omods = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(SRC, "oracle/sources/*.move")))
mods, mid = [], {}
for i, m in enumerate(["lending_core::" + x for x in lmods] + ["oracle::" + x for x in omods]):
    pkg, name = m.split("::")
    k = "M%02d" % (i + 1)
    mid[m] = k
    mods.append({"id": k, "name": m, "source_id": "S01", "file": "%s/sources/%s.move" % (pkg, name), "is_external": False,
                 "business_ids": ["BZ01"], "purpose": "借贷主流程" if pkg == "lending_core" else "价格预言机",
                 "calls_module_ids": []})
for m in mods:
    if m["name"] == "lending_core::lending":
        m["calls_module_ids"] = [mid[x] for x in ("lending_core::logic", "lending_core::pool", "lending_core::storage", "oracle::oracle")]
w("P3-business-modules.json", {"businesses": [{
    "id": "BZ01", "name": "借贷（主市场）", "specialty": "lending",
    "user_entries": ["incentive_v3::entry_deposit", "incentive_v3::entry_withdraw_v2", "incentive_v3::entry_borrow_v2",
                     "incentive_v3::entry_repay", "incentive_v3::entry_liquidation"],
    "assets_or_state": ["主市场 35 个资产池的余额", "用户存款和债务"]}], "modules": mods})

# ---------------------------------------------------------------- P4（粗粒度：本次只评链上，不评代码覆盖）
def whole(names, pkg):
    return [{"source_id": "S01", "file": "%s/sources/%s.move" % (pkg, n), "start": 1, "end": nlines("%s/sources/%s.move" % (pkg, n))} for n in names]
core = ["lending", "logic", "pool", "storage", "calculator", "validation", "flash_loan", "pool_manager", "dynamic_calculator", "account", "ray_math", "safe_math", "utils", "version", "error", "constants", "event"]
inc = ["incentive", "incentive_v2", "incentive_v3", "manage"]
w("P4-responsibilities.json", {"responsibilities": [
    {"id": "D01", "result": "存款、提款、借款、还款、清算的记账与资金划转", "business_ids": ["BZ01"],
     "module_ids": [mid["lending_core::" + n] for n in core], "ranges": whole(core, "lending_core"),
     "q1_assets_or_authority": "yes", "q1_evidence": "base_withdraw/base_borrow 从池中划出资金并改写余额", "q1_locations": [code("lending_core/sources/lending.move", 241, 300)],
     "q2_preconditions_or_availability": "yes", "q2_evidence": "全部入口先检查 Storage.paused", "q2_locations": [code("lending_core/sources/lending.move", 186, 186)],
     "impact_object": "资产池余额、用户存款和债务", "failure_consequence": "资金被错误划转或必要操作被阻断"},
    {"id": "D02", "result": "价格的写入、校验与读取", "business_ids": ["BZ01"],
     "module_ids": [mid["oracle::" + n] for n in omods], "ranges": whole(omods, "oracle"),
     "q1_assets_or_authority": "yes", "q1_evidence": "价格决定借款额度和清算", "q1_locations": [code("oracle/sources/oracle.move", 137, 151)],
     "q2_preconditions_or_availability": "yes", "q2_evidence": "价格过期时估值断言失败", "q2_locations": [code("lending_core/sources/calculator.move", 97, 101)],
     "impact_object": "各资产价格", "failure_consequence": "错误估值导致多借或错误清算"},
    {"id": "D03", "result": "激励与管理入口", "business_ids": ["BZ01"],
     "module_ids": [mid["lending_core::" + n] for n in inc], "ranges": whole(inc, "lending_core"),
     "q1_assets_or_authority": "yes", "q1_evidence": "manage 中有改写清算对象的管理入口", "q1_locations": [code("lending_core/sources/manage.move", 201, 208)],
     "q2_preconditions_or_availability": "no", "q2_evidence": "无", "q2_locations": [],
     "impact_object": "激励余额、清算保护名单", "failure_consequence": "部分用户被排除在清算之外"}]})

# ---------------------------------------------------------------- P5
roles = [
    ("R01", "storage::OwnerCap", code("lending_core/sources/storage.move", 323, 330), "初始化给发布者；StorageAdminCap 可再铸造", ["R02"]),
    ("R02", "storage::StorageAdminCap", code("lending_core/sources/storage.move", 822, 826), "初始化给发布者，可转移", []),
    ("R03", "pool::PoolAdminCap", code("lending_core/sources/pool.move", 258, 265), "初始化给发布者，可转移", []),
    ("R04", "oracle::OracleAdminCap", code("oracle/sources/oracle.move", 61, 63), "初始化给发布者，可转移", []),
    ("R05", "oracle::OracleFeederCap", code("oracle/sources/oracle.move", 137, 151), "由 OracleAdminCap 调用 create_feeder 铸造", ["R04"]),
    ("R06", "0x2::package::UpgradeCap（lending_core）", "lending_core/Published.toml:1-6", "发布时生成", []),
    ("R07", "0x2::package::UpgradeCap（oracle）", "oracle/Published.toml:1-6", "发布时生成", []),
]
w("P5-roles-controls.json", {
    "roles": [{"id": r, "credential": c, "check_locations": [loc], "how_obtained": h, "granted_by_role_ids": g} for r, c, loc, h, g in roles],
    "controls": [
        {"id": "K01", "role_ids": ["R01"], "entry": "storage::set_pause", "conditions": "无", "what_changes": "Storage.paused",
         "effect_locations": [code("lending_core/sources/storage.move", 323, 330), code("lending_core/sources/lending.move", 406, 406)],
         "affected_responsibility_ids": ["D01"], "consequence": "H3", "reachability": "source_closed"},
        {"id": "K02", "role_ids": ["R01"], "entry": "storage::set_liquidation_threshold 等风险参数", "conditions": "无",
         "what_changes": "各资产的清算线、清算奖励、LTV，对存量仓位生效",
         "effect_locations": [code("lending_core/sources/storage.move", 417, 445)], "affected_responsibility_ids": ["D01"],
         "consequence": "H2", "reachability": "source_closed"},
        {"id": "K03", "role_ids": ["R02"], "entry": "storage::mint_owner_cap", "conditions": "无", "what_changes": "铸造新的 OwnerCap",
         "effect_locations": [code("lending_core/sources/storage.move", 822, 826)], "affected_responsibility_ids": ["D01"],
         "consequence": "H2", "reachability": "source_closed"},
        {"id": "K04", "role_ids": ["R03"], "entry": "pool::withdraw_treasury", "conditions": "金额不超过国库余额",
         "what_changes": "转出国库余额（不含用户存款）", "effect_locations": [code("lending_core/sources/pool.move", 258, 265)],
         "affected_responsibility_ids": ["D01"], "consequence": "none", "reachability": "source_closed"},
        {"id": "K05", "role_ids": ["R05"], "entry": "oracle::update_token_price", "conditions": "无价格范围限制",
         "what_changes": "直接写入任意价格，借贷估值读取这份价格",
         "effect_locations": [code("oracle/sources/oracle.move", 137, 151), code("lending_core/sources/calculator.move", 97, 101)],
         "affected_responsibility_ids": ["D02"], "consequence": "H1", "reachability": "source_closed"},
        {"id": "K06", "role_ids": ["R04"], "entry": "oracle::create_feeder", "conditions": "无", "what_changes": "铸造新的喂价凭证",
         "effect_locations": [code("oracle/sources/oracle.move", 61, 63)], "affected_responsibility_ids": ["D02"],
         "consequence": "H1", "reachability": "source_closed"},
        {"id": "K07", "role_ids": ["R04"], "entry": "oracle_manage 价格源配置", "conditions": "无",
         "what_changes": "价格源、最大时差、价格区间等配置", "effect_locations": [code("oracle/sources/oracle_manage.move", 42, 110)],
         "affected_responsibility_ids": ["D02"], "consequence": "H2", "reachability": "source_closed"},
        {"id": "K08", "role_ids": ["R06"], "entry": "0x2::package::authorize_upgrade（lending_core）", "conditions": "UpgradeCap policy=0（兼容升级）",
         "what_changes": "替换 lending_core 的全部逻辑", "effect_locations": ["lending_core/Published.toml:1-6"],
         "affected_responsibility_ids": ["D01"], "consequence": "H1", "reachability": "source_closed"},
        {"id": "K09", "role_ids": ["R07"], "entry": "0x2::package::authorize_upgrade（oracle）", "conditions": "UpgradeCap policy=0（兼容升级）",
         "what_changes": "替换价格读取逻辑", "effect_locations": ["oracle/Published.toml:1-6"],
         "affected_responsibility_ids": ["D02"], "consequence": "H1", "reachability": "source_closed"},
        {"id": "K10", "role_ids": ["R01"], "entry": "manage::set_protected_liquidation_users", "conditions": "无",
         "what_changes": "把指定用户排除在清算之外", "effect_locations": [code("lending_core/sources/manage.move", 205, 208)],
         "affected_responsibility_ids": ["D03"], "consequence": "H3", "reachability": "source_closed"}]})

w("gaps.json", {"gaps": [
    {"id": "G01", "step": "P2", "object_ids": ["S01"], "missing": "未做字节码级源码核验（sui client verify-source），只核对了 Published.toml 与链上版本号一致",
     "searched": "仓库 Published.toml；UpgradeCap 的 package 和 version", "blocks_denominator": False}]})

# ---------------------------------------------------------------- 读数
res = {x["name"]["json"]: x["value"]["json"] for x in raw("reserves-main")["address"]["dynamicFields"]["nodes"]}
prices = {x["name"]["json"]: x["value"]["json"] for x in raw("prices-main")["address"]["dynamicFields"]["nodes"]}
emodes = [x["value"]["json"] for x in raw("emodes-main")["address"]["dynamicFields"]["nodes"]]
storage = raw("storage-0xbb4e2f4b")["object"]["asMoveObject"]["contents"]["json"]
po = raw("priceoracle")["object"]["asMoveObject"]["contents"]["json"]


def sym(r):
    s = r["coin_type"].split("::")
    return s[-1] if s[-1] != "COIN" else s[-2].upper()


targets, readings = [], []
tid = {}


def target(key, addr, kind, fields, serves, reason, prio="required"):
    t = "OT%02d" % (len(targets) + 1)
    tid[key] = t
    targets.append({"id": t, "chain_id": C, "address": addr, "kind": kind,
                    "fields": [{"name": n, "meaning": m} for n, m in fields], "serves": serves, "priority": prio, "reason": reason})
    return t


RID = {}


def reading(key, tkey, field, value, unit, method, detail, evname, at="exact"):
    r = "RD%03d" % (len(readings) + 1)
    RID[key] = r
    readings.append({"id": r, "target_id": tid[tkey], "field": field, "status": "read", "value": str(value), "unit": unit,
                     "chain_id": C, "method": method, "method_detail": detail, "at_snapshot": at,
                     "source": "collector", "evidence": ev(evname)})
    return r


uc_l = raw("upgradecap-lending")["object"]
uc_o = raw("upgradecap-oracle")["object"]
target("upcap_l", UPCAP_L, "capability", [("owner", "持有人地址"), ("package", "当前包")], ["H1@BZ01"], "lending_core 升级凭证")
reading("upcap_l.owner", "upcap_l", "owner", uc_l["owner"]["address"]["address"], "地址", "object_field", "owner", "upgradecap-lending")
reading("upcap_l.package", "upcap_l", "package", uc_l["asMoveObject"]["contents"]["json"]["package"], "地址", "object_field", "contents.package", "upgradecap-lending")
target("upcap_o", UPCAP_O, "capability", [("owner", "持有人地址")], ["H1@BZ01"], "oracle 升级凭证")
reading("upcap_o.owner", "upcap_o", "owner", uc_o["owner"]["address"]["address"], "地址", "object_field", "owner", "upgradecap-oracle")
caps = {}
for k, fname in [("OwnerCap", "caps-OwnerCap"), ("StorageAdminCap", "caps-StorageAdminCap"), ("PoolAdminCap", "caps-PoolAdminCap"),
                 ("OracleAdminCap", "caps-OracleAdminCap"), ("OracleFeederCap", "caps-OracleFeederCap")]:
    nodes = raw(fname)["checkpoint"]["query"]["objects"]["nodes"]
    caps[k] = []
    for i, nd in enumerate(nodes):
        key = "%s#%d" % (k, i)
        target(key, nd["address"], "capability", [("owner", "持有人地址")], ["H1@BZ01", "H2@BZ01", "H3@BZ01"], "%s 实例（按类型在快照上查询）" % k)
        reading(key + ".owner", key, "owner", nd["owner"]["address"]["address"], "地址", "object_field", "owner", fname)
        caps[k].append((nd["address"], nd["owner"]["address"]["address"], RID[key + ".owner"]))
for name, addr in [("ms35", MS35), ("msA", MSA), ("msB", MSB)]:
    target(name, addr, "multisig", [("members_threshold", "从最近一笔交易签名解出的成员、权重和门限")], ["H1@BZ01"], "Sui 原生多签成员")
    d = raw("lasttx-" + addr[:10])["transactions"]["nodes"][0]
    readings.append({"id": "RD%03d" % (len(readings) + 1), "target_id": tid[name], "field": "members_threshold", "status": "read",
                     "value": "见 navi/msig.py 的解码结果；解出的多签地址与本地址一致", "unit": "成员地址列表",
                     "chain_id": C, "method": "targeted_tx", "method_detail": "交易 %s 的 MultiSig 签名" % d["digest"],
                     "at_snapshot": "not_applicable", "source": "collector", "evidence": "tx:sui:mainnet:" + d["digest"]})
    RID[name + ".members"] = readings[-1]["id"]
target("storage", STORAGE, "config", [("paused", "主市场暂停开关")], ["L-C3.1@BZ01"], "主市场 Storage")
reading("storage.paused", "storage", "paused", str(storage["paused"]).lower(), "布尔", "object_field", "contents.paused", "storage-0xbb4e2f4b")
target("po", PRICEORACLE, "oracle_feed", [("update_interval", "价格最大年龄（毫秒）")], ["OR-2@BZ01"], "PriceOracle")
reading("po.update_interval", "po", "update_interval", po["update_interval"], "毫秒", "object_field", "contents.update_interval", "priceoracle")
rfields = []
for aid, r in sorted(res.items()):
    for f, m in [("ltv", "开仓上限，1e27"), ("threshold", "清算线，1e27"), ("bonus", "清算奖励，1e27"), ("supply_cap", "供应上限"),
                 ("base_rate", "基础利率"), ("multiplier", "拐点前斜率"), ("jump", "拐点后斜率"), ("optimal", "拐点利用率"),
                 ("total_supply", "存款份额总量，9 位精度"), ("supply_index", "存款指数，1e27")]:
        rfields.append(("reserve[%d].%s" % (aid, f), "%s %s" % (sym(r), m)))
target("reserves", RESERVES, "market_or_pool", rfields, ["L-C2.1@MK", "L-C2.2@MK", "L-C2.4@MK", "TVL"], "主市场储备表，一次查询读出 35 个条目")
for aid, r in sorted(res.items()):
    lf, bf = r["liquidation_factors"], r["borrow_rate_factors"]
    vals = {"ltv": r["ltv"], "threshold": lf["threshold"], "bonus": lf["bonus"], "supply_cap": r["supply_cap_ceiling"],
            "base_rate": bf["base_rate"], "multiplier": bf["multiplier"], "jump": bf["jump_rate_multiplier"],
            "optimal": bf["optimal_utilization"], "total_supply": r["supply_balance"]["total_supply"], "supply_index": r["current_supply_index"]}
    for f, v in vals.items():
        reading("r%d.%s" % (aid, f), "reserves", "reserve[%d].%s" % (aid, f), v, "原始整数", "dynamic_field", "Table<u8,ReserveData>[%d]" % aid, "reserves-main")
pfields = [("price[%s]" % k, "价格值和精度") for k in sorted(prices)]
target("prices", PRICES, "oracle_feed", pfields, ["TVL"], "价格表，一次查询读出全部价格", prio="optional")
for k, p in sorted(prices.items()):
    reading("p%s" % k, "prices", "price[%s]" % k, "%s@%s" % (p["value"], p["decimal"]), "值@精度", "dynamic_field", "Table<u8,Price>[%s]" % k, "prices-main")
target("emodes", EMODES, "config", [("emode[%d].%s.%s" % (i, sd, f), "E-mode 组合参数") for i in range(len(emodes)) for sd in ("assetA", "assetB") for f in ("ltv", "lt", "liquidation_bonus")], ["L-C2.3@BZ01"], "E-mode 组合表")
for i, e in enumerate(emodes):
    for side in ("assetA", "assetB"):
        for f in ("ltv", "lt", "liquidation_bonus"):
            reading("e%d.%s.%s" % (i, side, f), "emodes", "emode[%d].%s.%s" % (i, side, f), e[side][f], "ray 1e27", "dynamic_field", "Table<u64,EmodePair>[%d]" % i, "emodes-main")
w("O2-targets.json", {"targets": targets})
w("O3-readings.json", {"readings": readings})

# ---------------------------------------------------------------- O1
markets = []
for aid, r in sorted(res.items()):
    markets.append({"id": "MK%02d" % (aid + 1), "name": "%s（资产 %d）" % (sym(r), aid), "object": RESERVES, "key": str(aid),
                    "discovered_by": "onchain_registry", "discovery_evidence": ev("reserves-main")})
# market.object：储备条目没有独立对象 ID，用储备表 ID（发现的问题之一）
w("O1-scope.json", {
    "snapshots": [snap_rec],
    "baseline_check": [{"deployment_id": "I01", "unchanged": "yes", "evidence": ev("upgradecap-lending")},
                       {"deployment_id": "I02", "unchanged": "yes", "evidence": ev("upgradecap-oracle")}],
    "businesses": [{"business_id": "BZ01", "necessary_ops": [
        {"op": "还款", "entry": "incentive_v3::entry_repay"}, {"op": "提款", "entry": "incentive_v3::entry_withdraw_v2"},
        {"op": "清算", "entry": "incentive_v3::entry_liquidation"}], "markets": markets}],
    "module_objects": [
        {"module_id": mid["lending_core::storage"], "chain_id": C, "object": STORAGE, "object_kind": "global_config", "evidence": ev("find-Storage")},
        {"module_id": mid["lending_core::storage"], "chain_id": C, "object": RESERVES, "object_kind": "registry", "evidence": ev("reserves-main")},
        {"module_id": mid["oracle::oracle"], "chain_id": C, "object": PRICEORACLE, "object_kind": "global_config", "evidence": ev("find-PriceOracle")},
        {"module_id": mid["lending_core::lending"], "chain_id": C, "object": LV, "object_kind": "package", "evidence": ev("upgradecap-lending")},
        {"module_id": mid["oracle::oracle"], "chain_id": C, "object": ORV, "object_kind": "package", "evidence": ev("upgradecap-oracle")}],
    "out_of_scope": ["9 个非主市场 Storage（market_id 1–12）：本次只评主市场", "激励业务"]})

# ---------------------------------------------------------------- O4
sig = {}
sys.path.insert(0, HERE)
from msig import decode  # noqa: E402
principals, pid = [], {}


def principal(addr, kind, thr=0, members=(), rids=()):
    if addr in pid:
        return pid[addr]
    p = "PR%02d" % (len(principals) + 1)
    pid[addr] = p
    principals.append({"id": p, "chain_id": C, "address": addr, "kind": kind, "threshold": thr,
                       "members": list(members), "reading_ids": list(rids), "delay_seconds": 0})
    return p


for name, addr in [("ms35", MS35), ("msA", MSA), ("msB", MSB)]:
    d = raw("lasttx-" + addr[:10])["transactions"]["nodes"][0]
    m = decode(d["signatures"][0]["signatureBytes"])
    assert m["derived_address"] == addr
    mem = [{"principal_id": principal(x["address"], "eoa"), "weight": x["weight"]} for x in m["members"]]
    principal(addr, "multisig", m["threshold"], mem, [RID[name + ".members"]])
holders = {}
for k, lst in caps.items():
    for _, owner, rid in lst:
        holders.setdefault(k, set()).add((owner, rid))
role_cap = {"R01": "OwnerCap", "R02": "StorageAdminCap", "R03": "PoolAdminCap", "R04": "OracleAdminCap", "R05": "OracleFeederCap"}
rh = []
for r, k in role_cap.items():
    rh.append({"role_id": r, "chain_id": C, "credential": "、".join(a for a, _, _ in caps[k]), "holder_status": "held",
               "holder_principal_ids": sorted({pid[o] for o, _ in holders[k]}), "reading_ids": sorted({x for _, x in holders[k]}),
               "evidence": [ev("caps-" + k)]})
rh.append({"role_id": "R06", "chain_id": C, "credential": UPCAP_L, "holder_status": "held", "holder_principal_ids": [pid[MS35]],
           "reading_ids": [RID["upcap_l.owner"]], "evidence": [ev("upgradecap-lending")]})
rh.append({"role_id": "R07", "chain_id": C, "credential": UPCAP_O, "holder_status": "held", "holder_principal_ids": [pid[MSA]],
           "reading_ids": [RID["upcap_o.owner"]], "evidence": [ev("upgradecap-oracle")]})


def path(pid_, cons, ctrls, desc, appr, rids, evs, covers="na", rate="na", auto="na"):
    return {"id": pid_, "business_ids": ["BZ01"], "consequence": cons, "control_ids": ctrls, "description": desc,
            "approver_ids": appr, "initiator_ids": [], "delay_seconds": 0, "delay_public": "na", "delay_bypass": "na", "exit_closable_in_delay": "na",
            "h1_rate_limited": rate if cons == "H1" else "na", "h1_covers_all_assets": covers if cons == "H1" else "na",
            "h3_auto_expire": auto if cons == "H3" else "na", "reading_ids": rids, "evidence": evs}


own = [pid[o] for o, _ in sorted(holders["OwnerCap"])]
paths = [
    path("PA01", "H1", ["K08"], "lending_core UpgradeCap → 升级替换全部逻辑", [pid[MS35]], [RID["upcap_l.owner"]], [ev("upgradecap-lending")], "yes", "no"),
    path("PA02", "H1", ["K09"], "oracle UpgradeCap → 升级价格逻辑", [pid[MSA]], [RID["upcap_o.owner"]], [ev("upgradecap-oracle")], "yes", "no"),
    path("PA03", "H1", ["K05"], "OracleFeederCap → 直接写入任意价格", [pid[MSA]], sorted({x for _, x in holders["OracleFeederCap"]}), [code("oracle/sources/oracle.move", 137, 151)], "yes", "no"),
    path("PA04", "H1", ["K06", "K05"], "OracleAdminCap → 铸造喂价凭证 → 写入任意价格", [pid[MSA]], sorted({x for _, x in holders["OracleAdminCap"]}), [code("oracle/sources/oracle.move", 61, 63)], "yes", "no"),
]
for i, o in enumerate(own):
    paths.append(path("PA%02d" % (5 + i), "H2", ["K02"], "OwnerCap 持有人 %d → 调整对存量仓位生效的风险参数" % (i + 1), [o], [], [code("lending_core/sources/storage.move", 417, 445)]))
paths.append(path("PA07", "H2", ["K03", "K02"], "StorageAdminCap → 铸造 OwnerCap → 调整风险参数", [pid[MSA]], [], [code("lending_core/sources/storage.move", 822, 826)]))
paths.append(path("PA08", "H2", ["K07"], "OracleAdminCap → 修改价格源配置", [pid[MSA]], [], [code("oracle/sources/oracle_manage.move", 42, 110)]))
for i, o in enumerate(own):
    paths.append(path("PA%02d" % (9 + i), "H3", ["K01"], "OwnerCap 持有人 %d → 暂停（另一持有人能解除但不能撤销对方凭证，任一持有人都能持续暂停）" % (i + 1), [o], [RID["storage.paused"]], [code("lending_core/sources/storage.move", 323, 330)], auto="no"))
    paths.append(path("PA%02d" % (11 + i), "H3", ["K10"], "OwnerCap 持有人 %d → 把指定用户排除在清算之外" % (i + 1), [o], [], [code("lending_core/sources/manage.move", 205, 208)], auto="no"))
w("O4-permissions.json", {"role_holders": rh, "principals": principals, "paths": paths, "absent": []})

# ---------------------------------------------------------------- O5 / O6
checks5, checks6 = [], []


def ck(lst, mk, cid, reason, evs, inputs=(), na="no", agg="no", hard="no", warn="no", weak="no", rids=(), refers="无"):
    n = len(checks5) + len(checks6) + 1
    lst.append({"id": "CK%03d" % n, "business_id": "BZ01", "market_id": mk, "check_id": cid, "inputs": list(inputs),
                "q_not_applicable": na, "q_aggregate_not_stored": agg, "q_hard": hard, "q_warn": warn, "q_weakened": weak,
                "refers_to": refers, "reading_ids": sorted(set(list(rids) + [i["reading_id"] for i in inputs if i["reading_id"] != "无"])),
                "reason": reason, "evidence": list(evs)})


def rin(name, key, div, note, group="无"):
    return {"name": name, "reading_id": RID[key], "constant": "无", "divide_by": div, "note": note, "group": group}


def cin(name, val, note, group="无"):
    return {"name": name, "reading_id": "无", "constant": str(val), "divide_by": 1, "note": note, "group": group}


RAY = 1e27
ck(checks5, "ALL", "L-C1.1", "储备表的 coin_type 与 oracle_id 一一对应，35 个资产未见重复或错配", [ev("reserves-main")],
   rids=[RID["r%d.ltv" % a] for a in sorted(res)][:1])
ck(checks5, "ALL", "L-C3.1", "快照时主市场 Storage.paused = true；还款、提款、借款、清算入口都先检查该开关，全部受阻，没有替代入口",
   [ev("storage-0xbb4e2f4b"), code("lending_core/sources/lending.move", 406, 406)], hard="yes", rids=[RID["storage.paused"]])
combos = {}
USD = {1, 2, 9, 10, 12, 16, 18, 19, 33, 34}   # 美元稳定币及美元收益资产（需人工复核）
SUIF = {0, 5, 6, 20}                          # SUI 及其 LST：vSUI(CERT)、haSUI、stSUI
for i, e in enumerate(emodes):
    if not e["isActive"]:
        continue
    for side, oside in (("assetA", "assetB"), ("assetB", "assetA")):
        a_ = e[side]
        if a_["isCollateral"] and int(a_["ltv"]) > 0:
            combos.setdefault(a_["assetId"], []).append((i, side, e[oside]["assetId"]))
for aid, r in sorted(res.items()):
    mk = "MK%02d" % (aid + 1)
    s = sym(r)
    if int(r["ltv"]) == 0:
        ck(checks5, mk, "L-C2.1", "LTV = 0，该资产不能作抵押，没有抵押×借款组合", [ev("reserves-main")], na="yes", rids=[RID["r%d.ltv" % aid]])
    else:
        bon = int(r["liquidation_factors"]["bonus"]) / RAY
        ck(checks5, mk, "L-C2.1", "默认模式：%s 作抵押" % s, [ev("reserves-main")], hard="by_formula", warn="by_formula", inputs=[
            rin("b", "r%d.ltv" % aid, RAY, "ray 精度"), rin("lambda", "r%d.threshold" % aid, RAY, "ray 精度"),
            rin("bonus", "r%d.bonus" % aid, RAY, "清算奖励；奖励在清算人与国库之间分配，用户被扣押的总额为债务 × (1 + bonus)，见 logic.move:225-233"),
            cin("same_underlying", "no", "默认模式按一般组合")])
    if aid in combos:
        inputs, rids = [], []
        for i, side, other in combos[aid]:
            g = "emode-%d" % i
            same = "yes" if {aid, other} <= USD or {aid, other} <= SUIF else "no"
            inputs += [rin("b", "e%d.%s.ltv" % (i, side), RAY, "E-mode ltv", g), rin("lambda", "e%d.%s.lt" % (i, side), RAY, "E-mode lt", g),
                       rin("bonus", "e%d.%s.liquidation_bonus" % (i, side), RAY, "E-mode 清算奖励", g),
                       cin("same_underlying", same, "借款资产 %d；两边同为美元计价资产，或同为 SUI 及其 LST 时按同底层（分类需人工复核）" % other, g)]
        ck(checks5, mk, "L-C2.3", "E-mode：%s 作抵押的全部 %d 个有效组合，脚本逐组计算取最差" % (s, len(combos[aid])),
           [ev("emodes-main")], hard="by_formula", warn="by_formula", inputs=inputs)
    else:
        ck(checks5, mk, "L-C2.3", "该资产不在任何有效的 E-mode 抵押组合中", [ev("emodes-main")], na="yes")
    bf = r["borrow_rate_factors"]
    base, mul, jump, opt = (int(bf[k]) / RAY for k in ("base_rate", "multiplier", "jump_rate_multiplier", "optimal_utilization"))
    if opt <= 0 or int(r["borrow_balance"]["total_supply"]) == 0 and int(r["ltv"]) == 0 and False:
        pass
    ck(checks5, mk, "L-C2.2", "分段线性利率：r(u)=base+mul·u（u<opt），之后加 jump·(u−opt)，见 calculator.move:24-36", [code("lending_core/sources/calculator.move", 24, 36)],
       hard="by_formula", warn="by_formula", inputs=[
           rin("base_rate", "r%d.base_rate" % aid, RAY, "基础利率"), rin("slope_low", "r%d.multiplier" % aid, RAY, "multiplier"),
           rin("slope_high", "r%d.jump" % aid, RAY, "jump_rate_multiplier"), rin("u_kink", "r%d.optimal" % aid, RAY, "optimal_utilization")])
    capv = int(r["supply_cap_ceiling"])
    if int(r["ltv"]) == 0:
        ck(checks5, mk, "L-C2.4", "LTV = 0，不能作抵押", [ev("reserves-main")], na="yes", rids=[RID["r%d.ltv" % aid]])
    else:
        ck(checks5, mk, "L-C2.4", "设有供应上限（supply_cap_ceiling = %s），无论是否主流资产都不触发" % capv, [ev("reserves-main")],
           rids=[RID["r%d.supply_cap" % aid]])
# O6
ck(checks6, "ALL", "L-F1.1", "借贷协议没有明确到期的应付；存款人提款依赖池内现金和利率机制", [ev("reserves-main")], na="yes")
ck(checks6, "ALL", "L-F1.2", "协议没有公开承诺最低储备", [REPO + "/blob/" + COMMIT + "/SECURITY.md"], na="yes")
ck(checks6, "ALL", "L-F2.1", "SUI 池的部分资金由 pool_manager 质押为 vSUI；本次未读取管理器状态，引用 L-C3.1：主市场已暂停，所有提款都受阻",
   [code("lending_core/sources/pool.move", 353, 400)], refers="CK001")
ck(checks6, "ALL", "L-D1.1", "价格表中各价格的存储时间早于快照 6 分钟到 12 小时不等，但 oracle_pro 可在交易内按需更新，存储价格过期本身不导致必要操作受阻",
   [ev("prices-main")], rids=[RID["p0"]])
ck(checks6, "ALL", "L-D2.1", "价格适配器（Pyth、Supra、Switchboard）出错时 oracle_pro 拒绝更新、估值断言失败；没有发现会继续执行的分支",
   [code("lending_core/sources/calculator.move", 97, 101)])
ck(checks6, "ALL", "OR-1", "估值读价 calculate_value 断言 is_valid，价格年龄超过 update_interval 即无效", [code("oracle/sources/oracle.move", 179, 197)],
   rids=[RID["po.update_interval"]])
ck(checks6, "ALL", "OR-2", "PriceOracle.update_interval = 15000 毫秒", [ev("priceoracle")], hard="by_formula", warn="by_formula", inputs=[
    cin("oracle_type", "pull", "oracle_pro 由使用方在交易内按需更新"), rin("max_age_s", "po.update_interval", 1000, "毫秒换算成秒"),
    cin("heartbeat_s", "none", "拉取型没有心跳")])
ck(checks6, "ALL", "OR-3", "oracle_pro 配置了价格区间和双源偏差阈值；置信区间只披露", [code("oracle/sources/oracle_manage.move", 52, 80)])
ck(checks6, "ALL", "OR-4", "Sui 不是 EVM L2", [ev("snapshot")], na="yes")
# 编号要连续：重新编号，并修正 refers_to
allc = checks5 + checks6
old = {c["id"]: "CK%03d" % (i + 1) for i, c in enumerate(allc)}
for c in allc:
    c["id"] = old[c["id"]]
    if c["refers_to"] != "无":
        c["refers_to"] = next(x["id"] for x in checks5 if x["check_id"] == "L-C3.1")
w("O5-config.json", {"checks": checks5})
w("O6-funds.json", {"checks": checks6})
w("O7-fatal.json", {"fatal": []})

# ---------------------------------------------------------------- O8
mrows, tot = [], 0.0
for aid, r in sorted(res.items()):
    p = prices[r["oracle_id"]]
    usd = int(r["supply_balance"]["total_supply"]) * int(r["current_supply_index"]) / RAY / 1e9 * int(p["value"]) / 10 ** p["decimal"]
    tot += usd
    mrows.append({"market_id": "MK%02d" % (aid + 1), "tvl_usd": round(usd, 2),
                  "basis": "存款份额 × 存款指数 ÷ 1e27 ÷ 1e9 × 价格表中的存储价格（存储价格可能比快照早，见 L-D1.1）",
                  "reading_ids": [RID["r%d.total_supply" % aid], RID["r%d.supply_index" % aid], RID["p%s" % r["oracle_id"]]], "evidence": []})
w("O8-tvl.json", {"tvl_available": "yes", "tvl_source": "onchain_balances", "market_tvl_source": "onchain_balances",
                  "price_source": "NAVI PriceOracle 存储价格", "tvl_time_utc": snap["timestamp"],
                  "businesses": [{"business_id": "BZ01", "tvl_usd": round(tot, 2), "basis": "35 个市场的存款价值之和",
                                  "reading_ids": [x for m in mrows for x in m["reading_ids"]][:3], "evidence": []}],
                  "markets": mrows})
print("ok", len(targets), "targets", len(readings), "readings", len(checks5) + len(checks6), "checks", round(tot))
