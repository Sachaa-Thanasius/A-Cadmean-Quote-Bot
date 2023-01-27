#!/usr/bin/env python
"""
bot.py: The main bot initializer and starter.
"""

from __future__ import annotations

import logging
import asyncio
from pathlib import Path

import discord
from discord.ext import commands

import config

CONFIG = config.config()
LOGGER = logging.getLogger("bot.ACadmeanQuoteBot")


class ACadmeanQuoteBot(commands.Bot):
    """A bot that searches through the works of M J Bradley based on user input, and returns matching quotes.

    Currently only supports *A Cadmean Victory*.

    Parameters
    ----------
    *args
        Variable length argument list, primarily for :class:`commands.Bot`. See that class for more
        information.
    initial_extensions : list[:class:`str`]
        A list of extension names that the bot will initially load.
    **kwargs
        Arbitrary keyword arguments, primarily for :class:`commands.Bot`. See that class for more information.

    Attributes
    ----------
    emojis_stock: dict[:class:`discord.Emoji`]
        A collection of :class:`discord.Emoji`s with truncated names stored on startup for easy future retrieval.
    """

    def __init__(self,
                 *args,
                 initial_extensions: list[str] = None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_extensions = initial_extensions
        self._config = CONFIG

        # Things to load before connecting to the Websocket.
        self.prefixes: list[str] = []

        # Things to load right after connecting to the Websocket.
        self.emojis_stock: dict[str, discord.Emoji] = {}

    @property
    def config(self) -> dict:
        """dict: All configuration information from the config.json file."""
        return self._config

    @config.setter
    def config(self, value: dict) -> None:
        self._config = value

    async def on_ready(self) -> None:
        """Loads several reference variables and dicts if they haven't been loaded already."""

        if len(self.emojis_stock) == 0:
            self._load_emoji_stock()

        if not self.owner_id:
            await self.is_owner(self.user)

        LOGGER.info(f'Logged in as {self.user} (ID: {self.user.id})')

    async def setup_hook(self) -> None:
        """Performs setup after the bot is logged in but before it has connected to the Websocket."""

        await self._load_extensions()

    async def get_prefix(self, message: discord.Message, /) -> list[str] | str:
        if not self.prefixes:
            await self._load_guild_prefixes()

        if message.guild is not None:
            return self.prefixes
        else:
            return "?"

    async def _load_guild_prefixes(self) -> None:
        """Load all prefixes from the bot database."""

        self.prefixes = config.config()["discord"]["all_prefixes"]

    async def _load_extensions(self) -> None:
        """Loads extensions/cogs.

        If a list of initial ones isn't provided, all extensions are loaded by default.
        """

        if self.initial_extensions is not None:
            # Attempt to load all specified extensions.
            for extension in self.initial_extensions:
                try:
                    await self.load_extension(extension)
                    LOGGER.info(f"Loaded extension: {extension}")
                except discord.ext.commands.ExtensionError as err:
                    LOGGER.exception(f"Failed to load extension: {extension}\n\n{err}")

        else:
            # Attempt to load all extensions visible to the bot.
            test_cogs_folder = Path(__file__).parent.joinpath("exts/cogs")
            for filepath in test_cogs_folder.iterdir():
                if filepath.suffix == ".py":
                    try:
                        await self.load_extension(f"exts.cogs.{filepath.stem}")
                        LOGGER.info(f"Loaded extension: {filepath.stem}")
                    except discord.ext.commands.ExtensionError as err:
                        LOGGER.exception(f"Failed to load extension: {filepath.stem}\n\n{err}")

    def _load_emoji_stock(self) -> None:
        """Sets a dict of emojis for quick reference.

        Most of the keys used here are shorthand for the actual names.
        """

        self.emojis_stock = {
            "acvr": self.get_emoji(1021875940067905566)
        }


async def main() -> None:
    """Starts an instance of the bot."""

    discord.utils.setup_logging()

    # Set the starting parameters.
    default_prefixes = CONFIG["discord"]["all_prefixes"]
    default_intents = discord.Intents.all()
    init_exts = ["exts.admin", "exts.story_quote"]

    async with ACadmeanQuoteBot(
            command_prefix=default_prefixes,
            intents=default_intents,
            initial_extensions=init_exts
    ) as bot:
        await bot.start(CONFIG["discord"]["token"])


if __name__ == "__main__":
    asyncio.run(main())
