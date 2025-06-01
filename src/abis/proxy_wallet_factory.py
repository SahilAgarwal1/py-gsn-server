"""ProxyWalletFactory ABI - Essential functions for proxy calls"""

PROXY_WALLET_FACTORY_ABI = [
    {
        "constant": False,
        "inputs": [
            {
                "components": [
                    {"name": "typeCode", "type": "uint8"},
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "data", "type": "bytes"}
                ],
                "name": "calls",
                "type": "tuple[]"
            }
        ],
        "name": "proxy",
        "outputs": [
            {"name": "returnValues", "type": "bytes[]"}
        ],
        "payable": True,
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "getHubAddr",
        "outputs": [{"name": "", "type": "address"}],
        "payable": False,
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "relay", "type": "address"},
            {"name": "from", "type": "address"},
            {"name": "encodedFunction", "type": "bytes"},
            {"name": "transactionFee", "type": "uint256"},
            {"name": "gasPrice", "type": "uint256"},
            {"name": "gasLimit", "type": "uint256"},
            {"name": "nonce", "type": "uint256"},
            {"name": "approvalData", "type": "bytes"},
            {"name": "maxPossibleCharge", "type": "uint256"}
        ],
        "name": "acceptRelayedCall",
        "outputs": [
            {"name": "", "type": "uint256"},
            {"name": "", "type": "bytes"}
        ],
        "payable": False,
        "type": "function"
    }
]

# ERC20 ABI for approve function
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "type": "function"
    }
]

# ERC1155 ABI for setApprovalForAll function
ERC1155_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "operator", "type": "address"},
            {"name": "approved", "type": "bool"}
        ],
        "name": "setApprovalForAll",
        "outputs": [],
        "payable": False,
        "type": "function"
    }
] 