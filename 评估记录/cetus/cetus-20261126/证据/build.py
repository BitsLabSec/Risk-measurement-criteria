# 把 Cetus CLMM 的链上读数整理成工作流的 T0–P5、O1–O8 文件。
# 只做「整理」：每个答案的依据写在 reason / note 里；需要人判断的地方单独标出。
# 原始读数全部来自 证据/raw/（由 工作流/scripts/sui_read.py 在快照上读取并保存）。
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
RAW = os.path.join(HERE, "raw")
sys.path.insert(0, os.path.join(OUT, "..", "..", "..", "工作流", "scripts"))
from bitsscore import src_root  # noqa: E402

LOCAL = "cache:packages/cetus_clmm"     # 先运行 bitsscore.py fetch-sources <目录> 检出
C = "sui:mainnet"
REPO = "https://github.com/CetusProtocol/cetus-contracts"
COMMIT = "4e6147ed5584def9eb6b8e36ef7e62ccb7551fd3"
SRC = src_root({"repo_url": REPO, "commit": COMMIT, "local_path": LOCAL})
PKG0 = "0x1eabed72c53feb3805120a081dc15963c204dc8d091542592abaf7a35689b2fb"   # 原始包 ID（类型都定义在这里）
PKG = "0x260693ec785a6e6c9d81d58c7d2ff72f1288ae0fa6a9725abe05a6478b11f084"    # 当前版本 15
UPCAP = "0x4462a572640227717cb8c60b6dd337f022743de6bc13f1fe0b7adb182d1fa274"
CONFIG = "0xdaa46292632c3c4d8f31f23ea0f9b36a28ff3677e9684980e4438403a67a3d8f"
ACL = "0xcf1897ae0793665f0e3f676d86450675bbf31842fde1aa02613b7b53f34b764c"
POOLS = "0xf699e7f2276f5c9a75944b37a0c5b5d9ddfd2471bf6242483b03ab2887d198d0"
VAULT = "0xce7bceef26d3ad1f6d9b6f13a953f053e6ed3ca77907516481ce99ae8e588f2b"
MSA = "0x2891c6b8dca29a075d263c1bb21c7b88adf3ff6baddae1b8743cc00b66bd2c47"
MSB = "0xdbfd0b17fa804c98f51d552b050fb7f850b85db96fa2a0d79e50119525814a47"
POOL_LIST = [  # O1 选定的池：官方 dapp 按 TVL 排名前三（证据/web/cetus-stats-pools.json）
    ("MK01", "hasui-sui", "haSUI-SUI（费率 0.01%）", "0x871d8a227114f375170f149f7e9d45be822dd003eba225e83c05ac80828596bc"),
    ("MK02", "usdc-usdy", "USDC-USDY（费率 0.01%）", "0xdcd762ad374686fa890fc4f3b9bbfe2a244e713d7bffbfbd1b9221cb290da2ed"),
    ("MK03", "usdc-sui", "USDC-SUI（费率 0.25%）", "0xb8d7d9e66a60c239e7a60110efcf8de6c705580ed924d0dde141f4a0e2c90105"),
]
STATS_URL = ("https://api-sui.cetus.zone/v2/sui/stats_pools?is_vaults=false&display_all_pools=true&has_mining=true"
             "&has_farming=true&no_incentives=true&order_by=-tvl&limit=10&offset=0")
LLAMA_URL = "https://api.llama.fi/protocol/cetus-amm"


def raw(name):
    return json.load(open(os.path.join(RAW, name + ".json")))["response"]["data"]


def w(name, data):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def ev(name):
    return "file:证据/raw/%s.json" % name


def code(f, a, b):
    return "sources/%s:%d-%d" % (f, a, b)


def nlines(rel):
    return len(open(os.path.join(SRC, rel), encoding="utf-8").read().split("\n"))


snap = raw("snapshot")["checkpoint"]
CP = snap["sequenceNumber"]
snap_rec = {"chain_id": C, "block_or_checkpoint": str(CP), "block_hash_or_digest": snap["digest"],
            "time_utc": snap["timestamp"], "evidence": ev("snapshot")}

# ---------------------------------------------------------------- T0
w("T0-task.json", {
    "assessment_id": os.path.basename(OUT), "previous_assessment_id": "无", "reason": "first",
    "project": "Cetus Protocol", "dimensions": ["onchain"],
    "chains": [{"chain_id": C, "name": "Sui Mainnet"}],
    "scope_statement": "工作流试跑（DEX 专项）：Cetus CLMM 原生做市（cetus_clmm 包）的链上安全",
    "known_entries": [PKG0, PKG], "known_repos": [REPO],
    "out_of_scope": ["Cetus DLMM：只公开了接口仓库，没有完整源码", "Aggregator V3、Tide RFQ：不同专项业务，本次只试跑原生 AMM",
                     "Limit、DCA、Vaults、Stable Farming、LP Burn、xCETUS、Launchpad、Margin", "Aptos 上的 Cetus 部署",
                     "CLMM 的奖励领取（Farming 专项范围）"],
    "assessor": "claude（试跑）", "date": snap["timestamp"][:10]})

