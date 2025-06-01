"""Configuration for GSN Relayer"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # RPC and blockchain settings
    rpc_url: str = os.getenv("RPC_URL", "https://polygon-rpc.com")
    chain_id: int = int(os.getenv("CHAIN_ID", "137"))  # Default to Polygon
    
    # Relayer settings
    relayer_private_key: str = os.getenv("RELAYER_PRIVATE_KEY", "")
    relay_hub_address: str = os.getenv("RELAY_HUB_ADDRESS", "0xD216153c06E857cD7f72665E0aF1d7D82172F494")
    proxy_wallet_factory_address: str = os.getenv("PROXY_WALLET_FACTORY_ADDRESS", "0xaB45c5A4B0c941a2F231C04C3f49182e1A254052")
    
    # Server settings
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8090"))
    
    # Relay configuration
    relay_fee_percentage: int = int(os.getenv("RELAY_FEE_PERCENTAGE", "10"))
    relay_url: str = os.getenv("RELAY_URL", "http://localhost:8090")
    
    # Staking settings
    stake_amount_ether: str = os.getenv("STAKE_AMOUNT_ETHER", "1")
    unstake_delay_seconds: int = int(os.getenv("UNSTAKE_DELAY_SECONDS", str(14 * 24 * 60 * 60)))  # 2 weeks
    
    # Gas settings
    max_gas_price_gwei: int = int(os.getenv("MAX_GAS_PRICE_GWEI", "200"))
    gas_limit_multiplier: float = float(os.getenv("GAS_LIMIT_MULTIPLIER", "1.2"))
    
    # Owner configuration (for staking)
    owner_private_key: str = os.getenv("OWNER_PRIVATE_KEY", relayer_private_key)
    
    def validate(self):
        """Validate required configuration"""
        if not self.relayer_private_key:
            raise ValueError("RELAYER_PRIVATE_KEY is required")
        if not self.relayer_private_key.startswith("0x"):
            self.relayer_private_key = f"0x{self.relayer_private_key}"
        

config = Config()
# config.validate() 