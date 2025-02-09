#!/usr/bin/python3
"""Ui Input."""
import os
from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from typing import Self

from matplotlib.font_manager import FontProperties
from nicegui import app
from nicegui import ui
from typing_extensions import TypedDict

from pretty_gpx.common.drawing.utils.fonts import get_css_header
from pretty_gpx.common.utils.paths import FONTS_DIR
from pretty_gpx.common.utils.utils import safe

app.add_static_files('/fonts', os.path.abspath(FONTS_DIR))

class DiscreteValue(TypedDict):
    """Structured representation of discrete values for dropdowns."""
    name: str
    priority: Any


@dataclass
class UiInput:
    """NiceGUI Input Wrapper."""
    input: ui.input

    @classmethod
    def create(cls,
               *,
               label: str,
               value: str,
               tooltip: str,
               on_enter: Callable[[], Awaitable[None]]) -> Self:
        """Create NiceGUI Input element and add a tooltip."""
        with ui.input(label=label, value=value).on('keydown.enter', on_enter).style('width: 100%') as input:
            ui.tooltip(tooltip)
        return cls(input)

    @property
    def _value_str(self) -> str | None:
        """Return the str value."""
        val = str(safe(self.input.value))
        return val if val != "" else None


@dataclass
class UiDropdown:
    """NiceGUI Input Wrapper."""
    input: ui.select

    @classmethod
    def create(cls,
               *,
               label: str,
               discrete_val: list[str] | dict[Any, str],
               default_val: Any,
               tooltip: str,
               on_change: Callable[[], Awaitable[None]]) -> Self:
        """Create NiceGUI Dropdown select element and add a tooltip."""
        if isinstance(discrete_val, list):
            discrete_val = {val: val for val in discrete_val}

        assert isinstance(discrete_val, dict)
        assert default_val in list(discrete_val.keys())
        with ui.select(discrete_val,
                       label=label,
                       value=default_val).on('update:modelValue', on_change).style('width:100%') as input:
            ui.tooltip(tooltip)
        return cls(input)

    @property
    def _value_str(self) -> str:
        """Return the str value."""
        val = str(safe(self.input.value))
        return val

    @property
    def _value_raw(self) -> Any:
        """Return the str value."""
        val: Any = safe(self.input.value)
        return val


@dataclass
class UiFontsMenu:
    """NiceGui menu to select a font in a list."""

    button: ui.dropdown_button
    fonts: tuple[FontProperties, ...]

    @classmethod
    def create(cls,
               *,
               label :str,
               fonts_l: tuple[FontProperties, ...],
               tooltip: str,
               on_change: Callable[[], Awaitable[None]]) -> Self:
        """Create a UiFontsMenu."""
        default_font = fonts_l[0].get_name()
        ui.label(label)
        with ui.dropdown_button(default_font, auto_close=True) as button:
            button.tooltip(tooltip)
            button.classes('bg-white text-black w-48 justify-start')
            button.style(f'display: block; font-family: "{default_font}"; width: 100%;' \
                          'border: 1px solid #ddd; border-radius: 4px; position: relative;')
            for font in fonts_l:
                font_css_header = get_css_header(font=font)
                if font_css_header is not None:
                    ui.add_css(font_css_header)
                font_name = font.get_name()
                def create_click_handler(selected_font: str) -> Callable[[], Awaitable[None]]:
                    async def handler() -> None:
                        button.text = selected_font
                        button.style(f'font-family: "{selected_font}";')
                        await on_change()
                    return handler
                ui.item(font_name, on_click=create_click_handler(font_name)) \
                        .style(f'display: block; font-family:"{font_name}"; width: 100%;' \
                                'border: 1px solid #ddd; border-radius: 4px; position: relative;')
        return cls(button, fonts_l)


@dataclass
class UiFontsMenuFontProp(UiFontsMenu):
    """NiceGUI Str Dropdown Wrapper."""

    @property
    def value(self) -> FontProperties:
        """Return the value."""
        str_to_font = {font.get_name(): font for font in self.fonts}
        font_output = str_to_font.get(self.button.text, None)
        if font_output is None:
            raise KeyError
        else:
            return font_output


@dataclass
class UiDropdownStr(UiDropdown):
    """NiceGUI Str Dropdown Wrapper."""

    @property
    def value(self) -> str:
        """Return the value."""
        return self._value_str

@dataclass
class UiDropdownGeneric(UiDropdown):
    """NiceGUI Str Dropdown Wrapper."""

    @property
    def value(self) -> Any:
        """Return the value."""
        return self._value_raw

@dataclass
class UiInputStr(UiInput):
    """NiceGUI Str Input Wrapper."""

    @property
    def value(self) -> str | None:
        """Return the value."""
        return self._value_str


@dataclass
class UiInputFloat(UiInput):
    """NiceGUI Float Input Wrapper."""

    @property
    def value(self) -> float | None:
        """Return the value."""
        val = self._value_str
        if val is None:
            return None
        return float(val)


@dataclass
class UiInputInt(UiInput):
    """NiceGUI Int Input Wrapper."""

    @property
    def value(self) -> int | None:
        """Return the value."""
        val = self._value_str
        if val is None:
            return None
        return int(float(val))
