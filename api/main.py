"""
Noble Port Realty API Backend
Python FastAPI implementation for blockchain real estate platform

This API provides endpoints for:
- Property management and tokenization
- Investor KYC/AML verification
- Token transactions and portfolio tracking
- Compliance reporting and audit trails
- Multi-chain blockchain integration
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import uuid

# Initialize FastAPI app
app = FastAPI(
    title="Noble Port Realty API",
    description="Institutional-grade tokenized real estate platform with embedded compliance",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums

class PropertyType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    DEVELOPMENT = "development"
    MIXED_USE = "mixed_use"

class InvestorStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    ACCREDITED = "accredited"
    REJECTED = "rejected"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"

class BlockchainNetwork(str, Enum):
    SOLANA = "solana"
    ETHEREUM = "ethereum"
    ARBITRUM = "arbitrum"
    POLYGON = "polygon"
    AVALANCHE = "avalanche"
    CARDANO = "cardano"
    BNB_CHAIN = "bnb_chain"
    OPTIMISM = "optimism"
    BASE = "base"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"

class PlanType(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"

# Data Models

class Property(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    property_type: PropertyType
    location: str
    address: str
    description: str
    total_value: float
    token_symbol: str
    total_tokens: int
    available_tokens: int
    price_per_token: float
    projected_annual_return: float
    minimum_ownership_percentage: float
    images: List[str] = []
    documents: List[str] = []
    llc_entity: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

class Investor(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    full_name: str
    wallet_address: str
    investor_status: InvestorStatus
    is_accredited: bool = False
    kyc_verification_hash: Optional[str] = None
    investor_pass_issued: bool = False
    investor_pass_issued_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class KYCVerification(BaseModel):
    investor_id: str
    full_name: str
    date_of_birth: str
    ssn_last_four: str
    address: str
    identity_document_type: str
    identity_document_number: str
    identity_document_image: str
    proof_of_address_image: str
    accreditation_proof: Optional[str] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)

class TokenTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    property_id: str
    buyer_id: str
    seller_id: Optional[str] = None
    token_amount: int
    price_per_token: float
    total_price: float
    payment_currency: str = "USDC"
    blockchain_network: BlockchainNetwork
    transaction_hash: Optional[str] = None
    status: TransactionStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_at: Optional[datetime] = None

class Portfolio(BaseModel):
    investor_id: str
    holdings: List[Dict[str, Any]] = []
    total_value: float = 0.0
    total_tokens: int = 0
    properties_count: int = 0

class Student(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str
    grade_level: str
    subjects: List[str]
    weak_areas: List[str] = []
    learning_speed: str = "standard"
    current_plan: str = "math_k3_mastery_track"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Skill(BaseModel):
    id: str
    subject: str
    grade_band: str
    name: str

class Item(BaseModel):
    id: str
    skill_id: str
    prompt: str
    answer: str
    difficulty: int = 1
    version: int = 1

class LearningAttempt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    item_id: str
    skill_id: str
    is_correct: bool
    submitted_answer: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MasteryState(BaseModel):
    student_id: str
    skill_id: str
    p_mastered: float = 0.2
    streak: int = 0
    spaced_successes: int = 0
    last_attempt_at: Optional[datetime] = None
    recent_verification_passed: bool = False
    capstone_passed: bool = False

class CertificateAward(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    name: str = "NoblePort Certificate of Mastery"
    skill_ids: List[str]
    attempt_ids: List[str]
    mastery_snapshot: Dict[str, float]
    item_versions: Dict[str, int]
    evidence_hash: str
    audit_chain_seq: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CheckoutRequest(BaseModel):
    parent_id: str

class WebhookRequest(BaseModel):
    parent_id: str
    subscription_status: SubscriptionStatus

class AttemptRequest(BaseModel):
    student_id: str
    item_id: str
    submitted_answer: str

class CertificateEvaluateRequest(BaseModel):
    student_id: str

# In-memory storage (replace with PostgreSQL in production)
properties_db: Dict[str, Property] = {}
investors_db: Dict[str, Investor] = {}
transactions_db: Dict[str, TokenTransaction] = {}
subscriptions_db: Dict[str, Dict[str, Any]] = {}
students_db: Dict[str, Student] = {}
skills_db: Dict[str, Skill] = {}
items_db: Dict[str, Item] = {}
attempts_db: Dict[str, LearningAttempt] = {}
mastery_db: Dict[str, MasteryState] = {}
certificate_db: Dict[str, List[CertificateAward]] = {}
audit_log_db: Dict[str, List[Dict[str, Any]]] = {}
daily_log_db: Dict[str, str] = {}

def _audit(student_id: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    chain = audit_log_db.setdefault(student_id, [])
    previous_hash = chain[-1]["hash"] if chain else "GENESIS"
    seq = len(chain) + 1
    data = f"{student_id}|{seq}|{action}|{payload}|{previous_hash}"
    current_hash = hashlib.sha256(data.encode()).hexdigest()
    event = {"seq": seq, "action": action, "payload": payload, "previous_hash": previous_hash, "hash": current_hash, "at": datetime.utcnow()}
    chain.append(event)
    return event

def _require_paid(parent_id: str):
    sub = subscriptions_db.get(parent_id)
    if not sub or sub["status"] not in {SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value}:
        raise HTTPException(status_code=402, detail="Active payment required")

def _daily_log_key(student_id: str) -> str:
    return f"{student_id}:{datetime.utcnow().date().isoformat()}"

def _seed_learning_content():
    if skills_db:
        return
    skills = [
        Skill(id="math-k-1-addition", subject="math", grade_band="K-1", name="Addition Foundations"),
        Skill(id="math-1-2-subtraction", subject="math", grade_band="1-2", name="Subtraction Foundations"),
        Skill(id="math-2-3-multiplication", subject="math", grade_band="2-3", name="Multiplication Basics"),
    ]
    for s in skills:
        skills_db[s.id] = s
    seeded_items = [
        Item(id="item-1", skill_id="math-k-1-addition", prompt="2 + 3 = ?", answer="5"),
        Item(id="item-2", skill_id="math-k-1-addition", prompt="4 + 1 = ?", answer="5"),
        Item(id="item-3", skill_id="math-1-2-subtraction", prompt="9 - 4 = ?", answer="5"),
        Item(id="item-4", skill_id="math-2-3-multiplication", prompt="2 x 3 = ?", answer="6"),
    ]
    for i in seeded_items:
        items_db[i.id] = i

def _bkt_update(state: MasteryState, is_correct: bool) -> MasteryState:
    p_learn, p_guess, p_slip = 0.15, 0.2, 0.1
    prior = state.p_mastered
    if is_correct:
        numer = prior * (1 - p_slip)
        denom = numer + (1 - prior) * p_guess
    else:
        numer = prior * p_slip
        denom = numer + (1 - prior) * (1 - p_guess)
    posterior = numer / denom if denom else prior
    posterior = posterior + (1 - posterior) * p_learn
    state.p_mastered = max(0.01, min(0.99, posterior))
    state.streak = state.streak + 1 if is_correct else 0
    state.spaced_successes = min(3, state.spaced_successes + 1) if is_correct else 0
    state.last_attempt_at = datetime.utcnow()
    return state

# API Endpoints

@app.get("/")
async def root():
    """API health check and information"""
    return {
        "name": "Noble Port Realty API",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "SEC Rule 506(b) compliance",
            "Token 2022 standard",
            "Multi-chain support (9 networks)",
            "Zero-knowledge proofs",
            "Soulbound Investor Pass",
            "USDC stablecoin payments"
        ]
    }

@app.post("/checkout/monthly")
async def checkout_monthly(request: CheckoutRequest):
    subscriptions_db[request.parent_id] = {"plan": PlanType.MONTHLY.value, "price": 99, "status": SubscriptionStatus.ACTIVE.value}
    return {"message": "Subscription activated", "plan": "monthly", "price": 99}

@app.post("/checkout/yearly")
async def checkout_yearly(request: CheckoutRequest):
    subscriptions_db[request.parent_id] = {"plan": PlanType.YEARLY.value, "price": 999, "status": SubscriptionStatus.ACTIVE.value}
    return {"message": "Subscription activated", "plan": "yearly", "price": 999}

@app.post("/stripe/webhook")
async def stripe_webhook(request: WebhookRequest):
    if request.parent_id not in subscriptions_db:
        subscriptions_db[request.parent_id] = {"plan": PlanType.MONTHLY.value, "price": 99, "status": request.subscription_status.value}
    else:
        subscriptions_db[request.parent_id]["status"] = request.subscription_status.value
    return {"received": True}

# Property Endpoints

@app.get("/api/properties", response_model=List[Property])
async def get_properties(
    property_type: Optional[PropertyType] = None,
    is_active: bool = True
):
    """Get all properties with optional filtering"""
    properties = list(properties_db.values())
    
    if property_type:
        properties = [p for p in properties if p.property_type == property_type]
    
    if is_active is not None:
        properties = [p for p in properties if p.is_active == is_active]
    
    return properties

@app.get("/api/properties/{property_id}", response_model=Property)
async def get_property(property_id: str):
    """Get specific property details"""
    if property_id not in properties_db:
        raise HTTPException(status_code=404, detail="Property not found")
    
    return properties_db[property_id]

@app.post("/api/properties", response_model=Property, status_code=status.HTTP_201_CREATED)
async def create_property(property_data: Property):
    """Create new tokenized property (admin only)"""
    properties_db[property_data.id] = property_data
    return property_data

# Investor Endpoints

@app.post("/api/investors/register", response_model=Investor, status_code=status.HTTP_201_CREATED)
async def register_investor(
    email: EmailStr,
    full_name: str,
    wallet_address: str
):
    """Register new investor"""
    # Check if investor already exists
    for investor in investors_db.values():
        if investor.email == email or investor.wallet_address == wallet_address:
            raise HTTPException(
                status_code=400,
                detail="Investor with this email or wallet address already exists"
            )
    
    investor = Investor(
        email=email,
        full_name=full_name,
        wallet_address=wallet_address,
        investor_status=InvestorStatus.PENDING
    )
    
    investors_db[investor.id] = investor
    return investor

@app.get("/api/investors/{investor_id}", response_model=Investor)
async def get_investor(investor_id: str):
    """Get investor details"""
    if investor_id not in investors_db:
        raise HTTPException(status_code=404, detail="Investor not found")
    
    return investors_db[investor_id]

@app.post("/api/investors/{investor_id}/kyc", status_code=status.HTTP_200_OK)
async def submit_kyc(investor_id: str, kyc_data: KYCVerification):
    """Submit KYC verification documents"""
    if investor_id not in investors_db:
        raise HTTPException(status_code=404, detail="Investor not found")
    
    investor = investors_db[investor_id]
    
    # Generate KYC verification hash (in production, integrate with KYC provider)
    kyc_hash = hashlib.sha256(
        f"{kyc_data.full_name}{kyc_data.ssn_last_four}{kyc_data.identity_document_number}".encode()
    ).hexdigest()
    
    investor.kyc_verification_hash = kyc_hash
    investor.investor_status = InvestorStatus.VERIFIED
    
    # Check accreditation
    if kyc_data.accreditation_proof:
        investor.is_accredited = True
        investor.investor_status = InvestorStatus.ACCREDITED
    
    investor.updated_at = datetime.utcnow()
    
    return {
        "message": "KYC verification submitted successfully",
        "investor_status": investor.investor_status,
        "kyc_hash": kyc_hash
    }

@app.post("/api/investors/{investor_id}/investor-pass", status_code=status.HTTP_200_OK)
async def issue_investor_pass(investor_id: str):
    """Issue soulbound Investor Pass token after KYC verification"""
    if investor_id not in investors_db:
        raise HTTPException(status_code=404, detail="Investor not found")
    
    investor = investors_db[investor_id]
    
    if investor.investor_status not in [InvestorStatus.VERIFIED, InvestorStatus.ACCREDITED]:
        raise HTTPException(
            status_code=400,
            detail="Investor must complete KYC verification before receiving Investor Pass"
        )
    
    if investor.investor_pass_issued:
        raise HTTPException(
            status_code=400,
            detail="Investor Pass already issued"
        )
    
    # In production, this would call the Solana smart contract
    investor.investor_pass_issued = True
    investor.investor_pass_issued_at = datetime.utcnow()
    investor.updated_at = datetime.utcnow()
    
    return {
        "message": "Investor Pass issued successfully",
        "investor_id": investor_id,
        "is_accredited": investor.is_accredited,
        "issued_at": investor.investor_pass_issued_at
    }

# Transaction Endpoints

@app.post("/api/transactions/purchase", response_model=TokenTransaction, status_code=status.HTTP_201_CREATED)
async def purchase_tokens(
    property_id: str,
    investor_id: str,
    token_amount: int,
    blockchain_network: BlockchainNetwork
):
    """Purchase property tokens"""
    # Validate property
    if property_id not in properties_db:
        raise HTTPException(status_code=404, detail="Property not found")
    
    property_data = properties_db[property_id]
    
    # Validate investor
    if investor_id not in investors_db:
        raise HTTPException(status_code=404, detail="Investor not found")
    
    investor = investors_db[investor_id]
    
    # Compliance checks
    if not investor.investor_pass_issued:
        raise HTTPException(
            status_code=403,
            detail="Investor Pass required - please complete KYC verification"
        )
    
    if token_amount > property_data.available_tokens:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient tokens available. Only {property_data.available_tokens} tokens remaining"
        )
    
    # Calculate total price
    total_price = token_amount * property_data.price_per_token
    
    # Create transaction
    transaction = TokenTransaction(
        property_id=property_id,
        buyer_id=investor_id,
        token_amount=token_amount,
        price_per_token=property_data.price_per_token,
        total_price=total_price,
        blockchain_network=blockchain_network,
        status=TransactionStatus.PENDING
    )
    
    # In production, this would:
    # 1. Verify USDC balance
    # 2. Execute smart contract transfer
    # 3. Update blockchain state
    
    # Simulate blockchain confirmation
    transaction.transaction_hash = f"0x{hashlib.sha256(transaction.id.encode()).hexdigest()}"
    transaction.status = TransactionStatus.CONFIRMED
    transaction.confirmed_at = datetime.utcnow()
    
    # Update property availability
    property_data.available_tokens -= token_amount
    
    transactions_db[transaction.id] = transaction
    
    return transaction

@app.get("/api/transactions/{transaction_id}", response_model=TokenTransaction)
async def get_transaction(transaction_id: str):
    """Get transaction details"""
    if transaction_id not in transactions_db:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return transactions_db[transaction_id]

@app.get("/api/investors/{investor_id}/portfolio", response_model=Portfolio)
async def get_investor_portfolio(investor_id: str):
    """Get investor's token portfolio"""
    if investor_id not in investors_db:
        raise HTTPException(status_code=404, detail="Investor not found")
    
    # Calculate holdings from transactions
    holdings = {}
    
    for transaction in transactions_db.values():
        if transaction.buyer_id == investor_id and transaction.status == TransactionStatus.CONFIRMED:
            property_id = transaction.property_id
            
            if property_id not in holdings:
                property_data = properties_db[property_id]
                holdings[property_id] = {
                    "property_id": property_id,
                    "property_name": property_data.name,
                    "token_symbol": property_data.token_symbol,
                    "tokens_owned": 0,
                    "total_invested": 0.0,
                    "current_value": 0.0,
                    "ownership_percentage": 0.0
                }
            
            holdings[property_id]["tokens_owned"] += transaction.token_amount
            holdings[property_id]["total_invested"] += transaction.total_price
    
    # Calculate current values
    total_value = 0.0
    total_tokens = 0
    
    for property_id, holding in holdings.items():
        property_data = properties_db[property_id]
        holding["current_value"] = holding["tokens_owned"] * property_data.price_per_token
        holding["ownership_percentage"] = (holding["tokens_owned"] / property_data.total_tokens) * 100
        total_value += holding["current_value"]
        total_tokens += holding["tokens_owned"]
    
    portfolio = Portfolio(
        investor_id=investor_id,
        holdings=list(holdings.values()),
        total_value=total_value,
        total_tokens=total_tokens,
        properties_count=len(holdings)
    )
    
    return portfolio

