# -*- coding: utf-8 -*-
"""人工复核记录和重评索引。

- 复核：开发对齐阶段，每一步的中间产物都由人看过。复核时记下文件的 sha256，文件之后被改过，复核就自动标为过期。
- 重评：每次评估一个目录，目录名就是评估 ID；旧目录不改。`history` 扫描项目目录，生成评估索引。
"""
import datetime
import hashlib
import json
import os

STEP_FILES = {
    "T0": ["T0-task.json"], "P1": ["P1-baseline.json"], "P2": ["P2-sources.json"],
    "P3": ["P3-business-modules.json"], "P4": ["P4-responsibilities.json"], "P5": ["P5-roles-controls.json"],
    "P6": ["P6-graph.md"], "gaps": ["gaps.json"],
    "C1": ["C1-lines.json"], "C2": ["C2-reports.json"], "C3": ["C3-semantic-changes.json", "C3-coverage.json"],
    "C4": ["C4-findings.json"], "C5": ["C5-overall.json"], "C6": ["C6-score.json", "C6-score.md"],
    "O1": ["O1-scope.json"], "O2": ["O2-targets.json"], "O3": ["O3-readings.json"],
    "O4": ["O4-permissions.json", "O4-role-graph.md"], "O5": ["O5-config.json"], "O6": ["O6-funds.json"],
    "O7": ["O7-fatal.json"], "O8": ["O8-tvl.json", "O8-score.json", "O8-score.md"],
    "export": ["deliverable.json"],
}
VERDICTS = {"pass": "通过", "needs_fix": "需修改"}


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load(d):
    p = os.path.join(d, "reviews.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {"reviews": []}


def save(d, data):
    with open(os.path.join(d, "reviews.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def add_review(d, step, reviewer, verdict, comments):
    if step not in STEP_FILES:
        raise SystemExit("步骤只能是 %s" % ", ".join(STEP_FILES))
    if verdict not in VERDICTS:
        raise SystemExit("--verdict 只能是 pass 或 needs_fix")
    if not reviewer:
        raise SystemExit("要用 --reviewer 写复核人")
    if verdict == "needs_fix" and not comments:
        raise SystemExit("需修改时至少写一条 --comment")
    files = {}
    for n in STEP_FILES[step]:
        p = os.path.join(d, n)
        if os.path.exists(p):
            files[n] = sha(p)
    if not files:
        raise SystemExit("这一步还没有产出文件，不能复核")
    data = load(d)
    rid = "RV%02d" % (len(data["reviews"]) + 1)
    data["reviews"].append({"id": rid, "step": step, "files": files, "reviewer": reviewer, "time_utc": now(),
                            "verdict": verdict, "comments": comments})
    save(d, data)
    print("已记录复核 %s：%s %s（%s）" % (rid, step, VERDICTS[verdict], reviewer))


def status_rows(d):
    data = load(d)
    rows = []
    for step, names in STEP_FILES.items():
        present = [n for n in names if os.path.exists(os.path.join(d, n))]
        if not present:
            continue
        mine = [r for r in data["reviews"] if r["step"] == step]
        if not mine:
            rows.append((step, "未复核", "", "", []))
            continue
        last = mine[-1]
        stale = any(sha(os.path.join(d, n)) != last["files"].get(n) for n in present)
        state = "已过期（复核后文件改过）" if stale else VERDICTS[last["verdict"]]
        rows.append((step, state, last["reviewer"], last["time_utc"], last["comments"] if last["verdict"] == "needs_fix" else []))
    return rows


def print_status(d):
    rows = status_rows(d)
    print("| 步骤 | 复核状态 | 复核人 | 时间 | 待改意见 |")
    print("| --- | --- | --- | --- | --- |")
    for step, state, who, t, cm in rows:
        print("| %s | %s | %s | %s | %s |" % (step, state, who, t, "；".join(cm)))
    todo = [r for r in rows if r[1] != "通过"]
    print("\n共 %d 步有产出，%d 步还没有通过复核。" % (len(rows), len(todo)))


def history(project_dir):
    """扫描项目目录下的每个评估目录，生成 index.json 和 index.md。"""
    items = []
    for name in sorted(os.listdir(project_dir)):
        d = os.path.join(project_dir, name)
        t0p = os.path.join(d, "T0-task.json")
        if not os.path.isfile(t0p):
            continue
        with open(t0p, encoding="utf-8") as f:
            t0 = json.load(f)
        item = {"assessmentId": t0.get("assessment_id"), "directory": name, "date": t0.get("date"),
                "previousAssessmentId": t0.get("previous_assessment_id"), "reason": t0.get("reason"),
                "dimensions": {}, "snapshots": [], "ruleVersions": None, "deliverable": None}
        dp = os.path.join(d, "deliverable.json")
        if os.path.isfile(dp):
            with open(dp, encoding="utf-8") as f:
                doc = json.load(f)
            item["deliverable"] = "%s/deliverable.json" % name
            item["ruleVersions"] = doc.get("ruleVersions")
            item["snapshots"] = doc.get("snapshots", [])
            for c in doc["tree"]["children"]:
                item["dimensions"][c["id"]] = {"status": c["status"], "score": c["score"]}
        items.append(item)
    ids = {x["assessmentId"] for x in items}
    problems = []
    for x in items:
        if x["directory"] != x["assessmentId"]:
            problems.append("目录 %s 和评估 ID %s 不一致" % (x["directory"], x["assessmentId"]))
        p = x["previousAssessmentId"]
        if p not in (None, "无") and p not in ids:
            problems.append("%s 指向的上一次评估 %s 不在这个项目目录里" % (x["assessmentId"], p))
    with open(os.path.join(project_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"generatedAt": now(), "assessments": items, "problems": problems}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    dims = ["code_security", "onchain"]
    md = ["# 评估记录索引（脚本生成，不要手改）", "",
          "| 评估 ID | 日期 | 原因 | 上一次 | 代码安全 | 链上 | 交付物 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for x in items:
        cells = []
        for k in dims:
            v = x["dimensions"].get(k)
            cells.append("—" if not v else ("%.2f" % v["score"] if v["score"] is not None else v["status"]))
        md.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            x["assessmentId"], x["date"], x["reason"], x["previousAssessmentId"], cells[0], cells[1],
            "[deliverable.json](./%s)" % x["deliverable"] if x["deliverable"] else "未导出"))
    if problems:
        md += ["", "**问题：**"] + ["- " + p for p in problems]
    with open(os.path.join(project_dir, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("已写入 index.json、index.md（%d 次评估）" % len(items))
    for p in problems:
        print("  - " + p)
