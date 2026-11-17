import csv,io
from app.pipeline import execute,load_sample
from app import store
def test_full_sample_flow(client):
    r=client.post("/api/runs",json={"sample":"dirty.csv"});assert r.status_code==200
    p=r.get_json();assert len(p["stages"])==7
    assert p["stages"][5]["metrics"]["balanced"] is True
def test_idempotent_real_input(sample):
    a=execute(sample);b=execute(sample)
    assert a["run_id"]==b["run_id"] and len(store.history())==1
def test_stale_review_409(client):
    "TRAP-26 陈旧复核不得覆盖新版本"
    p=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json();u="/api/runs/"+p["run_id"]+"/review"
    assert client.post(u,json={"version":1,"decision":"已复核"}).status_code==200
    assert client.post(u,json={"version":1,"decision":"退回复核"}).status_code==409
def test_export_has_manifest_and_quarantine(client):
    p=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json()
    r=client.get("/api/runs/"+p["run_id"]+"/archive")
    rows=list(csv.reader(io.StringIO(r.data.decode("utf-8-sig"))))
    assert rows[0][1]=="input_sha256" and any(x[3]=="quarantine" for x in rows[1:])
def test_failed_import_is_atomic(client):
    assert client.post("/api/runs",json={"csv":"bad"}).status_code==422
    assert store.history()==[]
def test_export_conflict_lines_follow_conclusion(client):
    "证据导出与页面服从同一结论：冲突行单独成行并带取舍依据"
    p=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json()
    rows=list(csv.reader(io.StringIO(client.get("/api/runs/"+p["run_id"]+"/archive").data.decode("utf-8-sig"))))
    import json
    conflict=[x for x in rows[1:] if x[3]=="conflict"]
    assert len(conflict)==1 and conflict[0][5]=="越权放行证据"
    evidence=json.loads(conflict[0][6])
    assert evidence["conflict_of"]=="00001" and evidence["review"]["basis"]
    accepted=[x for x in rows[1:] if x[3]=="accepted"]
    assert len({json.loads(x[6])["event_id"] for x in accepted})==len(accepted)
def test_export_violations_per_record_not_netted(client):
    "越权放行逐条成行，不用总数抵消"
    p=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json()
    rows=list(csv.reader(io.StringIO(client.get("/api/runs/"+p["run_id"]+"/archive").data.decode("utf-8-sig"))))
    overperm=[x for x in rows[1:] if x[3]=="accepted" and x[5]=="越权放行"]
    false_block=[x for x in rows[1:] if x[3]=="accepted" and x[5]=="误拦截"]
    assert len(overperm)==16 and len(false_block)==0
def test_rerun_same_input_adds_no_records(client):
    assert client.post("/api/runs",json={"sample":"dirty.csv"}).status_code==200
    assert client.post("/api/runs",json={"sample":"dirty.csv"}).status_code==200
    assert len(store.history())==1
def test_failed_switch_keeps_previous_run(client):
    "切换失败后仍保留旧版"
    p=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json()
    assert client.post("/api/runs",json={"csv":"bad"}).status_code==422
    assert client.post("/api/runs",json={"sample":"missing.csv"}).status_code==404
    assert [r["run_id"] for r in store.history()]==[p["run_id"]]
    assert store.latest()["run_id"]==p["run_id"]
def test_failed_review_keeps_version(client):
    "失效版本复核返回409且不改变现状"
    p=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json()
    u="/api/runs/"+p["run_id"]+"/review"
    assert client.post(u,json={"version":1,"decision":"已复核"}).status_code==200
    assert client.post(u,json={"version":1,"decision":"退回复核"}).status_code==409
    after=client.get("/api/runs/"+p["run_id"]).get_json()
    assert after["version"]==2 and after["decision"]=="已复核"
def test_module_entrances(client):
    from app.config import MODULES
    for slug,name in MODULES:
        assert client.get("/api/"+slug).status_code==200
        assert client.get("/"+slug).status_code==200
def test_missing_run_404(client): assert client.get("/api/runs/missing").status_code==404