# Compliance Endpoints

@app.get("/api/compliance/report")
async def get_compliance_report():
    """Generate compliance report for regulatory audit"""
    # Count accredited vs non-accredited investors
    accredited_count = sum(1 for i in investors_db.values() if i.is_accredited)
    non_accredited_count = sum(1 for i in investors_db.values() if not i.is_accredited and i.investor_pass_issued)
    
    # Transaction volume
    total_transactions = len([t for t in transactions_db.values() if t.status == TransactionStatus.CONFIRMED])
    total_volume = sum(t.total_price for t in transactions_db.values() if t.status == TransactionStatus.CONFIRMED)
    
    return {
        "generated_at": datetime.utcnow(),
        "total_properties": len(properties_db),
        "active_properties": len([p for p in properties_db.values() if p.is_active]),
        "total_investors": len(investors_db),
        "verified_investors": len([i for i in investors_db.values() if i.investor_pass_issued]),
        "accredited_investors": accredited_count,
        "non_accredited_investors": non_accredited_count,
        "sec_506b_compliance": non_accredited_count <= 35,  # SEC Rule 506(b) limit
        "total_transactions": total_transactions,
        "total_transaction_volume_usdc": total_volume,
        "blockchain_networks_supported": [network.value for network in BlockchainNetwork]
    }

