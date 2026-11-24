"""Server-side SVG charts for real simulation data.

No JavaScript, no plotting library, no image files: the browser receives an
SVG built from the numbers ngspice wrote. Labels are HTML-escaped.
"""

from __future__ import annotations

import math
from html import escape
from typing import Optional

_W = 720
_H = 310
_M_LEFT = 64
_M_RIGHT = 16
_M_TOP = 30
_M_BOTTOM = 68

_COLORS = {
    "teal": "#2dd4bf",
    "cyan": "#38e1ff",
    "amber": "#fbbf24",
    "violet": "#a78bfa",
}


def _fmt(value: float) -> str:
    magnitude = abs(value)
    if magnitude >= 1e6:
        return f"{value / 1e6:g}M"
    if magnitude >= 1e3:
        return f"{value / 1e3:g}k"
    if magnitude and magnitude < 1e-2:
        return f"{value:.1e}"
    return f"{value:g}"


def _nice_ticks(low: float, high: float, count: int = 5) -> list:
    if not (math.isfinite(low) and math.isfinite(high)):
        return []
    if high == low:
        high = low + 1.0
    span = high - low
    raw = span / max(count, 1)
    magnitude = 10 ** math.floor(math.log10(raw))
    step = magnitude
    for multiple in (1, 2, 2.5, 5, 10):
        if span / (multiple * magnitude) <= count:
            step = multiple * magnitude
            break
    start = math.ceil(low / step) * step
    ticks = []
    value = start
    guard = 0
    while value <= high + step * 1e-9 and guard < 50:
        ticks.append(round(value, 10))
        value += step
        guard += 1
    return ticks


def _log_ticks(low: float, high: float) -> list:
    if low <= 0 or high <= 0:
        return []
    start = math.floor(math.log10(low))
    stop = math.ceil(math.log10(high))
    return [10.0 ** power for power in range(start, stop + 1)
            if low <= 10.0 ** power <= high]