# ---------------------------------------------------------------- P1
tx = raw("usertx-clmm")["transactions"]["nodes"][0]
w("P1-baseline.json", {"baseline_id": "B01", "snapshots": [snap_rec], "deployments": [
    {"id": "I01", "chain_id": C, "entry": PKG, "proxy_kind": "sui_package", "actual_code": PKG, "version": "15",
     "how_found": "packageVersions 的最新版本是 15（0x2606…）；UpgradeCap 的 package 字段也指向 0x2606…、version=15；"
                  "快照前的真实交易 %s 直接调用了 0x2606…::pool::flash_swap" % tx["digest"],
     "evidence": [ev("pkgversions-clmm"), ev("upgradecap-clmm"), ev("usertx-clmm"), "tx:sui:mainnet:" + tx["digest"]], "status": "confirmed"}]})

# ---------------------------------------------------------------- P2
w("P2-sources.json", {"sources": [
    {"id": "S01", "deployment_ids": ["I01"], "language": "move", "repo_url": REPO, "commit": COMMIT,
     "local_path": LOCAL, "in_scope_globs": ["sources/*.move", "sources/math/*.move"],
     "excluded_globs": ["tests/**"], "verify_method": "not_verified", "verify_result": "not_verified",
     "verify_evidence": [REPO + "/blob/" + COMMIT + "/packages/cetus_clmm/Published.toml"]}]})

# ---------------------------------------------------------------- P3
names = ["acl", "config", "factory", "partner", "pool", "pool_creator", "position", "position_snapshot", "rewarder", "tick",
         "utils", "math/clmm_math", "math/tick_math"]
purpose = {"acl": "按地址记录角色位的权限表", "config": "全局配置：费率档、协议费率、权限、包版本与紧急暂停",
           "factory": "建池、池列表、币种黑白名单", "partner": "合作方返佣", "pool": "池子：加减流动性、兑换、领费、闪电贷、管理入口",
           "pool_creator": "建池并同时加流动性的入口", "position": "LP 头寸 NFT 与头寸记账", "position_snapshot": "2025 年事件后受影响头寸的快照",
           "rewarder": "奖励发放与奖励金库", "tick": "tick 表与区间记账", "utils": "工具函数",
           "math/clmm_math": "流动性与数量换算", "math/tick_math": "tick 与价格换算"}
mid, mods = {}, []
for i, n in enumerate(names):
    k = "M%02d" % (i + 1)
    mid[n] = k
    mods.append({"id": k, "name": "cetus_clmm::" + n.split("/")[-1], "source_id": "S01", "file": "sources/%s.move" % n,
                 "is_external": False, "business_ids": ["BZ01"], "purpose": purpose[n], "calls_module_ids": []})
calls = {"pool": ["config", "position", "tick", "rewarder", "partner", "position_snapshot", "math/clmm_math", "math/tick_math"],
         "factory": ["config", "pool"], "pool_creator": ["factory", "pool"], "config": ["acl"], "rewarder": ["config"],
         "partner": ["config"], "position": ["math/clmm_math"], "tick": ["math/tick_math"]}
for m in mods:
    short = m["file"][len("sources/"):-len(".move")]
    m["calls_module_ids"] = [mid[x] for x in calls.get(short, [])]
w("P3-business-modules.json", {"businesses": [{
    "id": "BZ01", "name": "CLMM 原生做市与兑换", "specialty": "dex_amm",
    "user_entries": ["pool::remove_liquidity", "pool::collect_fee", "pool::flash_swap", "pool::add_liquidity", "pool::open_position",
                     "pool::close_position"],
    "assets_or_state": ["各池的两种币余额（coin_a、coin_b）", "LP 头寸的流动性和未领手续费", "协议费（fee_protocol_coin_a/b）"]}],
    "modules": mods})


# ---------------------------------------------------------------- P4（粗粒度：本次只评链上，不评代码覆盖）
def whole(ns):
    return [{"source_id": "S01", "file": "sources/%s.move" % n, "start": 1, "end": nlines("sources/%s.move" % n)} for n in ns]


