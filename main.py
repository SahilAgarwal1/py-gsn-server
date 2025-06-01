"""Main entry point for GSN Relayer"""

import asyncio
import uvicorn
from src.config import config
from src.api.server import app


async def main():
    """Start the GSN relayer server"""
    print(f"Starting GSN Relayer on {config.host}:{config.port}")
    
    config_dict = {
        "app": "src.api.server:app",
        "host": config.host,
        "port": config.port,
        "reload": True,
        "log_level": "info"
    }
    
    await uvicorn.Server(uvicorn.Config(**config_dict)).serve()


if __name__ == "__main__":
    asyncio.run(main())
