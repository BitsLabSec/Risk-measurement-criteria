import base64,hashlib,json,glob
def uleb(b,i):
    r=s=0
    while True:
        x=b[i]; i+=1; r|=(x&0x7f)<<s; s+=7
        if x<0x80: return r,i
def decode(sigb64):
    b=base64.b64decode(sigb64); assert b[0]==3,"not multisig"
    i=1; n,i=uleb(b,i)
    for _ in range(n):
        v=b[i]; i+=1
        if v in (0,1,2): i+=64
        else: l,i=uleb(b,i); i+=l
    bitmap=int.from_bytes(b[i:i+2],"little"); i+=2
    m,i=uleb(b,i); members=[]; raw=b""
    for _ in range(m):
        f=b[i]; i+=1
        if f==0: pk=b[i:i+32]; i+=32
        elif f in (1,2,4): pk=b[i:i+33]; i+=33
        else:
            l,i=uleb(b,i); pk=b[i:i+l]; i+=l   # zklogin: simplified
        w=b[i]; i+=1
        addr="0x"+hashlib.blake2b(bytes([f])+pk,digest_size=32).hexdigest()
        members.append({"scheme":{0:"ed25519",1:"secp256k1",2:"secp256r1",3:"zklogin",4:"passkey"}[f],"address":addr,"weight":w})
        raw+=bytes([f])+pk+bytes([w])
    thr=int.from_bytes(b[i:i+2],"little")
    msaddr="0x"+hashlib.blake2b(bytes([3])+thr.to_bytes(2,"little")+raw,digest_size=32).hexdigest()
    return {"threshold":thr,"members":members,"derived_address":msaddr}
if __name__=="__main__":
    for f in sorted(glob.glob("raw/lasttx-*.json")):
        d=json.load(open(f))["response"]["data"]["transactions"]["nodes"][0]
        r=decode(d["signatures"][0]["signatureBytes"]); r["digest"]=d["digest"]
        print(f, json.dumps(r,indent=1))
