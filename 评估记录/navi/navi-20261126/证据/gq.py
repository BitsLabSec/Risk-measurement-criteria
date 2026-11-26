import json,sys,urllib.request,hashlib,os
G="https://graphql.mainnet.sui.io/graphql"
RAW=os.path.join(os.path.dirname(os.path.abspath(__file__)),"raw")
def q(query, variables=None, save=None):
    body=json.dumps({"query":query,"variables":variables or {}}).encode()
    req=urllib.request.Request(G,data=body,headers={"Content-Type":"application/json"})
    out=json.load(urllib.request.urlopen(req,timeout=60))
    if save:
        json.dump({"query":query,"variables":variables,"response":out},open(os.path.join(RAW,save+".json"),"w"),ensure_ascii=False,indent=1)
    if "errors" in out: print("ERR",json.dumps(out["errors"])[:500],file=sys.stderr)
    return out.get("data")
