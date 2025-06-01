"""Test script for GSN Relayer on local Hardhat network"""

import os
import sys
import asyncio
import requests
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.encoders import encode_erc20_approve

# Load local environment
load_dotenv('.env')

# Configuration
RELAYER_URL = "http://localhost:8090"
RPC_URL = os.getenv("RPC_URL", "http://localhost:8545")

# Hardhat test accounts (well-known keys, DO NOT use in production!)
TEST_ACCOUNTS = [
    {
        "address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
        "key": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    },
    {
        "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", 
        "key": "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
    },
    {
        "address": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
        "key": "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
    }
]


async def test_relayer_setup():
    """Test relayer setup and registration"""
    print("🧪 Testing Relayer Setup")
    print("=" * 50)
    
    # Check relayer status
    try:
        response = requests.get(f"{RELAYER_URL}/status")
        status = response.json()
        
        print(f"Relayer address: {status['address']}")
        print(f"State: {status['state_text']}")
        print(f"Balance: {Web3.from_wei(int(status['balance']), 'ether')} ETH")
        
        if status['is_ready']:
            print("✅ Relayer is ready!")
        else:
            print("❌ Relayer is not ready. Run: python manage_relayer.py setup")
            return False
            
    except Exception as e:
        print(f"❌ Failed to connect to relayer: {e}")
        print("Make sure the relayer is running: python main.py")
        return False
    
    return True


async def test_proxy_wallet_creation():
    """Test creating a proxy wallet through GSN"""
    print("\n🧪 Testing Proxy Wallet Creation")
    print("=" * 50)
    
    # Use test account #2 as user
    user = TEST_ACCOUNTS[2]
    user_account = Account.from_key(user['key'])
    
    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Get contract addresses from environment
    proxy_factory_address = os.getenv("PROXY_WALLET_FACTORY_ADDRESS")
    relay_hub_address = os.getenv("RELAY_HUB_ADDRESS")
    
    print(f"User address: {user_account.address}")
    print(f"ProxyWalletFactory: {proxy_factory_address}")
    
    # Get nonce
    response = requests.get(f"{RELAYER_URL}/nonce/{user_account.address}")
    nonce = response.json()['nonce']
    print(f"User nonce: {nonce}")
    
    # Get relayer address
    response = requests.get(f"{RELAYER_URL}/status")
    relay_address = response.json()['address']
    
    # Create a simple proxy call (just to trigger wallet creation)
    proxy_calls = []  # Empty calls will create wallet
    
    # Encode the proxy function call
    function_selector = Web3.keccak(text="proxy((uint8,address,uint256,bytes)[])")[:4]
    from eth_abi import encode
    encoded_params = encode(['(uint8,address,uint256,bytes)[]'], [[]])
    encoded_function = function_selector + encoded_params
    
    # Prepare relay parameters
    transaction_fee = 10
    gas_price = w3.eth.gas_price
    gas_limit = 300000
    
    # Create the packed message exactly as RelayHub does
    # Use eth_abi to encode packed data (equivalent to abi.encodePacked)
    from eth_abi.packed import encode_packed
    
    packed = encode_packed(
        ['string', 'address', 'address', 'bytes', 'uint256', 'uint256', 'uint256', 'uint256', 'address'],
        ['rlx:', user_account.address, proxy_factory_address, encoded_function, transaction_fee, gas_price, gas_limit, nonce, relay_hub_address]
    )
    
    # Then concatenate packed bytes with relay address and hash
    relay_address_bytes = Web3.to_bytes(hexstr=relay_address)
    concatenated = packed + relay_address_bytes
    hashed_message = Web3.keccak(concatenated)
    
    # GSN v1 RelayHub uses toEthSignedMessageHash, so we need to sign with EIP-191 prefix
    signable_message = encode_defunct(hashed_message)
    signature = user_account.sign_message(signable_message)
    
    # Send relay request
    relay_request = {
        "from": user_account.address,
        "to": proxy_factory_address,
        "encodedFunction": encoded_function.hex(),
        "transactionFee": transaction_fee,
        "gasPrice": gas_price,
        "gasLimit": gas_limit,
        "nonce": nonce,
        "signature": signature.signature.hex(),
        "approvalData": "0x"
    }
    
    print("\nSending relay request...")
    
    try:
        response = requests.post(f"{RELAYER_URL}/relay", json=relay_request)
        result = response.json()
        
        if result['success']:
            print(f"✅ Transaction relayed successfully!")
            print(f"TX Hash: {result['tx_hash']}")
            return True
        else:
            print(f"❌ Relay failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to send relay request: {e}")
        return False


