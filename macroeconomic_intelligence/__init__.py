"""ARGUS-PANTHER ULTIMA — Macroeconomic Intelligence Module.

Provides sovereign risk assessment, cross-border contagion modeling,
IMF WEO integration, World Bank Open Data feeds, and BIS-compatible
shadow-banking exposure analytics.

Exports
-------
IMFIntelligence         — IMF World Economic Outlook & COFER data
WorldBankIntelligence   — World Bank indicators & governance data
ContagionPathwayAnalyzer — Multi-order contagion pathway engine
ContagionReport         — Typed dataclass for contagion results
"""

from __future__ import annotations

from macroeconomic_intelligence.imf_module import IMFIntelligence
from macroeconomic_intelligence.world_bank_module import WorldBankIntelligence
from macroeconomic_intelligence.contagion_engine import (
    ContagionPathwayAnalyzer,
    ContagionReport,
)

__all__ = [
    "IMFIntelligence",
    "WorldBankIntelligence",
    "ContagionPathwayAnalyzer",
    "ContagionReport",
]
