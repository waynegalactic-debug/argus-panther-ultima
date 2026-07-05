"""Web Dashboard module for ARGUS-PANTHER ULTIMA.

Exports:
    generate_radar_html: Generate the interactive radar dashboard HTML
"""

from .radar_system import generate_radar_html

__all__ = [
    "generate_radar_html",
]
