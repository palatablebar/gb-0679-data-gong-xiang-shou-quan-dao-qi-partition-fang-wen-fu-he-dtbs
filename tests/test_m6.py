from app.modules.m6_audit.rules import evaluate
from decimal import Decimal
def test_real_sample_four_books(result): assert result["stages"][5]["metrics"]["balanced"] is True
def test_real_sample_final_lineage(result):
    m=result["stages"][5]["metrics"];assert m["accepted_inputs"]+m["quarantine_inputs"]+m["excluded"]==m["input"]
def test_real_sample_difference_is_explicit(result):
    rows=result["stages"][5]["rows"];assert any(r["status"]=="差异" for r in rows)
def test_real_sample_totals_exact(result):
    rows=result["stages"][5]["rows"];m=result["stages"][5]["metrics"]
    assert sum((Decimal(r["difference"]) for r in rows),Decimal(0))==Decimal(m["expected_total"])-Decimal(m["reported_total"])
def test_empty_reconcile():
    r=evaluate([],{});assert r["metrics"]["balanced"] is True and r["metrics"]["expected_total"]=="0"
def test_overlap_is_rejected():
    import pytest
    from app.errors import DomainError
    with pytest.raises(DomainError):evaluate([{"_line":1}],{"quarantine":[{"_line":1}]})
def test_real_sample_rejected_have_reason(result):
    assert all(r["reason"] and r["detail"] for r in result["stages"][5]["cumulative_quarantine"])
def test_unique_conclusion_per_event(result):
    "每个事件号只有一条对账结论"
    ids=[r["event_id"] for r in result["stages"][5]["rows"]]
    assert len(ids)==len(set(ids))
def test_conflict_evidence_attached_with_basis(result):
    "冲突原行挂到唯一结论下，保留差异字段与取舍依据"
    row=[r for r in result["stages"][5]["rows"] if r["event_id"]=="00001"][0]
    evidence=row["conflict_evidence"]
    assert row["conflict_count"]==1 and len(evidence)==1
    assert "principal" in evidence[0]["diff_fields"] and evidence[0]["basis"]
    assert evidence[0]["verdict"]=="越权放行证据"
def test_conflict_review_shared_with_export(result):
    "页面与证据导出共用同一份conflict_review"
    review=result["stages"][5]["conflict_review"]
    assert len(review)==1 and review[0]["event_id"]=="00001" and review[0]["verdict"]=="越权放行证据"
    assert result["stages"][6]["conflict_review"]==review
def test_violations_kept_separate_not_netted(result):
    "越权放行与误拦截分别计数，互不抵消"
    m=result["stages"][5]["metrics"]
    assert m["violations"]==16 and m["false_blocks"]==0
    assert m["conflict_rows"]==1 and m["conflict_overperm"]==1 and m["conflict_false_block"]==0
def test_audit_first_wins_and_keeps_conflict():
    "对账阶段自身也按首条定事实，后到冲突行留证"
    rows=[{"event_id":"E1","_line":1,"expected":"1","reported":"1","observed":"allowed","principal":"a"},
          {"event_id":"E1","_line":2,"expected":"1","reported":"0","observed":"blocked","principal":"b"}]
    r=evaluate(rows,{})
    assert len(r["rows"])==1 and r["rows"][0]["status"]=="通过"
    assert r["quarantine"][0]["reason"]=="DUPLICATE_CONFLICT" and r["quarantine"][0]["conflict_of"]=="E1"
    assert r["rows"][0]["conflict_evidence"][0]["verdict"]=="误拦截证据"
    assert r["metrics"]["accepted_inputs"]==1 and r["metrics"]["quarantine_inputs"]==1
def test_conflict_without_conclusion_stays_quarantined():
    "首条未进入对账时，冲突行保持隔离待核且不伪造结论"
    rows=[{"event_id":"E2","_line":5,"expected":"0","reported":"0","observed":"blocked","principal":"a"}]
    context={"quarantine":[{"event_id":"E2","_line":9,"reason":"DUPLICATE_CONFLICT","detail":"同键不同值","conflict_of":"E2","adopted_line":4,"diff_fields":["observed"],"observed":"allowed","principal":"a","_sources":[9]}]}
    r=evaluate(rows,context)
    assert r["conflict_review"][0]["verdict"]=="越权放行证据"
    orphan=[{"event_id":"E3","_line":10,"reason":"DUPLICATE_CONFLICT","detail":"同键不同值","conflict_of":"E3","adopted_line":6,"diff_fields":[],"observed":"allowed","_sources":[10]}]
    r2=evaluate(rows,{"quarantine":orphan})
    assert r2["conflict_review"][0]["verdict"]=="无对应结论"
