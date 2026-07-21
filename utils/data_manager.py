"""
Data persistence manager for Twitter Alert Bot
Uses JSON file storage for simplicity
"""
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DATA_FILE = os.path.join(DATA_DIR, 'database.json')

@dataclass
class MonitoredAccount:
    """Represents a monitored Twitter account"""
    username: str
    display_name: str
    avatar_url: str
    last_tweet_id: str
    guild_id: int
    channel_ids: List[int]
    added_at: str

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'MonitoredAccount':
        return cls(**data)

@dataclass
class GuildSettings:
    """Settings for a Discord guild"""
    guild_id: int
    default_channel_id: Optional[int] = None
    notification_channels: List[int] = None
    poll_interval: int = 60
    include_replies: bool = False
    include_retweets: bool = False

    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = []

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'GuildSettings':
        return cls(**data)

class DataManager:
    """Manages data persistence for the bot"""

    def __init__(self):
        self._ensure_data_dir()
        self._data = self._load_data()

    def _ensure_data_dir(self):
        """Ensure the data directory exists"""
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

    def _load_data(self) -> Dict:
        """Load data from JSON file"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return self._get_default_data()

    def _get_default_data(self) -> Dict:
        """Get default data structure"""
        return {
            'accounts': {},
            'guilds': {},
            'last_updated': datetime.utcnow().isoformat()
        }

    def _save_data(self):
        """Save data to JSON file"""
        self._data['last_updated'] = datetime.utcnow().isoformat()
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving data: {e}")

    # Account Management
    def add_account(self, account: MonitoredAccount) -> bool:
        """Add or update a monitored account"""
        key = self._account_key(account.guild_id, account.username)
        self._data['accounts'][key] = account.to_dict()
        self._save_data()
        return True

    def remove_account(self, guild_id: int, username: str) -> bool:
        """Remove a monitored account"""
        key = self._account_key(guild_id, username.lower())
        if key in self._data['accounts']:
            del self._data['accounts'][key]
            self._save_data()
            return True
        return False

    def get_account(self, guild_id: int, username: str) -> Optional[MonitoredAccount]:
        """Get a monitored account"""
        key = self._account_key(guild_id, username.lower())
        if key in self._data['accounts']:
            return MonitoredAccount.from_dict(self._data['accounts'][key])
        return None

    def get_all_accounts(self) -> List[MonitoredAccount]:
        """Get all monitored accounts"""
        accounts = []
        for data in self._data['accounts'].values():
            accounts.append(MonitoredAccount.from_dict(data))
        return accounts

    def get_accounts_by_guild(self, guild_id: int) -> List[MonitoredAccount]:
        """Get all monitored accounts for a guild"""
        accounts = []
        for data in self._data['accounts'].values():
            if data['guild_id'] == guild_id:
                accounts.append(MonitoredAccount.from_dict(data))
        return accounts

    def update_account_tweet_id(self, guild_id: int, username: str, tweet_id: str):
        """Update the last tweet ID for an account"""
        account = self.get_account(guild_id, username)
        if account:
            account.last_tweet_id = tweet_id
            self.add_account(account)

    @staticmethod
    def _account_key(guild_id: int, username: str) -> str:
        """Generate a unique key for an account"""
        return f"{guild_id}_{username.lower()}"

    # Channel Management
    def add_channel_to_account(self, guild_id: int, username: str, channel_id: int):
        """Add a channel to receive notifications for an account"""
        account = self.get_account(guild_id, username)
        if account and channel_id not in account.channel_ids:
            account.channel_ids.append(channel_id)
            self.add_account(account)

    def remove_channel_from_account(self, guild_id: int, username: str, channel_id: int):
        """Remove a channel from receiving notifications"""
        account = self.get_account(guild_id, username)
        if account and channel_id in account.channel_ids:
            account.channel_ids.remove(channel_id)
            self.add_account(account)

    # Guild Settings
    def get_guild_settings(self, guild_id: int) -> GuildSettings:
        """Get or create guild settings"""
        if str(guild_id) in self._data['guilds']:
            return GuildSettings.from_dict(self._data['guilds'][str(guild_id)])
        return GuildSettings(guild_id=guild_id)

    def update_guild_settings(self, settings: GuildSettings):
        """Update guild settings"""
        self._data['guilds'][str(settings.guild_id)] = settings.to_dict()
        self._save_data()

    def set_default_channel(self, guild_id: int, channel_id: int):
        """Set the default notification channel for a guild"""
        settings = self.get_guild_settings(guild_id)
        settings.default_channel_id = channel_id
        if channel_id not in settings.notification_channels:
            settings.notification_channels.append(channel_id)
        self.update_guild_settings(settings)
