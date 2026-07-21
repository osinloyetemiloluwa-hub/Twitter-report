"""
Twitter monitoring module using snscrape
Scrapes tweets without requiring API access
"""
import snscrape.modules.twitter as sntwitter
import asyncio
import re
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class Tweet:
    """Represents a scraped tweet"""
    id: str
    url: str
    date: datetime
    raw_content: str
    rendered_content: str
    user_username: str
    user_displayname: str
    user_verified: bool
    user_avatar: str
    reply_count: int
    retweet_count: int
    like_count: int
    quote_count: int
    view_count: int
    media: List[str]  # URLs of images/videos
    quoted_tweet: Optional[Dict[str, Any]] = None
    is_reply: bool = False
    is_retweet: bool = False
    is_quote: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'url': self.url,
            'date': self.date.isoformat(),
            'raw_content': self.raw_content,
            'rendered_content': self.rendered_content,
            'user_username': self.user_username,
            'user_displayname': self.user_displayname,
            'user_verified': self.user_verified,
            'user_avatar': self.user_avatar,
            'reply_count': self.reply_count,
            'retweet_count': self.retweet_count,
            'like_count': self.like_count,
            'quote_count': self.quote_count,
            'view_count': self.view_count,
            'media': self.media,
            'quoted_tweet': self.quoted_tweet,
            'is_reply': self.is_reply,
            'is_retweet': self.is_retweet,
            'is_quote': self.is_quote,
        }

