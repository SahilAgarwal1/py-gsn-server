"""Pydantic models for API requests and responses"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ProxyCall(BaseModel):
    """Represents a single call in a proxy transaction"""
    typeCode: int = Field(..., description="Call type: 2 for CALL, 3 for DELEGATECALL")
    to: str = Field(..., description="Target contract address")
    value: str = Field(default="0", description="ETH value to send")
    data: str = Field(..., description="Encoded function call data")


class RelayRequest(BaseModel):
    """GSN relay request"""
    from_address: str = Field(..., alias="from", description="Transaction sender address")
    to: str = Field(..., description="Target contract address")
    encoded_function: str = Field(..., alias="encodedFunction", description="Encoded function call")
    transaction_fee: int = Field(..., alias="transactionFee", description="Fee percentage for relayer")
    gas_price: int = Field(..., alias="gasPrice", description="Gas price in wei")
    gas_limit: int = Field(..., alias="gasLimit", description="Gas limit")
    nonce: int = Field(..., description="Sender's nonce from RelayHub")
    signature: str = Field(..., description="User's signature")
    approval_data: Optional[str] = Field(default="0x", alias="approvalData", description="Additional approval data")

    class Config:
        populate_by_name = True


class ProxyWalletRequest(BaseModel):
    """Request to execute proxy wallet calls"""
    user_address: str = Field(..., description="User's address (owner of proxy wallet)")
    proxy_calls: List[ProxyCall] = Field(..., description="List of calls to execute")
    signature: str = Field(..., description="User's signature for GSN")
    gas_price: Optional[int] = Field(None, description="Gas price in wei (optional)")
    gas_limit: Optional[int] = Field(default=800000, description="Gas limit")


class RelayResponse(BaseModel):
    """Response from relay operations"""
    success: bool
    tx_hash: Optional[str] = None
    error: Optional[str] = None
    gas_used: Optional[int] = None
    charge: Optional[int] = None


class StatusResponse(BaseModel):
    """Relay status response"""
    address: str
    state: int
    state_text: str
    total_stake: Optional[int] = None
    unstake_delay: Optional[int] = None
    owner: Optional[str] = None
    balance: Optional[str] = None
    is_ready: bool 