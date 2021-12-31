# -*- coding: utf-8 -*-
# Copyright © NeonJonn 2021-present
#
# This file is part of Neon.
#
# Neon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Neon is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Neon. If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import lightbulb

__all__ = [
    "ComponentMenu",
    "Button",
    "SelectMenuOption",
    "SelectMenu",
    "ButtonGroup",
    "TimeoutFunc",
    "button",
    "button_group",
    "select_menu",
    "option",
    "on_timeout",
]

import abc
import asyncio
import dataclasses
import inspect
import typing as t

import hikari
from hikari.interactions.component_interactions import ComponentInteraction

if t.TYPE_CHECKING:
    import lightbulb

CallbackT = t.TypeVar(
    "CallbackT", bound=t.Callable[..., t.Coroutine[t.Any, t.Any, None]]
)


@dataclasses.dataclass
class _BindableObjectMixin(abc.ABC):
    callback: t.Callable[..., t.Coroutine[t.Any, t.Any, None]]
    _bound_to: t.Optional[ComponentMenu] = dataclasses.field(init=False, default=None)

    def __call__(
        self, *args: t.Any, **kwargs: t.Any
    ) -> t.Coroutine[t.Any, t.Any, None]:
        assert self._bound_to is not None
        return self.callback(self._bound_to, *args, **kwargs)

    def __get__(
        self, instance: ComponentMenu, _: t.Type[ComponentMenu]
    ) -> _BindableObjectMixin:
        self._bound_to = instance
        return self


@dataclasses.dataclass
class Button(_BindableObjectMixin):
    label: str
    custom_id: str
    style: t.Union[int, hikari.ButtonStyle]
    emoji: t.Union[hikari.Snowflakeish, hikari.Emoji, str, None]
    is_disabled: bool

    def build_for(
        self, row: hikari.api.ActionRowBuilder, disabled: bool = False
    ) -> None:
        b = row.add_button(self.style, self.custom_id)  # type: ignore
        b.set_label(self.label)
        if self.emoji is not None:
            b.set_emoji(self.emoji)
        b.set_is_disabled(disabled or self.is_disabled)
        b.add_to_container()


@dataclasses.dataclass
class SelectMenuOption:
    label: str
    custom_id: str
    description: str
    emoji: t.Union[hikari.Snowflakeish, hikari.Emoji, str, None]
    is_default: bool

    def build_for(
        self, menu: hikari.api.SelectMenuBuilder[hikari.api.ActionRowBuilder]
    ) -> None:
        o = menu.add_option(self.label, self.custom_id)
        o.set_description(self.description)
        if self.emoji is not None:
            o.set_emoji(self.emoji)
        o.set_is_default(self.is_default)
        o.add_to_menu()


@dataclasses.dataclass
class SelectMenu(_BindableObjectMixin):
    custom_id: str
    placeholder: str
    is_disabled: bool
    min_values: int = 1
    max_values: int = 1

    options: t.MutableMapping[str, SelectMenuOption] = dataclasses.field(
        default_factory=dict
    )

    def build_for(
        self, row: hikari.api.ActionRowBuilder, disabled: bool = False
    ) -> None:
        m = row.add_select_menu(self.custom_id)
        m.set_placeholder(self.placeholder)
        m.set_min_values(self.min_values)
        m.set_max_values(self.max_values)
        m.set_is_disabled(disabled or self.is_disabled)

        for opt in self.options.values():
            opt.build_for(m)

        m.add_to_container()


@dataclasses.dataclass
class ButtonGroup(_BindableObjectMixin):
    buttons: t.MutableMapping[str, Button] = dataclasses.field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(getattr(self.callback, "__name__"))


@dataclasses.dataclass
class TimeoutFunc(_BindableObjectMixin):
    disable_components: bool


