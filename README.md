# Twitter Alert Bot for Discord

A powerful Discord bot that monitors Twitter/X accounts and sends real-time rich embed notifications to your Discord channels.

## Features

- **One-Command Setup**: Add any Twitter account with a single slash command
- **Rich Embeds**: Beautiful Discord embeds matching the Twitter post format with:
  - Author name and handle with profile picture
  - Full post content with preserved formatting
  - Inline images from tweets
  - Engagement metrics (replies, retweets, likes, views)
  - Timestamp and direct link to post
- **Multi-Channel Support**: Send notifications to multiple channels
- **Persistent Storage**: Remembers your settings across restarts
- **No API Key Required**: Uses snscrape for Twitter monitoring

---

## Deploy to Render (Free Tier)

### One-Click Deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### Manual Deploy Steps

1. **Fork this repository** to your GitHub account

2. **Create a Discord Bot**:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and name it
   - Go to "Bot" section and click "Add Bot"
   - Copy the token
   - Enable "Message Content Intent" in Bot permissions

3. **Deploy to Render**:
   - Sign up at [render.com](https://render.com) (free tier)
   - Click "New +" > "Blueprint"
   - Connect your GitHub repo
   - Render auto-detects `render.yaml`

4. **Add Environment Variables**:
   - `DISCORD_TOKEN`: Your Discord bot token

5. **Invite the Bot**:
   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=2147483647&scope=bot%20applications.commands
   ```

---

## Local Development Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure the Bot

```bash
cp .env.example .env
```

Edit `.env`:
```
DISCORD_TOKEN=your_actual_bot_token_here
```

### 3. Run the Bot

```bash
python bot.py
```

---

## Slash Commands

| Command | Description |
|---------|-------------|
| `/twitter add <username>` | Add a Twitter account to monitor |
| `/twitter add <username> #channel` | Add with specific channel |
| `/twitter remove <username>` | Remove from monitoring |
| `/twitter list` | View all monitored accounts |
| `/twitter channel <channel>` | Set default channel |
| `/twitter settings` | View bot settings |
| `/twitter help` | Show help |

## Usage Examples

```
/twitter add elonmusk
/twitter add TouchlineX #sports-news
/twitter channel #twitter-alerts
/twitter list
```

---

## Render Free Tier Notes

> **Important Limitations**:
> - Instance spins down after 15 min of inactivity
> - Cold starts may take 30+ seconds
> - Data stored in JSON (ephemeral on free tier)
> - For production, consider upgrading

**Tip**: Use UptimeRobot to keep the bot awake.

---

## Project Structure

```
twitter-alert-bot/
├── bot.py                      # Main entry point
├── config.py                   # Configuration
├── commands/
│   └── twitter_commands.py     # Slash commands
├── monitors/
│   └── twitter_monitor.py      # Twitter scraping
├── utils/
│   ├── data_manager.py          # JSON persistence
│   └── embed_builder.py         # Rich embeds
├── data/                       # Storage
├── render.yaml                 # Render config
├── Procfile                    # Process type
├── requirements.txt
└── README.md
```

## Support

For issues, please open an issue on the repository.