resp = [
    ("D01", "加减流动性、头寸记账、领取手续费", ["pool", "position", "tick", "math/clmm_math", "math/tick_math", "utils"],
     "yes", "remove_liquidity 从池中划出两种币并减少头寸流动性", [code("pool.move", 758, 843)],
     "yes", "撤资、领费先检查包版本和池状态开关", [code("pool.move", 764, 765), code("pool.move", 2445, 2487)],
     "池子余额、LP 头寸", "LP 资金被错误划转或撤资被阻断"),
    ("D02", "兑换与闪电贷", ["pool", "pool_creator"],
     "yes", "flash_swap 按价格曲线划出资产，repay 时收回", [code("pool.move", 1181, 1252)],
     "yes", "兑换受 is_allow_swap 开关控制", [code("pool.move", 2415, 2428)],
     "池子余额和价格", "兑换价格或收付金额出错"),
    ("D03", "全局配置、角色权限、包版本与紧急暂停", ["config", "acl"],
     "yes", "AdminCap 授予和撤销全部角色", [code("config.move", 339, 374)],
     "yes", "emergency_pause 把包版本改成极大值，所有入口的版本检查都会失败", [code("config.move", 524, 569)],
     "全部池子的可用性和权限边界", "必要操作被全局阻断，或权限被错误授予"),
    ("D04", "建池、池列表与币种名单", ["factory"],
     "no", "无", [], "no", "无", [], "新池的创建", "只影响新池创建，不影响已有头寸"),
    ("D05", "奖励金库与合作方返佣", ["rewarder", "partner"],
     "yes", "emergent_withdraw 可从奖励金库取走任意数量奖励币", [code("rewarder.move", 374, 389)],
     "no", "无", [], "奖励金库余额、合作方返佣", "LP 已累计奖励无法领取"),
    ("D06", "2025 年事件后的头寸快照与恢复入口", ["position_snapshot"],
     "yes", "受影响头寸记录快照，apply_liquidity_cut 已改为直接 abort", [code("pool.move", 1630, 1650)],
     "yes", "被快照的头寸不能 close_position", [code("pool.move", 879, 886)],
     "受影响头寸", "受影响头寸的关闭受限"),
]
w("P4-responsibilities.json", {"responsibilities": [
    {"id": d, "result": r, "business_ids": ["BZ01"], "module_ids": [mid[n] for n in ns], "ranges": whole(ns),
     "q1_assets_or_authority": q1, "q1_evidence": q1e, "q1_locations": q1l,
     "q2_preconditions_or_availability": q2, "q2_evidence": q2e, "q2_locations": q2l,
     "impact_object": io, "failure_consequence": fc}
    for d, r, ns, q1, q1e, q1l, q2, q2e, q2l, io, fc in resp]})

# ---------------------------------------------------------------- P5
ACL_ROLES = [("R03", 0, "ACL_POOL_MANAGER（池管理员）"), ("R04", 1, "ACL_FEE_TIER_MANAGER（费率档管理员）"),
             ("R05", 2, "ACL_CLAIM_PROTOCOL_FEE（协议费领取）"), ("R06", 3, "ACL_PARTNER_MANAGER（合作方管理员）"),
             ("R07", 4, "ACL_REWARDER_MANAGER（奖励管理员）"), ("R08", 5, "ACL_EMERGENCY_UNPAUSE（解除紧急暂停）"),
             ("R09", 6, "ACL_EMERGENCY_PAUSE（紧急暂停）")]
ACL_CHECK = {0: (435, 437), 1: (442, 444), 2: (449, 457), 3: (459, 464), 4: (466, 471), 5: (480, 485), 6: (473, 475)}
roles = [{"id": "R01", "credential": "config::AdminCap", "check_locations": [code("config.move", 339, 374), code("config.move", 575, 583)],
          "how_obtained": "init 时转给部署者，可转移（key, store）", "granted_by_role_ids": []},
         {"id": "R02", "credential": "0x2::package::UpgradeCap（cetus_clmm）", "check_locations": ["Published.toml:1-9"],
          "how_obtained": "发布时生成，可转移", "granted_by_role_ids": []}]
for r, bit, nm in ACL_ROLES:
    a, b = ACL_CHECK[bit]
    roles.append({"id": r, "credential": "GlobalConfig.acl 角色位 %d：%s" % (bit, nm), "check_locations": [code("config.move", a, b)],
                  "how_obtained": "AdminCap 调用 set_roles／add_role 授予，remove_role 撤销；init 时给部署者 0、1、3、4 位",
                  "granted_by_role_ids": ["R01"]})
