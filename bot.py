"""
Twitter Alert Bot for Discord
Main entry point
"""
import discord
from discord import Intents
import asyncio
import logging
from datetime import datetime
import signal
import sys

from config import config
from utils.data_manager import DataManager
from utils.embed_builder import EmbedBuilder
from monitors.twitter_monitor import TwitterMonitor
from commands.twitter_commands import TwitterCommands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TwitterAlertBot(discord.Bot):
    """Main Discord bot class"""

    def __init__(self):
        # Set up intents
        intents = Intents.default()
        intents.message_content = True
        intents.guilds = True

        super().__init__(intents=intents)

        # Initialize components
        self.data_manager = DataManager()
        self.twitter_monitor = TwitterMonitor(poll_interval=config.poll_interval)

        # Initialize commands
        self.twitter_commands = TwitterCommands(self, self.data_manager, self.twitter_monitor)

        # Add the command group
        self.add_application_command(self.twitter_commands.twitter_group)

        # Monitoring task
        self._monitor_task: asyncio.Task = None
        self._running = True

        # Flag to sync commands only once
        self._commands_synced = False

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")

        # Sync commands only once – prevents hitting 429 on every reconnect
        if not self._commands_synced:
            await self.sync_commands()
            self._commands_synced = True
            logger.info("Commands synced")

        # Start the monitoring loop
        self._start_monitoring()

    def _start_monitoring(self):
        """Start the Twitter monitoring background task"""
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("Monitoring loop started")

    async def _monitor_loop(self):
        """Background task that monitors Twitter accounts"""
        while self._running:
            try:
                # Get all accounts to monitor
                accounts = self.data_manager.get_all_accounts()

                if accounts:
                    await self._check_accounts(accounts)

                # Sleep for poll interval
                await asyncio.sleep(config.poll_interval)

            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(config.poll_interval)

    async def _check_accounts(self, accounts):
        """Check all accounts for new tweets"""
        for account in accounts:
            try:
                # Get guild and channels
                guild = self.get_guild(account.guild_id)   # FIXED: no self.bot
                if not guild:
                    continue

                # Get notification channels
                channels = []
                for channel_id in account.channel_ids:
                    channel = guild.get_channel(channel_id)
                    if channel:
                        channels.append(channel)

                # If no specific channels, use default
                if not channels:
                    guild_settings = self.data_manager.get_guild_settings(account.guild_id)
                    if guild_settings.default_channel_id:
                        default_channel = guild.get_channel(guild_settings.default_channel_id)
                        if default_channel:
                            channels.append(default_channel)
                    else:
                        # Use first text channel
                        for channel in guild.text_channels:
                            channels.append(channel)
                            break

                if not channels:
                    continue

                # Get guild settings for filters
                guild_settings = self.data_manager.get_guild_settings(account.guild_id)

                # Check for new tweets
                new_tweets = await self.twitter_monitor.get_new_tweets_since(
                    username=account.username,
                    since_id=account.last_tweet_id,
                    include_replies=guild_settings.include_replies,
                    include_retweets=guild_settings.include_retweets
                )

                # Process new tweets
                for tweet in new_tweets:
                    # Update last tweet ID
                    self.data_manager.update_account_tweet_id(
                        account.guild_id,
                        account.username,
                        tweet.id
                    )

                    # Build embed
                    embed = EmbedBuilder.build_tweet_embed(
                        author_name=tweet.user_displayname,
                        author_handle=tweet.user_username,
                        author_avatar=tweet.user_avatar,
                        content=tweet.rendered_content,
                        images=tweet.media,
                        reply_count=tweet.reply_count,
                        retweet_count=tweet.retweet_count,
                        like_count=tweet.like_count,
                        view_count=tweet.view_count,
                        tweet_url=tweet.url,
                        timestamp=tweet.date,
                        quote_tweet=tweet.quoted_tweet
                    )

                    # Send to all notification channels with a delay between messages
                    for idx, channel in enumerate(channels):
                        try:
                            if isinstance(channel, discord.TextChannel):
                                await channel.send(embed=embed)
                                logger.info(f"Sent tweet notification to #{channel.name} for @{account.username}")
                                
                                # ***** RATE LIMIT PROTECTION *****
                                # Wait 1.5 seconds between messages to avoid 429
                                # This applies globally across all channels/accounts
                                await asyncio.sleep(1.5)

                        except Exception as e:
                            logger.error(f"Error sending to #{channel.name}: {e}")

            except Exception as e:
                logger.error(f"Error checking account @{account.username}: {e}")

    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a guild"""
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")

        # Initialize guild settings
        settings = self.data_manager.get_guild_settings(guild.id)
        self.data_manager.update_guild_settings(settings)

    async def on_guild_remove(self, guild: discord.Guild):
        """Called when the bot is removed from a guild"""
        logger.info(f"Left guild: {guild.name} (ID: {guild.id})")

    def run(self):
        """Run the bot"""
        if not config.validate():
            logger.error("Configuration validation failed. Please check your .env file.")
            sys.exit(1)

        logger.info("Starting Twitter Alert Bot...")

        # Set up signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            logger.info("Shutting down...")
            self._running = False
            if self._monitor_task:
                self._monitor_task.cancel()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run the bot
        super().run(config.discord_token, reconnect=True)


def main():
    """Main entry point"""
    bot = TwitterAlertBot()
    bot.run()


if __name__ == "__main__":
    main()
