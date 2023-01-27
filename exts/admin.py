"""
admin.py: A cog that implements commands for changing prefixes and other administrative tasks.
"""

from __future__ import annotations

from json import load, dump
import logging
from typing import Literal, TYPE_CHECKING

from pathlib import Path
import discord
from discord.ext import commands

from utils.checks import is_guild_owner, certain_channels_only

if TYPE_CHECKING:
    from bot import ACadmeanQuoteBot

LOGGER = logging.getLogger(__name__)

MessageableGuildChannel = discord.TextChannel | discord.VoiceChannel | discord.Thread


class AdminCog(commands.Cog):
    """A cog for handling bot-related administrative tasks like syncing commands or reloading cogs while live."""

    def __init__(self, bot: ACadmeanQuoteBot) -> None:
        self.bot = bot
        self.allowed_channels = None

        # Paths for files.
        self.channels_file_path = None
        self.config_file_path = None

    async def cog_load(self) -> None:
        self.channels_file_path = Path(__file__).resolve().parents[1].joinpath("data/allowed_channels.json")
        self.config_file_path = Path(__file__).resolve().parents[1].joinpath("config.json")

        with open(self.channels_file_path, mode="r") as f:
            self.allowed_channels = load(f)

    @commands.group()
    @commands.guild_only()
    @certain_channels_only()
    async def prefixes(self, ctx: commands.Context) -> None:
        """View the prefixes set for this bot in this location."""

        async with ctx.typing():
            local_prefixes = await self.bot.get_prefix(ctx.message)
            await ctx.send(f"Prefixes:\n{', '.join(local_prefixes)}")

    @prefixes.command(name="add")
    @commands.guild_only()
    @commands.check_any(commands.is_owner(), is_guild_owner())
    @commands.cooldown(1, 30, commands.cooldowns.BucketType.user)
    async def prefixes_add(self, ctx: commands.Context, *, new_prefix: str) -> None:
        """Set a prefix that you'd like this bot to respond to.

        Parameters
        ----------
        ctx : :class:`commands.Context`
            The invocation context.
        new_prefix : :class:`str`
            The prefix to be added.
        """

        if new_prefix in await self.bot.get_prefix(ctx.message):
            await ctx.send("This prefix has already been registered.")

        else:
            # Create an updated config dictionary.
            updated_config = self.bot.config
            updated_config["discord"]["all_prefixes"].append(new_prefix)

            # Overwrite the config file with the dict.
            with open(self.config_file_path, mode="w") as f:
                try:
                    dump(updated_config, f)
                except Exception as e:
                    LOGGER.exception("Prefix update in config failed", exc_info=e)

            # Reload the bot's prefixes from the config file.
            await self.bot._load_guild_prefixes()

            # Notify the user whether the process was successful.
            if new_prefix not in await self.bot.get_prefix(ctx.message):
                await ctx.send(f"'{new_prefix}' could not be registered at this time.")

            else:
                await ctx.send(f"'{new_prefix}' has been registered as a prefix for this guild.")

    @prefixes.command(name="remove")
    @commands.guild_only()
    @commands.check_any(commands.is_owner(), is_guild_owner())
    @commands.cooldown(1, 30, commands.cooldowns.BucketType.user)
    async def prefixes_remove(self, ctx: commands.Context, *, old_prefix: str) -> None:
        """Remove a prefix that you'd like this bot to no longer respond to.

        Parameters
        ----------
        ctx : :class:`commands.Context`
            The invocation context.
        old_prefix : :class:`str`
            The prefix to be removed.
        """

        if old_prefix not in await self.bot.get_prefix(ctx.message):
            await ctx.send("This prefix either was never registered in this guild or has already been unregistered.")

        else:
            # Create an updated config dictionary.
            updated_config = self.bot.config
            updated_config["discord"]["all_prefixes"].remove(old_prefix)

            # Overwrite the config file with the dict.
            with open(self.config_file_path, mode="w") as f:
                try:
                    dump(updated_config, f)
                except Exception as e:
                    LOGGER.exception("Prefix update in config failed", exc_info=e)

            # Reload the bot's prefixes from the config file.
            await self.bot._load_guild_prefixes()

            # Notify the user whether the process was successful.
            if old_prefix in await self.bot.get_prefix(ctx.message):
                await ctx.send(f"'{old_prefix}' could not be unregistered at this time.")

            else:
                await ctx.send(f"'{old_prefix}' has been unregistered as a prefix in this guild.")

    @commands.command()
    @commands.guild_only()
    @commands.check_any(commands.is_owner(), is_guild_owner())
    async def allow(self, ctx: commands.Context, channels: Literal["all", "this"] | None = "this") -> None:
        """Set the bot to trigger in this channel.

        Parameters
        ----------
        ctx : :class:`commands.Context`
            The invocation context.
        channels
            Whether the current channel or all guild channels should be affected. Enter "this" or "all".
        """

        guild_id = str(ctx.guild.id)

        # Populate the ids of channels to allow.
        channel_ids = [ctx.channel.id] if channels == "this" else [channel.id for channel in ctx.guild.channels]

        # Add the channel ids to the allow set.
        if self.allowed_channels.get(guild_id):
            self.allowed_channels[guild_id].extend(channel_ids)
        else:
            self.allowed_channels[guild_id] = channel_ids

        # Write the adjusted allowed list to the storage file.
        with open(self.channels_file_path, mode="w") as f:
            dump(self.allowed_channels, f)

        await ctx.send("Channel(s) allowed.")

    @commands.command()
    @commands.guild_only()
    @commands.check_any(commands.is_owner(), is_guild_owner())
    async def disallow(self, ctx: commands.Context, channels: Literal["all", "this"] | None = "this") -> None:
        """Set the bot to not trigger in this channel.

        Parameters
        ----------
        ctx : :class:`commands.Context`
            The invocation context.
        channels
            Whether the current channel or all guild channels should be affected. Enter "this" or "all".
        """

        guild_id = str(ctx.guild.id)

        # Populate the ids of channels to disallow.
        channel_ids = [ctx.channel.id] if channels == "this" else [channel.id for channel in ctx.guild.channels]

        # Remove the channel ids from the allow set.
        if self.allowed_channels.get(guild_id):
            self.allowed_channels[guild_id] = [ch for ch in self.allowed_channels[guild_id] if ch not in channel_ids]
        else:
            self.allowed_channels[guild_id] = []

        # Write the adjusted allowed list to the storage file.
        with open(self.channels_file_path, mode="w") as f:
            dump(self.allowed_channels, f)

        await ctx.send("Channel(s) disallowed.")


async def setup(bot: ACadmeanQuoteBot) -> None:
    """Connects cog to bot."""

    await bot.add_cog(AdminCog(bot))