controls = [
    ("K01", ["R02"], "0x2::package::authorize_upgrade（cetus_clmm）", "UpgradeCap policy=0（兼容升级），无时间锁",
     "替换 cetus_clmm 的全部逻辑，对全部已有池和头寸生效", ["Published.toml:1-9"], ["D01", "D02", "D03", "D05", "D06"], "H1"),
    ("K02", ["R01"], "rewarder::emergent_withdraw", "包版本检查",
     "从 RewarderGlobalVault 取走任意数量的奖励币（含 LP 已累计、未领取的奖励）", [code("rewarder.move", 374, 389)], ["D05"], "H1"),
    ("K03", ["R01"], "config::set_roles／add_role／remove_role", "无",
     "给任意地址授予或撤销任意角色位（包括池管理员、紧急暂停）", [code("config.move", 339, 374)], ["D03"], "H3"),
    ("K04", ["R01"], "config::update_package_version", "新版本号必须大于旧值且小于 EMERGENCY_PAUSE_VERSION",
     "把 GlobalConfig.package_version 改成大于代码 VERSION 的值，所有入口的版本检查失败，直到升级出新包",
     [code("config.move", 575, 583), code("config.move", 524, 526)], ["D01", "D02", "D03"], "H3"),
    ("K05", ["R03"], "pool::set_pool_status", "包版本检查",
     "逐池关闭撤资、领费、兑换等开关，没有到期时间", [code("pool.move", 2514, 2570), code("pool.move", 2445, 2487)], ["D01"], "H3"),
    ("K06", ["R03"], "pool::update_fee_rate", "新费率 ≤ MAX_FEE_RATE（200000，即 20%）",
     "修改已有池的手续费率，对存量 LP 和交易者立即生效", [code("pool.move", 1444, 1463)], ["D02"], "H2"),
    ("K07", ["R09"], "config::emergency_pause", "已在暂停中不能重复暂停",
     "把包版本改成 EMERGENCY_PAUSE_VERSION，全部池的撤资、领费、兑换都失败；只有 R08 能解除",
     [code("config.move", 540, 569)], ["D01", "D02", "D03"], "H3"),
    ("K08", ["R08"], "config::emergency_unpause", "必须处于紧急暂停中；恢复的版本号不小于暂停前的版本",
     "恢复包版本，解除紧急暂停", [code("config.move", 554, 569)], ["D03"], "none"),
    ("K09", ["R03"], "config::update_protocol_fee_rate", "新值 ≤ MAX_PROTOCOL_FEE_RATE（3000，即手续费的 30%）",
     "修改全部池的协议分成比例，对存量 LP 立即生效", [code("config.move", 242, 257)], ["D02"], "H2"),
    ("K10", ["R07"], "pool::initialize_rewarder／update_emission", "调整前先结算",
     "调整奖励发放速度，只影响之后的奖励", [code("pool.move", 1368, 1421)], ["D05"], "none"),
    ("K11", ["R05"], "pool::collect_protocol_fee", "只能取 fee_protocol_coin_a/b",
     "取走协议费余额，不涉及 LP 本金和 LP 手续费", [code("pool.move", 1332, 1349)], ["D02"], "none"),
    ("K12", ["R04"], "config::add_fee_tier／update_fee_tier／delete_fee_tier", "费率 ≤ MAX_FEE_RATE",
     "费率档只在建池时使用，不改已有池", [code("config.move", 264, 332)], ["D04"], "none"),
    ("K13", ["R06"], "partner::create_partner／update_ref_fee_rate 等", "无",
     "合作方返佣比例，只影响合作方收入", [code("partner.move", 170, 310)], ["D05"], "none"),
    ("K14", ["R03"], "pool::init_position_snapshot", "包版本必须等于 EMERGENCY_RESTORE_NEED_VERSION，且池已暂停",
     "为池子建立头寸快照；配套的 apply_liquidity_cut 已改为直接 abort", [code("pool.move", 1630, 1650), code("pool.move", 1723, 1733)],
     ["D06"], "none"),
]
w("P5-roles-controls.json", {"roles": roles, "controls": [
    {"id": k, "role_ids": rs, "entry": e, "conditions": cnd, "what_changes": wc, "effect_locations": el,
     "affected_responsibility_ids": ar, "consequence": cq, "reachability": "source_closed"}
    for k, rs, e, cnd, wc, el, ar, cq in controls]})

w("gaps.json", {"gaps": [
    {"id": "G01", "step": "P2", "object_ids": ["S01"], "missing": "未做字节码级源码核验（sui client verify-source），只核对了 Published.toml 与链上版本号、包 ID 一致",
     "searched": "仓库 Published.toml；UpgradeCap 的 package 和 version；packageVersions", "blocks_denominator": False}]})

# ---------------------------------------------------------------- O2 / O3
targets, readings, tid, RID = [], [], {}, {}


def target(key, addr, kind, fields, serves, reason, prio="required"):
    t = "OT%02d" % (len(targets) + 1)
    tid[key] = t
    targets.append({"id": t, "chain_id": C, "address": addr, "kind": kind,
                    "fields": [{"name": n, "meaning": m} for n, m in fields], "serves": serves, "priority": prio, "reason": reason})


def reading(key, tkey, field, value, unit, method, detail, evname, at="exact", evidence=None):
    r = "RD%03d" % (len(readings) + 1)
    RID[key] = r
    readings.append({"id": r, "target_id": tid[tkey], "field": field, "status": "read", "value": str(value), "unit": unit,
                     "chain_id": C, "method": method, "method_detail": detail, "at_snapshot": at,
                     "source": "collector", "evidence": evidence or ev(evname)})
    return r


uc = raw("upgradecap-clmm")["object"]
target("upcap", UPCAP, "capability", [("owner", "持有人地址"), ("package", "当前包"), ("version", "版本"), ("policy", "升级策略，0=兼容")],
       ["H1@BZ01"], "cetus_clmm 的升级凭证")
reading("upcap.owner", "upcap", "owner", uc["owner"]["address"]["address"], "地址", "object_field", "owner", "upgradecap-clmm")
for f in ("package", "version", "policy"):
    reading("upcap." + f, "upcap", f, uc["asMoveObject"]["contents"]["json"][f], "原始值", "object_field", "contents." + f, "upgradecap-clmm")
adm = raw("caps-AdminCap")["checkpoint"]["query"]["objects"]["nodes"]
assert len(adm) == 1
ADMINCAP = adm[0]["address"]
target("admincap", ADMINCAP, "capability", [("owner", "持有人地址")], ["H1@BZ01", "H2@BZ01", "H3@BZ01"],
       "config::AdminCap 的全部实例（按类型在快照上查询，只有 1 个）")
reading("admincap.owner", "admincap", "owner", adm[0]["owner"]["address"]["address"], "地址", "type_query",
        "checkpoint(%d).objects(type: %s::config::AdminCap)" % (CP, PKG0), "caps-AdminCap")
gc = raw("globalconfig")["object"]["asMoveObject"]["contents"]["json"]
target("config", CONFIG, "config", [("package_version", "当前允许的包版本；等于 2^63 表示紧急暂停中"),
                                    ("protocol_fee_rate", "协议分成，分母 10000"),
                                    ("acl.permissions", "角色表（LinkedTable）的 ID 和条目数")],
       ["H3@BZ01", "DX-C3.1@MK01", "DX-C3.1@MK02", "DX-C3.1@MK03", "DX-C2.1@MK01", "DX-C2.1@MK02", "DX-C2.1@MK03"], "CLMM 全局配置")
