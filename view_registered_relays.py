"""View registered relays on the network, filtering out removed relays"""

import os
import sys
from web3 import Web3
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List, Set

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import config
from src.abis import RELAY_HUB_ABI

load_dotenv()


def get_relay_events(w3: Web3, relay_hub, from_block: int = 0, to_block: str = 'latest'):
    """Get all relay events from the blockchain"""
    
    # Get RelayAdded events using get_logs instead of create_filter
    relay_added_events = relay_hub.events.RelayAdded.get_logs(
        from_block=from_block,
        to_block=to_block
    )
    
    # Get RelayRemoved events (if the event exists in ABI)
    relay_removed_events = []
    try:
        relay_removed_events = relay_hub.events.RelayRemoved.get_logs(
            from_block=from_block,
            to_block=to_block
        )
    except:
        # RelayRemoved event might not be in our ABI
        pass
    
    return relay_added_events, relay_removed_events


def get_active_relays(w3: Web3, relay_hub) -> Dict[str, Dict]:
    """Get all active relays by filtering out removed ones"""
    
    print("Fetching relay events from blockchain...")
    
    # Get all events
    added_events, removed_events = get_relay_events(w3, relay_hub)
    
    # Track removed relays
    removed_relays: Set[str] = set()
    for event in removed_events:
        removed_relays.add(event['args']['relay'].lower())
    
    # Build active relay list
    active_relays: Dict[str, Dict] = {}
    
    for event in added_events:
        relay_address = event['args']['relay'].lower()
        
        # Skip if relay was removed
        if relay_address in removed_relays:
            continue
        
        # Store relay info (latest registration wins if re-registered)
        active_relays[relay_address] = {
            'address': event['args']['relay'],
            'owner': event['args']['owner'],
            'transactionFee': event['args']['transactionFee'],
            'stake': event['args']['stake'],
            'unstakeDelay': event['args']['unstakeDelay'],
            'url': event['args']['url'],
            'blockNumber': event['blockNumber'],
            'transactionHash': event['transactionHash'].hex(),
            'timestamp': None  # We'll skip timestamp to avoid POA issues
        }
    
    return active_relays


def check_relay_status(relay_hub, relay_address: str) -> Dict:
    """Check current on-chain status of a relay"""
    try:
        relay_info = relay_hub.functions.getRelay(Web3.to_checksum_address(relay_address)).call()
        return {
            'totalStake': relay_info[0],
            'unstakeDelay': relay_info[1],
            'unstakeTime': relay_info[2],
            'owner': relay_info[3],
            'state': relay_info[4],
            'stateText': get_relay_state_text(relay_info[4])
        }
    except Exception as e:
        return {'error': str(e)}


def get_relay_state_text(state: int) -> str:
    """Convert relay state enum to text"""
    states = {
        0: "Unknown",
        1: "Staked", 
        2: "Registered",
        3: "Removed"
    }
    return states.get(state, "Unknown")


def format_wei_to_ether(wei_value: int) -> str:
    """Format wei value to ether with 4 decimal places"""
    return f"{Web3.from_wei(wei_value, 'ether'):.4f}"


def main():
    """Main function to view registered relays"""
    
    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(config.rpc_url))
    if not w3.is_connected():
        print(f"Failed to connect to {config.rpc_url}")
        return
    
    print(f"Connected to network: Chain ID {w3.eth.chain_id}")
    
    # Initialize RelayHub contract
    relay_hub = w3.eth.contract(
        address=Web3.to_checksum_address(config.relay_hub_address),
        abi=RELAY_HUB_ABI + [
            # Add RelayRemoved event to ABI if not present
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "relay", "type": "address"},
                    {"indexed": False, "name": "unstakeTime", "type": "uint256"}
                ],
                "name": "RelayRemoved",
                "type": "event"
            }
        ]
    )
    
    print(f"RelayHub address: {config.relay_hub_address}\n")
    
    # Get active relays
    active_relays = get_active_relays(w3, relay_hub)
    
    if not active_relays:
        print("No active relays found on the network.")
        return
    
    print(f"Found {len(active_relays)} active relay(s):\n")
    print("=" * 100)
    
    # Display each relay
    for i, (relay_address, relay_info) in enumerate(active_relays.items(), 1):
        print(f"\n{i}. Relay: {relay_info['address']}")
        print(f"   Owner: {relay_info['owner']}")
        print(f"   URL: {relay_info['url']}")
        print(f"   Transaction Fee: {relay_info['transactionFee']}%")
        print(f"   Stake: {format_wei_to_ether(relay_info['stake'])} ETH")
        print(f"   Unstake Delay: {relay_info['unstakeDelay']} seconds ({relay_info['unstakeDelay'] / 86400:.1f} days)")
        print(f"   Registered at: Block #{relay_info['blockNumber']}")
        print(f"   TX: {relay_info['transactionHash']}")
        
        # Check current on-chain status
        current_status = check_relay_status(relay_hub, relay_address)
        if 'error' not in current_status:
            print(f"   Current State: {current_status['stateText']} ({current_status['state']})")
            
            # Check if stake amount changed
            if current_status['totalStake'] != relay_info['stake']:
                print(f"   Current Stake: {format_wei_to_ether(current_status['totalStake'])} ETH (changed from registration)")
        else:
            print(f"   Current State: Error checking status - {current_status['error']}")
        
        print("-" * 100)
    
    # Summary
    print(f"\nSummary:")
    print(f"Total active relays: {len(active_relays)}")
    
    # Group by owner
    owners = {}
    for relay in active_relays.values():
        owner = relay['owner'].lower()
        if owner not in owners:
            owners[owner] = []
        owners[owner].append(relay['address'])
    
    print(f"Unique owners: {len(owners)}")
    for owner, relays in owners.items():
        print(f"  {owner}: {len(relays)} relay(s)")


if __name__ == "__main__":
    main() 