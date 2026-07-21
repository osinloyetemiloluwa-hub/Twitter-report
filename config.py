"""
Configuration management for Twitter Alert Bot
"""
import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List

load_dotenv()

@dataclass
class BotConfig:
    """Bot configuration settings"""
    discord_token: str
    poll_interval: int
    debug: bool
    twitter_sessions: List[str]

    @classmethod
    def from_env(cls) -> 'BotConfig':
        """Load configuration from environment variables"""
        return cls(
            discord_token=os.getenv('DISCORD_TOKEN', ''),
            poll_interval=int(os.getenv('POLL_INTERVAL', '60')),
            debug=os.getenv('DEBUG', 'False').lower() == 'true',
            twitter_sessions=cls._parse_sessions()
        )

    @staticmethod
    def _parse_sessions() -> List[str]:
        """Parse Twitter session cookies from environment"""
        sessions_str = os.getenv('TWITTER_SESSIONS', '[]')
        if sessions_str == '[]' or not sessions_str:
            return []
        try:
            import json
            return json.loads(sessions_str)
        except:
            return []

    def validate(self) -> bool:
        """Validate that required configuration is present"""
        if not self.discord_token:
            print("Error: DISCORD_TOKEN is not set!")
            print("For local: Add it to your .env file")
            print("For Render: Add it in Render Dashboard > Environment Variables")
            return False
        return True

# Global config instance
config = BotConfig.from_env()