class ComponentMenu:
    """
    Base class for making a ``ComponentMenu``.

    Args:
        context (:obj:`lightbulb.Context`): The :obj:`lightbulb.Context` to use.
        timeout (:obj:`float`): The timeout length in seconds.
        author_only (:obj:`bool`): Whether the menu can only be used by the user who ran the command.

    Example:

        .. code-block:: python

            class Menu(neon.ComponentMenu):
                @neon.button("earth", "earth_button", hikari.ButtonStyle.SUCCESS, emoji="\\N{DECIDUOUS TREE}")
                async def earth(self, button: neon.Button) -> None:
                    await self.edit_msg(f"{button.emoji} - {button.custom_id}")

                @neon.option("Water", "water", emoji="\\N{DROPLET}")
                @neon.option("Fire", "fire", emoji="\\N{FIRE}")
                @neon.select_menu("sample_select_menu", "Pick fire or water!")
                async def select_menu_test(self, values: list) -> None:
                    await self.edit_msg(f"You chose: {values[0]}!")

                @neon.button("Wind", "wind_button", hikari.ButtonStyle.PRIMARY, emoji="\\N{WIND BLOWING FACE}\\N{VARIATION SELECTOR-16}")
                @neon.button("Rock", "rock_button", hikari.ButtonStyle.SECONDARY, emoji="\\N{MOYAI}")
                @neon.button_group()
                async def wind_rock(self, button: neon.Button) -> None:
                    await self.edit_msg(f"You pressed: {button.custom_id}")

                @neon.on_timeout(disable_components=True)
                async def on_timeout(self) -> None:
                    await self.edit_msg("\\N{ALARM CLOCK} Timed out!")

            @bot.command
            @lightbulb.command("neon", "Check out Neon's component builder!")
            @lightbulb.implements(lightbulb.SlashCommand, lightbulb.PrefixCommand)
            async def neon_command(ctx: lightbulb.Context) -> None:
                menu = Menu(ctx, timeout=30)
                resp = await ctx.respond("Bar", components=menu.build())
                await menu.run(resp)
    """

    __slots__ = (
        "context",
        "timeout_length",
        "author_only",
        "buttons",
        "button_groups",
        "select_menus",
        "timeout_func",
        "_msg",
        "_inter",
    )

    def __init__(
        self,
        context: lightbulb.Context,
        timeout: float = 60,
        author_only: bool = True,
        disable_on_one_click: bool = False,
    ) -> None:
        self.context = context
        self.timeout_length = timeout
        self.author_only = author_only
        self.disable_on_one_click = disable_on_one_click

        self.buttons: t.MutableMapping[str, Button] = {}
        self.button_groups: t.MutableMapping[
            ButtonGroup, t.MutableMapping[str, Button]
        ] = {}
        self.select_menus: t.MutableMapping[str, SelectMenu] = {}
        self.timeout_func: t.Optional[TimeoutFunc] = None

        self._msg: t.Optional[hikari.Message] = None
        self._inter: t.Optional[ComponentInteraction] = None

    @property
    def msg(self) -> hikari.Message:
        if self._msg is None:
            raise RuntimeError("Attribute '_msg' was None at runtime")
        return self._msg

    @property
    def inter(self) -> hikari.ComponentInteraction:
        if self._inter is None:
            raise RuntimeError("Attribute '_inter' was None at runtime")
        return self._inter

    def build(self) -> t.List[hikari.api.ActionRowBuilder]:
        """
        Builds the :obj:`ComponentMenu` components.

        Returns:
            List[:obj:`hikari.api.ActionRowBuilder`]
        """
        for item in self.__class__.__dict__.keys():
            if item in ["inter", "msg"]:
                continue
            obj = getattr(self, item)

            if isinstance(obj, Button):
                self.buttons[obj.custom_id] = obj
            elif isinstance(obj, SelectMenu):
                self.select_menus[obj.custom_id] = obj
            elif isinstance(obj, ButtonGroup):
                self.button_groups[obj] = obj.buttons
            elif isinstance(obj, TimeoutFunc):
                self.timeout_func = obj

        return self.build_components()

    async def edit_msg(self, *args: t.Any, **kwargs: t.Any) -> None:
        """
        Edit the :obj:`ComponentMenu` message.

        Anything you can pass to :obj:`hikari.messages.PartialMessage.edit` can be passed here.
        """
        if self._inter is not None:
            try:
                await self.inter.create_initial_response(
                    hikari.ResponseType.MESSAGE_UPDATE,
                    *args,
                    **kwargs,
                )
            except hikari.NotFoundError:
                await self.inter.edit_initial_response(
                    *args,
                    **kwargs,
                )
        else:
            await self.msg.edit(*args, **kwargs)

    async def process_interaction_create(
        self, event: hikari.InteractionCreateEvent
    ) -> None:
        assert isinstance(event.interaction, hikari.ComponentInteraction)
        self._inter = event.interaction

        if self.author_only and self.inter.user.id != self.context.user.id:
            return

        cid = self.inter.custom_id

        if self.inter.component_type == hikari.ComponentType.BUTTON:
            button = self.buttons.get(cid)
            if button is not None:
                if len(inspect.signature(button.callback).parameters) > 1:
                    await button(button)
                else:
                    await button()
                return

            for group in self.button_groups:
                button = group.buttons.get(cid)
                if button is not None:
                    await group(button)
                    break

        elif self.inter.component_type == hikari.ComponentType.SELECT_MENU:
            menu = self.select_menus[cid]
            await menu(self.inter.values)

        if self.disable_on_one_click:
            components = self.build_components(disabled=True)
            await self.edit_msg(components=components)

    async def run(self, resp: lightbulb.ResponseProxy) -> None:
        """
        Run the :obj:`ComponentMenu` using the given message.
        """
        if isinstance(resp, lightbulb.ResponseProxy):
            self._msg = await resp.message()
        else:
            self._msg = resp
        while True:
            try:
                assert self.msg is not None
                event = await self.context.bot.wait_for(
                    hikari.InteractionCreateEvent,
                    timeout=self.timeout_length,
                    predicate=lambda e: isinstance(
                        e.interaction, hikari.ComponentInteraction
                    )
                    and e.interaction.message.id == self.msg.id,
                )
            except asyncio.TimeoutError:
                await self.timeout_job(self.timeout_func)
                break
            else:
                await self.process_interaction_create(event)

    async def timeout_job(self, timeout_func: t.Optional[TimeoutFunc]) -> None:
        if timeout_func is not None:
            await timeout_func()

        if timeout_func is None or timeout_func.disable_components:
            components = self.build_components(disabled=True)
            await self.edit_msg(components=components)

    def build_components(
        self, *, disabled: bool = False
    ) -> t.List[hikari.api.ActionRowBuilder]:
        rows = []

        if len(self.buttons) > 0:
            buttons = list(self.buttons.values())
            chunked = [buttons[i : i + 5] for i in range(0, len(buttons), 5)]

            for chunk in chunked:
                row = self.context.bot.rest.build_action_row()
                for btn in chunk:
                    btn.build_for(row, disabled)
                rows.append(row)

        if len(self.button_groups) > 0:
            for group_buttons in self.button_groups.values():
                buttons = list(group_buttons.values())
                chunked = [buttons[i : i + 5] for i in range(0, len(buttons), 5)]

                for chunk in chunked:
                    row = self.context.bot.rest.build_action_row()
                    for btn in chunk:
                        btn.build_for(row, disabled)
                    rows.append(row)

        if len(self.select_menus) > 0:
            for menu in self.select_menus.values():
                row = self.context.bot.rest.build_action_row()
                menu.build_for(row, disabled)
                rows.append(row)

        return rows