reading("config.package_version", "config", "package_version", gc["package_version"], "整数", "object_field", "contents.package_version", "globalconfig")
reading("config.protocol_fee_rate", "config", "protocol_fee_rate", gc["protocol_fee_rate"], "1/10000", "object_field", "contents.protocol_fee_rate", "globalconfig")
reading("config.acl", "config", "acl.permissions", "%s（%s 个条目）" % (gc["acl"]["permissions"]["id"], gc["acl"]["permissions"]["size"]),
        "对象 ID", "object_field", "contents.acl.permissions", "globalconfig")
target("config_df", CONFIG, "config", [("dynamic_fields", "GlobalConfig 下的动态字段；有 emergency_pause_before_version 表示处于紧急暂停")],
       ["DX-C3.1@MK01", "DX-C3.1@MK02", "DX-C3.1@MK03"], "确认是否处于紧急暂停")
reading("config.df", "config_df", "dynamic_fields", "[]（0 个条目）", "列表", "dynamic_field", "address(%s).dynamicFields" % CONFIG, "globalconfig-dynfields")
acl = raw("acl-members")["address"]["dynamicFields"]["nodes"]
target("acl", ACL, "config", [("member[%s]" % n["name"]["json"], "该地址的角色位（u128 位图）") for n in acl],
       ["H1@BZ01", "H2@BZ01", "H3@BZ01"], "CLMM 角色表，一次查询读出 7 个成员")
acl_bits = {}
for n in acl:
    addr = n["name"]["json"]
    acl_bits[addr] = int(n["value"]["json"]["value"])
    reading("acl." + addr, "acl", "member[%s]" % addr, n["value"]["json"]["value"], "u128 角色位图", "dynamic_field",
            "LinkedTable<address, Member>[%s].value.roles" % addr, "acl-members")
for key, addr, evn in [("msB", MSB, "msig-dbfd"), ("msA", MSA, "msig-2891")]:
    d = raw(evn)
    dec = d["decoded"]
    assert dec["matches_address"]
    target(key, addr, "multisig", [("members_threshold", "从一笔交易签名解出的成员、权重和门限")], ["H1@BZ01", "H2@BZ01", "H3@BZ01"],
           "Sui 原生多签成员")
    reading(key + ".members", key, "members_threshold",
            "门限 %d；" % dec["threshold"] + "，".join("%s×%d" % (m["address"], m["weight"]) for m in dec["members"]),
            "成员地址×权重", "targeted_tx",
            "交易 %s 的 MultiSig 签名；Sui 多签地址由成员公钥、权重和门限推出，解出的地址与本地址一致，所以不受交易时间影响" % dec["digest"],
            evn, at="not_applicable")
pools = {}
for mk, n, label, addr in POOL_LIST:
    p = raw("pool-" + n)["object"]["asMoveObject"]["contents"]["json"]
    pools[mk] = p
    target("pool." + mk, addr, "market_or_pool",
           [("type", "池的币种类型（A, B）"), ("tick_spacing", "tick 间距"), ("fee_rate", "手续费率，分母 1000000"),
            ("coin_a", "A 币真实余额（最小单位）"), ("coin_b", "B 币真实余额（最小单位）"),
            ("fee_protocol_coin_a", "A 币协议费（最小单位）"), ("fee_protocol_coin_b", "B 币协议费（最小单位）"),
            ("liquidity", "当前价格处的流动性"), ("current_sqrt_price", "当前价格的平方根，Q64.64"),
            ("is_pause", "池级暂停标志"), ("position_manager.positions.size", "头寸数量（只披露）")],
           ["DX-C1.1@" + mk, "DX-C2.1@" + mk, "DX-C3.1@" + mk, "DX-F1.1@" + mk], "选定的池（%s）" % label)
    typ = raw("pool-" + n)["object"]["asMoveObject"]["contents"]["type"]["repr"]
    reading(mk + ".type", "pool." + mk, "type", typ.split("<", 1)[1].rstrip(">"), "类型", "object_field", "contents.type", "pool-" + n)
    for f in ("tick_spacing", "fee_rate", "coin_a", "coin_b", "fee_protocol_coin_a", "fee_protocol_coin_b", "liquidity",
              "current_sqrt_price", "is_pause"):
        unit = {"fee_rate": "1/1000000", "current_sqrt_price": "Q64.64", "is_pause": "布尔", "tick_spacing": "整数",
                "liquidity": "整数"}.get(f, "最小单位")
        reading("%s.%s" % (mk, f), "pool." + mk, f, str(p[f]).lower() if f == "is_pause" else p[f], unit, "object_field", "contents." + f, "pool-" + n)
    reading(mk + ".positions", "pool." + mk, "position_manager.positions.size", p["position_manager"]["positions"]["size"], "个",
            "object_field", "contents.position_manager.positions.size", "pool-" + n)
    df = raw("pool-%s-dynfields" % n)["address"]["dynamicFields"]["nodes"]
    target("pooldf." + mk, addr, "market_or_pool", [("dynamic_fields", "池下的动态字段：有 pool_status 表示设置过逐项开关")],
           ["DX-C3.1@" + mk], "确认池级开关状态（%s）" % label)
    reading(mk + ".df", "pooldf." + mk, "dynamic_fields", "，".join(x["name"]["json"] for x in df) + "（没有 pool_status）", "列表",
            "dynamic_field", "address(%s).dynamicFields" % addr, "pool-%s-dynfields" % n)
    tk = p["tick_manager"]["ticks"]
    due = json.load(open(os.path.join(RAW, "due-%s.json" % n)))
    assert due["result"]["rebuild_ok"]
    target("ticks." + mk, tk["id"], "market_or_pool",
           [("due_a", "全部头寸的 A 币本金应得（最小单位），由整张 tick 表（%s 个）重建" % tk["size"]),
            ("due_b", "全部头寸的 B 币本金应得（最小单位），由整张 tick 表重建")],
           ["DX-F1.1@" + mk], "DEX 专项 DX-F1.1：一次读出 tick 表，重建全部头寸的本金应得（%s）" % label)
    for f in ("due_a", "due_b"):
        reading("%s.%s" % (mk, f), "ticks." + mk, f, due["result"][f], "最小单位", "derived", due["command"], "due-" + n)
