import pytest,csv,io
from app.pipeline import load_sample
from app.modules.m1_accesses.rules import evaluate,decode
from app.config import COLUMNS
from app.errors import DomainError
def test_bom_real_sample(sample):
    "TRAP-02"
    r=evaluate(sample);assert r["metrics"]["encoding"]=="utf-8-sig" and r["rows"][0][COLUMNS[0]].startswith("00")
def test_legacy_encoding_real_sample():
    "TRAP-01"
    r=evaluate(load_sample("legacy.csv"));assert r["metrics"]["encoding"]=="gb18030" and r["metrics"]["accepted"]>=30
def test_bad_columns_real_sample(sample):
    "TRAP-05"
    assert any(r["reason"]=="BAD_COLUMNS" for r in evaluate(sample)["quarantine"])
def test_duplicate_conflict_real_sample(sample):
    "TRAP-14"
    assert any(r["reason"]=="DUPLICATE_CONFLICT" for r in evaluate(sample)["quarantine"])
def test_duplicate_conflict_keeps_basis(sample):
    "TRAP-14 冲突原行保留取舍依据：首条行号、差异字段、所属事件"
    r=evaluate(sample)
    q=[x for x in r["quarantine"] if x["reason"]=="DUPLICATE_CONFLICT"][0]
    assert q["conflict_of"]=="00001" and q["adopted_line"]==r["rows"][0]["_line"]
    assert "principal" in q["diff_fields"] and "以首条" in q["detail"]
def test_identifier_preserved_real_sample(sample):
    "TRAP-08"
    r=evaluate(sample)["rows"][0];assert r[COLUMNS[0]].startswith("00")
def test_three_empty_states():
    "TRAP-18"
    for raw,code in [(b"","EMPTY_FILE"),(b"\n\r\n","BLANK_ONLY"),((",".join(COLUMNS)+"\n").encode(),"HEADER_ONLY")]:
        with pytest.raises(DomainError) as e:evaluate(raw)
        assert e.value.code==code
def test_intake_conservation_real_sample(sample):
    r=evaluate(sample);m=r["metrics"]
    assert m["input"]==m["accepted"]+m["quarantine"]+m["duplicate"]+m["blank"]+m["repeated_headers"]
def test_quoted_newline_is_one_record(sample):
    "TRAP-03"
    r=evaluate(sample);assert any("\n" in str(x) for row in r["rows"] for x in row.values())