async def test_erc20_approval():
    """Test ERC20 approval through proxy wallet"""
    print("\n🧪 Testing ERC20 Approval via Proxy Wallet")
    print("=" * 50)
    
    # Use test account #2 as user
    user = TEST_ACCOUNTS[2]
    user_account = Account.from_key(user['key'])
    
    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Get contract addresses
    proxy_factory_address = os.getenv("PROXY_WALLET_FACTORY_ADDRESS")
    relay_hub_address = os.getenv("RELAY_HUB_ADDRESS")
    mock_token_address = os.getenv("MOCK_TOKEN_ADDRESS", "0x0000000000000000000000000000000000000000")
    
    if mock_token_address == "0x0000000000000000000000000000000000000000":
        print("❌ Mock token address not found. Make sure contracts are deployed.")
        return False
    
    print(f"Mock token address: {mock_token_address}")
    
    # Get nonce
    response = requests.get(f"{RELAYER_URL}/nonce/{user_account.address}")
    nonce = response.json()['nonce']
    
    # Get relayer address
    response = requests.get(f"{RELAYER_URL}/status")
    relay_address = response.json()['address']
    
    # Create proxy call for ERC20 approval
    spender_address = "0x1234567890123456789012345678901234567890"  # Example spender
    approval_amount = 2**256 - 1  # Max approval
    
    # Directly test with the relay endpoint
    print(f"\nApproving {spender_address} to spend tokens...")
    return await test_direct_relay_approval(user_account, mock_token_address, spender_address)


async def test_direct_relay_approval(user_account, token_address, spender_address):
    """Test approval using direct relay endpoint"""
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    proxy_factory_address = os.getenv("PROXY_WALLET_FACTORY_ADDRESS")
    relay_hub_address = os.getenv("RELAY_HUB_ADDRESS")
    
    # Get updated nonce
    response = requests.get(f"{RELAYER_URL}/nonce/{user_account.address}")
    nonce = response.json()['nonce']
    
    # Get relayer address
    response = requests.get(f"{RELAYER_URL}/status")
    relay_address = response.json()['address']
    
    # Encode proxy call
    from eth_abi import encode
    
    proxy_calls = [(
        2,  # CALL
        Web3.to_checksum_address(token_address),
        0,  # value
        bytes.fromhex(encode_erc20_approve(spender_address, 2**256 - 1)[2:])
    )]
    
    function_selector = Web3.keccak(text="proxy((uint8,address,uint256,bytes)[])")[:4]
    encoded_params = encode(['(uint8,address,uint256,bytes)[]'], [proxy_calls])
    encoded_function = function_selector + encoded_params
    
    # Sign relay request
    transaction_fee = 10
    gas_price = w3.eth.gas_price
    gas_limit = 400000
    
    # Create the packed message exactly as RelayHub does
    # Use eth_abi to encode packed data (equivalent to abi.encodePacked)
    from eth_abi.packed import encode_packed
    
    packed = encode_packed(
        ['string', 'address', 'address', 'bytes', 'uint256', 'uint256', 'uint256', 'uint256', 'address'],
        ['rlx:', user_account.address, proxy_factory_address, encoded_function, transaction_fee, gas_price, gas_limit, nonce, relay_hub_address]
    )
    
    # Then concatenate packed bytes with relay address and hash
    relay_address_bytes = Web3.to_bytes(hexstr=relay_address)
    concatenated = packed + relay_address_bytes
    hashed_message = Web3.keccak(concatenated)
    
    # GSN v1 RelayHub uses toEthSignedMessageHash, so we need to sign with EIP-191 prefix
    signable_message = encode_defunct(hashed_message)
    signature = user_account.sign_message(signable_message)
    
    relay_request = {
        "from": user_account.address,
        "to": proxy_factory_address,
        "encodedFunction": encoded_function.hex(),
        "transactionFee": transaction_fee,
        "gasPrice": gas_price,
        "gasLimit": gas_limit,
        "nonce": nonce,
        "signature": signature.signature.hex(),
        "approvalData": "0x"
    }
    
    try:
        response = requests.post(f"{RELAYER_URL}/relay", json=relay_request)
        result = response.json()
        
        if result['success']:
            print(f"✅ Direct relay successful!")
            print(f"TX Hash: {result['tx_hash']}")
            return True
        else:
            print(f"❌ Direct relay failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("🚀 GSN Relayer Local Test Suite")
    print("================================\n")
    
    # Test 1: Check relayer setup
    if not await test_relayer_setup():
        print("\n❌ Relayer not ready. Please set it up first.")
        return
    
    # Test 2: Create proxy wallet
    if not await test_proxy_wallet_creation():
        print("\n❌ Failed to create proxy wallet")
        return
    
    # Test 3: ERC20 approval
    await test_erc20_approval()
    
    print("\n✅ Test suite completed!")


if __name__ == "__main__":
    asyncio.run(main()) 