vault = raw("rewarder-vault")["object"]["asMoveObject"]["contents"]["json"]
target("vault", VAULT, "vault_or_reserve", [("balances.size", "奖励金库中的币种数")], ["H1@BZ01"],
       "emergent_withdraw 能取走的奖励金库（只确认对象存在和币种数）", prio="optional")
reading("vault.size", "vault", "balances.size", vault["balances"]["size"], "个", "object_field", "contents.balances.size", "rewarder-vault")
fac = raw("factory-pools")["object"]["asMoveObject"]["contents"]["json"]
target("factory", POOLS, "other", [("list.size", "已创建的池数量")], ["TVL"], "池注册表，只读池数量（不枚举）", prio="disclosure")
reading("factory.size", "factory", "list.size", fac["list"]["size"], "个", "object_field", "contents.list.size", "factory-pools")
w("O2-targets.json", {"targets": targets})
w("O3-readings.json", {"readings": readings})

# ---------------------------------------------------------------- O1
w("O1-scope.json", {
    "snapshots": [snap_rec],
    "baseline_check": [{"deployment_id": "I01", "unchanged": "yes", "evidence": ev("upgradecap-clmm")}],
    "businesses": [{"business_id": "BZ01", "necessary_ops": [
        {"op": "撤资（取回流动性）", "entry": "pool::remove_liquidity"},
        {"op": "领取已产生的手续费", "entry": "pool::collect_fee"},
        {"op": "交易", "entry": "pool::flash_swap"}],
        "markets": [{"id": mk, "name": label, "object": addr, "key": "无", "discovered_by": "official_list",
                     "discovery_evidence": STATS_URL} for mk, n, label, addr in POOL_LIST]}],
    "module_objects": [
        {"module_id": mid["pool"], "chain_id": C, "object": PKG, "object_kind": "package", "evidence": ev("pkgversions-clmm")},
        {"module_id": mid["config"], "chain_id": C, "object": CONFIG, "object_kind": "global_config", "evidence": ev("globalconfig")},
        {"module_id": mid["config"], "chain_id": C, "object": ADMINCAP, "object_kind": "capability", "evidence": ev("caps-AdminCap")},
        {"module_id": mid["acl"], "chain_id": C, "object": ACL, "object_kind": "registry", "evidence": ev("acl-members")},
        {"module_id": mid["factory"], "chain_id": C, "object": POOLS, "object_kind": "registry", "evidence": ev("factory-pools")},
        {"module_id": mid["rewarder"], "chain_id": C, "object": VAULT, "object_kind": "treasury", "evidence": ev("rewarder-vault")},
        {"module_id": mid["pool"], "chain_id": C, "object": UPCAP, "object_kind": "capability", "evidence": ev("upgradecap-clmm")}],
    "out_of_scope": ["其余 %s 个 CLMM 池：按 DEX 专项第 0 节不全量扫池，只选了官方 dapp 按 TVL 排名前三的池" % (int(fac["list"]["size"]) - 3),
                     "奖励领取（collect_reward）：属于 Farming 专项，本次不评"]})

# ---------------------------------------------------------------- O4
principals, pid = [], {}


def principal(addr, kind, thr=0, members=(), rids=()):
    if addr in pid:
        return pid[addr]
    p = "PR%02d" % (len(principals) + 1)
    pid[addr] = p
    principals.append({"id": p, "chain_id": C, "address": addr, "kind": kind, "threshold": thr,
                       "members": list(members), "reading_ids": list(rids), "delay_seconds": 0})
    return p


for key, addr, evn in [("msB", MSB, "msig-dbfd"), ("msA", MSA, "msig-2891")]:
    dec = raw(evn)["decoded"]
    mem = [{"principal_id": principal(m["address"], "eoa"), "weight": m["weight"]} for m in dec["members"]]
    principal(addr, "multisig", dec["threshold"], mem, [RID[key + ".members"]])
for addr in acl_bits:
    principal(addr, "eoa")
