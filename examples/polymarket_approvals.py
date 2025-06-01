"""Example: Relaying Polymarket approval transactions through GSN"""

import os
import sys
import requests
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.encoders import encode_erc20_approve, encode_erc1155_set_approval_for_all

load_dotenv()

# Configuration
RELAYER_URL = "http://localhost:8090"
RPC_URL = os.getenv("RPC_URL", "https://polygon-rpc.com")
USER_PRIVATE_KEY = os.getenv("USER_PRIVATE_KEY")  # For testing only!

# Polygon addresses
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CONDITIONAL_TOKENS_ADDRESS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
PROXY_WALLET_FACTORY_ADDRESS = "0xaB45c5A4B0c941a2F231C04C3f49182e1A254052"
RELAY_HUB_ADDRESS = "0xD216153c06E857cD7f72665E0aF1d7D82172F494"

# Spender addresses (Polymarket contracts)
USDC_SPENDERS = [
    "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045",  # Conditional Tokens Framework
    "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E",  # CTF Exchange
    "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296",  # Neg Risk Adapter
    "0xC5d563A36AE78145C45a50134d48A1215220f80a",  # Neg Risk CTF Exchange
]

OUTCOME_TOKEN_SPENDERS = [
    "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E",  # CTF Exchange
    "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296",  # Neg Risk Adapter
    "0xC5d563A36AE78145C45a50134d48A1215220f80a",  # Neg Risk Exchange
]


def create_proxy_calls():
    """Create the proxy calls for all necessary approvals"""
    proxy_calls = []
    
    # USDC approvals
    for spender in USDC_SPENDERS:
        proxy_calls.append({
            "typeCode": 2,  # CALL
            "to": USDC_ADDRESS,
            "value": "0",
            "data": encode_erc20_approve(spender, 2**256 - 1)
        })
    
    # Conditional Token approvals
    for spender in OUTCOME_TOKEN_SPENDERS:
        proxy_calls.append({
            "typeCode": 2,  # CALL
            "to": CONDITIONAL_TOKENS_ADDRESS,
            "value": "0",
            "data": encode_erc1155_set_approval_for_all(spender, True)
        })
    
    return proxy_calls


def sign_relay_request(user_address, encoded_function, transaction_fee, gas_price, gas_limit, nonce, relay_address):
    """Sign a relay request for GSN"""
    if not USER_PRIVATE_KEY:
        raise ValueError("USER_PRIVATE_KEY not set in environment")
    
    # Create account from private key
    account = Account.from_key(USER_PRIVATE_KEY)
    
    # Create the message to sign (GSN v1 format)
    packed = Web3.solidity_keccak([
        'string',
        'address',
        'address', 
        'bytes',
        'uint256',
        'uint256',
        'uint256',
        'uint256',
        'address'
    ], [
        'rlx:',
        user_address,
        PROXY_WALLET_FACTORY_ADDRESS,
        Web3.to_bytes(hexstr=encoded_function),
        transaction_fee,
        gas_price,
        gas_limit,
        nonce,
        RELAY_HUB_ADDRESS
    ])
    
    # Add relay address to the hash
    hashed_message = Web3.solidity_keccak(['bytes', 'address'], [packed, relay_address])
    
    # Sign the message
    signature = account.signHash(hashed_message)
    
    return signature.signature.hex()


async def main():
    """Main function to relay Polymarket approvals"""
    print("Starting Polymarket approval relay example...")
    
    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print(f"Failed to connect to {RPC_URL}")
        return
    
    # Get user account
    if not USER_PRIVATE_KEY:
        print("Please set USER_PRIVATE_KEY in .env file")
        return
    
    account = Account.from_key(USER_PRIVATE_KEY)
    user_address = account.address
    print(f"User address: {user_address}")
    
    # Check relayer status
    try:
        response = requests.get(f"{RELAYER_URL}/status")
        status = response.json()
        print(f"Relayer status: {status['state_text']}")
        
        if not status['is_ready']:
            print("Relayer is not ready. Please stake and register first.")
            return
            
        relay_address = status['address']
        print(f"Relay address: {relay_address}")
    except Exception as e:
        print(f"Failed to get relayer status: {e}")
        return
    
    # Get user's nonce from RelayHub
    try:
        response = requests.get(f"{RELAYER_URL}/nonce/{user_address}")
        nonce = response.json()['nonce']
        print(f"User nonce: {nonce}")
    except Exception as e:
        print(f"Failed to get nonce: {e}")
        return
    
    # Create proxy calls
    proxy_calls = create_proxy_calls()
    print(f"Created {len(proxy_calls)} proxy calls")
    
    # Get current gas price
    gas_price = w3.eth.gas_price
    gas_limit = 800000  # Adjust as needed
    transaction_fee = 0  # 0% fee (like in the Polymarket transaction)
    
    # Encode the proxy function call
    from web3 import Web3
    from eth_abi import encode
    
    # Manually encode the proxy function call
    function_selector = Web3.keccak(text="proxy((uint8,address,uint256,bytes)[])")[:4]
    
    # Prepare calls for encoding
    encoded_calls = []
    for call in proxy_calls:
        encoded_calls.append((
            call['typeCode'],
            Web3.to_checksum_address(call['to']),
            int(call['value']),
            Web3.to_bytes(hexstr=call['data'])
        ))
    
    # Encode the parameters
    encoded_params = encode(['(uint8,address,uint256,bytes)[]'], [encoded_calls])
    encoded_function = function_selector + encoded_params
    
    # Sign the relay request
    signature = sign_relay_request(
        user_address,
        encoded_function.hex(),
        transaction_fee,
        gas_price,
        gas_limit,
        nonce,
        relay_address
    )
    
    print(f"Signature: {signature}")
    
    # Send relay request
    relay_request = {
        "from": user_address,
        "to": PROXY_WALLET_FACTORY_ADDRESS,
        "encodedFunction": encoded_function.hex(),
        "transactionFee": transaction_fee,
        "gasPrice": gas_price,
        "gasLimit": gas_limit,
        "nonce": nonce,
        "signature": signature,
        "approvalData": "0x"
    }
    
    print("Sending relay request...")
    
    try:
        response = requests.post(
            f"{RELAYER_URL}/relay",
            json=relay_request
        )
        result = response.json()
        
        if result['success']:
            print(f"✅ Transaction relayed successfully!")
            print(f"Transaction hash: {result['tx_hash']}")
        else:
            print(f"❌ Relay failed: {result['error']}")
            
    except Exception as e:
        print(f"Failed to send relay request: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 