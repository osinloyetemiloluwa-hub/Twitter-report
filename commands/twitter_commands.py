"""
Twitter slash commands for Discord
"""
import discord
from discord import option
from discord.commands import SlashCommandGroup
from typing import Optional
import re
import asyncio

from utils.data_manager import DataManager, MonitoredAccount
from utils.embed_builder import EmbedBuilder
from monitors.twitter_monitor import TwitterMonitor
from datetime import datetime

# ==== REPLACE THIS WITH YOUR ACTUAL DISCORD USER ID (integer) ====
YOUR_USER_ID = 123456789012345678   # <-- CHANGE THIS


class TwitterCommands:
    # Define the command group as a CLASS attribute so decorators can see it
    twitter_group = SlashCommandGroup(
        "twitter",
        "Twitter account monitoring commands"
    )

    def __init__(self, bot, data_manager: DataManager, twitter_monitor: TwitterMonitor):
        self.bot = bot
        self.data_manager = data_manager
        self.twitter_monitor = twitter_monitor

        # Optional: store a reference on the instance if needed elsewhere
        self.twitter_group = self.twitter_group

        # We DO NOT need to manually add commands – the decorators do it.

    @twitter_group.command(
        name="add",
        description="Add a Twitter account to monitor"
    )
    @option("username", str, description="Twitter username (without @)")
    @option("channel", discord.TextChannel, description="Notification channel (optional)", required=False)
    async def add(self, ctx: discord.ApplicationContext, username: str, channel: Optional[discord.TextChannel]):
        """
        Add a Twitter account to monitor

        Examples:
        /twitter add elonmusk
        /twitter add elonmusk #alerts
        """
        await ctx.defer()

        # Clean username
        username = username.lstrip('@').lower()

        # Validate username format
        if not self._is_valid_username(username):
            embed = EmbedBuilder.build_error_embed(
                "Invalid username format. Please use only letters, numbers, and underscores."
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            return

        # Check if already monitoring
        existing = self.data_manager.get_account(ctx.guild_id, username)
        if existing:
            embed = EmbedBuilder.build_error_embed(
                f"**@{username}** is already being monitored in this server."
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            return

        # Get user info from Twitter
        try:
            user_info = await self.twitter_monitor.get_user_info(username)
        except Exception as e:
            embed = EmbedBuilder.build_error_embed(
                f"Could not find Twitter user **@{username}**. Please check the username and try again."
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            return

        if not user_info:
            embed = EmbedBuilder.build_error_embed(
                f"Could not find Twitter user **@{username}**. Please check the username and try again."
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            return

        # Determine notification channel
        channel_id = channel.id if channel else None
        guild_settings = self.data_manager.get_guild_settings(ctx.guild_id)

        if not channel_id:
            if guild_settings.default_channel_id:
                channel_id = guild_settings.default_channel_id
            else:
                channel_id = ctx.channel_id

        # Get latest tweet to set as starting point
        latest_tweet = await self.twitter_monitor.get_latest_tweet(
            username,
            include_replies=guild_settings.include_replies,
            include_retweets=guild_settings.include_retweets
        )

        last_tweet_id = latest_tweet.id if latest_tweet else ""

        # Create monitored account
        account = MonitoredAccount(
            username=username,
            display_name=user_info['display_name'],
            avatar_url=user_info['avatar_url'],
            last_tweet_id=last_tweet_id,
            guild_id=ctx.guild_id,
            channel_ids=[channel_id],
            added_at=datetime.utcnow().isoformat()
        )

        # Save account
        self.data_manager.add_account(account)

        # Get channel mention
        channel_mentions = [f"<#{channel_id}>"]

        # Build success embed
        embed = EmbedBuilder.build_account_added_embed(
            username=username,
            display_name=user_info['display_name'],
            avatar_url=user_info['avatar_url'],
            channel_mentions=channel_mentions
        )

        if latest_tweet:
            embed.set_footer(text=f"Now tracking from: {latest_tweet.url}")

        await ctx.followup.send(embed=embed)

    @twitter_group.command(
        name="remove",
        description="Remove a Twitter account from monitoring"
    )
    @option("username", str, description="Twitter username to stop monitoring (without @)")
    async def remove(self, ctx: discord.ApplicationContext, username: str):
        """Remove a Twitter account from monitoring"""
        await ctx.defer()

        username = username.lstrip('@').lower()

        # Check if monitoring
        existing = self.data_manager.get_account(ctx.guild_id, username)
        if not existing:
            embed = EmbedBuilder.build_error_embed(
                f"**@{username}** is not being monitored in this server."
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            return

        # Remove account
        self.data_manager.remove_account(ctx.guild_id, username)

        embed = EmbedBuilder.build_account_removed_embed(username)
        await ctx.followup.send(embed=embed)

    @twitter_group.command(
        name="list",
        description="List all monitored Twitter accounts"
    )
    async def list_accounts(self, ctx: discord.ApplicationContext):
        """List all monitored accounts in this server"""
        accounts = self.data_manager.get_accounts_by_guild(ctx.guild_id)

        accounts_data = [
            {
                'username': acc.username,
                'display_name': acc.display_name,
                'channel_ids': acc.channel_ids
            }
            for acc in accounts
        ]

        guild_name = ctx.guild.name if ctx.guild else "Direct Messages"
        embed = EmbedBuilder.build_account_list_embed(accounts_data, guild_name)

        await ctx.respond(embed=embed, ephemeral=True)

    @twitter_group.command(
        name="channel",
        description="Set the default notification channel"
    )
    @option("channel", discord.TextChannel, description="Discord channel for notifications")
    async def set_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Set the default channel for Twitter notifications"""
        await ctx.defer()

        self.data_manager.set_default_channel(ctx.guild_id, channel.id)

        # Update existing accounts without specific channels
        accounts = self.data_manager.get_accounts_by_guild(ctx.guild_id)
        for acc in accounts:
            if not acc.channel_ids:
                acc.channel_ids = [channel.id]
                self.data_manager.add_account(acc)

        embed = discord.Embed(
            title="\u2705 Notification Channel Set",
            description=f"All Twitter notifications will be sent to {channel.mention}",
            color=0x00FF00
        )

        await ctx.followup.send(embed=embed, ephemeral=True)

    @twitter_group.command(
        name="settings",
        description="View current bot settings"
    )
    async def settings(self, ctx: discord.ApplicationContext):
        """View current monitoring settings"""
        guild_settings = self.data_manager.get_guild_settings(ctx.guild_id)

        embed = EmbedBuilder.build_settings_embed(
            default_channel=guild_settings.default_channel_id,
            poll_interval=guild_settings.poll_interval,
            include_replies=guild_settings.include_replies,
            include_retweets=guild_settings.include_retweets
        )

        await ctx.respond(embed=embed, ephemeral=True)

    @twitter_group.command(
        name="help",
        description="Show help information"
    )
    async def help_cmd(self, ctx: discord.ApplicationContext):
        """Show help information about the bot"""
        embed = EmbedBuilder.build_help_embed()
        await ctx.respond(embed=embed, ephemeral=True)

    # ===== NEW: Manual sync command (owner only) =====
    @twitter_group.command(
        name="sync",
        description="[Owner Only] Manually sync slash commands"
    )
    async def sync_commands(self, ctx: discord.ApplicationContext):
        """Private command to sync commands – only the bot owner can run it."""
        if ctx.author.id != YOUR_USER_ID:
            await ctx.respond("You don't have permission to use this command.", ephemeral=True)
            return

        await ctx.defer(ephemeral=True)
        try:
            # This will sync all global commands
            await self.bot.sync_commands()
            await ctx.followup.send("✅ Slash commands synced successfully!", ephemeral=True)
        except Exception as e:
            await ctx.followup.send(f"❌ Failed to sync commands: {e}", ephemeral=True)

    @staticmethod
    def _is_valid_username(username: str) -> bool:
        """Validate Twitter username format"""
        if not username:
            return False
        # Twitter usernames: letters, numbers, underscores, max 15 chars
        pattern = r'^[a-zA-Z0-9_]{1,15}$'
        return bool(re.match(pattern, username))
