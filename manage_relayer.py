"""CLI tool to manage the GSN relayer"""

import asyncio
import argparse
import sys
from src.config import config
from src.relayer import relayer


async def status():
    """Show relayer status"""
    status = await relayer.get_relay_status()
    balance = relayer.w3.eth.get_balance(relayer.address)
    
    print(f"\n🔍 Relayer Status")
    print(f"─" * 40)
    print(f"Address: {status['address']}")
    print(f"State: {status['stateText']} ({status['state']})")
    print(f"Balance: {relayer.w3.from_wei(balance, 'ether')} ETH")
    
    if status.get('totalStake'):
        print(f"Total Stake: {relayer.w3.from_wei(status['totalStake'], 'ether')} ETH")
        print(f"Unstake Delay: {status['unstakeDelay']} seconds")
        print(f"Owner: {status['owner']}")
    
    if status['state'] == 2:
        print(f"\n✅ Relayer is ready to relay transactions!")
    else:
        print(f"\n⚠️  Relayer needs to be staked and registered")
    print()


async def stake(amount: str = None):
    """Stake the relayer"""
    amount = amount or config.stake_amount_ether
    
    print(f"\n💰 Staking {amount} ETH...")
    try:
        tx_hash = await relayer.stake_relay(amount)
        print(f"✅ Staking successful! TX: {tx_hash}")
    except Exception as e:
        print(f"❌ Staking failed: {e}")
        sys.exit(1)


async def register(fee: int = None, url: str = None):
    """Register the relayer"""
    fee = fee or config.relay_fee_percentage
    url = url or config.relay_url
    
    print(f"\n📝 Registering relayer with {fee}% fee at {url}...")
    try:
        tx_hash = await relayer.register_relay(fee, url)
        print(f"✅ Registration successful! TX: {tx_hash}")
    except Exception as e:
        print(f"❌ Registration failed: {e}")
        sys.exit(1)


async def main():
    parser = argparse.ArgumentParser(description='Manage GSN Relayer')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Status command
    subparsers.add_parser('status', help='Show relayer status')
    
    # Stake command
    stake_parser = subparsers.add_parser('stake', help='Stake ETH for the relayer')
    stake_parser.add_argument('--amount', type=str, help='Amount of ETH to stake (default: from config)')
    
    # Register command
    register_parser = subparsers.add_parser('register', help='Register the relayer')
    register_parser.add_argument('--fee', type=int, help='Transaction fee percentage (default: from config)')
    register_parser.add_argument('--url', type=str, help='Relayer URL (default: from config)')
    
    # Setup command (stake + register)
    setup_parser = subparsers.add_parser('setup', help='Setup relayer (stake + register)')
    setup_parser.add_argument('--amount', type=str, help='Amount of ETH to stake')
    setup_parser.add_argument('--fee', type=int, help='Transaction fee percentage')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'status':
        await status()
    elif args.command == 'stake':
        await stake(args.amount)
    elif args.command == 'register':
        await register(args.fee, args.url)
    elif args.command == 'setup':
        # First stake
        await stake(args.amount)
        # Then register
        await register(args.fee)
        # Show final status
        await status()


if __name__ == "__main__":
    asyncio.run(main()) 