"""
Rich embed builder for Twitter posts
Creates Discord embeds matching the reference format
"""
import discord
from typing import List, Optional, Dict, Any
from datetime import datetime
import re

class EmbedBuilder:
    """Builds rich Discord embeds for Twitter posts"""

    # Colors
    ACCENT_COLOR = 0x1DA1F2  # Twitter blue
    EMBED_BACKGROUND = 0x2B2D31  # Dark gray (Discord dark mode)

    # Icons (using emoji as Discord doesn't support custom icons easily)
    REPLY_ICON = "\u25B6\uFE0F"  # Play button for replies
    RETWEET_ICON = "\u267B\uFE0F"  # Recycle for retweets
    LIKE_ICON = "\u2764\uFE0F"  # Heart
    VIEW_ICON = "\uD83D\uDC41\uFE0F"  # Eyes

    @classmethod
    def format_number(cls, num: int) -> str:
        """Format large numbers with K/M suffixes"""
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        return str(num)

    @classmethod
    def build_tweet_embed(
        cls,
        author_name: str,
        author_handle: str,
        author_avatar: str,
        content: str,
        images: List[str],
        reply_count: int,
        retweet_count: int,
        like_count: int,
        view_count: int,
        tweet_url: str,
        timestamp: datetime,
        quote_tweet: Optional[Dict[str, Any]] = None
    ) -> discord.Embed:
        """
        Build a rich Discord embed for a tweet

        Args:
            author_name: Display name of the tweet author
            author_handle: Twitter handle (without @)
            author_avatar: URL to author's profile picture
            content: Full tweet text content
            images: List of image URLs from the tweet
            reply_count: Number of replies
            retweet_count: Number of retweets
            like_count: Number of likes
            view_count: Number of views
            tweet_url: Direct URL to the tweet
            timestamp: When the tweet was posted
            quote_tweet: Optional dict with quote tweet info

        Returns:
            discord.Embed: A formatted embed ready to send
        """
        # Create main embed with dark background
        embed = discord.Embed(
            color=cls.ACCENT_COLOR,
            timestamp=timestamp
        )

        # Format the content to preserve line breaks
        formatted_content = content.replace('\n', '\n')

        # Add author info as the description (below the title)
        author_block = f"**{author_name}**\n@{author_handle}"
        embed.description = author_block

        # Set author info with avatar
        embed.set_author(
            name=f"@{author_handle}",
            icon_url=author_avatar if author_avatar else discord.Embed.Empty
        )

        # Add tweet content
        embed.add_field(
            name="\u200b",  # Zero-width space for clean formatting
            value=formatted_content,
            inline=False
        )

        # Add images if present
        if images:
            # For up to 4 images, use the image field
            if len(images) == 1:
                embed.set_image(url=images[0])
            elif len(images) == 2:
                # Discord only supports one image field, so we'll use the first
                embed.set_image(url=images[0])
                # Store additional images in footer or description
                embed.add_field(
                    name="Additional Images",
                    value=f"[View image 2]({images[1]})",
                    inline=True
                )
            elif len(images) >= 3:
                embed.set_image(url=images[0])
                image_links = "\n".join([f"[Image {i+1}]({url})" for i, url in enumerate(images[1:4])])
                embed.add_field(
                    name="More Images",
                    value=image_links,
                    inline=True
                )

        # Add engagement metrics
        metrics = []
        metrics.append(f"\uD83D\uDCAC **{cls.format_number(reply_count)}**")  # Replies
        metrics.append(f"\u267B\uFE0F **{cls.format_number(retweet_count)}**")  # Retweets
        metrics.append(f"\u2764\uFE0F **{cls.format_number(like_count)}**")  # Likes
        metrics.append(f"\uD83D\uDC41\uFE0F **{cls.format_number(view_count)}**")  # Views

        embed.add_field(
            name="\u200b",  # Spacer
            value=" | ".join(metrics),
            inline=False
        )

        # Add quote tweet if present
        if quote_tweet:
            qt_content = quote_tweet.get('content', '')
            qt_author = quote_tweet.get('author_name', 'Unknown')
            qt_handle = quote_tweet.get('author_handle', '')
            embed.add_field(
                name="Quote Tweet",
                value=f"> {qt_content}\n— **{qt_author}** @{qt_handle}",
                inline=False
            )

        # Add footer with link and timestamp
        embed.add_field(
            name="\u200b",
            value=f"[Open in X]({tweet_url}) \u2022 Posted {cls._format_timestamp(timestamp)}",
            inline=False
        )

        # Set thumbnail to author avatar
        if author_avatar:
            embed.set_thumbnail(url=author_avatar)

        return embed

    @staticmethod
    def _format_timestamp(dt: datetime) -> str:
        """Format timestamp for display"""
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        return dt.strftime("%B %d, %Y %I:%M %p")

    @classmethod
    def build_account_added_embed(
        cls,
        username: str,
        display_name: str,
        avatar_url: str,
        channel_mentions: List[str]
    ) -> discord.Embed:
        """Build an embed for account added confirmation"""
        embed = discord.Embed(
            title="\u2705 Twitter Account Added",
            color=0x00FF00,  # Green
            description=f"**@{username}** ({display_name}) is now being monitored."
        )

        if channel_mentions:
            embed.add_field(
                name="Notification Channels",
                value="\n".join(channel_mentions),
                inline=False
            )

        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        return embed

    @classmethod
    def build_account_removed_embed(cls, username: str) -> discord.Embed:
        """Build an embed for account removed confirmation"""
        return discord.Embed(
            title="\u274C Twitter Account Removed",
            color=0xFF0000,  # Red
            description=f"**@{username}** is no longer being monitored."
        )

    @classmethod
    def build_account_list_embed(
        cls,
        accounts: List[Dict],
        guild_name: str
    ) -> discord.Embed:
        """Build an embed listing all monitored accounts"""
        embed = discord.Embed(
            title=f"\uD83D\uDC41 Monitored Accounts for {guild_name}",
            color=cls.ACCENT_COLOR
        )

        if not accounts:
            embed.description = "No accounts are currently being monitored.\nUse `/twitter add <username>` to add one!"
            return embed

        account_lines = []
        for acc in accounts:
            name = acc.get('display_name', acc['username'])
            username = acc['username']
            channels = acc.get('channel_ids', [])
            channel_str = f"<#{channels[0]}>" if channels else "Default"
            account_lines.append(f"• **{name}** (@{username}) — {channel_str}")

        embed.description = "\n".join(account_lines)
        embed.set_footer(text=f"Total: {len(accounts)} account(s)")

        return embed

    @classmethod
    def build_error_embed(cls, error_message: str) -> discord.Embed:
        """Build an error embed"""
        return discord.Embed(
            title="\u26A0\uFE0F Error",
            color=0xFFA500,  # Orange
            description=error_message
        )

    @classmethod
    def build_help_embed(cls) -> discord.Embed:
        """Build a help embed with command reference"""
        embed = discord.Embed(
            title="\uD83D\uDC4B Twitter Alert Bot Help",
            color=cls.ACCENT_COLOR,
            description="Monitor Twitter accounts and get instant Discord notifications!"
        )

        commands = [
            ("`/twitter add <username>`", "Add a Twitter account to monitor"),
            ("`/twitter add <username> #channel`", "Add account with specific channel"),
            ("`/twitter remove <username>`", "Stop monitoring an account"),
            ("`/twitter list`", "View all monitored accounts"),
            ("`/twitter channel <channel>`", "Set default notification channel"),
            ("`/twitter settings`", "View current settings"),
            ("`/twitter help`", "Show this help message"),
        ]

        for cmd, desc in commands:
            embed.add_field(name=cmd, value=desc, inline=False)

        embed.add_field(
            name="\uD83D\uDCDD Example",
            value="`/twitter add elonmusk #musk-alerts`",
            inline=False
        )

        return embed

    @classmethod
    def build_settings_embed(
        cls,
        default_channel: Optional[int],
        poll_interval: int,
        include_replies: bool,
        include_retweets: bool
    ) -> discord.Embed:
        """Build an embed showing current settings"""
        embed = discord.Embed(
            title="\u2699\uFE0F Bot Settings",
            color=cls.ACCENT_COLOR
        )

        channel_str = f"<#{default_channel}>" if default_channel else "Not set"
        embed.add_field(
            name="Default Channel",
            value=channel_str,
            inline=True
        )

        embed.add_field(
            name="Poll Interval",
            value=f"{poll_interval} seconds",
            inline=True
        )

        embed.add_field(
            name="Include Replies",
            value="\u2705 Yes" if include_replies else "\u274C No",
            inline=True
        )

        embed.add_field(
            name="Include Retweets",
            value="\u2705 Yes" if include_retweets else "\u274C No",
            inline=True
        )

        return embed