class TwitterMonitor:
    """Monitors Twitter accounts for new tweets"""

    def __init__(self, poll_interval: int = 60):
        self.poll_interval = poll_interval
        self._running = False
        self._tasks: List[asyncio.Task] = []

    async def get_user_info(self, username: str) -> Optional[Dict[str, str]]:
        """
        Get information about a Twitter user

        Args:
            username: Twitter username (without @)

        Returns:
            Dict with 'username', 'display_name', 'avatar_url', 'bio', 'followers'
            or None if user not found
        """
        try:
            # Clean username
            username = username.lstrip('@').lower()

            # Get user profile using snscrape
            scraper = sntwitter.TwitterUserScraper(username=username)

            # Try to get user info
            for obj in scraper.get_items():
                if isinstance(obj, sntwitter.User):
                    return {
                        'username': obj.username,
                        'display_name': obj.displayname,
                        'avatar_url': obj.avatarUrl,
                        'bio': obj.description,
                        'followers': obj.followers,
                        'verified': obj.verified,
                    }
                break  # Get only first item

            return None

        except Exception as e:
            logger.error(f"Error getting user info for @{username}: {e}")
            return None

    async def get_latest_tweet(
        self,
        username: str,
        include_replies: bool = False,
        include_retweets: bool = False
    ) -> Optional[Tweet]:
        """
        Get the latest tweet from a user

        Args:
            username: Twitter username
            include_replies: Include reply tweets
            include_retweets: Include retweets

        Returns:
            Tweet object or None
        """
        try:
            username = username.lstrip('@').lower()
            tweets = await self.get_tweets(username, count=5, include_replies=include_replies, include_retweets=include_retweets)
            return tweets[0] if tweets else None

        except Exception as e:
            logger.error(f"Error getting latest tweet for @{username}: {e}")
            return None

    async def get_tweets(
        self,
        username: str,
        count: int = 10,
        include_replies: bool = False,
        include_retweets: bool = False
    ) -> List[Tweet]:
        """
        Get recent tweets from a user

        Args:
            username: Twitter username
            count: Number of tweets to retrieve
            include_replies: Include reply tweets
            include_retweets: Include retweets

        Returns:
            List of Tweet objects
        """
        tweets = []

        try:
            username = username.lstrip('@').lower()
            scraper = sntwitter.TwitterUserScraper(username=username)

            for i, obj in enumerate(scraper.get_items()):
                if i >= count:
                    break

                # Skip retweets if not requested
                if not include_retweets and hasattr(obj, 'retweetedTweet') and obj.retweetedTweet:
                    continue

                # Skip replies if not requested
                if not include_replies and hasattr(obj, 'inReplyToTweetId') and obj.inReplyToTweetId:
                    continue

                tweet = self._parse_tweet_object(obj)
                if tweet:
                    tweets.append(tweet)

        except Exception as e:
            logger.error(f"Error getting tweets for @{username}: {e}")

        return tweets

    async def get_new_tweets_since(
        self,
        username: str,
        since_id: str,
        include_replies: bool = False,
        include_retweets: bool = False
    ) -> List[Tweet]:
        """
        Get all new tweets since a specific tweet ID

        Args:
            username: Twitter username
            since_id: Tweet ID to get tweets after
            include_replies: Include reply tweets
            include_retweets: Include retweets

        Returns:
            List of new Tweet objects (oldest first)
        """
        new_tweets = []
        since_id_int = int(since_id) if since_id else 0

        try:
            username = username.lstrip('@').lower()
            scraper = sntwitter.TwitterUserScraper(username=username)

            for obj in scraper.get_items():
                tweet = self._parse_tweet_object(obj)
                if not tweet:
                    continue

                # Stop if we've reached the old tweet
                if int(tweet.id) <= since_id_int:
                    break

                # Apply filters
                if not include_retweets and tweet.is_retweet:
                    continue
                if not include_replies and tweet.is_reply:
                    continue

                # Skip if it's the same tweet (edge case)
                if tweet.id == since_id:
                    continue

                new_tweets.append(tweet)

            # Reverse to get oldest first
            new_tweets.reverse()

        except Exception as e:
            logger.error(f"Error getting new tweets for @{username}: {e}")

        return new_tweets

    def _parse_tweet_object(self, obj) -> Optional[Tweet]:
        """Parse a snscrape tweet object into our Tweet format"""
        try:
            # Extract media URLs
            media = []
            if hasattr(obj, 'media') and obj.media:
                for m in obj.media:
                    if hasattr(m, 'fullUrl'):
                        media.append(m.fullUrl)
                    elif hasattr(m, 'previewUrl'):
                        media.append(m.previewUrl)
                    elif hasattr(m, 'thumbnailUrl'):
                        media.append(m.thumbnailUrl)

            # Handle quoted tweet
            quoted_tweet = None
            is_quote = False
            if hasattr(obj, 'quotedTweet') and obj.quotedTweet:
                is_quote = True
                qt = obj.quotedTweet
                quoted_tweet = {
                    'id': str(qt.id),
                    'url': qt.url,
                    'content': qt.rawContent,
                    'author_name': qt.user.displayname if hasattr(qt, 'user') else 'Unknown',
                    'author_handle': qt.user.username if hasattr(qt, 'user') else '',
                }

            # Check if it's a retweet
            is_retweet = hasattr(obj, 'retweetedTweet') and obj.retweetedTweet

            # Check if it's a reply
            is_reply = hasattr(obj, 'inReplyToTweetId') and obj.inReplyToTweetId

            # Get user info
            user = getattr(obj, 'user', None)
            user_username = user.username if user else 'unknown'
            user_displayname = user.displayname if user else 'Unknown'
            user_verified = user.verified if user else False
            user_avatar = user.avatarUrl if user else ''

            # Get engagement counts
            reply_count = getattr(obj, 'replyCount', 0) or 0
            retweet_count = getattr(obj, 'retweetCount', 0) or 0
            like_count = getattr(obj, 'likeCount', 0) or 0
            quote_count = getattr(obj, 'quoteCount', 0) or 0
            view_count = getattr(obj, 'viewCount', 0) or 0

            return Tweet(
                id=str(obj.id),
                url=obj.url,
                date=obj.date,
                raw_content=obj.rawContent or '',
                rendered_content=obj.renderedContent or obj.rawContent or '',
                user_username=user_username,
                user_displayname=user_displayname,
                user_verified=user_verified,
                user_avatar=user_avatar,
                reply_count=reply_count,
                retweet_count=retweet_count,
                like_count=like_count,
                quote_count=quote_count,
                view_count=view_count,
                media=media,
                quoted_tweet=quoted_tweet,
                is_reply=is_reply,
                is_retweet=is_retweet,
                is_quote=is_quote,
            )

        except Exception as e:
            logger.error(f"Error parsing tweet object: {e}")
            return None

    async def validate_username(self, username: str) -> bool:
        """
        Check if a Twitter username exists

        Args:
            username: Twitter username to validate

        Returns:
            True if username exists, False otherwise
        """
        try:
            user_info = await self.get_user_info(username)
            return user_info is not None
        except:
            return False

    async def start_monitoring(
        self,
        accounts: List[Dict],
        callback: Callable[[Dict, Tweet], None],
        poll_interval: Optional[int] = None
    ):
        """
        Start monitoring multiple accounts

        Args:
            accounts: List of account dicts with 'username', 'guild_id', 'channel_ids', 'last_tweet_id
            callback: Async function to call when new tweets are found
            poll_interval: Override default poll interval
        """
        interval = poll_interval or self.poll_interval
        self._running = True

        while self._running:
            for account in accounts:
                try:
                    new_tweets = await self.get_new_tweets_since(
                        username=account['username'],
                        since_id=account.get('last_tweet_id', ''),
                        include_replies=account.get('include_replies', False),
                        include_retweets=account.get('include_retweets', False)
                    )

                    for tweet in new_tweets:
                        await callback(account, tweet)

                except Exception as e:
                    logger.error(f"Error monitoring @{account['username']}: {e}")

            await asyncio.sleep(interval)

    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
