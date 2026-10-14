from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
app = FastAPI(title="NP-CREDIT-001", version="0.1.1")
class Card(BaseModel):
    balance: float = Field(ge=0, allow_inf_nan=False)
    limit: float = Field(gt=0, allow_inf_nan=False)
class Calc(BaseModel):
    cards: list[Card] = Field(max_length=100)
class Sim(Calc):
    extra_payment: float = Field(ge=0, allow_inf_nan=False)
class Account(BaseModel):
    id: str
    creditor: str
    account_last4: str
    opened: str
    consumer_statement: Literal["not_mine"] | None = None
class Report(BaseModel):
    accounts: list[Account] = Field(max_length=100)
def utilization(cards):
    b=sum(c.balance for c in cards); l=sum(c.limit for c in cards)
    return {"aggregate":round(b/l,4) if l else None,"per_card":[{"index":i,"util":round(c.balance/c.limit,4)} for i,c in enumerate(cards)]}
def simulate_paydown(cards, extra):
    work=[c.model_copy(deep=True) for c in cards]; remaining=extra
    for i in sorted(range(len(work)),key=lambda i:-(work[i].balance/work[i].limit)):
        paid=min(remaining,work[i].balance);work[i].balance-=paid;remaining-=paid
    return {"before":utilization(cards),"after":utilization(work),"applied":round(extra-remaining,2)}
@app.get("/healthz")
def health():
    return {"ok":True,"module":"NP-CREDIT-001","version":"0.1.1","mode":"synthetic-only"}
@app.post("/v1/utilization/calculate")
def calc(req:Calc):
    return utilization(req.cards)
@app.post("/v1/utilization/simulate")
def sim(req:Sim):
    return simulate_paydown(req.cards,req.extra_payment)
@app.post("/v1/reports/analyze")
def analyze(report:Report):
    seen=set();out=[]
    for a in report.accounts:
        key=(a.creditor,a.account_last4,a.opened)
        if key in seen:out.append({"account_ref":a.id,"kind":"possible_duplicate","rationale":"Matching fields; verify independently"})
        seen.add(key)
        if a.consumer_statement=="not_mine":out.append({"account_ref":a.id,"kind":"consumer_reported_not_mine","rationale":"Consumer assertion, not verified"})
    return {"discrepancies":out}
@app.post("/v1/disputes/draft")
def draft():
    raise HTTPException(409,"Drafting disabled pending identity, consent and legal review")
@app.post("/v1/disputes/submit")
def submit():
    raise HTTPException(403,"Automated dispute submission blocked pending legal approval")
