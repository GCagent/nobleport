"""NoblePort API backend.

Legacy tokenized-real-estate routes remain staged simulation endpoints. GCagent
field-operations routes are separately mounted and protected by their own auth
and evidence controls.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from .gcagent import router as gcagent_router
from .health import router as health_router
from .runtime import application_lifespan, configure_runtime
from .settings import get_settings

settings = get_settings()

app = FastAPI(
    title="NoblePort API",
    description="Staged NoblePort field-operations and legacy platform API",
    version=settings.APP_VERSION,
    lifespan=application_lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
configure_runtime(app)
app.include_router(health_router)
app.include_router(gcagent_router)


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


class Property(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=1, max_length=200)
    property_type: PropertyType
    location: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=5000)
    total_value: float = Field(gt=0)
    token_symbol: str = Field(min_length=1, max_length=20)
    total_tokens: int = Field(gt=0)
    available_tokens: int = Field(ge=0)
    price_per_token: float = Field(gt=0)
    projected_annual_return: float = Field(ge=0)
    minimum_ownership_percentage: float = Field(gt=0, le=100)
    images: List[str] = Field(default_factory=list)
    documents: List[str] = Field(default_factory=list)
    llc_entity: str = Field(min_length=1, max_length=200)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class Investor(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    wallet_address: str = Field(min_length=1, max_length=256)
    investor_status: InvestorStatus
    is_accredited: bool = False
    kyc_verification_hash: Optional[str] = None
    investor_pass_issued: bool = False
    investor_pass_issued_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KYCVerification(BaseModel):
    """Provider reference only; raw identity documents and SSNs are not accepted."""

    provider: str = Field(min_length=1, max_length=100)
    verification_reference: str = Field(min_length=1, max_length=512)
    evidence_hash: str = Field(min_length=32, max_length=128)
    accreditation_verified: bool = False
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class TokenTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    property_id: str
    buyer_id: str
    seller_id: Optional[str] = None
    token_amount: int = Field(gt=0)
    price_per_token: float = Field(gt=0)
    total_price: float = Field(gt=0)
    payment_currency: str = "USDC"
    blockchain_network: BlockchainNetwork
    transaction_hash: Optional[str] = None
    status: TransactionStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_at: Optional[datetime] = None


class Portfolio(BaseModel):
    investor_id: str
    holdings: List[Dict[str, Any]] = Field(default_factory=list)
    total_value: float = 0.0
    total_tokens: int = 0
    properties_count: int = 0


# Legacy simulation state. This data is intentionally non-persistent and never
# permitted to serve a production investment, payment, or compliance workflow.
properties_db: Dict[str, Property] = {}
investors_db: Dict[str, Investor] = {}
transactions_db: Dict[str, TokenTransaction] = {}


def require_legacy_staging_mode() -> None:
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Legacy investor workflow is staged simulation only and is disabled in production.",
        )


@app.get("/")
async def root() -> Dict[str, object]:
    """Return service identity without making production-evidence claims."""
    return {
        "name": "NoblePort API",
        "version": settings.APP_VERSION,
        "status": "staged",
        "environment": settings.APP_ENV,
        "health": {"live": "/health/live", "ready": "/health/ready"},
        "notes": [
            "GCagent routes require bearer authentication.",
            "Legacy investor and token routes are simulation-only and disabled in production.",
        ],
    }


@app.get(
    "/api/properties",
    response_model=List[Property],
    dependencies=[Depends(require_legacy_staging_mode)],
)
async def get_properties(
    property_type: Optional[PropertyType] = None,
    is_active: bool = True,
) -> List[Property]:
    properties = list(properties_db.values())
    if property_type:
        properties = [item for item in properties if item.property_type == property_type]
    if is_active is not None:
        properties = [item for item in properties if item.is_active == is_active]
    return properties


@app.get(
    "/api/properties/{property_id}",
    response_model=Property,
    dependencies=[Depends(require_legacy_staging_mode)],
)
async def get_property(property_id: str) -> Property:
    if property_id not in properties_db:
        raise HTTPException(status_code=404, detail="Property not found")
    return properties_db[property_id]


@app.post(
    "/api/properties",
    response_model=Property,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_legacy_staging_mode)],
)
async def create_property(property_data: Property) -> Property:
    if property_data.available_tokens > property_data.total_tokens:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="available_tokens cannot exceed total_tokens",
        )
    properties_db[property_data.id] = property_data
    return property_data


@app.post(
    "/api/investors/register",
    response_model=Investor,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_legacy_staging_mode)],
)
async def register_investor(
    email: EmailStr,
    full_name: str,
    wallet_address: str,
) -> Investor:
    for investor in investors_db.values():
        if investor.email == email or investor.wallet_address == wallet_address:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Investor with this email or wallet address already exists",
            )

    investor = Investor(
        email=email,
        full_name=full_name,
        wallet_address=wallet_address,
        investor_status=InvestorStatus.PENDING,
    )
    investors_db[investor.id] = investor
    return investor


@app.get(
    "/api/investors/{investor_id}",
    response_model=Investor,
    dependencies=[Depends(require_legacy_staging_mode)],
)
async def get_investor(investor_id: str) -> Investor:
    if investor_id not in investors_db:
        raise HTTPException(status_code=404, detail="Investor not found")
    return investors_db[investor_id]


@app.post(
    "/api/investors/{investor_id}/kyc",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_legacy_staging_mode)],
)
async def submit_kyc(investor_id: str, kyc_data: KYCVerification) -> Dict[str, object]:
    if investor_id not in investors_db:
        raise HTTPException(status_code=404, detail="Investor not found")

    investor = investors_db[investor_id]
    kyc_hash = hashlib.sha256(
        f"{kyc_data.provider}:{kyc_data.verification_reference}:{kyc_data.evidence_hash}".encode()
    ).hexdigest()
    investor.kyc_verification_hash = kyc_hash
    investor.investor_status = InvestorStatus.VERIFIED
    if kyc_data.accreditation_verified:
        investor.is_accredited = True
        investor.investor_status = InvestorStatus.ACCREDITED
    investor.updated_at = datetime.utcnow()

    return {
        "message": "Staged KYC provider reference recorded",
        "investor_status": investor.investor_status,
        "kyc_hash": kyc_hash,
    }


@app.post(
    "/api/investors/{investor_id}/investor-pass",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_legacy_staging_mode)],
)
async def issue_investor_pass(investor_id: str) -> Dict[str, object]:
    if investor_id not in investors_db:
        raise HTTPException(status_code=404, detail="Investor not found")

    investor = investors_db[investor_id]
    if investor.investor_status not in {InvestorStatus.VERIFIED, InvestorStatus.ACCREDITED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Investor must complete KYC verification before receiving Investor Pass",
        )
    if investor.investor_pass_issued:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Investor Pass already issued",
        )

    investor.investor_pass_issued = True
    investor.investor_pass_issued_at = datetime.utcnow()
    investor.updated_at = datetime.utcnow()
    return {
        "message": "Staged Investor Pass simulation completed",
        "investor_id": investor_id,
        "is_accredited": investor.is_accredited,
        "issued_at": investor.investor_pass_issued_at,
    }


@app.post(
    "/api/transactions/purchase",
    response_model=TokenTransaction,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_legacy_staging_mode)],
)
async def purchase_tokens(
    property_id: str,
    investor_id: str,
    token_amount: int = Query(gt=0),
    blockchain_network: BlockchainNetwork = BlockchainNetwork.SOLANA,
) -> TokenTransaction:
    if property_id not in properties_db:
        raise HTTPException(status_code=404, detail="Property not found")
    if investor_id not in investors_db:
        raise HTTPException(status_code=404, detail="Investor not found")

    property_data = properties_db[property_id]
    investor = investors_db[investor_id]
    if not investor.investor_pass_issued:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Investor Pass required before simulated purchase",
        )
    if token_amount > property_data.available_tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient tokens available. Only {property_data.available_tokens} remain.",
        )

    total_price = token_amount * property_data.price_per_token
    transaction = TokenTransaction(
        property_id=property_id,
        buyer_id=investor_id,
        token_amount=token_amount,
        price_per_token=property_data.price_per_token,
        total_price=total_price,
        blockchain_network=blockchain_network,
        status=TransactionStatus.CONFIRMED,
        transaction_hash=f"simulated:{hashlib.sha256(uuid.uuid4().bytes).hexdigest()}",
        confirmed_at=datetime.utcnow(),
    )
    property_data.available_tokens -= token_amount
    transactions_db[transaction.id] = transaction
    return transaction


@app.get(
    "/api/transactions/{transaction_id}",
    response_model=TokenTransaction,
    dependencies=[Depends(require_legacy_staging_mode)],
)
async def get_transaction(transaction_id: str) -> TokenTransaction:
    if transaction_id not in transactions_db:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transactions_db[transaction_id]


@app.get(
    "/api/investors/{investor_id}/portfolio",
    response_model=Portfolio,
    dependencies=[Depends(require_legacy_staging_mode)],
)
async def get_investor_portfolio(investor_id: str) -> Portfolio:
    if investor_id not in investors_db:
        raise HTTPException(status_code=404, detail="Investor not found")

    holdings: Dict[str, Dict[str, Any]] = {}
    for transaction in transactions_db.values():
        if transaction.buyer_id != investor_id or transaction.status != TransactionStatus.CONFIRMED:
            continue
        property_data = properties_db[transaction.property_id]
        holding = holdings.setdefault(
            transaction.property_id,
            {
                "property_id": transaction.property_id,
                "property_name": property_data.name,
                "token_symbol": property_data.token_symbol,
                "tokens_owned": 0,
                "total_invested": 0.0,
                "current_value": 0.0,
                "ownership_percentage": 0.0,
            },
        )
        holding["tokens_owned"] += transaction.token_amount
        holding["total_invested"] += transaction.total_price

    total_value = 0.0
    total_tokens = 0
    for property_id, holding in holdings.items():
        property_data = properties_db[property_id]
        holding["current_value"] = holding["tokens_owned"] * property_data.price_per_token
        holding["ownership_percentage"] = (
            holding["tokens_owned"] / property_data.total_tokens
        ) * 100
        total_value += holding["current_value"]
        total_tokens += holding["tokens_owned"]

    return Portfolio(
        investor_id=investor_id,
        holdings=list(holdings.values()),
        total_value=total_value,
        total_tokens=total_tokens,
        properties_count=len(holdings),
    )


@app.get(
    "/api/compliance/report",
    dependencies=[Depends(require_legacy_staging_mode)],
)
async def get_compliance_report() -> Dict[str, object]:
    accredited_count = sum(1 for item in investors_db.values() if item.is_accredited)
    non_accredited_count = sum(
        1
        for item in investors_db.values()
        if not item.is_accredited and item.investor_pass_issued
    )
    confirmed = [
        item for item in transactions_db.values() if item.status == TransactionStatus.CONFIRMED
    ]
    return {
        "evidence_status": "staged_simulation_only",
        "generated_at": datetime.utcnow(),
        "total_properties": len(properties_db),
        "active_properties": sum(1 for item in properties_db.values() if item.is_active),
        "total_investors": len(investors_db),
        "verified_investors": sum(
            1 for item in investors_db.values() if item.investor_pass_issued
        ),
        "accredited_investors": accredited_count,
        "non_accredited_investors": non_accredited_count,
        "sec_506b_simulation_check": non_accredited_count <= 35,
        "total_transactions": len(confirmed),
        "total_transaction_volume_usdc": sum(item.total_price for item in confirmed),
        "blockchain_networks_supported": [item.value for item in BlockchainNetwork],
    }


@app.get(
    "/api/blockchain/networks",
    dependencies=[Depends(require_legacy_staging_mode)],
)
async def get_supported_networks() -> Dict[str, List[Dict[str, str]]]:
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
            {"name": "Base", "symbol": "BASE", "network_id": "base"},
        ]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, proxy_headers=True)
