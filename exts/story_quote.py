"""
story_quote.py: This cog is meant to provide functionality for searching the text of some books.
"""

from __future__ import annotations

import logging
import re
from json import load
from pathlib import Path
from copy import deepcopy
from random import randint, choice
from time import perf_counter
from bisect import bisect_left
from typing import TYPE_CHECKING, ClassVar

from attrs import define, field
import cattrs
from discord.ext import commands

from utils.embeds import StoryQuoteEmbed
from utils.paginated_views import StoryQuoteView

if TYPE_CHECKING:
    from bot import ACadmeanQuoteBot

LOGGER = logging.getLogger(__name__)
PROJECT_PATH = Path(__file__).resolve().parents[1]

_MISSING = object()  # sentinel value


@define
class StoryInfo:
    """A class to hold all the information about each story."""

    acronym: str
    title: str
    author: str
    link: str
    emoji_id: int
    template_embed: StoryQuoteEmbed = None
    text: list[str] = field(factory=list)
    chapter_index: list[int] = field(factory=list)
    collection_index: list[int] = field(factory=list)


class StorySearchCog(commands.Cog):
    """A cog with commands for people to search the text of some M J Bradley works while in Discord.

    Parameters
    ----------
    bot : :class:`bot.ACadmeanQuoteBot`
        The main Discord bot this cog is a part of.

    Attributes
    ----------
    story_records : :class:`dict`
        The dictionary holding the metadata and text for all stories being scanned.
    """

    story_records: ClassVar[dict[str, StoryInfo]] = {}

    def __init__(self, bot: ACadmeanQuoteBot) -> None:
        self.bot = bot
        self.convertor = cattrs.Converter()

    async def cog_load(self) -> None:
        """Load whatever is necessary to avoid reading from files or querying the database during runtime."""

        # Load story metadata from local file.
        with open(PROJECT_PATH.joinpath("data/story_info.json")) as f:
            temp_records = load(f)

        self.story_records.update(self.convertor.structure(temp_records, dict[str, StoryInfo]))

        # Store template quote embeds for every story.
        for acronym, record in self.story_records.items():
            temp_rec = self.convertor.unstructure(record)
            self.story_records[acronym].template_embed = StoryQuoteEmbed(story_data=temp_rec)

        # Load story text from local markdown files.
        for file in PROJECT_PATH.glob("data/story_text/**/*.md"):
            if "text" in file.name:
                await self.load_story_text(file)

    @classmethod
    async def load_story_text(cls, filepath: Path):
        """Load the story metadata and text."""

        # Compile all necessary regex patterns. To be updated as necessary.
        # -- ACVR text
        re_acvr_chap_title = re.compile(r"(^# \w+)")
        re_volume_heading = re.compile(r"(^A Cadmean Victory Volume \w+)")

        # Start file copying and indexing.
        with filepath.open("r", encoding="utf-8") as f:

            indexing_start_time = perf_counter()

            # Instantiate index lists, which act as a table of contents of sorts.
            stem = str(filepath.stem)[:-5]
            temp_text = cls.story_records[stem].text = [line for line in f if line.strip() != ""]
            temp_chap_index = cls.story_records[stem].chapter_index
            temp_coll_index = cls.story_records[stem].collection_index

            # Create the "table of contents" for the story.
            for index, line in enumerate(temp_text):

                # Prologue: A Quest for Europa is split among two lines and needs special parsing logic.
                if re.search(re_acvr_chap_title, line):
                    if "*A Quest for Europa*" in line:
                        temp_chap_index[0] += " A Quest for Europa"
                    else:
                        temp_chap_index.append(index)

                elif re.search(re_volume_heading, line):
                    # Add to the index if it's empty or if the newest possible entry is unique.
                    if (len(temp_coll_index) == 0) or (line != temp_text[temp_coll_index[-1]]):
                        temp_coll_index.append(index)

            indexing_end_time = perf_counter()
            indexing_time = indexing_end_time - indexing_start_time

        LOGGER.info(f"Loaded file: {filepath.stem} | Indexing time: {indexing_time:.5f}")

    @commands.hybrid_command()
    async def random_text(self, ctx: commands.Context) -> None:
        """Display a random line from an M J Bradley work.

        Parameters
        ----------
        ctx : :class:`discord.ext.commands.Context`
            The invocation context where the command was called.
        """

        # Randomly choose an M J Bradley story.
        story = choice([key for key in self.story_records])

        # Randomly choose two paragraphs from the story.
        b_range = randint(2, len(self.story_records[story].text) - 3)
        b_sample = self.story_records[story].text[b_range: (b_range + 2)]

        # Get the chapter and collection of the quote.
        quote_year = self._binary_search_text(story, self.story_records[story].collection_index, (b_range + 2))
        quote_chapter = self._binary_search_text(story, self.story_records[story].chapter_index, (b_range + 2))

        # Bundle the quote in an embed.
        embed = StoryQuoteEmbed(
            color=0xdb05db,
            story_data=self.convertor.unstructure(self.story_records[story]),
            page_content=(quote_year, quote_chapter, "".join(b_sample))
        ).set_footer(text="Randomly chosen quote from an M J Bradley story.")

        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def search_cadmean(self, ctx: commands.Context, query: str) -> None:
        """Search *A Cadmean Victory Remastered* by MJ Bradley for a word or phrase.

        Parameters
        ----------
        ctx : :class:`discord.ext.commands.Context`
            The invocation context.
        query : :class:`str`
            The string to search for in the story.
        """

        async with ctx.typing():
            start_time = perf_counter()
            processed_text = self._process_text("acvr", query)
            end_time = perf_counter()

            LOGGER.info(f"_process_text() time: {end_time - start_time:.8f}")

            story_embed = deepcopy(self.story_records["acvr"].template_embed)

            if len(processed_text) == 0:
                story_embed.title = "N/A"
                story_embed.description = "No quotes found!"
                story_embed.set_page_footer(0, 0)
                await ctx.send(embed=story_embed)

            else:
                story_embed.set_page_content(processed_text[0]).set_page_footer(1, len(processed_text))
                await ctx.send(
                    embed=story_embed,
                    view=StoryQuoteView(
                        interaction=ctx.interaction,
                        all_pages_content=processed_text,
                        story_data=self.convertor.unstructure(self.story_records["acvr"])
                    )
                )

    @classmethod
    def _process_text(cls, story: str, terms: str, exact: bool = True) -> list[tuple | None]:
        """Collects all lines from story text that contain the given terms."""

        all_text = cls.story_records[story].text
        results = []

        # Iterate through all text in the story.
        for index, line in enumerate(all_text):

            # Determine if searching based on exact words/phrases, or keywords.
            if exact:
                terms_presence = terms.lower() in line.lower()
            else:
                terms_presence = any([term.lower() in line.lower() for term in terms.split()])

            if terms_presence:
                # Connect the paragraph with the terms to the one following it.
                quote = "\n".join(all_text[index:index + 3])

                # Underline the terms.
                quote = re.sub(f'( |^)({terms})', r'\1__\2__', quote, flags=re.I)

                # Fit the paragraphs in the space of a Discord embed field.
                if len(quote) > 1024:
                    quote = quote[0:1020] + "..."

                # Get the "collection" and "chapter" text lines using binary search.
                quote_collection = cls._binary_search_text(story, cls.story_records[story].collection_index, index)
                quote_chapter = cls._binary_search_text(story, cls.story_records[story].chapter_index, index)

                # Take special care for ACVR.
                if story == "acvr":
                    acvr_title_with_space = "A Cadmean Victory "
                    quote_collection = quote_collection[len(acvr_title_with_space):]
                    quote_chapter = quote_chapter[2:]

                # Aggregate the quotes.
                results.append((quote_collection, quote_chapter, quote))

        return results

    @classmethod
    def _binary_search_text(cls, story: str, list_of_indices: list[int], index: int) -> str:
        """Finds the element in a list of elements closest to but less than the given element."""

        if len(list_of_indices) == 0:
            return "—————"

        # Get the list index of the element that's closest to and less than the given index value.
        i_of_index = bisect_left(list_of_indices, index)

        # Get the element from the list based on the previously calculated list index.
        actual_index = list_of_indices[max(i_of_index - 1, 0)] if (i_of_index is not None) else -1

        # Use that element as an index in the story text list to get a quote, whether it's a chapter, volume, etc.
        value_from_index = cls.story_records[story].text[actual_index] if actual_index != -1 else "—————"

        return value_from_index


async def setup(bot: ACadmeanQuoteBot) -> None:
    """Connect bot to cog."""

    await bot.add_cog(StorySearchCog(bot))
