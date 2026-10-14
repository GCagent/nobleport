from fastapi.testclient import TestClient
from app import app
client=TestClient(app)
def test_health():
    assert client.get("/healthz").json()["ok"] is True
def test_calculation():
    assert client.post("/v1/utilization/calculate",json={"cards":[{"balance":500,"limit":1000}]}).json()["aggregate"]==0.5
def test_paydown():
    x=client.post("/v1/utilization/simulate",json={"cards":[{"balance":900,"limit":1000},{"balance":100,"limit":1000}],"extra_payment":500}).json()
    assert x["after"]["per_card"][0]["util"]==0.4
def test_negative_block():
    assert client.post("/v1/utilization/calculate",json={"cards":[{"balance":-1,"limit":100}]}).status_code==422
def test_zero_limit_block():
    assert client.post("/v1/utilization/calculate",json={"cards":[{"balance":1,"limit":0}]}).status_code==422
def test_duplicate():
    a={"id":"a","creditor":"X","account_last4":"0000","opened":"2020"}
    b=dict(a,id="b")
    assert len(client.post("/v1/reports/analyze",json={"accounts":[a,b]}).json()["discrepancies"])==1
def test_not_mine():
    a={"id":"a","creditor":"X","account_last4":"0000","opened":"2020","consumer_statement":"not_mine"}
    assert len(client.post("/v1/reports/analyze",json={"accounts":[a]}).json()["discrepancies"])==1
def test_clean_report():
    assert client.post("/v1/reports/analyze",json={"accounts":[]}).json()["discrepancies"]==[]
def test_submission_blocked():
    assert client.post("/v1/disputes/submit").status_code==403
def test_draft_blocked():
    assert client.post("/v1/disputes/draft").status_code==409
