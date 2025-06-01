"""Core GSN Relayer implementation"""

import asyncio
from typing import Dict, Any, Optional, Tuple
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from hexbytes import HexBytes
from eth_abi.packed import encode_packed

from .config import config
from .abis import RELAY_HUB_ABI


class GSNRelayer:
    def __init__(self):
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(config.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {config.rpc_url}")
        
        # Initialize account
        self.account = Account.from_key(config.relayer_private_key)
        self.address = self.account.address
        
        # Initialize RelayHub contract
        self.relay_hub = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.relay_hub_address),
            abi=RELAY_HUB_ABI
        )
        
        print(f"Relayer initialized with address: {self.address}")
        print(f"Connected to network: Chain ID {self.w3.eth.chain_id}")
    
    async def get_relay_status(self) -> Dict[str, Any]:
        """Get the current status of this relay"""
        try:
            relay_info = self.relay_hub.functions.getRelay(self.address).call()
            return {
                "address": self.address,
                "totalStake": relay_info[0],
                "unstakeDelay": relay_info[1],
                "unstakeTime": relay_info[2],
                "owner": relay_info[3],
                "state": relay_info[4],
                "stateText": self._get_relay_state_text(relay_info[4])
            }
        except Exception as e:
            return {
                "address": self.address,
                "error": str(e),
                "state": 0,
                "stateText": "Unknown"
            }
    
    def _get_relay_state_text(self, state: int) -> str:
        """Convert relay state enum to text"""
        states = {
            0: "Unknown",
            1: "Staked",
            2: "Registered",
            3: "Removed"
        }
        return states.get(state, "Unknown")
    
    async def stake_relay(self, stake_amount_ether: Optional[str] = None, unstake_delay: Optional[int] = None) -> str:
        """Stake ETH for the relay"""
        stake_amount = Web3.to_wei(stake_amount_ether or config.stake_amount_ether, 'ether')
        unstake_delay = unstake_delay or config.unstake_delay_seconds
        
        # Use owner account for staking
        owner_account = Account.from_key(config.owner_private_key)
        owner_address = owner_account.address
        
        # Check owner balance
        balance = self.w3.eth.get_balance(owner_address)
        if balance < stake_amount:
            raise ValueError(f"Insufficient owner balance. Have {Web3.from_wei(balance, 'ether')} ETH, need {Web3.from_wei(stake_amount, 'ether')} ETH")
        
        print(f"Owner {owner_address} staking for relay {self.address}")
        
        # Build transaction
        tx = self.relay_hub.functions.stake(
            self.address,  # Relay address to stake for
            unstake_delay
        ).build_transaction({
            'from': owner_address,  # Owner sends the transaction
            'value': stake_amount,
            'gas': 100000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(owner_address),
        })
        
        # Sign with owner account
        signed_tx = owner_account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"Staking transaction sent: {tx_hash.hex()}")
        
        # Wait for confirmation
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print(f"Successfully staked {Web3.from_wei(stake_amount, 'ether')} ETH")
            return tx_hash.hex()
        else:
            raise Exception("Staking transaction failed")
    
    async def register_relay(self, transaction_fee: Optional[int] = None, url: Optional[str] = None) -> str:
        """Register the relay after staking"""
        transaction_fee = transaction_fee or config.relay_fee_percentage
        url = url or config.relay_url
        
        # Check if already staked
        relay_info = await self.get_relay_status()
        if relay_info.get("state", 0) < 1:
            raise ValueError("Relay must be staked before registering")
        
        # Build transaction
        tx = self.relay_hub.functions.registerRelay(
            transaction_fee,
            url
        ).build_transaction({
            'from': self.address,
            'gas': 150000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.address),
        })
        
        # Sign and send transaction
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"Registration transaction sent: {tx_hash.hex()}")
        
        # Wait for confirmation
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print(f"Successfully registered relay with {transaction_fee}% fee at {url}")
            return tx_hash.hex()
        else:
            raise Exception("Registration transaction failed")
    
    async def can_relay(self, relay_request: Dict[str, Any]) -> Tuple[int, bytes]:
        """Check if a relay request can be fulfilled"""
        status, context = self.relay_hub.functions.canRelay(
            self.address,
            relay_request['from'],
            relay_request['to'],
            HexBytes(relay_request['encodedFunction']),
            relay_request['transactionFee'],
            relay_request['gasPrice'],
            relay_request['gasLimit'],
            relay_request['nonce'],
            HexBytes(relay_request['signature']),
            HexBytes(relay_request.get('approvalData', '0x'))
        ).call()
        
        return status, context
    
    async def relay_call(self, relay_request: Dict[str, Any]) -> str:
        """Execute a relay call"""
        # First check if we can relay
        status, context = await self.can_relay(relay_request)
        if status != 0:
            raise ValueError(f"Cannot relay: status {status}")
        
        # Calculate required gas using the same formula as RelayHub
        # Constants from RelayHub contract
        GAS_OVERHEAD = 48204
        GAS_RESERVE = 100000
        ACCEPT_RELAYED_CALL_MAX_GAS = 50000
        PRE_RELAYED_CALL_MAX_GAS = 100000
        POST_RELAYED_CALL_MAX_GAS = 100000
        
        required_gas = (
            GAS_OVERHEAD + 
            GAS_RESERVE + 
            ACCEPT_RELAYED_CALL_MAX_GAS + 
            PRE_RELAYED_CALL_MAX_GAS + 
            POST_RELAYED_CALL_MAX_GAS + 
            relay_request['gasLimit']
        )
        
        # Add some extra buffer for safety
        total_gas = int(required_gas * 1.1)
        
        # Build the relay transaction
        tx = self.relay_hub.functions.relayCall(
            relay_request['from'],
            relay_request['to'],
            HexBytes(relay_request['encodedFunction']),
            relay_request['transactionFee'],
            relay_request['gasPrice'],
            relay_request['gasLimit'],
            relay_request['nonce'],
            HexBytes(relay_request['signature']),
            HexBytes(relay_request.get('approvalData', '0x'))
        ).build_transaction({
            'from': self.address,
            'gas': total_gas,
            'gasPrice': relay_request['gasPrice'],
            'nonce': self.w3.eth.get_transaction_count(self.address),
        })
        
        # Sign and send transaction
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"Relay transaction sent: {tx_hash.hex()}")
        
        # Wait for confirmation
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print(f"Successfully relayed transaction")
            # Parse TransactionRelayed event
            for log in receipt.logs:
                try:
                    event = self.relay_hub.events.TransactionRelayed().process_log(log)
                    print(f"Relay status: {event['args']['status']}, charge: {event['args']['charge']}")
                except:
                    pass
            return tx_hash.hex()
        else:
            raise Exception("Relay transaction failed")
    
    def verify_relay_request_signature(self, relay_request: Dict[str, Any]) -> bool:
        """Verify the signature of a relay request"""
        # Reconstruct the message that was signed
        packed = encode_packed(
            ['string', 'address', 'address', 'bytes', 'uint256', 'uint256', 'uint256', 'uint256', 'address'],
            ['rlx:', relay_request['from'], relay_request['to'], HexBytes(relay_request['encodedFunction']), 
             relay_request['transactionFee'], relay_request['gasPrice'], relay_request['gasLimit'], 
             relay_request['nonce'], config.relay_hub_address]
        )
        
        # Hash the concatenation of packed and relay address (matching abi.encodePacked in RelayHub)
        relay_address_bytes = Web3.to_bytes(hexstr=self.address)
        concatenated = packed + relay_address_bytes
        hashed_message = Web3.keccak(concatenated)
        
        # Recover the signer - GSN v1 RelayHub uses toEthSignedMessageHash
        try:
            # The RelayHub applies EIP-191 prefix, so we need to recover from the prefixed message
            from eth_account.messages import encode_defunct
            prefixed_message = encode_defunct(hashed_message)
            recovered = Account.recover_message(prefixed_message, signature=HexBytes(relay_request['signature']))
            return recovered.lower() == relay_request['from'].lower()
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False


# Global relayer instance
relayer = GSNRelayer() 