def _downsample(xs: list, ys: list, limit: int = 420) -> tuple:
    """Keep the shape of the curve: stride, but always keep the extremes."""
    if len(xs) <= limit:
        return xs, ys
    stride = max(1, len(xs) // limit)
    out_x = xs[::stride]
    out_y = ys[::stride]
    if out_x[-1] != xs[-1]:
        out_x.append(xs[-1])
        out_y.append(ys[-1])
    return out_x, out_y


def line_chart(series: list, *, x_label: str, y_label: str,
               title: str = "", x_log: bool = False,
               y_zero: bool = False, height: int = _H) -> str:
    """Render one chart with axes, ticks, grid and a legend."""
    clean = []
    for entry in series:
        xs = [x for x, y in zip(entry["x"], entry["y"])
              if math.isfinite(x) and math.isfinite(y)]
        ys = [y for x, y in zip(entry["x"], entry["y"])
              if math.isfinite(x) and math.isfinite(y)]
        if len(xs) >= 2:
            clean.append({**entry, "x": xs, "y": ys})
    if not clean:
        return ('<p class="chart-empty">No data to plot.</p>')

    xs_all = [x for entry in clean for x in entry["x"]]
    ys_all = [y for entry in clean for y in entry["y"]]
    x_low, x_high = min(xs_all), max(xs_all)
    y_low, y_high = min(ys_all), max(ys_all)
    if y_zero:
        y_low = min(y_low, 0.0)
        y_high = max(y_high, 0.0)
    if y_high == y_low:
        y_high = y_low + 1.0
    pad = (y_high - y_low) * 0.08
    y_low -= pad
    y_high += pad

    plot_w = _W - _M_LEFT - _M_RIGHT
    plot_h = height - _M_TOP - _M_BOTTOM

    def sx(value: float) -> float:
        if x_log:
            low, high = math.log10(max(x_low, 1e-12)), math.log10(max(x_high, 1e-12))
            if high == low:
                high = low + 1
            return _M_LEFT + (math.log10(max(value, 1e-12)) - low) / (high - low) * plot_w
        if x_high == x_low:
            return _M_LEFT
        return _M_LEFT + (value - x_low) / (x_high - x_low) * plot_w

    def sy(value: float) -> float:
        return _M_TOP + (y_high - value) / (y_high - y_low) * plot_h

    y_ticks = _nice_ticks(y_low, y_high, 5)
    x_ticks = _log_ticks(x_low, x_high) if x_log else _nice_ticks(x_low, x_high, 6)

    parts = [
        f'<svg class="chart" viewBox="0 0 {_W} {height}" role="img" '
        f'aria-label="{escape(title or y_label)}" '
        f'preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">',
    ]
    if title:
        parts.append(f'<text x="{_M_LEFT}" y="18" class="chart-title">'
                     f'{escape(title)}</text>')

    for tick in y_ticks:
        y = sy(tick)
        parts.append(f'<line x1="{_M_LEFT:.1f}" y1="{y:.1f}" '
                     f'x2="{_M_LEFT + plot_w:.1f}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{_M_LEFT - 8:.1f}" y="{y + 3.5:.1f}" '
                     f'class="tick" text-anchor="end">{escape(_fmt(tick))}</text>')

    for tick in x_ticks:
        x = sx(tick)
        parts.append(f'<line x1="{x:.1f}" y1="{_M_TOP}" x2="{x:.1f}" '
                     f'y2="{_M_TOP + plot_h}" class="grid"/>')
        parts.append(f'<text x="{x:.1f}" y="{_M_TOP + plot_h + 16:.1f}" '
                     f'class="tick" text-anchor="middle">{escape(_fmt(tick))}</text>')

    parts.append(
        f'<rect x="{_M_LEFT}" y="{_M_TOP}" width="{plot_w}" height="{plot_h}" '
        f'class="plot-frame"/>')

    legend_x = _M_LEFT
    for entry in clean:
        xs, ys = _downsample(entry["x"], entry["y"])
        points = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in zip(xs, ys))
        color = _COLORS.get(entry.get("color", "teal"), _COLORS["teal"])
        dash = ' stroke-dasharray="5 4"' if entry.get("dash") else ""
        parts.append(f'<polyline points="{points}" fill="none" '
                     f'stroke="{color}" stroke-width="2"{dash} '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        parts.append(
            f'<line x1="{legend_x}" y1="{height - 10}" '
            f'x2="{legend_x + 18}" y2="{height - 10}" '
            f'stroke="{color}" stroke-width="2.4"{dash}/>')
        parts.append(f'<text x="{legend_x + 24}" y="{height - 7}" '
                     f'class="legend">{escape(entry["label"])}</text>')
        legend_x += 26 + 8 * len(entry["label"]) + 18

    parts.append(f'<text x="{_M_LEFT + plot_w / 2:.1f}" y="{height - 36:.1f}" '
                 f'class="axis-title" text-anchor="middle">{escape(x_label)}</text>')
    parts.append(f'<text x="14" y="{_M_TOP + plot_h / 2:.1f}" class="axis-title" '
                 f'text-anchor="middle" transform="rotate(-90 14 '
                 f'{_M_TOP + plot_h / 2:.1f})">{escape(y_label)}</text>')
    parts.append('</svg>')
    return "".join(parts)


def bode_gain_chart(ac: dict) -> Optional[str]:
    if not ac or not ac.get("freq_hz"):
        return None
    return line_chart(
        [{"label": "|Vout / Vin|", "x": ac["freq_hz"], "y": ac["gain_db"],
          "color": "teal"}],
        x_label="Frequency (Hz)", y_label="Gain (dB)",
        title="AC sweep: gain magnitude", x_log=True,
    )


def bode_phase_chart(ac: dict) -> Optional[str]:
    if not ac or not ac.get("freq_hz"):
        return None
    return line_chart(
        [{"label": "phase(Vout) - phase(Vin)", "x": ac["freq_hz"],
          "y": ac["phase_deg"], "color": "violet"}],
        x_label="Frequency (Hz)", y_label="Phase (deg)",
        title="AC sweep: phase", x_log=True,
    )


def transient_chart(tran: dict) -> Optional[str]:
    if not tran or not tran.get("time_ms"):
        return None
    return line_chart(
        [
            {"label": "Vin (source)", "x": tran["time_ms"],
             "y": tran["vin_mv"], "color": "cyan"},
            {"label": "Vout (collector)", "x": tran["time_ms"],
             "y": tran["vout_mv"], "color": "amber"},
        ],
        x_label="Time (ms)", y_label="Voltage (mV)",
        title="Transient: input and output", y_zero=True,
    )
