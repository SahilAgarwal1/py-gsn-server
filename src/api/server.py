"""FastAPI server for GSN Relayer"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from web3 import Web3
import traceback

from ..config import config
from ..relayer import relayer
from ..encoders import encode_proxy_calls
from ..abis import PROXY_WALLET_FACTORY_ABI
from .models import (
    RelayRequest, ProxyWalletRequest, RelayResponse, 
    StatusResponse, ProxyCall
)


app = FastAPI(
    title="GSN Relayer",
    description="Gas Station Network Relayer for Ethereum/Polygon",
    version="0.1.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "relayer": relayer.address,
        "network": relayer.w3.eth.chain_id
    }


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get relayer status"""
    try:
        status = await relayer.get_relay_status()
        balance = relayer.w3.eth.get_balance(relayer.address)
        
        return StatusResponse(
            address=status['address'],
            state=status['state'],
            state_text=status['stateText'],
            total_stake=status.get('totalStake'),
            unstake_delay=status.get('unstakeDelay'),
            owner=status.get('owner'),
            balance=str(balance),
            is_ready=status['state'] == 2  # Registered state
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stake", response_model=RelayResponse)
async def stake_relay(stake_amount_ether: str = "1", unstake_delay_seconds: int = None):
    """Stake the relay"""
    try:
        tx_hash = await relayer.stake_relay(stake_amount_ether, unstake_delay_seconds)
        return RelayResponse(
            success=True,
            tx_hash=tx_hash
        )
    except Exception as e:
        return RelayResponse(
            success=False,
            error=str(e)
        )


@app.post("/register", response_model=RelayResponse)
async def register_relay(transaction_fee: int = None, url: str = None):
    """Register the relay after staking"""
    try:
        tx_hash = await relayer.register_relay(transaction_fee, url)
        return RelayResponse(
            success=True,
            tx_hash=tx_hash
        )
    except Exception as e:
        return RelayResponse(
            success=False,
            error=str(e)
        )


@app.post("/relay", response_model=RelayResponse)
async def relay_transaction(request: RelayRequest):
    """Relay a transaction"""
    try:
        # Convert request to dict format expected by relayer
        relay_request = {
            'from': request.from_address,
            'to': request.to,
            'encodedFunction': request.encoded_function,
            'transactionFee': request.transaction_fee,
            'gasPrice': request.gas_price,
            'gasLimit': request.gas_limit,
            'nonce': request.nonce,
            'signature': request.signature,
            'approvalData': request.approval_data
        }
        
        # Verify signature
        if not relayer.verify_relay_request_signature(relay_request):
            raise ValueError("Invalid signature")
        
        # Execute relay
        tx_hash = await relayer.relay_call(relay_request)
        
        return RelayResponse(
            success=True,
            tx_hash=tx_hash
        )
    except Exception as e:
        traceback.print_exc()
        return RelayResponse(
            success=False,
            error=str(e)
        )


@app.post("/relay/proxy-wallet", response_model=RelayResponse)
async def relay_proxy_wallet_transaction(request: ProxyWalletRequest):
    """Relay a ProxyWalletFactory transaction (simplified endpoint)"""
    try:
        # Get nonce for user
        nonce = relayer.relay_hub.functions.getNonce(request.user_address).call()
        
        # Encode the proxy calls
        proxy_calls_data = []
        for call in request.proxy_calls:
            proxy_calls_data.append({
                'typeCode': call.typeCode,
                'to': call.to,
                'value': int(call.value),
                'data': call.data
            })
        
        # Get ProxyWalletFactory address (you'll need to set this in config)
        proxy_factory_address = config.proxy_wallet_factory_address
        
        # Create contract instance
        proxy_factory = relayer.w3.eth.contract(
            address=Web3.to_checksum_address(proxy_factory_address),
            abi=PROXY_WALLET_FACTORY_ABI
        )
        
        # Encode the proxy function call
        encoded_function = proxy_factory.encodeABI(
            fn_name='proxy',
            args=[proxy_calls_data]
        )
        
        # Use provided gas price or current network gas price
        gas_price = request.gas_price or relayer.w3.eth.gas_price
        
        # Create relay request
        relay_request = {
            'from': request.user_address,
            'to': proxy_factory_address,
            'encodedFunction': encoded_function,
            'transactionFee': config.relay_fee_percentage,
            'gasPrice': gas_price,
            'gasLimit': request.gas_limit,
            'nonce': nonce,
            'signature': request.signature,
            'approvalData': '0x'
        }
        
        # Execute relay
        tx_hash = await relayer.relay_call(relay_request)
        
        return RelayResponse(
            success=True,
            tx_hash=tx_hash
        )
    except Exception as e:
        traceback.print_exc()
        return RelayResponse(
            success=False,
            error=str(e)
        )


@app.get("/nonce/{address}")
async def get_nonce(address: str):
    """Get nonce for an address from RelayHub"""
    try:
        nonce = relayer.relay_hub.functions.getNonce(
            Web3.to_checksum_address(address)
        ).call()
        return {"address": address, "nonce": nonce}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return HTTPException(status_code=400, detail=str(exc))


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    traceback.print_exc()
    return HTTPException(status_code=500, detail=str(exc)) 