rh = [{"role_id": "R01", "chain_id": C, "credential": ADMINCAP, "holder_status": "held", "holder_principal_ids": [pid[MSB]],
       "reading_ids": [RID["admincap.owner"]], "evidence": [ev("caps-AdminCap")]},
      {"role_id": "R02", "chain_id": C, "credential": UPCAP, "holder_status": "held", "holder_principal_ids": [pid[MSB]],
       "reading_ids": [RID["upcap.owner"]], "evidence": [ev("upgradecap-clmm")]}]
holders_of = {}
for r, bit, nm in ACL_ROLES:
    hs = sorted(a for a, b in acl_bits.items() if b >> bit & 1)
    holders_of[r] = hs
    rh.append({"role_id": r, "chain_id": C, "credential": "%s#acl:%d" % (CONFIG, bit), "holder_status": "held" if hs else "unassigned",
               "holder_principal_ids": [pid[a] for a in hs], "reading_ids": [RID["acl." + a] for a in hs],
               "evidence": [ev("acl-members")]})
B, A = pid[MSB], pid[MSA]
ACLR = [RID["acl." + a] for a in acl_bits]


def path(p, cons, ctrls, desc, appr, rids, evs, covers="na", auto="na", inits=()):
    return {"id": p, "business_ids": ["BZ01"], "consequence": cons, "control_ids": ctrls, "description": desc,
            "approver_ids": appr, "initiator_ids": list(inits), "delay_seconds": 0, "delay_public": "na", "delay_bypass": "na", "exit_closable_in_delay": "na",
            "h1_rate_limited": "no" if cons == "H1" else "na", "h1_covers_all_assets": covers if cons == "H1" else "na",
            "h3_auto_expire": auto if cons == "H3" else "na", "reading_ids": rids, "evidence": evs}


paths = [
    path("PA01", "H1", ["K01"], "UpgradeCap 由多签 B（5/10 加权）持有，无时间锁，兼容升级可替换全部池和头寸的处理逻辑", [B],
         [RID["upcap.owner"], RID["upcap.policy"], RID["msB.members"]], [ev("upgradecap-clmm"), ev("msig-dbfd")], covers="yes"),
    path("PA02", "H1", ["K02"], "AdminCap（多签 B）调用 emergent_withdraw 取走奖励金库中 LP 已累计的奖励；不涉及池中本金", [B],
         [RID["admincap.owner"], RID["vault.size"], RID["msB.members"]], [ev("caps-AdminCap"), code("rewarder.move", 374, 389)], covers="no"),
    path("PA03", "H2", ["K06"], "池管理员（多签 A，2/3）调整已有池的手续费率，上限 20%", [A],
         [RID["acl." + MSA], RID["msA.members"]], [ev("acl-members"), code("pool.move", 1444, 1463)]),
    path("PA04", "H2", ["K09"], "池管理员（多签 A）调整全部池的协议分成，上限 30%", [A],
         [RID["acl." + MSA], RID["msA.members"]], [ev("acl-members"), code("config.move", 242, 257)]),
    path("PA05", "H2", ["K03", "K06", "K09"], "间接路径：AdminCap（多签 B）先给自己授予池管理员角色，再调整费率或协议分成", [B],
         [RID["admincap.owner"], RID["msB.members"]], [ev("caps-AdminCap"), code("config.move", 339, 360)]),
    path("PA06", "H3", ["K03", "K05"],
         "池管理员（多签 A）可关闭撤资和领费开关，没有到期时间；多签 B 能用 AdminCap 撤掉 A 的角色并给自己授权恢复，所以阻断能否持续取决于 B", [B],
         [RID["acl." + MSA], RID["admincap.owner"], RID["msB.members"]], [code("pool.move", 2514, 2570), code("config.move", 339, 374)], auto="no",
         inits=[A]),
    path("PA07", "H3", ["K03", "K07"],
         "4 个单签地址都能紧急暂停全部池；只有多签 B 能解除（角色位 5），并能用 AdminCap 撤掉暂停者的角色，所以阻断能否持续取决于 B", [B],
         ACLR + [RID["msB.members"]], [ev("acl-members"), code("config.move", 540, 569)], auto="no",
         inits=[pid[a] for a in holders_of["R09"]]),
    path("PA08", "H3", ["K04"], "AdminCap（多签 B）把 package_version 调到代码版本之上，全部入口失效，只能靠升级恢复", [B],
         [RID["admincap.owner"], RID["config.package_version"], RID["msB.members"]], [code("config.move", 575, 583)], auto="no"),
]
w("O4-permissions.json", {"role_holders": rh, "principals": principals, "paths": paths, "absent": []})

# ---------------------------------------------------------------- O5 / O6
ck = []


def check(bz, mk, cid, na="no", hard="no", warn="no", weak="no", rids=(), reason="", evs=(), agg="no", inputs=()):
    ck.append({"id": "CK%02d" % (len(ck) + 1), "business_id": bz, "market_id": mk, "check_id": cid, "inputs": list(inputs),
               "q_not_applicable": na, "q_aggregate_not_stored": agg, "q_hard": hard, "q_warn": warn, "q_weakened": weak,
               "refers_to": "无", "reading_ids": list(rids), "reason": reason, "evidence": list(evs)})


