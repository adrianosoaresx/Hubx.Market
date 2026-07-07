from __future__ import annotations

import re
from dataclasses import dataclass


DEFAULT_CONVERSION_PRIMARY = "#9a6410"
CONVERSION_TEXT_COLOR = "#ffffff"
MIN_CONVERSION_TEXT_CONTRAST = 4.5

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


@dataclass(frozen=True)
class ConversionColorTheme:
    primary: str
    hover: str
    text: str
    focus_ring: str


def normalize_hex_color(value: object) -> str:
    color = str(value or "").strip()
    if not color:
        return ""
    if not _HEX_COLOR_RE.match(color):
        return ""
    return color.lower()


def validate_conversion_primary_color(value: object) -> tuple[str, str]:
    color = str(value or "").strip()
    if not color:
        return "", ""

    normalized = normalize_hex_color(color)
    if not normalized:
        return "", "Cor de conversão deve usar formato hexadecimal, ex.: #9a6410."

    contrast = contrast_ratio(normalized, CONVERSION_TEXT_COLOR)
    if contrast < MIN_CONVERSION_TEXT_CONTRAST:
        return "", "Use uma cor mais escura ou saturada para manter contraste AA com texto branco."

    return normalized, ""


def build_conversion_color_theme(value: object) -> ConversionColorTheme | None:
    normalized = normalize_hex_color(value)
    if not normalized:
        return None
    red, green, blue = _hex_to_rgb(normalized)
    return ConversionColorTheme(
        primary=normalized,
        hover=_darken(normalized, amount=0.16),
        text=CONVERSION_TEXT_COLOR,
        focus_ring=f"rgba({red}, {green}, {blue}, 0.35)",
    )


def conversion_theme_inline_style(value: object) -> str:
    theme = build_conversion_color_theme(value)
    if theme is None:
        return ""
    return (
        f"--tenant-conversion-primary: {theme.primary}; "
        f"--tenant-conversion-primary-hover: {theme.hover}; "
        f"--tenant-conversion-primary-text: {theme.text}; "
        f"--focus-ring: {theme.focus_ring};"
    )


def contrast_ratio(first: str, second: str) -> float:
    first_luminance = _relative_luminance(first)
    second_luminance = _relative_luminance(second)
    lighter = max(first_luminance, second_luminance)
    darker = min(first_luminance, second_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    color = normalize_hex_color(value)
    if not color:
        return (0, 0, 0)
    return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))


def _relative_luminance(value: str) -> float:
    red, green, blue = (_linear_channel(channel / 255) for channel in _hex_to_rgb(value))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _linear_channel(value: float) -> float:
    if value <= 0.03928:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _darken(value: str, *, amount: float) -> str:
    red, green, blue = _hex_to_rgb(value)
    factor = max(0, min(1, 1 - amount))
    return f"#{int(red * factor):02x}{int(green * factor):02x}{int(blue * factor):02x}"