# Utility Endpoints

@app.get("/api/blockchain/networks")
async def get_supported_networks():
    """Get list of supported blockchain networks"""
    return {
        "networks": [
            {"name": "Solana", "symbol": "SOL", "network_id": "solana"},
            {"name": "Ethereum", "symbol": "ETH", "network_id": "ethereum"},
            {"name": "Arbitrum", "symbol": "ARB", "network_id": "arbitrum"},
            {"name": "Polygon", "symbol": "MATIC", "network_id": "polygon"},
            {"name": "Avalanche", "symbol": "AVAX", "network_id": "avalanche"},
            {"name": "Cardano", "symbol": "ADA", "network_id": "cardano"},
            {"name": "BNB Chain", "symbol": "BNB", "network_id": "bnb_chain"},
            {"name": "Optimism", "symbol": "OP", "network_id": "optimism"},
            {"name": "Base", "symbol": "BASE", "network_id": "base"}
        ]
    }

# NoblePort AI Teacher (paid product) endpoints
@app.post("/students", response_model=Student, status_code=status.HTTP_201_CREATED)
async def create_student(student: Student):
    _require_paid(student.parent_id)
    students_db[student.id] = student
    _seed_learning_content()
    _audit(student.id, "student_created", student.model_dump())
    return student

@app.get("/students/{student_id}", response_model=Student)
async def get_student(student_id: str):
    if student_id not in students_db:
        raise HTTPException(status_code=404, detail="Student not found")
    _require_paid(students_db[student_id].parent_id)
    return students_db[student_id]

