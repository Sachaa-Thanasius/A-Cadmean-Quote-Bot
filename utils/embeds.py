"""
embeds.py: This class provides embeds for user-specific statistics separated into fields.
"""

from __future__ import annotations

import logging
from typing_extensions import Self

from discord import Embed

LOGGER = logging.getLogger(__name__)
EMOJI_URL = "https://cdn.discordapp.com/emojis/{0}.webp?size=128&quality=lossless"

_MISSING = object()     # sentinel value


class PaginatedEmbed(Embed):
    """A subclass of :class:`Embed` customized to create an embed 'page'.

    Parameters
    ----------
    page_content : :class:`tuple`, optional
        The content of an embed page.
    current_page : :class:`int`, optional
        The number of the current page.
    max_pages : :class:`int`, optional
        The total number of pages possible.
    **kwargs
        Keyword arguments for the normal initialization of an :class:`Embed`.

    See Also
    --------
    :class:`utils.paginated_views.PaginatedEmbedView`
    """

    def __init__(
            self,
            *,
            page_content: tuple | None = _MISSING,
            current_page: int | None = _MISSING,
            max_pages: int | None = _MISSING,
            **kwargs
    ) -> None:

        super().__init__(**kwargs)

        if page_content is not _MISSING:
            self.set_page_content(page_content)

        if (current_page is not _MISSING) and (max_pages is not _MISSING):
            self.set_page_footer(current_page, max_pages)

    def set_page_content(self, page_content: tuple | None = None) -> Self:
        """Sets the content field for this embed page.

        This function returns the class instance to allow for fluent-style chaining.

        Parameters
        ----------
        page_content : tuple
            A tuple with 3 elements (unless overriden) that contains the content for this embed page.
        """

        if page_content is None:
            self.title = "N/A"
            if self.fields:
                self.remove_field(0)

        else:
            self.title = str(page_content[0])
            chapter_name, quote = str(page_content[1]), str(page_content[2])
            self.add_field(name=chapter_name, value=quote)

        return self

    def set_page_footer(self, current_page: int | None = None, max_pages: int | None = None) -> Self:
        """Sets the footer for this embed page.

        This function returns the class instance to allow for fluent-style chaining.

        Parameters
        ----------
        current_page : :class:`int`
            The number of the current page.
        max_pages : :class:`int`
            The total number of pages possible.
        """

        if current_page is None:
            current_page = 0
        if max_pages is None:
            current_page = 0

        self.set_footer(text=f"Page {current_page}/{max_pages}")

        return self


class StoryQuoteEmbed(PaginatedEmbed):
    """A subclass of :class:`PaginatedEmbed` customized to create an embed 'page' for a story, given actual data about
    the story.

    Parameters
    ----------
    story_data : dict, optional
        The information about the story to be put in the author field, including the story title, author, and link.
    **kwargs
        Keyword arguments for the normal initialization of an :class:`PaginatedEmbed`. Refer to that class for all
        possible arguments.
    """

    def __init__(self, *, story_data: dict | None = _MISSING, **kwargs) -> None:
        super().__init__(**kwargs)

        if story_data is not _MISSING:
            self.set_page_author(story_data)

    def set_page_content(self, page_content: tuple | None = None) -> Self:
        return super().set_page_content(page_content)

    def set_page_footer(self, current_page: int | None = None, max_pages: int | None = None) -> Self:
        return super().set_page_footer(current_page, max_pages)

    def set_page_author(self, story_data: dict | None = None) -> Self:
        """Sets the author for this embed page.

        This function returns the class instance to allow for fluent-style chaining.
        """

        if story_data is None:
            self.remove_author()

        else:
            self.set_author(
                name=story_data["title"],
                url=story_data["link"],
                icon_url=EMOJI_URL.format(str(story_data["emoji_id"]))
            )

        return self
