# Python GSN Relayer

A simple Gas Station Network (GSN) relayer server implementation in Python for Ethereum/Polygon networks.

## Features

- Stake and register relay on GSN RelayHub
- Relay meta-transactions for users
- Support for ProxyWalletFactory proxy calls
- REST API for easy integration
- Automatic signature verification
- Support for ERC20 approvals and ERC1155 setApprovalForAll

## Prerequisites

- Python 3.12+
- An Ethereum/Polygon node RPC URL
- ETH/MATIC for staking and gas fees
- A private key for the relayer account

## Installation

1. Clone the repository and navigate to the py-gsn-relayer directory:
```bash
cd py-gsn-relayer
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

4. Copy the environment example and configure:
```bash
cp env.example .env
```

5. Edit `.env` with your configuration:
```env
RPC_URL=https://polygon-rpc.com  # Your RPC URL
RELAYER_PRIVATE_KEY=your_private_key_here  # Without 0x prefix
RELAY_HUB_ADDRESS=0xD216153c06E857cD7f72665E0aF1d7D82172F494
PROXY_WALLET_FACTORY_ADDRESS=0xaB45c5A4B0c941a2F231C04C3f49182e1A254052
```

## Usage

### Initial Setup

1. Check relayer status:
```bash
python manage_relayer.py status
```

2. Stake and register the relayer (one-time setup):
```bash
# Quick setup with defaults
python manage_relayer.py setup

# Or with custom parameters
python manage_relayer.py setup --amount 2 --fee 5
```

3. Or stake and register separately:
```bash
# Stake 1 ETH
python manage_relayer.py stake --amount 1

# Register with 10% fee
python manage_relayer.py register --fee 10
```

### Starting the Relayer

```bash
python main.py
```

The server will start on `http://localhost:8090` by default.

### API Endpoints

#### Health Check
```bash
curl http://localhost:8090/
```

#### Get Relayer Status
```bash
curl http://localhost:8090/status
```

#### Stake Relay (Required first step)
```bash
curl -X POST http://localhost:8090/stake \
  -H "Content-Type: application/json" \
  -d '{"stake_amount_ether": "1"}'
```

#### Register Relay (Required after staking)
```bash
curl -X POST http://localhost:8090/register \
  -H "Content-Type: application/json" \
  -d '{"transaction_fee": 10}'
```

#### Relay a Transaction
```bash
curl -X POST http://localhost:8090/relay \
  -H "Content-Type: application/json" \
  -d '{
    "from": "0xUserAddress",
    "to": "0xContractAddress",
    "encodedFunction": "0x...",
    "transactionFee": 10,
    "gasPrice": 30000000000,
    "gasLimit": 500000,
    "nonce": 0,
    "signature": "0x..."
  }'
```

#### Relay Proxy Wallet Calls (Simplified)
```bash
curl -X POST http://localhost:8090/relay/proxy-wallet \
  -H "Content-Type: application/json" \
  -d '{
    "user_address": "0xUserAddress",
    "proxy_calls": [
      {
        "typeCode": 2,
        "to": "0xUSDCAddress",
        "value": "0",
        "data": "0x095ea7b3..."
      }
    ],
    "signature": "0x...",
    "gas_limit": 800000
  }'
```

## Example: Relaying Polymarket Approvals

Here's how to relay the approval transactions like in the Polymarket example:

```python
import requests
from web3 import Web3

# Configuration
RELAYER_URL = "http://localhost:8090"
USER_ADDRESS = "0xYourAddress"
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

# Encode approve function
def encode_approve(spender, amount):
    selector = Web3.keccak(text="approve(address,uint256)")[:4]
    params = Web3.solidity_keccak(['address', 'uint256'], [spender, amount])
    return selector + params

# Create proxy calls for approvals
proxy_calls = []
spenders = [
    "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045",
    "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E",
]

for spender in spenders:
    proxy_calls.append({
        "typeCode": 2,  # CALL
        "to": USDC_ADDRESS,
        "value": "0",
        "data": encode_approve(spender, 2**256 - 1).hex()
    })

# Sign the message (implement your signing logic)
signature = sign_message(...)  

# Send relay request
response = requests.post(
    f"{RELAYER_URL}/relay/proxy-wallet",
    json={
        "user_address": USER_ADDRESS,
        "proxy_calls": proxy_calls,
        "signature": signature,
        "gas_limit": 800000
    }
)

print(response.json())
```

## Architecture

The relayer consists of:

1. **Core Relayer (`src/relayer.py`)**: Handles blockchain interactions, staking, registration, and relaying
2. **API Server (`src/api/server.py`)**: FastAPI server exposing REST endpoints
3. **Models (`src/api/models.py`)**: Pydantic models for request/response validation
4. **Encoders (`src/encoders.py`)**: Helper functions for encoding contract calls
5. **ABIs (`src/abis/`)**: Contract ABIs for RelayHub and ProxyWalletFactory

## Security Considerations

- Keep your relayer private key secure
- Monitor your relayer balance for gas fees
- Implement rate limiting in production
- Add authentication for sensitive endpoints
- Validate all inputs thoroughly

## Development

To run in development mode with auto-reload:
```bash
python main.py
```

To run tests:
```bash
pytest
```

## License

MIT
