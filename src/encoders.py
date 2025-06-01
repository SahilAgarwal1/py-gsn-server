"""Helper functions for encoding contract calls"""

from web3 import Web3
from eth_abi import encode
from hexbytes import HexBytes


def encode_erc20_approve(spender: str, amount: int) -> str:
    """Encode an ERC20 approve call"""
    # Function selector for approve(address,uint256)
    selector = Web3.keccak(text="approve(address,uint256)")[:4]
    
    # Encode parameters
    params = encode(['address', 'uint256'], [Web3.to_checksum_address(spender), amount])
    
    return HexBytes(selector + params).hex()


def encode_erc1155_set_approval_for_all(operator: str, approved: bool) -> str:
    """Encode an ERC1155 setApprovalForAll call"""
    # Function selector for setApprovalForAll(address,bool)
    selector = Web3.keccak(text="setApprovalForAll(address,bool)")[:4]
    
    # Encode parameters
    params = encode(['address', 'bool'], [Web3.to_checksum_address(operator), approved])
    
    return HexBytes(selector + params).hex()


def encode_proxy_calls(calls: list) -> bytes:
    """Encode proxy calls for ProxyWalletFactory"""
    # Encode the array of ProxyCall structs
    encoded_calls = []
    for call in calls:
        encoded_calls.append((
            call['typeCode'],
            Web3.to_checksum_address(call['to']),
            int(call.get('value', 0)),
            HexBytes(call['data'])
        ))
    
    # The proxy function takes an array of structs
    return encode(
        ['(uint8,address,uint256,bytes)[]'],
        [encoded_calls]
    ) 