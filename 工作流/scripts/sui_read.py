#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sui 链上读取工具（基于 Sui GraphQL，公共 JSON-RPC 已停用）。

每次读取都把查询和完整响应存到 <评估目录>/证据/raw/<名字>.json，
并打印可以直接填进 evidence 的引用：file:证据/raw/<名字>.json

用法（<目录> 是评估目录，--at 是快照检查点号）：
  python3 sui_read.py <目录> checkpoint                                  最新检查点（定快照用）
  python3 sui_read.py <目录> object <对象ID> --at <检查点> [--name 名字]   读对象：持有人、类型、全部字段
  python3 sui_read.py <目录> table <表或对象ID> --at <检查点> [--name 名字] 读表或动态字段的全部条目（表不是对象，不能用 object 读）
  python3 sui_read.py <目录> by-type <完整类型> --at <检查点> [--name 名字] 按类型找对象（用于找权限凭证），类型写定义它的包 ID
  python3 sui_read.py <目录> package <原始包ID> [--name 名字]             包的全部版本
  python3 sui_read.py <目录> msig <地址> [--name 名字]                    定向读该地址发出的最近一笔交易，解出多签成员和门限

不扫描历史交易：msig 只读一笔交易；by-type 只按凭证类型查询，不枚举用户。
"""
import base64
import hashlib
import json
import os
import sys
import urllib.request

ENDPOINT = os.environ.get("SUI_GRAPHQL", "https://graphql.mainnet.sui.io/graphql")

Q_OBJECT = """query($a:SuiAddress!,$c:UInt53){ object(address:$a, atCheckpoint:$c){ address version
  owner{ __typename ... on AddressOwner{ address{ address } } ... on ObjectOwner{ address{ address } } }
  asMoveObject{ contents{ type{ repr } json } } } }"""
Q_TABLE = """query($a:SuiAddress!,$c:UInt53,$after:String){ address(address:$a, atCheckpoint:$c){
  dynamicFields(first:50, after:$after){ pageInfo{ hasNextPage endCursor }
  nodes{ name{ json type{ repr } } value{ __typename ... on MoveValue{ json type{ repr } } ... on MoveObject{ address contents{ json type{ repr } } } } } } } }"""
Q_BYTYPE = """query($t:String!,$c:UInt53!){ checkpoint(sequenceNumber:$c){ query{ objects(filter:{type:$t}, first:50){
  nodes{ address version owner{ __typename ... on AddressOwner{ address{ address } } ... on ObjectOwner{ address{ address } } } } } } } }"""
Q_PACKAGE = """query($a:SuiAddress!){ packageVersions(address:$a, first:50){ nodes{ address version previousTransaction{ digest } } } }"""
Q_LASTTX = """query($a:SuiAddress!){ transactions(filter:{sentAddress:$a}, last:1){ nodes{ digest signatures{ signatureBytes }
  effects{ timestamp checkpoint{ sequenceNumber } } } } }"""


def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={"Content-Type": "application/json"})
    out = json.load(urllib.request.urlopen(req, timeout=60))
    if out.get("errors"):
        raise SystemExit("GraphQL 报错：%s" % json.dumps(out["errors"], ensure_ascii=False)[:500])
    return out["data"]


def save(d, name, query, variables, data):
    raw = os.path.join(d, "证据", "raw")
    os.makedirs(raw, exist_ok=True)
    with open(os.path.join(raw, name + ".json"), "w", encoding="utf-8") as f:
        json.dump({"endpoint": ENDPOINT, "query": query, "variables": variables, "response": {"data": data}},
                  f, ensure_ascii=False, indent=1)
    return "file:证据/raw/%s.json" % name


def _uleb(b, i):
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        s += 7
        if x < 0x80:
            return r, i


SCHEMES = {0: "ed25519", 1: "secp256k1", 2: "secp256r1", 3: "zklogin", 4: "passkey"}


def decode_multisig(sig_b64):
    """解析 Sui MultiSig 签名，返回成员地址、权重、门限，以及由公钥推回的多签地址。"""
    b = base64.b64decode(sig_b64)
    if b[0] != 3:
        return None
    i = 1
    n, i = _uleb(b, i)
    for _ in range(n):
        v = b[i]
        i += 1
        if v in (0, 1, 2):
            i += 64
        else:
            ln, i = _uleb(b, i)
            i += ln
    i += 2  # bitmap
    m, i = _uleb(b, i)
    members, raw = [], b""
    for _ in range(m):
        f = b[i]
        i += 1
        if f == 0:
            pk = b[i:i + 32]
            i += 32
        elif f in (1, 2, 4):
            pk = b[i:i + 33]
            i += 33
        else:
            ln, i = _uleb(b, i)
            pk = b[i:i + ln]
            i += ln
        w = b[i]
        i += 1
        members.append({"scheme": SCHEMES.get(f, str(f)), "address": "0x" + hashlib.blake2b(bytes([f]) + pk, digest_size=32).hexdigest(),
                        "weight": w})
        raw += bytes([f]) + pk + bytes([w])
    thr = int.from_bytes(b[i:i + 2], "little")
    derived = "0x" + hashlib.blake2b(bytes([3]) + thr.to_bytes(2, "little") + raw, digest_size=32).hexdigest()
    return {"threshold": thr, "members": members, "derived_address": derived}


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    d, cmd = a[0], a[1]
    opt = lambda k: a[a.index(k) + 1] if k in a else None  # noqa: E731
    at = int(opt("--at")) if opt("--at") else None
    name = opt("--name")
    if cmd == "checkpoint":
        q = "{ checkpoint { sequenceNumber digest timestamp } }"
        data = gql(q, {})
        ref = save(d, name or "snapshot", q, {}, data)
        print(json.dumps(data["checkpoint"], ensure_ascii=False))
    elif cmd == "object":
        v = {"a": a[2], "c": at}
        data = gql(Q_OBJECT, v)
        ref = save(d, name or "object-" + a[2][:10], Q_OBJECT, v, data)
        print(json.dumps(data["object"], ensure_ascii=False, indent=1)[:3000])
        if data["object"] is None:
            print("读不到对象。如果这是表（Table）或动态字段的 ID，改用 table 命令。")
    elif cmd == "table":
        nodes, after = [], None
        while True:
            v = {"a": a[2], "c": at, "after": after}
            data = gql(Q_TABLE, v)
            df = data["address"]["dynamicFields"]
            nodes += df["nodes"]
            if not df["pageInfo"]["hasNextPage"]:
                break
            after = df["pageInfo"]["endCursor"]
        ref = save(d, name or "table-" + a[2][:10], Q_TABLE, {"a": a[2], "c": at}, {"address": {"dynamicFields": {"nodes": nodes}}})
        print("共 %d 个条目（一次读取，算 1 个取证目标）" % len(nodes))
    elif cmd == "by-type":
        v = {"t": a[2], "c": at}
        data = gql(Q_BYTYPE, v)
        ref = save(d, name or "bytype-" + a[2].split("::")[-1], Q_BYTYPE, v, data)
        for x in data["checkpoint"]["query"]["objects"]["nodes"]:
            o = x["owner"]
            print(x["address"], o.get("__typename"), (o.get("address") or {}).get("address", ""))
    elif cmd == "package":
        v = {"a": a[2]}
        data = gql(Q_PACKAGE, v)
        ref = save(d, name or "package-" + a[2][:10], Q_PACKAGE, v, data)
        for x in data["packageVersions"]["nodes"]:
            print(x["version"], x["address"])
    elif cmd == "msig":
        v = {"a": a[2]}
        data = gql(Q_LASTTX, v)
        nodes = data["transactions"]["nodes"]
        if not nodes:
            raise SystemExit("这个地址没有发出过交易，解不出成员：按单签登记，并在 gaps.json 登记")
        res = decode_multisig(nodes[0]["signatures"][0]["signatureBytes"])
        if res is None:
            print("最近一笔交易不是多签签名：这个地址是单个密钥（eoa）")
        else:
            res["matches_address"] = res["derived_address"] == a[2].lower()
            res["digest"] = nodes[0]["digest"]
            data["decoded"] = res
            print(json.dumps(res, ensure_ascii=False, indent=1))
            if not res["matches_address"]:
                print("警告：由公钥推回的地址和目标地址不一致，不要采用，交人处理")
        ref = save(d, name or "msig-" + a[2][:10], Q_LASTTX, v, data)
    else:
        raise SystemExit(__doc__)
    print("证据引用：" + ref)


if __name__ == "__main__":
    main()
