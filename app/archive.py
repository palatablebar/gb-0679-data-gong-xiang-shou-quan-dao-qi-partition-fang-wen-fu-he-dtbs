import csv,io,json
def build_archive(run):
    stream=io.StringIO(newline="");writer=csv.writer(stream)
    writer.writerow(["run_id","input_sha256","rule_version","kind","source_lines","reason","evidence"])
    meta=run["manifest"];final=run["stages"][-1]
    review={(str(e.get("event_id")),e.get("line")):e for e in final.get("conflict_review",[])}
    for row in final["rows"]:
        # 越权放行与误拦截逐条成行，reason直接给出执行差异，不用总数抵消
        reason=row.get("violation") if row.get("violation") not in (None,"一致") else row.get("status","")
        writer.writerow([run["run_id"],meta["input_sha256"],meta["rule_version"],"accepted",json.dumps(row.get("_sources",[])),reason,json.dumps(row,ensure_ascii=False)])
    for row in final.get("cumulative_quarantine",[]):
        kind="conflict" if row.get("reason")=="DUPLICATE_CONFLICT" else "quarantine"
        reason=row.get("reason","");evidence=row
        if kind=="conflict":
            entry=review.get((str(row.get("conflict_of",row.get("event_id",""))),row.get("_line")))
            if entry: reason=entry["verdict"];evidence={**row,"review":entry}
        writer.writerow([run["run_id"],meta["input_sha256"],meta["rule_version"],kind,json.dumps(row.get("_sources",[])),reason,json.dumps(evidence,ensure_ascii=False)])
    return "﻿"+stream.getvalue()
