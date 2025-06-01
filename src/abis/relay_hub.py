"""RelayHub ABI - Essential functions for GSN relayer"""

RELAY_HUB_ABI = [
    # Stake management
    {
        "constant": False,
        "inputs": [
            {"name": "relay", "type": "address"},
            {"name": "unstakeDelay", "type": "uint256"}
        ],
        "name": "stake",
        "outputs": [],
        "payable": True,
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "transactionFee", "type": "uint256"},
            {"name": "url", "type": "string"}
        ],
        "name": "registerRelay",
        "outputs": [],
        "payable": False,
        "type": "function"
    },
    # Relay functions
    {
        "constant": False,
        "inputs": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "encodedFunction", "type": "bytes"},
            {"name": "transactionFee", "type": "uint256"},
            {"name": "gasPrice", "type": "uint256"},
            {"name": "gasLimit", "type": "uint256"},
            {"name": "nonce", "type": "uint256"},
            {"name": "signature", "type": "bytes"},
            {"name": "approvalData", "type": "bytes"}
        ],
        "name": "relayCall",
        "outputs": [],
        "payable": False,
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "relay", "type": "address"},
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "encodedFunction", "type": "bytes"},
            {"name": "transactionFee", "type": "uint256"},
            {"name": "gasPrice", "type": "uint256"},
            {"name": "gasLimit", "type": "uint256"},
            {"name": "nonce", "type": "uint256"},
            {"name": "signature", "type": "bytes"},
            {"name": "approvalData", "type": "bytes"}
        ],
        "name": "canRelay",
        "outputs": [
            {"name": "status", "type": "uint256"},
            {"name": "recipientContext", "type": "bytes"}
        ],
        "payable": False,
        "type": "function"
    },
    # View functions
    {
        "constant": True,
        "inputs": [{"name": "from", "type": "address"}],
        "name": "getNonce",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "relay", "type": "address"}],
        "name": "getRelay",
        "outputs": [
            {"name": "totalStake", "type": "uint256"},
            {"name": "unstakeDelay", "type": "uint256"},
            {"name": "unstakeTime", "type": "uint256"},
            {"name": "owner", "type": "address"},
            {"name": "state", "type": "uint8"}
        ],
        "payable": False,
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "target", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "type": "function"
    },
    # Events
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "relay", "type": "address"},
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "selector", "type": "bytes4"},
            {"indexed": False, "name": "status", "type": "uint8"},
            {"indexed": False, "name": "charge", "type": "uint256"}
        ],
        "name": "TransactionRelayed",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "relay", "type": "address"},
            {"indexed": False, "name": "stake", "type": "uint256"},
            {"indexed": False, "name": "unstakeDelay", "type": "uint256"}
        ],
        "name": "Staked",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "relay", "type": "address"},
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": False, "name": "transactionFee", "type": "uint256"},
            {"indexed": False, "name": "stake", "type": "uint256"},
            {"indexed": False, "name": "unstakeDelay", "type": "uint256"},
            {"indexed": False, "name": "url", "type": "string"}
        ],
        "name": "RelayAdded",
        "type": "event"
    }
] 