@app.get("/skills")
async def get_skills(subject: str = "math"):
    _seed_learning_content()
    return [s for s in skills_db.values() if s.subject == subject]

@app.post("/students/{student_id}/daily-log")
async def submit_daily_log(student_id: str):
    if student_id not in students_db:
        raise HTTPException(status_code=404, detail="Student not found")
    key = _daily_log_key(student_id)
    daily_log_db[key] = "done"
    _audit(student_id, "daily_log_submitted", {"key": key})
    return {"logged": True, "date": datetime.utcnow().date().isoformat()}

@app.get("/items/next")
async def get_next_item(student_id: str):
    if student_id not in students_db:
        raise HTTPException(status_code=404, detail="Student not found")
    _require_paid(students_db[student_id].parent_id)
    if _daily_log_key(student_id) not in daily_log_db:
        raise HTTPException(status_code=423, detail="Daily assignment is locked until daily log is submitted")
    _seed_learning_content()
    attempted_ids = {a.item_id for a in attempts_db.values() if a.student_id == student_id}
    for item in items_db.values():
        if item.id not in attempted_ids:
            return item
    return list(items_db.values())[0]

@app.post("/attempts", response_model=LearningAttempt)
async def submit_attempt(request: AttemptRequest):
    student_id = request.student_id
    item_id = request.item_id
    submitted_answer = request.submitted_answer
    if student_id not in students_db:
        raise HTTPException(status_code=404, detail="Student not found")
    _require_paid(students_db[student_id].parent_id)
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    item = items_db[item_id]
    is_correct = item.answer.strip().lower() == submitted_answer.strip().lower()
    attempt = LearningAttempt(student_id=student_id, item_id=item_id, skill_id=item.skill_id, is_correct=is_correct, submitted_answer=submitted_answer)
    attempts_db[attempt.id] = attempt
    mastery_key = f"{student_id}:{item.skill_id}"
    state = mastery_db.get(mastery_key) or MasteryState(student_id=student_id, skill_id=item.skill_id)
    mastery_db[mastery_key] = _bkt_update(state, is_correct)
    _audit(student_id, "attempt_submitted", {"attempt_id": attempt.id, "item_id": item_id, "is_correct": is_correct, "p_mastered": mastery_db[mastery_key].p_mastered})
    return attempt