def button(
    label: str,
    url_or_custom_id: str,
    style: t.Union[int, hikari.ButtonStyle],
    *,
    emoji: t.Union[hikari.Snowflakeish, hikari.Emoji, str, None] = None,
    is_disabled: bool = False,
) -> t.Callable[[t.Union[CallbackT, ButtonGroup]], t.Union[Button, ButtonGroup]]:
    """
    Creates a :obj:`hikari.messages.ButtonComponent` which is added to the message components.

    Args:
        label (:obj:`str`): The label of the button.
        url_or_custom_id (:obj:`str`): The URL (if the button style is of :obj:`hikari.messages.ButtonStyle.LINK`), or custom ID of the button.
        style: The style of the button.
        emoji: The emoji of the button.
        is_disabled (:obj:`bool`): Whether the button is disabled.
    """

    def decorate(func: t.Union[CallbackT, ButtonGroup]) -> t.Union[Button, ButtonGroup]:
        if isinstance(func, ButtonGroup):
            func.buttons[url_or_custom_id] = Button(
                func.callback, label, url_or_custom_id, style, emoji, is_disabled
            )
            return func
        return Button(func, label, url_or_custom_id, style, emoji, is_disabled)

    return decorate


def button_group() -> t.Callable[[CallbackT], ButtonGroup]:
    """
    Creates a group of buttons which is added to the message components.
    """

    def decorate(func: CallbackT) -> ButtonGroup:
        return ButtonGroup(func)

    return decorate


def select_menu(
    custom_id: str,
    placeholder: str,
    *,
    is_disabled: bool = False,
    min_values: int = 1,
    max_values: int = 1,
) -> t.Callable[[CallbackT], SelectMenu]:
    """
    Creates a :obj:`hikari.messages.SelectMenuComponent` which is added to the message components.

    Args:
        custom_id: The custom ID of the select menu.
        placeholder: The placeholder of the select menu.
        is_disabled: Whether the select menu is disabled.
        min_values: The minimum amount of options which must be chosen for this menu.
        max_values: The maximum amount of options which can be chosen for this menu.
    """

    def decorate(func: CallbackT) -> SelectMenu:
        return SelectMenu(
            func, custom_id, placeholder, is_disabled, min_values, max_values
        )

    return decorate


def option(
    label: str,
    custom_id: str,
    description: str = "",
    *,
    emoji: t.Union[hikari.Snowflakeish, hikari.Emoji, str, None] = None,
    is_default: bool = False,
) -> t.Callable[[SelectMenu], SelectMenu]:
    """
    Creates a :obj:`hikari.messages.SelectMenuOption` which is added to the select menu options.

    Args:
        label: The label of the option.
        custom_id: The custom ID of the option.
        description: The description of the option.
        emoji: The emoji of the option.
        is_default: Whether the option is the default option.
    """

    def decorate(menu: SelectMenu) -> SelectMenu:
        menu.options[custom_id] = SelectMenuOption(
            label, custom_id, description, emoji, is_default
        )
        return menu

    return decorate


def on_timeout(
    *, disable_components: bool = True
) -> t.Callable[[CallbackT], TimeoutFunc]:
    """
    Set the timeout function for the menu.

    Args:
        disable_components: Whether to disable the components of the menu after the timeout.
    """

    def decorate(func: CallbackT) -> TimeoutFunc:
        return TimeoutFunc(func, disable_components)

    return decorate
