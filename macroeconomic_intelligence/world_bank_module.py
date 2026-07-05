"""World Bank Open Data integration for country-level development and economic indicators.

Provides asynchronous access to World Development Indicators (WDI),
Worldwide Governance Indicators (WGI), financial sector depth metrics,
and composite country risk indexing across all 194 WIPO jurisdictions.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from numpy.polynomial import polynomial as P

# ---------------------------------------------------------------------------
# ARGUS-PANTHER ULTIMA shared configuration
# ---------------------------------------------------------------------------
try:
    from config import API_VAULT, SEIZABLE_VALUE, CONTAGION_RISK, WIPO_JURISDICTION_COUNT
except ImportError:
    API_VAULT = {}
    SEIZABLE_VALUE = Decimal("0")
    CONTAGION_RISK = {
        "sovereign_debt_threshold": 90.0,
        "inflation_crisis_threshold": 20.0,
        "reserve_coverage_minimum": 3.0,
        "current_account_deficit_max": -5.0,
    }
    WIPO_JURISDICTION_COUNT = 194

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Indicator catalogue
# ---------------------------------------------------------------------------
WB_INDICATORS: Dict[str, str] = {
    # Economic aggregates
    "NY.GDP.MKTP.CD": "gdp_current_usd",
    "NY.GDP.MKTP.KD.ZG": "gdp_growth",
    "NY.GDP.PCAP.CD": "gdp_per_capita",
    "NE.TRD.GNFS.ZS": "trade_balance_pct_gdp",
    "NE.EXP.GNFS.CD": "exports_goods_services",
    "NE.IMP.GNFS.CD": "imports_goods_services",
    "BN.CAB.XOKA.GD.ZS": "current_account_balance_pct_gdp",
    # Governance (WGI)
    "CC.EST": "control_of_corruption",
    "RL.EST": "rule_of_law",
    "RQ.EST": "regulatory_quality",
    "GE.EST": "government_effectiveness",
    "VA.EST": "voice_accountability",
    "PV.EST": "political_stability",
    # Financial sector
    "GFDD.DI.14": "domestic_credit_private_sector",
    "FM.AST.PRVT.GD.ZS": "private_credit_pct_gdp",
    "BX.KLT.DINV.WD.GD.ZS": "fdi_net_inflows_pct_gdp",
    "GC.DOD.TOTL.GD.ZS": "central_govt_debt_pct_gdp",
    # Social / development
    "SI.POV.GINI": "gini_index",
    "SP.DYN.LE00.IN": "life_expectancy",
    "SE.ADT.LITR.ZS": "literacy_rate",
    "SL.UEM.TOTL.ZS": "unemployment_total",
}

# Risk index weights
RISK_WEIGHTS: Dict[str, float] = {
    "control_of_corruption": 0.20,
    "rule_of_law": 0.20,
    "regulatory_quality": 0.15,
    "private_credit_pct_gdp": 0.15,
    "trade_balance_pct_gdp": 0.15,
    "gdp_growth": 0.15,
}

# WIPO 194 jurisdiction ISO3 codes (core set — expanded at runtime)
WIPO_CORE_JURISDICTIONS: List[str] = [
    "USA", "CHN", "JPN", "DEU", "GBR", "IND", "FRA", "ITA", "BRA", "CAN",
    "KOR", "RUS", "MEX", "ESP", "AUS", "TUR", "NLD", "CHE", "SAU", "ARG",
    "SWE", "POL", "BEL", "THA", "IRL", "ISR", "NOR", "AUT", "NGA", "ZAF",
    "BGD", "EGY", "DNK", "SGP", "MYS", "HKG", "PHL", "VNM", "GRC", "FIN",
    "CHL", "PAK", "IRQ", "PRT", "KAZ", "DZA", "QAT", "NZL", "PER", "KWT",
    "MAR", "SVK", "DOM", "LUX", "ECU", "COL", "HUN", "KEN", "ETH", "OMN",
    "CZE", "ROU", "JOR", "PAN", "BHR", "TTO", "UKR", "GTM", "MMR", "URY",
    "BGR", "CRI", "HRV", "UZB", "LTU", "SVN", "TZA", "LBN", "GHA", "VEN",
    "CIV", "BRN", "AGO", "CMR", "BOL", "LKA", "LVA", "NPL", "TUN", "LBY",
    "YEM", "EST", "UGA", "MAC", "MDA", "SEN", "ZWE", "BWA", "GAB", "PSE",
    "MNG", "JAM", "ARM", "NIC", "RWA", "MKD", "MLI", "HND", "BFA", "LAO",
    "KGZ", "TJK", "TCD", "SOM", "MLT", "MDV", "CPV", "TGO", "BEN", "MUS",
    "BTN", "SWZ", "FJI", "DJI", "GNB", "SLE", "CAF", "LBR", "SYC", "BDI",
    "LSO", "GNQ", "GMB", "VUT", "KIR", "COM", "SLB", "STP", "WSM", "PLW",
    "FSM", "TON", "NRU", "TUV", "KHM", "AZE", "GEO", "BLR", "TKM", "CUB",
    "PRY", "ZMB", "MWI", "MOZ", "NAM", "SUR", "GUY", "ISL", "SLV", "PNG",
    "ATG", "DMA", "GRD", "LCA", "VCT", "COG", "GIN",
]


class WorldBankIntelligence:
    """World Bank Open Data intelligence interface.

    Fetches economic, governance, and financial-sector indicators
    from the World Bank's WDI database, computes composite risk
    indices, and generates jurisdictional risk maps.

    Parameters
    ----------
    cache_dir : Optional[str]
        Directory for temporary CSV cache files.
    """

    def __init__(self, cache_dir: Optional[str] = None) -> None:
        self.cache_dir = cache_dir or tempfile.gettempdir()
        self._session_counter = 0
        self._cache: Dict[str, pd.DataFrame] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cache_path(self, label: str) -> str:
        self._session_counter += 1
        return os.path.join(self.cache_dir, f"wb_{label}_{self._session_counter}.csv")

    def _read_cached_csv(self, path: str) -> pd.DataFrame:
        if not os.path.exists(path):
            return pd.DataFrame()
        df = pd.read_csv(path)
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
        df.dropna(how="all", inplace=True)
        return df

    @staticmethod
    def _normalise_country_code(code: str) -> str:
        mapping = {
            "US": "USA", "UK": "GBR", "EU": "EUR",
            "CN": "CHN", "JP": "JPN", "DE": "DEU",
            "FR": "FRA", "IN": "IND", "BR": "BRA",
            "RU": "RUS", "MX": "MEX", "KR": "KOR",
            "CA": "CAN", "AU": "AUS", "IT": "ITA",
            "ES": "ESP", "NL": "NLD", "SE": "SWE",
            "NO": "NOR", "CH": "CHE", "SG": "SGP",
            "HK": "HKG", "TH": "THA", "MY": "MYS",
            "ID": "IDN", "PH": "PHL", "VN": "VNM",
            "TR": "TUR", "ZA": "ZAF", "AR": "ARG",
            "CL": "CHL", "CO": "COL", "PE": "PER",
            "EG": "EGY", "NG": "NGA", "KE": "KEN",
            "GH": "GHA", "ET": "ETH", "SA": "SAU",
            "AE": "ARE", "IL": "ISR", "QA": "QAT",
            "KW": "KWT", "BD": "BGD", "PK": "PAK",
        }
        code_up = code.upper().strip()
        return mapping.get(code_up, code_up)

    @staticmethod
    def _z_score(series: pd.Series) -> pd.Series:
        """Compute z-score normalisation."""
        mu = series.mean()
        sigma = series.std()
        if sigma == 0 or pd.isna(sigma):
            return pd.Series(0.0, index=series.index)
        return (series - mu) / sigma

    # ------------------------------------------------------------------
    # Generic indicator fetcher
    # ------------------------------------------------------------------

    async def fetch_indicator(
        self,
        indicator_code: str,
        country_codes: List[str],
        start_year: int = 2015,
        end_year: int = 2026,
    ) -> pd.DataFrame:
        """Fetch a World Bank indicator for given countries and date range.

        Parameters
        ----------
        indicator_code : str
            World Bank indicator code (e.g. ``"NY.GDP.MKTP.CD"``).
        country_codes : List[str]
            ISO-3 country codes.
        start_year : int
        end_year : int

        Returns
        -------
        pd.DataFrame
            Columns include ``country``, ``country_code``, ``year``, ``value``.
        """
        iso3_list = [self._normalise_country_code(c) for c in country_codes]
        country_str = ",".join(iso3_list)
        path = self._cache_path(indicator_code.replace(".", "_"))

        try:
            df = await asyncio.to_thread(
                self._fetch_wb_sync,
                indicator=indicator_code,
                country=country_str,
                start_year=start_year,
                end_year=end_year,
                path=path,
            )
            return df
        except Exception as exc:
            logger.error("World Bank fetch failed for %s: %s", indicator_code, exc)
            return pd.DataFrame(columns=["country", "country_code", "year", "value"])

    def _fetch_wb_sync(
        self,
        indicator: str,
        country: str,
        start_year: int,
        end_year: int,
        path: str,
    ) -> pd.DataFrame:
        """Synchronous World Bank data fetch wrapper."""
        from agents.tools.datasource import get_data_source

        get_data_source(
            data_source_name="world_bank_open_data",
            api_name="world_bank_open_data",
            params={
                "indicator": indicator,
                "country": country,
                "date_range": f"{start_year}:{end_year}",
                "filepath": path,
                "language": "en",
            },
        )
        df = self._read_cached_csv(path)
        if df.empty:
            return df

        # Normalise column names
        rename_map = {}
        for col in df.columns:
            if col in ("country", "country_name", "economy"):
                rename_map[col] = "country"
            elif col in ("country_code", "iso3_code", "economy_code"):
                rename_map[col] = "country_code"
            elif col in ("year", "date", "time_period"):
                rename_map[col] = "year"
            elif col in ("value", "obs_value"):
                rename_map[col] = "value"
        df.rename(columns=rename_map, inplace=True)

        # Ensure standard columns
        for col in ["country", "country_code", "year", "value"]:
            if col not in df.columns:
                df[col] = None

        return df[["country", "country_code", "year", "value"]]

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    async def fetch_gdp_series(self, country_codes: List[str]) -> pd.DataFrame:
        """Fetch GDP (current US$) — indicator ``NY.GDP.MKTP.CD``."""
        return await self.fetch_indicator("NY.GDP.MKTP.CD", country_codes)

    async def fetch_trade_balance(self, country_codes: List[str]) -> pd.DataFrame:
        """Fetch trade balance (% of GDP) — indicator ``NE.TRD.GNFS.ZS``."""
        return await self.fetch_indicator("NE.TRD.GNFS.ZS", country_codes)

    async def fetch_governance_indicators(self, country_codes: List[str]) -> pd.DataFrame:
        """Fetch Worldwide Governance Indicators (WGI).

        Indicators
        ----------
        - CC.EST : Control of Corruption
        - RL.EST : Rule of Law
        - RQ.EST : Regulatory Quality
        """
        gov_codes = ["CC.EST", "RL.EST", "RQ.EST"]
        frames: List[pd.DataFrame] = []
        for code in gov_codes:
            df = await self.fetch_indicator(code, country_codes)
            if not df.empty:
                df["indicator"] = WB_INDICATORS.get(code, code)
                frames.append(df)
        if not frames:
            return pd.DataFrame(columns=["country", "country_code", "year", "indicator", "value"])
        return pd.concat(frames, ignore_index=True)

    async def fetch_financial_sector_depth(self, country_codes: List[str]) -> pd.DataFrame:
        """Fetch domestic credit to private sector (% of GDP).

        Indicator ``FM.AST.PRVT.GD.ZS``.
        """
        return await self.fetch_indicator("FM.AST.PRVT.GD.ZS", country_codes)

    # ------------------------------------------------------------------
    # Composite risk index
    # ------------------------------------------------------------------

    async def compute_country_risk_index(self, country_code: str) -> Dict[str, float]:
        """Compute composite country risk index from WB indicators.

        Parameters
        ----------
        country_code : str
            ISO-3 country code.

        Returns
        -------
        Dict[str, float]
            ``overall_score`` (0=low risk, 100=high risk) plus component scores.
        """
        iso3 = self._normalise_country_code(country_code)

        # Fetch all relevant indicators
        indicators_to_fetch = [
            "CC.EST", "RL.EST", "RQ.EST", "FM.AST.PRVT.GD.ZS",
            "NE.TRD.GNFS.ZS", "NY.GDP.MKTP.KD.ZG",
        ]
        frames: List[pd.DataFrame] = []
        for ind in indicators_to_fetch:
            df = await self.fetch_indicator(ind, [iso3], start_year=2018, end_year=2026)
            if not df.empty:
                df["indicator"] = WB_INDICATORS.get(ind, ind)
                frames.append(df)

        if not frames:
            return {"overall_score": 50.0, "data_quality": 0.0}

        combined = pd.concat(frames, ignore_index=True)
        combined["value"] = pd.to_numeric(combined["value"], errors="coerce")
        combined.dropna(subset=["value"], inplace=True)

        if combined.empty:
            return {"overall_score": 50.0, "data_quality": 0.0}

        # Use most recent value per indicator
        latest = combined.sort_values("year").groupby("indicator").tail(1)
        values = dict(zip(latest["indicator"], latest["value"]))

        scores: Dict[str, float] = {}

        # Governance scores (WGI range ~ -2.5 to +2.5; higher = better)
        for gov_key in ["control_of_corruption", "rule_of_law", "regulatory_quality"]:
            val = values.get(gov_key, np.nan)
            if pd.notna(val):
                # Convert to risk score: low WGI = high risk
                scores[f"{gov_key}_risk"] = max(0.0, min(100.0, (1.0 - (float(val) + 2.5) / 5.0) * 100))
            else:
                scores[f"{gov_key}_risk"] = 50.0

        # Financial depth (higher credit/GDP = potential vulnerability)
        credit = values.get("private_credit_pct_gdp", np.nan)
        if pd.notna(credit):
            scores["financial_depth_risk"] = min(100.0, max(0.0, float(credit) / 2.0))
        else:
            scores["financial_depth_risk"] = 50.0

        # Trade balance (persistent deficit = risk)
        trade = values.get("trade_balance_pct_gdp", np.nan)
        if pd.notna(trade):
            scores["trade_risk"] = max(0.0, min(100.0, -float(trade) * 5.0))
        else:
            scores["trade_risk"] = 50.0

        # GDP growth (negative = risk)
        growth = values.get("gdp_growth", np.nan)
        if pd.notna(growth):
            scores["growth_risk"] = max(0.0, min(100.0, -float(growth) * 10.0 + 20.0))
        else:
            scores["growth_risk"] = 50.0

        # Weighted composite
        overall = (
            scores.get("control_of_corruption_risk", 50.0) * 0.20
            + scores.get("rule_of_law_risk", 50.0) * 0.20
            + scores.get("regulatory_quality_risk", 50.0) * 0.15
            + scores.get("financial_depth_risk", 50.0) * 0.15
            + scores.get("trade_risk", 50.0) * 0.15
            + scores.get("growth_risk", 50.0) * 0.15
        )
        scores["overall_score"] = round(overall, 2)
        scores["data_quality"] = sum(1 for v in scores.values() if v != 50.0) / 6.0

        return scores

    # ------------------------------------------------------------------
    # Jurisdictional risk map
    # ------------------------------------------------------------------

    async def get_jurisdictional_risk_map(self) -> Dict[str, Dict[str, float]]:
        """Build a risk map for all 194 WIPO jurisdictions.

        Returns
        -------
        Dict[str, Dict[str, float]]
            Mapping of ISO-3 code -> risk score dict.
        """
        jurisdictions = WIPO_CORE_JURISDICTIONS[:WIPO_JURISDICTION_COUNT]
        risk_map: Dict[str, Dict[str, float]] = {}

        # Process in batches of 20 to avoid rate limits
        batch_size = 20
        for i in range(0, len(jurisdictions), batch_size):
            batch = jurisdictions[i:i + batch_size]
            tasks = [self.compute_country_risk_index(cc) for cc in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for cc, result in zip(batch, results):
                if isinstance(result, Exception):
                    risk_map[cc] = {"overall_score": 50.0, "error": str(result)}
                else:
                    risk_map[cc] = result

        return risk_map

    # ------------------------------------------------------------------
    # Development trajectory
    # ------------------------------------------------------------------

    async def analyze_development_trajectory(self, country_code: str) -> Dict[str, Any]:
        """Analyze development trajectory with anomaly detection.

        Parameters
        ----------
        country_code : str
            ISO-3 country code.

        Returns
        -------
        Dict[str, Any]
            Trend coefficients, anomaly flags, growth regime classification.
        """
        iso3 = self._normalise_country_code(country_code)

        gdp_df = await self.fetch_gdp_series([iso3])
        if gdp_df.empty:
            return {"error": f"No GDP data for {iso3}", "country": iso3}

        gdp_df["value"] = pd.to_numeric(gdp_df["value"], errors="coerce")
        gdp_df.dropna(subset=["value"], inplace=True)
        gdp_df.sort_values("year", inplace=True)

        if len(gdp_df) < 3:
            return {"error": "Insufficient data points", "country": iso3}

        years = gdp_df["year"].astype(float).values
        values = np.log(gdp_df["value"].astype(float).values)  # log GDP

        # Polynomial trend fit (3rd order)
        coeffs = P.polyfit(years - years.mean(), values, 3)
        trend = P.polyval(years - years.mean(), coeffs)
        residuals = values - trend

        # Anomaly detection (z-score > 2)
        residual_z = (residuals - residuals.mean()) / (residuals.std() or 1.0)
        anomalies = [
            {"year": int(y), "residual": round(float(r), 4), "z_score": round(float(z), 2)}
            for y, r, z in zip(years, residuals, residual_z)
            if abs(z) > 2.0
        ]

        # Growth regime
        slope = coeffs[1] if len(coeffs) > 1 else 0.0
        curvature = coeffs[2] if len(coeffs) > 2 else 0.0

        if slope > 0.05 and curvature > 0:
            regime = "accelerating_growth"
        elif slope > 0.02:
            regime = "steady_growth"
        elif slope > 0:
            regime = "slowing_growth"
        elif slope > -0.02:
            regime = "stagnation"
        else:
            regime = "contraction"

        # CAGR
        if len(values) >= 2:
            cagr = (np.exp(values[-1]) / np.exp(values[0])) ** (1.0 / max(years[-1] - years[0], 1)) - 1
        else:
            cagr = 0.0

        return {
            "country": iso3,
            "regime": regime,
            "trend_slope": round(float(slope), 6),
            "trend_curvature": round(float(curvature), 8),
            "cagr_pct": round(float(cagr) * 100, 2),
            "anomalies": anomalies,
            "data_points": len(gdp_df),
            "latest_gdp_usd": float(gdp_df["value"].iloc[-1]) if not gdp_df.empty else None,
        }
