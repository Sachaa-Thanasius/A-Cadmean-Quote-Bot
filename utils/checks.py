"""
checks.py: Custom checks for commands.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from exts.admin import AdminCog

LOGGER = logging.getLogger(__name__)


def is_guild_owner():
    """A :func:`.check` that checks if the person invoking this command is the
    owner of the guild in the current context.

    This check raises the :exc:`commands.CheckFailure` on failure.
    """

    async def predicate(ctx: commands.Context) -> bool:
        if not (ctx.guild is not None and ctx.guild.owner_id == ctx.author.id):
            raise commands.CheckFailure("Only the server owner can do this.")
        return True

    return commands.check(predicate)


def certain_channels_only():
    """A :func:`.check` that checks if the person invoking this command is the
    right channels of the guild in the current context.

    This check raises the :exc:`commands.CheckFailure` on failure.
    """

    async def predicate(ctx: commands.Context) -> bool:
        admin_cog = ctx.bot.get_cog("AdminCog")

        # Ensure the message was sent in a guild.
        if ctx.guild is not None:
            # Ensure the message was sent in that guild's allowed channels.
            allowed_channels = admin_cog.allowed_channels[ctx.guild.id]
            if ctx.channel.id in allowed_channels:
                return True

        raise commands.CheckFailure("Only the server or bot owner can do this.")

    return commands.check(predicate)
