#!/usr/bin/env python3
"""Test relayer against local Hardhat network with verbose logging."""

import os
import sys
import json
import asyncio
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.relayer import GSNRelayer
from src.abis.proxy_wallet_factory import PROXY_WALLET_FACTORY_ABI, ERC20_ABI

# Load local environment
load_dotenv("env.local")

# Add ProxyWalletCreated event to the factory ABI
FACTORY_ABI_WITH_EVENTS = PROXY_WALLET_FACTORY_ABI + [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": True, "name": "wallet", "type": "address"}
        ],
        "name": "ProxyWalletCreated",
        "type": "event"
    }
]

# Add Approval event to ERC20 ABI
ERC20_ABI_WITH_EVENTS = ERC20_ABI + [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": True, "name": "spender", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"}
        ],
        "name": "Approval",
        "type": "event"
    }
]

async def decode_relay_call_logs(w3, tx_hash, proxy_factory_address, mock_token_address):
    """Decode and print all logs from a relay call transaction."""
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    
    print(f"\n📋 Transaction {tx_hash.hex()} Details:")
    print(f"   Status: {'✅ Success' if receipt['status'] == 1 else '❌ Failed'}")
    print(f"   Gas Used: {receipt['gasUsed']:,}")
    print(f"   Logs: {len(receipt['logs'])} events")
    
    factory_contract = w3.eth.contract(address=proxy_factory_address, abi=FACTORY_ABI_WITH_EVENTS)
    token_contract = w3.eth.contract(address=mock_token_address, abi=ERC20_ABI_WITH_EVENTS)
    
    # Decode each log
    for i, log in enumerate(receipt['logs']):
        print(f"\n   Log #{i}:")
        print(f"   Address: {log['address']}")
        
        # Try to decode as factory event
        try:
            decoded = factory_contract.events.ProxyWalletCreated().process_log(log)
            print(f"   ✨ ProxyWalletCreated Event!")
            print(f"      Owner: {decoded['args']['owner']}")
            print(f"      Wallet: {decoded['args']['wallet']}")
            continue
        except:
            pass
            
        # Try to decode as ERC20 Approval
        try:
            decoded = token_contract.events.Approval().process_log(log)
            print(f"   ✅ Approval Event!")
            print(f"      Owner: {decoded['args']['owner']}")
            print(f"      Spender: {decoded['args']['spender']}")
            print(f"      Value: {decoded['args']['value']}")
            continue
        except:
            pass
            
        # Raw log if can't decode
        print(f"   Topics: {[t.hex() for t in log['topics']]}")
        print(f"   Data: {log['data'].hex() if log['data'] else 'None'}")

async def trace_transaction(w3, tx_hash):
    """Get transaction trace to see all internal calls."""
    try:
        # Try to get trace (requires Hardhat with tracing enabled)
        trace = w3.provider.make_request('debug_traceTransaction', 
            [tx_hash.hex(), {"tracer": "callTracer"}])
        
        print(f"\n🔍 Transaction Trace for {tx_hash.hex()}:")
        
        def print_call(call, indent=0):
            prefix = "  " * indent
            print(f"{prefix}→ {call.get('type', 'CALL')} to {call.get('to', 'N/A')}")
            print(f"{prefix}  from: {call.get('from', 'N/A')}")
            if 'value' in call and int(call['value'], 16) > 0:
                print(f"{prefix}  value: {Web3.from_wei(int(call['value'], 16), 'ether')} ETH")
            if 'input' in call and len(call['input']) > 10:
                print(f"{prefix}  input: {call['input'][:10]}... ({len(call['input'])} chars)")
            if 'error' in call:
                print(f"{prefix}  ❌ ERROR: {call['error']}")
            
            # Print subcalls
            for subcall in call.get('calls', []):
                print_call(subcall, indent + 1)
        
        print_call(trace['result'])
        
    except Exception as e:
        print(f"\n⚠️  Could not get transaction trace: {e}")
        print("   (This is normal - tracing requires special node configuration)")

async def main():
    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
    
    # Initialize relayer
    relayer_account = Account.from_key(os.getenv("RELAYER_PRIVATE_KEY"))
    relayer = GSNRelayer(
        relay_hub_address=os.getenv("RELAY_HUB_ADDRESS"),
        relay_private_key=os.getenv("RELAYER_PRIVATE_KEY"),
        rpc_url=os.getenv("RPC_URL"),
        chain_id=int(os.getenv("CHAIN_ID"))
    )
    
    print("🔍 Verbose GSN Relayer Test")
    print("=" * 50)
    
    # Check relay status
    print("\n📊 Relay Status:")
    status = await relayer.get_relay_status()
    print(f"   Address: {status['address']}")
    print(f"   Ready: {status['ready']}")
    print(f"   Balance: {status['balance']} ETH")
    
    if status['ready']:
        print(f"   Stake: {status['stake']} tokens")
        print(f"   Owner: {status['owner']}")
    
    # Test 1: Create Proxy Wallet
    print("\n\n🏗️  Test 1: Creating Proxy Wallet")
    print("-" * 40)
    
    user_address = "0x90F79bf6EB2c4f870365E785982E1f101E93b906"  # Account #3
    proxy_factory = os.getenv("PROXY_WALLET_FACTORY_ADDRESS")
    
    try:
        result = await relayer.relay_proxy_wallet_call(
            target=proxy_factory,
            from_address=user_address,
            gas_limit=500000
        )
        
        if result['success']:
            print(f"✅ Relay call successful!")
            print(f"   Transaction: {result['tx_hash']}")
            
            # Decode logs to find proxy wallet creation
            await decode_relay_call_logs(w3, result['tx_hash'], proxy_factory, os.getenv("MOCK_TOKEN_ADDRESS"))
            
            # Try to get trace
            await trace_transaction(w3, result['tx_hash'])
            
            # Wait for confirmation
            await asyncio.sleep(2)
            
            # Get proxy wallet address from logs
            receipt = w3.eth.get_transaction_receipt(result['tx_hash'])
            proxy_wallet = None
            
            # Simple extraction of address from logs (assuming it's in the data)
            for log in receipt['logs']:
                if log['address'].lower() == proxy_factory.lower() and len(log['data']) >= 66:
                    # Extract address from data (assuming standard encoding)
                    proxy_wallet = '0x' + log['data'][-40:]
                    print(f"\n🏭 Proxy Wallet Created: {proxy_wallet}")
                    break
        else:
            print(f"❌ Relay call failed: {result['error']}")
            return
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Test 2: Relay Approval
    print("\n\n💰 Test 2: Relaying ERC20 Approval")
    print("-" * 40)
    
    mock_token = os.getenv("MOCK_TOKEN_ADDRESS")
    spender = "0x976EA74026E726554dB657fA54763abd0C3a0aa9"  # Random address
    amount = Web3.to_wei(100, 'ether')
    
    try:
        result = await relayer.relay_proxy_wallet_approval(
            target=proxy_factory,
            from_address=user_address,
            token_address=mock_token,
            spender=spender,
            amount=amount,
            gas_limit=800000
        )
        
        if result['success']:
            print(f"✅ Approval relay successful!")
            print(f"   Transaction: {result['tx_hash']}")
            
            # Decode logs to see approval
            await decode_relay_call_logs(w3, result['tx_hash'], proxy_factory, mock_token)
            
            # Try to get trace
            await trace_transaction(w3, result['tx_hash'])
            
        else:
            print(f"❌ Approval relay failed: {result['error']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n\n✅ Verbose test complete!")

if __name__ == "__main__":
    asyncio.run(main()) 