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

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import uuid
import os

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


class ReleaseIntent(str, Enum):
    RELEASE_APP = "release_app"

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
    holdings: List[Dict[str, any]] = []
    total_value: float = 0.0
    total_tokens: int = 0
    properties_count: int = 0


class ReleaseGateRequest(BaseModel):
    intent: ReleaseIntent
    app: str
    environment: str
    requested_by: str
    ci_tests_passing: bool = False
    version_bumped: bool = False
    second_confirmation: bool = False
    admin_signature: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReleaseGateDecision(BaseModel):
    accepted: bool
    workflow: str
    reason: str
    command: Optional[str] = None
    next_step: Optional[str] = None

# In-memory storage (replace with PostgreSQL in production)
properties_db: Dict[str, Property] = {}
investors_db: Dict[str, Investor] = {}
transactions_db: Dict[str, TokenTransaction] = {}


def _is_authorized_release_request(requested_by: str, admin_signature: str) -> bool:
    """Validate release request authorization data.

    In production this should verify signature material with your identity provider
    or custody/MPC system. Here we compare against configured allowlists/secrets.
    """
    allowed_users = {
        value.strip().lower()
        for value in os.getenv("RELEASE_ALLOWED_USERS", "").split(",")
        if value.strip()
    }
    expected_signature = os.getenv("RELEASE_ADMIN_SIGNATURE", "")

    if allowed_users and requested_by.lower() not in allowed_users:
        return False

    if expected_signature and admin_signature != expected_signature:
        return False

    return True

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


@app.post("/api/release-gate", response_model=ReleaseGateDecision)
async def release_gate(request: ReleaseGateRequest):
    """Governed release gate for production voice-triggered deployments."""
    if request.environment.lower() != "production":
        raise HTTPException(status_code=400, detail="Only production environment is allowed by this gate")

    if request.intent != ReleaseIntent.RELEASE_APP:
        raise HTTPException(status_code=400, detail="Invalid intent for release gate")

    if not _is_authorized_release_request(request.requested_by, request.admin_signature):
        raise HTTPException(status_code=403, detail="Unauthorized release request")

    if not request.ci_tests_passing:
        return ReleaseGateDecision(
            accepted=False,
            workflow="create-production-builds.yml",
            reason="CI test suite must pass before release",
            next_step="Run CI and re-submit release request"
        )

    if not request.version_bumped:
        return ReleaseGateDecision(
            accepted=False,
            workflow="create-production-builds.yml",
            reason="Version bump required for production release",
            next_step="Increment app version and re-submit release request"
        )

    if not request.second_confirmation:
        return ReleaseGateDecision(
            accepted=False,
            workflow="create-production-builds.yml",
            reason="Second confirmation required for production release",
            next_step="Ask user to confirm deployment explicitly"
        )

    return ReleaseGateDecision(
        accepted=True,
        workflow="create-production-builds.yml",
        reason="Release gate checks passed",
        command="npx eas-cli workflow:run create-production-builds.yml"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