tiers = {int(x["key"]): int(x["value"]["fee_rate"]) for x in gc["fee_tiers"]["contents"]}
for mk, n, label, addr in POOL_LIST:
    p = pools[mk]
    ts, fr = int(p["tick_spacing"]), int(p["fee_rate"])
    check("BZ01", mk, "DX-C1.1", rids=[RID[mk + ".type"], RID[mk + ".tick_spacing"], RID[mk + ".fee_rate"]],
          reason="池类型的两种币与官方列表一致；tick 间距 %d 对应的费率档为 %d，池费率 %d%s；协议费记在池内字段，由协议费领取角色提取，没有单独的接收方可错绑" % (
              ts, tiers.get(ts, -1), fr, "，一致" if tiers.get(ts) == fr else "，不一致（费率档可在建池后被修改，不构成错绑）"),
          evs=[ev("pool-" + n), ev("globalconfig")])
    check("BZ01", mk, "DX-C2.1", rids=[RID[mk + ".fee_rate"], RID["config.protocol_fee_rate"]],
          reason="池费率 %d/1000000 不超过代码上限 MAX_FEE_RATE=200000；协议分成 %s/10000 不超过 MAX_PROTOCOL_FEE_RATE=3000" % (fr, gc["protocol_fee_rate"]),
          evs=[ev("pool-" + n), code("config.move", 32, 36)])
for mk, n, label, addr in POOL_LIST:
    check("BZ01", mk, "DX-C3.1",
          rids=[RID["config.package_version"], RID["config.df"], RID[mk + ".is_pause"], RID[mk + ".df"]],
          reason="全局：package_version=15 等于代码 VERSION，GlobalConfig 下没有紧急暂停标记；池级：is_pause=false，没有 pool_status 动态字段，"
                 "撤资、领费、兑换的开关都是打开的",
          evs=[ev("globalconfig"), ev("globalconfig-dynfields"), ev("pool-" + n), ev("pool-%s-dynfields" % n)])
w("O5-config.json", {"checks": ck})
n_o5 = len(ck)

for mk, n, label, addr in POOL_LIST:
    inputs = []
    for coin in ("a", "b"):
        g = "coin_" + coin
        inputs += [{"name": "due", "reading_id": RID["%s.due_%s" % (mk, coin)], "constant": "无", "divide_by": 1,
                    "note": "sui_read.py clmm-due 由 tick 表重建", "group": g},
                   {"name": "balance", "reading_id": RID["%s.coin_%s" % (mk, coin)], "constant": "无", "divide_by": 1,
                    "note": "池对象 coin_%s" % coin, "group": g},
                   {"name": "reserved", "reading_id": RID["%s.fee_protocol_coin_%s" % (mk, coin)], "constant": "无", "divide_by": 1,
                    "note": "协议费不属于 LP，pool.move:154-155", "group": g}]
    check("BZ01", mk, "DX-F1.1", hard="by_formula", warn="by_formula", inputs=inputs,
          rids=[x["reading_id"] for x in inputs],
          reason="两种币各一组：真实余额扣掉协议费后，和 tick 表重建的全部头寸本金应得比较（重建出的当前流动性与池子记录一致；应得不含未领手续费）",
          evs=[ev("due-" + n), ev("pool-" + n)])
for cid, why in [("DX-F2.1", "两种币都直接存在池对象的 coin_a、coin_b 余额里，没有外部资金组件"),
                 ("DX-D1.1", "撤资和领费只使用池内状态，不需要外部报价（专项补充说明：记 N/A）"),
                 ("DX-D2.2", "CLMM 池没有 Hook 或资产管理器等外部组件")]:
    check("BZ01", "ALL", cid, na="yes", reason=why, evs=[code("pool.move", 758, 843)])
w("O6-funds.json", {"checks": ck[n_o5:]})
w("O7-fatal.json", {"fatal": []})

# ---------------------------------------------------------------- O8
llama = json.load(open(os.path.join(HERE, "web", "defillama-cetus-amm.json")))
stats = {p["address"]: p for p in json.load(open(os.path.join(HERE, "web", "cetus-stats-pools.json")))["data"]["lp_list"]}
import datetime  # noqa: E402
lt = llama["tvl"][-1]
w("O8-tvl.json", {
    "tvl_available": "yes", "tvl_source": "defillama", "market_tvl_source": "official_dapp", "price_source": "无",
    "tvl_time_utc": datetime.datetime.fromtimestamp(lt["date"], datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "businesses": [{"business_id": "BZ01", "tvl_usd": round(llama["currentChainTvls"]["Sui"], 2),
                    "basis": "DefiLlama「Cetus CLMM」的 currentChainTvls.Sui（不含 Aptos 和 staking）", "reading_ids": [],
                    "evidence": [LLAMA_URL, "https://defillama.com/protocol/cetus-amm", "file:证据/web/defillama-cetus-amm.json"]}],
    "markets": [{"market_id": mk, "tvl_usd": round(float(stats[addr]["pure_tvl_in_usd"]), 2),
                 "basis": "Cetus 官方 stats_pools 接口的 pure_tvl_in_usd", "reading_ids": [],
                 "evidence": [STATS_URL, "file:证据/web/cetus-stats-pools.json"]} for mk, n, label, addr in POOL_LIST]})
print("已写入 T0–P5、O1–O8")