@app.get("/mastery/{student_id}")
async def get_mastery(student_id: str):
    if student_id not in students_db:
        raise HTTPException(status_code=404, detail="Student not found")
    _require_paid(students_db[student_id].parent_id)
    rows = [m for m in mastery_db.values() if m.student_id == student_id]
    return rows

@app.post("/certificates/evaluate")
async def evaluate_certificate(request: CertificateEvaluateRequest):
    student_id = request.student_id
    if student_id not in students_db:
        raise HTTPException(status_code=404, detail="Student not found")
    _require_paid(students_db[student_id].parent_id)
    states = [m for m in mastery_db.values() if m.student_id == student_id]
    if not states:
        raise HTTPException(status_code=400, detail="No mastery state found")
    eligible = all(m.p_mastered >= 0.95 and m.spaced_successes >= 3 for m in states)
    for m in states:
        m.recent_verification_passed = m.p_mastered >= 0.95
        m.capstone_passed = m.spaced_successes >= 3
    if not eligible:
        raise HTTPException(status_code=400, detail="No mastery proof available for certificate")
    student_attempts = [a for a in attempts_db.values() if a.student_id == student_id]
    snapshot = {m.skill_id: m.p_mastered for m in states}
    item_versions = {a.item_id: items_db[a.item_id].version for a in student_attempts}
    evidence_payload = f"{student_id}|{snapshot}|{item_versions}|{[a.id for a in student_attempts]}"
    evidence_hash = hashlib.sha256(evidence_payload.encode()).hexdigest()
    audit_event = _audit(student_id, "certificate_evaluated", {"evidence_hash": evidence_hash})
    cert = CertificateAward(student_id=student_id, skill_ids=list(snapshot.keys()), attempt_ids=[a.id for a in student_attempts], mastery_snapshot=snapshot, item_versions=item_versions, evidence_hash=evidence_hash, audit_chain_seq=audit_event["seq"])
    certificate_db.setdefault(student_id, []).append(cert)
    return cert

@app.get("/certificates/{student_id}")
async def get_certificates(student_id: str):
    if student_id not in students_db:
        raise HTTPException(status_code=404, detail="Student not found")
    _require_paid(students_db[student_id].parent_id)
    return certificate_db.get(student_id, [])

@app.get("/parent/dashboard")
async def parent_dashboard(parent_id: str):
    _require_paid(parent_id)
    children = [s for s in students_db.values() if s.parent_id == parent_id]
    return {
        "product": "NoblePort AI Teacher",
        "positioning": "Parent-directed AI tutor + mastery credential system",
        "disclosure": "Not an accredited school, licensed teacher replacement, or diploma issuer.",
        "students": len(children),
        "mastery_rows": len([m for m in mastery_db.values() if m.student_id in {c.id for c in children}]),
        "certificates_awarded": sum(len(certificate_db.get(c.id, [])) for c in children),
    }

@app.get("/audit-log/{student_id}")
async def get_audit_log(student_id: str):
    if student_id in students_db:
        _require_paid(students_db[student_id].parent_id)
    if student_id not in audit_log_db:
        return []
    return audit_log_db[student_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
