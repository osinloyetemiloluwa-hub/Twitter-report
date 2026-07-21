# Twitter Alert Bot for Discord - Specification

## Project Overview

- **Project Name**: Twitter Alert Bot
- **Type**: Discord.py Bot with Twitter Integration
- **Core Functionality**: A Discord bot that monitors Twitter/X accounts and sends rich embed alerts to selected Discord channels whenever monitored accounts post new content
- **Target Users**: Discord server administrators and community managers who want real-time Twitter notifications

## Desired Visual Format

The bot should generate Discord embeds matching the reference image format:
- Dark embed with blue accent bar on the left
- Author name (bold white) and handle (light blue)
- Profile picture thumbnail
- Full post content with emoji
- Post images displayed inline
- Engagement metrics (replies, retweets, likes, views) with icons
- Timestamp and "Open in X" link

## Technical Stack

- **Language**: Python 3.10+
- **Discord Framework**: discord.py (v2.x with slash commands)
- **Twitter Scraping**: snscraper (no API key required)
- **Async Support**: asyncio, aiohttp
- **Data Storage**: JSON file-based persistence

## Functionality Specification

### Core Features

1. **Twitter Account Management**
   - Add Twitter accounts to monitor via slash command
   - Remove accounts from monitoring
   - List all monitored accounts
   - Support for both username and full URL input

2. **Channel Configuration**
   - Set notification channels per server
   - Multiple channels per server supported
   - Channel selection via slash command

3. **Post Monitoring**
   - Real-time polling (configurable interval, default 60 seconds)
   - Track latest tweet ID to avoid duplicates
   - Support for tweets, replies, retweets (configurable)
   - Image/media extraction

4. **Rich Embed Generation**
   - Author info (name, handle, avatar)
   - Post content with preserved formatting
   - Media attachments (images, videos indicated)
   - Engagement stats (replies, retweets, likes, views)
   - Timestamp
   - Direct link to post

### Slash Commands

| Command | Description | Options |
|---------|-------------|---------|
| `/twitter add <username> [channel]` | Add account to monitor | username (required), channel (optional) |
| `/twitter remove <username>` | Remove account from monitoring | username (required) |
| `/twitter list` | List all monitored accounts | none |
| `/twitter channel <channel>` | Set default notification channel | channel (required) |
| `/twitter settings` | View current settings | none |
| `/twitter help` | Show help information | none |

### Data Structures

**MonitoredAccount**
```python
{
    "username": str,
    "display_name": str,
    "avatar_url": str,
    "last_tweet_id": str,
    "guild_id": int,
    "channel_ids": List[int]
}
```

**GuildSettings**
```python
{
    "guild_id": int,
    "default_channel_id": int,
    "notification_channels": List[int],
    "poll_interval": int,
    "include_replies": bool,
    "include_retweets": bool
}
```

## Implementation Details

### File Structure
```
twitter-alert-bot/
├── bot.py                 # Main bot entry point
├── config.py              # Configuration management
├── monitors/
│   ├── __init__.py
│   └── twitter_monitor.py # Twitter monitoring logic
├── commands/
│   ├── __init__.py
│   └── twitter_commands.py # Slash commands
├── utils/
│   ├── __init__.py
│   ├── embed_builder.py    # Rich embed creation
│   └── data_manager.py    # JSON persistence
├── data/
│   └── database.json       # Persistent storage
├── requirements.txt
├── .env.example
└── README.md
```

### Error Handling
- Rate limiting detection and backoff
- Invalid username handling
- Network failure recovery
- Graceful degradation

### Rate Limiting
- Respect Twitter's rate limits
- Implement exponential backoff
- Queue management for high-volume scenarios

## Acceptance Criteria

1. ✅ Bot connects to Discord with slash commands visible
2. ✅ `/twitter add <username>` successfully adds account to monitoring
3. ✅ New tweets from monitored accounts trigger Discord notifications
4. ✅ Embed matches the reference format (blue accent, author info, metrics)
5. ✅ Multiple accounts can be monitored simultaneously
6. ✅ Multiple channels can receive notifications
7. ✅ Bot persists data across restarts
8. ✅ Error handling for invalid accounts or network issues
