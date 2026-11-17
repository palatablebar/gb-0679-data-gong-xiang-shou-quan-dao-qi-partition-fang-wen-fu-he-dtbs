from decimal import Decimal
from app.reasons import sources,reject
from app.errors import DomainError
FACT_FIELDS=("principal","resource","partition","access_time","observed","reported")
def verdict(observed,expected):
    "按本事件唯一结论复核冲突原行的执行结果；越权放行与误拦截分别标识，互不抵消。"
    if observed=="allowed" and expected=="0": return "越权放行证据"
    if observed=="blocked" and expected=="1": return "误拦截证据"
    if observed in {"allowed","blocked"}: return "执行一致"
    return "执行结果无效"
def evaluate(rows,context):
    intake=context.get("intake")
    bad=context.get("quarantine",[])
    # 同一事件号只形成一条结论：首条为准，后到冲突行转入隔离留证（与采信同规则）
    seen={};unique=[];local=[]
    for row in rows:
        key=str(row.get("event_id",row.get("_line","")))
        if key in seen:
            first=seen[key]
            diff=[f for f in FACT_FIELDS if str(row.get(f,""))!=str(first.get(f,""))]
            local.append(reject(row,"DUPLICATE_CONFLICT",f"同键不同值：{','.join(diff) or '派生字段'} 与首条不一致；结论以首条为准，本行留证",conflict_of=key,adopted_line=first.get("_line"),diff_fields=diff))
            continue
        seen[key]=row;unique.append(row)
    accepted=set(x for row in unique for x in sources(row))
    rejected=set(x for row in bad for x in sources(row))|set(x for row in local for x in sources(row))
    if accepted & rejected: raise DomainError("LINEAGE_OVERLAP","同一来源行被重复裁决")
    m={"accepted_inputs":len(accepted),"quarantine_inputs":len(rejected),"output_records":len(unique)}
    if intake:
        excluded=intake["duplicate"]+intake["blank"]+intake["repeated_headers"]
        m.update(input=intake["input"],excluded=excluded,balanced=intake["input"]==len(accepted)+len(rejected)+excluded)
    else:m.update(input=len(accepted)+len(rejected),excluded=0,balanced=True)
    output=[]
    for row in unique:
        expected=Decimal(str(row.get("expected","0")));reported=Decimal(str(row.get("reported","0")))
        output.append({**row,"difference":str(expected-reported),"status":"通过" if expected==reported else "差异"})
    conclusions={str(r.get("event_id",r.get("_line",""))):r for r in output}
    # 冲突原行逐条挂到本事件唯一结论下复核；页面与证据导出共用同一份conflict_review
    review=[]
    for q in [x for x in bad if x.get("reason")=="DUPLICATE_CONFLICT"]+local:
        key=str(q.get("conflict_of",q.get("event_id","")))
        target=conclusions.get(key)
        basis=f"以首条(行{q.get('adopted_line','—')})为准形成唯一结论，本行仅留证"
        entry={"event_id":key,"adopted_line":q.get("adopted_line"),"line":q.get("_line"),"sources":sources(q),"principal":q.get("principal"),"observed":q.get("observed"),"diff_fields":q.get("diff_fields",[]),"basis":basis}
        if target is None:
            entry.update(verdict="无对应结论",basis="首条未进入对账，冲突行保持隔离待核")
        else:
            entry["verdict"]=verdict(q.get("observed"),str(target.get("expected","0")))
            target.setdefault("conflict_evidence",[]).append(entry)
        review.append(entry)
    for row in output: row["conflict_count"]=len(row.get("conflict_evidence",[]))
    m.update(expected_total=str(sum((Decimal(str(r.get("expected","0"))) for r in unique),Decimal(0))),reported_total=str(sum((Decimal(str(r.get("reported","0"))) for r in unique),Decimal(0))),differences=sum(r["status"]=="差异" for r in output),violations=sum(r.get("violation")=="越权放行" for r in output),false_blocks=sum(r.get("violation")=="误拦截" for r in output),conflict_groups=sum(1 for r in output if r["conflict_count"]),conflict_rows=sum(r["conflict_count"] for r in output),conflict_overperm=sum(1 for e in review if e["verdict"]=="越权放行证据"),conflict_false_block=sum(1 for e in review if e["verdict"]=="误拦截证据"))
    return {"rows":output,"quarantine":local,"conflict_review":review,"metrics":m}
