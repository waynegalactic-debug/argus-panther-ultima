"""IMF World Economic Outlook integration for global macroeconomic contagion modeling.

Interfaces with the IMF's WEO (World Economic Outlook), COFER (Currency Composition
of Official Foreign Exchange Reserves), BOP (Balance of Payments), and IFS
(International Financial Statistics) datasets to build a comprehensive sovereign
risk and cross-border contagion assessment framework.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# ARGUS-PANTHER ULTIMA shared configuration
# ---------------------------------------------------------------------------
try:
    from config import API_VAULT, SEIZABLE_VALUE, CONTAGION_RISK, WIPO_JURISDICTION_COUNT
except ImportError:
    # Fallback defaults when config module is not yet available
    API_VAULT = {}
    SEIZABLE_VALUE = Decimal("0")
    CONTAGION_RISK = {
        "sovereign_debt_threshold": 90.0,   # debt/GDP %
        "inflation_crisis_threshold": 20.0,  # annual %
        "reserve_coverage_minimum": 3.0,     # months of imports
        "current_account_deficit_max": -5.0, # % of GDP
    }
    WIPO_JURISDICTION_COUNT = 194

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WEO indicator mappings
# ---------------------------------------------------------------------------
WEO_INDICATORS: Dict[str, str] = {
    "NGDP_RPCH": "gdp_growth",
    "PCPIPCH": "inflation",
    "GGXWDG_NGDP": "govt_debt_pct_gdp",
    "LUR": "unemployment",
    "BCA": "current_account_balance",
    "NGDP": "nominal_gdp",
    "PPPPC": "gdp_per_capita_ppp",
    "GGXCNL_NGDP": "fiscal_balance",
}

# Sovereign risk indicator weights (sum = 1.0)
SOVEREIGN_RISK_WEIGHTS: Dict[str, float] = {
    "govt_debt_pct_gdp": 0.30,
    "inflation": 0.20,
    "unemployment": 0.15,
    "current_account_balance": 0.20,
    "gdp_growth": 0.15,
}

# Crisis signal thresholds
CRISIS_THRESHOLDS: Dict[str, float] = {
    "debt_crisis": 90.0,      # government debt / GDP %
    "hyperinflation": 50.0,   # annual inflation %
    "high_inflation": 20.0,
    "currency_crisis_reserves": 3.0,  # months of import cover
    "twin_deficit": -5.0,     # current account % of GDP
    "recession": 0.0,         # real GDP growth
    "severe_recession": -3.0,
}


class IMFIntelligence:
    """IMF World Economic Outlook intelligence interface.

    Provides asynchronous methods to fetch WEO macroeconomic forecasts,
    COFER reserve currency data, and compute sovereign risk scores,
    currency crisis signals, and cross-border contagion probabilities.

    Parameters
    ----------
    cache_dir : Optional[str]
        Directory path for temporary CSV cache files. Defaults to system temp.
    """

    def __init__(self, cache_dir: Optional[str] = None) -> None:
        self.cache_dir = cache_dir or tempfile.gettempdir()
        self._session_counter = 0
        self._cache: Dict[str, pd.DataFrame] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cache_path(self, label: str) -> str:
        """Generate a temporary CSV file path for data-source calls."""
        self._session_counter += 1
        return os.path.join(self.cache_dir, f"imf_{label}_{self._session_counter}.csv")

    def _read_cached_csv(self, path: str) -> pd.DataFrame:
        """Read a cached CSV, normalising column names and dropping empty rows."""
        if not os.path.exists(path):
            return pd.DataFrame()
        df = pd.read_csv(path)
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
        df.dropna(how="all", inplace=True)
        return df

    @staticmethod
    def _normalise_country_code(code: str) -> str:
        """Normalise a country code to ISO-3 uppercase."""
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
    def _sigmoid(x: float, centre: float = 0.0, steepness: float = 1.0) -> float:
        """Sigmoid activation for risk normalisation to [0, 1]."""
        try:
            return 1.0 / (1.0 + np.exp(-steepness * (x - centre)))
        except (OverflowError, FloatingPointError):
            return 0.0 if x < centre else 1.0

    # ------------------------------------------------------------------
    # WEO data
    # ------------------------------------------------------------------

    async def fetch_weo_data(
        self,
        countries: List[str],
        indicators: Optional[List[str]] = None,
        start_year: int = 2020,
        end_year: int = 2026,
    ) -> pd.DataFrame:
        """Fetch IMF WEO macroeconomic forecast data.

        Parameters
        ----------
        countries : List[str]
            ISO-3 country codes (e.g. ``["USA", "CHN", "DEU"]``).
        indicators : Optional[List[str]]
            WEO subject codes. Defaults to core macro set.
        start_year : int
            First forecast year (inclusive).
        end_year : int
            Last forecast year (inclusive).

        Returns
        -------
        pd.DataFrame
            Long-format DataFrame with columns:
            ``country``, ``indicator``, ``year``, ``value``.
        """
        indicators = indicators or list(WEO_INDICATORS.keys())
        iso3_countries = [self._normalise_country_code(c) for c in countries]
        country_str = ",".join(iso3_countries)

        frames: List[pd.DataFrame] = []
        for subject in indicators:
            path = self._cache_path(f"weo_{subject}")
            try:
                df = await asyncio.to_thread(
                    self._fetch_weo_sync,
                    subject=subject,
                    country_str=country_str,
                    start_year=start_year,
                    end_year=end_year,
                    path=path,
                )
                if not df.empty:
                    frames.append(df)
            except Exception as exc:
                logger.warning("WEO fetch failed for %s: %s", subject, exc)
                continue

        if not frames:
            return pd.DataFrame(columns=["country", "indicator", "year", "value"])

        combined = pd.concat(frames, ignore_index=True)
        combined.drop_duplicates(["country", "indicator", "year"], inplace=True)
        return combined

    def _fetch_weo_sync(
        self,
        subject: str,
        country_str: str,
        start_year: int,
        end_year: int,
        path: str,
    ) -> pd.DataFrame:
        """Synchronous wrapper for WEO data fetch (runs in thread pool)."""
        from agents.tools.datasource import get_data_source

        get_data_source(
            data_source_name="imf",
            api_name="imf_weo_data",
            params={
                "subject": subject,
                "country": country_str,
                "start_year": str(start_year),
                "end_year": str(end_year),
                "filepath": path,
            },
        )
        df = self._read_cached_csv(path)
        if df.empty:
            return df
        # Normalise to long format
        if "country" not in df.columns and "country_code" in df.columns:
            df.rename(columns={"country_code": "country"}, inplace=True)
        df["indicator"] = WEO_INDICATORS.get(subject, subject)
        # Ensure year column exists
        for col in ["year", "period", "date", "time_period"]:
            if col in df.columns:
                df.rename(columns={col: "year"}, inplace=True)
                break
        # Ensure value column exists
        for col in ["value", "obs_value", "forecast", "weo_value"]:
            if col in df.columns:
                df.rename(columns={col: "value"}, inplace=True)
                break
        return df

    # ------------------------------------------------------------------
    # COFER data
    # ------------------------------------------------------------------

    async def fetch_cofer_data(self) -> pd.DataFrame:
        """Fetch COFER (Currency Composition of Official Foreign Exchange Reserves).

        Returns shares of USD, EUR, CNY, JPY, GBP, and other currencies
        in global official reserves.

        Returns
        -------
        pd.DataFrame
            Columns: ``year``, ``currency``, ``share_pct``.
        """
        currencies = ["CI_USD", "CI_EUR", "CI_JPY", "CI_GBP", "CI_CNY", "CI_OTHC"]
        frames: List[pd.DataFrame] = []

        for currency in currencies:
            path = self._cache_path(f"cofer_{currency}")
            try:
                df = await asyncio.to_thread(
                    self._fetch_cofer_sync,
                    currency=currency,
                    path=path,
                )
                if not df.empty:
                    frames.append(df)
            except Exception as exc:
                logger.warning("COFER fetch failed for %s: %s", currency, exc)
                continue

        if not frames:
            return pd.DataFrame(columns=["year", "currency", "share_pct"])
        return pd.concat(frames, ignore_index=True)

    def _fetch_cofer_sync(self, currency: str, path: str) -> pd.DataFrame:
        """Synchronous COFER fetch wrapper."""
        from agents.tools.datasource import get_data_source

        get_data_source(
            data_source_name="imf",
            api_name="imf_cofer_data",
            params={
                "indicator": "AFXRA",
                "country": "WOO",
                "currency": currency,
                "transformation": "SHRO_PT",
                "frequency": "A",
                "filepath": path,
            },
        )
        df = self._read_cached_csv(path)
        if df.empty:
            return df
        df["currency"] = currency.replace("CI_", "")
        for col in ["year", "period", "date"]:
            if col in df.columns:
                df.rename(columns={col: "year"}, inplace=True)
                break
        for col in ["value", "obs_value", "share_pct", "shro_pt"]:
            if col in df.columns:
                df.rename(columns={col: "share_pct"}, inplace=True)
                break
        return df[["year", "currency", "share_pct"]] if all(
            c in df.columns for c in ["year", "currency", "share_pct"]
        ) else df

    # ------------------------------------------------------------------
    # Sovereign risk scoring
    # ------------------------------------------------------------------

    async def compute_sovereign_risk_score(self, country_code: str) -> Dict[str, float]:
        """Compute a composite sovereign risk score from IMF indicators.

        Combines government debt/GDP, inflation, unemployment, current account,
        and GDP growth into a normalised 0-100 risk index.

        Parameters
        ----------
        country_code : str
            ISO-3 country code.

        Returns
        -------
        Dict[str, float]
            Keys: ``overall_score`` (0=low risk, 100=high risk) plus
            individual component scores.
        """
        iso3 = self._normalise_country_code(country_code)

        weo_df = await self.fetch_weo_data(
            countries=[iso3],
            indicators=list(WEO_INDICATORS.keys()),
            start_year=2022,
            end_year=2026,
        )

        if weo_df.empty:
            logger.warning("No WEO data for %s — returning neutral scores", iso3)
            return {"overall_score": 50.0, "data_quality": 0.0}

        # Pivot to wide format
        pivot = weo_df.pivot_table(
            index="year", columns="indicator", values="value", aggfunc="mean"
        )
        if pivot.empty:
            return {"overall_score": 50.0, "data_quality": 0.0}

        # Use most recent available year
        latest_year = pivot.index.max()
        row = pivot.loc[latest_year]

        scores: Dict[str, float] = {}
        thresholds = CONTAGION_RISK

        # Government debt score (higher debt = higher risk)
        debt_val = row.get("govt_debt_pct_gdp", np.nan)
        if pd.notna(debt_val):
            debt_norm = min(float(debt_val) / thresholds["sovereign_debt_threshold"], 2.0)
            scores["debt_risk"] = self._sigmoid(debt_norm - 1.0, 0.0, 4.0) * 100
        else:
            scores["debt_risk"] = 50.0

        # Inflation score (higher inflation = higher risk)
        infl_val = row.get("inflation", np.nan)
        if pd.notna(infl_val):
            infl_norm = min(float(infl_val) / thresholds["inflation_crisis_threshold"], 3.0)
            scores["inflation_risk"] = self._sigmoid(infl_norm - 1.0, 0.0, 4.0) * 100
        else:
            scores["inflation_risk"] = 50.0

        # Unemployment score
        unemp_val = row.get("unemployment", np.nan)
        if pd.notna(unemp_val):
            scores["unemployment_risk"] = min(float(unemp_val) / 15.0, 1.0) * 100
        else:
            scores["unemployment_risk"] = 50.0

        # Current account score (larger deficit = higher risk)
        ca_val = row.get("current_account_balance", np.nan)
        if pd.notna(ca_val):
            ca_norm = abs(min(float(ca_val) / thresholds["current_account_deficit_max"], 2.0))
            scores["external_risk"] = self._sigmoid(ca_norm - 0.5, 0.0, 3.0) * 100
        else:
            scores["external_risk"] = 50.0

        # GDP growth score (lower/negative growth = higher risk)
        gdp_val = row.get("gdp_growth", np.nan)
        if pd.notna(gdp_val):
            scores["growth_risk"] = self._sigmoid(-float(gdp_val), 0.0, 2.0) * 100
        else:
            scores["growth_risk"] = 50.0

        # Weighted composite
        overall = sum(
            scores.get(f"{k}_risk", 50.0) * w
            for k, w in SOVEREIGN_RISK_WEIGHTS.items()
        )
        scores["overall_score"] = round(overall, 2)
        scores["data_quality"] = sum(1 for v in scores.values() if v != 50.0) / 5.0
        scores["latest_year"] = float(latest_year)

        return scores

    # ------------------------------------------------------------------
    # Currency crisis early warning
    # ------------------------------------------------------------------

    async def detect_currency_crisis_signals(
        self, country_code: str
    ) -> List[Dict[str, Any]]:
        """Detect early warning signals for a currency / balance-of-payments crisis.

        Parameters
        ----------
        country_code : str
            ISO-3 country code.

        Returns
        -------
        List[Dict[str, Any]]
            Each dict contains: ``signal``, ``severity`` (low/medium/high/critical),
            ``value``, ``threshold``, ``description``.
        """
        iso3 = self._normalise_country_code(country_code)
        signals: List[Dict[str, Any]] = []

        weo_df = await self.fetch_weo_data(
            countries=[iso3],
            indicators=list(WEO_INDICATORS.keys()),
            start_year=2020,
            end_year=2026,
        )
        if weo_df.empty:
            return signals

        pivot = weo_df.pivot_table(
            index="year", columns="indicator", values="value", aggfunc="mean"
        )
        if pivot.empty:
            return signals

        latest_year = pivot.index.max()
        row = pivot.loc[latest_year]

        # Signal 1: Excessive government debt
        debt = row.get("govt_debt_pct_gdp", np.nan)
        if pd.notna(debt) and float(debt) > CRISIS_THRESHOLDS["debt_crisis"]:
            signals.append({
                "signal": "debt_crisis_risk",
                "severity": "critical" if float(debt) > 120 else "high",
                "value": round(float(debt), 2),
                "threshold": CRISIS_THRESHOLDS["debt_crisis"],
                "description": (
                    f"Government debt at {float(debt):.1f}% of GDP exceeds "
                    f"{CRISIS_THRESHOLDS['debt_crisis']}% threshold"
                ),
            })

        # Signal 2: High inflation
        infl = row.get("inflation", np.nan)
        if pd.notna(infl) and float(infl) > CRISIS_THRESHOLDS["high_inflation"]:
            severity = (
                "critical" if float(infl) > CRISIS_THRESHOLDS["hyperinflation"]
                else "high"
            )
            signals.append({
                "signal": "inflation_crisis",
                "severity": severity,
                "value": round(float(infl), 2),
                "threshold": CRISIS_THRESHOLDS["high_inflation"],
                "description": f"Inflation at {float(infl):.1f}% — elevated currency depreciation risk",
            })

        # Signal 3: Twin deficit (negative current account + fiscal deficit)
        ca = row.get("current_account_balance", np.nan)
        fiscal = row.get("fiscal_balance", np.nan)
        if pd.notna(ca) and float(ca) < CRISIS_THRESHOLDS["twin_deficit"]:
            signals.append({
                "signal": "external_vulnerability",
                "severity": "high" if float(ca) < -8.0 else "medium",
                "value": round(float(ca), 2),
                "threshold": CRISIS_THRESHOLDS["twin_deficit"],
                "description": f"Current account deficit at {float(ca):.1f}% of GDP — reserves pressure",
            })

        # Signal 4: Recession
        gdp_g = row.get("gdp_growth", np.nan)
        if pd.notna(gdp_g) and float(gdp_g) < CRISIS_THRESHOLDS["recession"]:
            signals.append({
                "signal": "recession_risk",
                "severity": "critical" if float(gdp_g) < CRISIS_THRESHOLDS["severe_recession"] else "high",
                "value": round(float(gdp_g), 2),
                "threshold": CRISIS_THRESHOLDS["recession"],
                "description": f"Real GDP growth at {float(gdp_g):.1f}% — contraction risk",
            })

        # Signal 5: Stagflation (high inflation + low growth)
        if (
            pd.notna(infl) and float(infl) > 5.0
            and pd.notna(gdp_g) and float(gdp_g) < 1.5
        ):
            signals.append({
                "signal": "stagflation_risk",
                "severity": "high",
                "value": {"inflation": round(float(infl), 2), "gdp_growth": round(float(gdp_g), 2)},
                "threshold": {"inflation": 5.0, "gdp_growth": 1.5},
                "description": "Stagflation — high inflation with stagnating growth",
            })

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        signals.sort(key=lambda s: severity_order.get(s["severity"], 99))
        return signals

    # ------------------------------------------------------------------
    # Cross-border contagion
    # ------------------------------------------------------------------

    async def analyze_cross_border_contagion(
        self, country_pairs: List[Tuple[str, str]]
    ) -> pd.DataFrame:
        """Compute pairwise contagion probability between country pairs.

        Contagion is modelled as a function of bilateral trade intensity,
        financial exposure correlation, and macro similarity.

        Parameters
        ----------
        country_pairs : List[Tuple[str, str]]
            Pairs of ISO-3 country codes.

        Returns
        -------
        pd.DataFrame
            Columns: ``country_a``, ``country_b``, ``contagion_probability``,
            ``trade_channel``, ``financial_channel``, ``macro_similarity``.
        """
        unique_countries = list(set(
            self._normalise_country_code(c)
            for pair in country_pairs for c in pair
        ))

        weo_df = await self.fetch_weo_data(
            countries=unique_countries,
            indicators=["NGDP_RPCH", "PCPIPCH", "GGXWDG_NGDP", "LUR", "BCA"],
            start_year=2022,
            end_year=2026,
        )

        # Build country profiles
        profiles: Dict[str, Dict[str, float]] = {}
        if not weo_df.empty:
            for country in unique_countries:
                subset = weo_df[weo_df["country"] == country]
                if subset.empty:
                    continue
                pivot = subset.pivot_table(
                    index="year", columns="indicator", values="value"
                )
                if not pivot.empty:
                    latest = pivot.loc[pivot.index.max()]
                    profiles[country] = {
                        k: float(v) if pd.notna(v) else 0.0
                        for k, v in latest.items()
                    }

        results: List[Dict[str, Any]] = []
        for a_raw, b_raw in country_pairs:
            a = self._normalise_country_code(a_raw)
            b = self._normalise_country_code(b_raw)
            pa = profiles.get(a, {})
            pb = profiles.get(b, {})

            # Macro similarity (inverse distance in macro space)
            keys = ["gdp_growth", "inflation", "govt_debt_pct_gdp"]
            vec_a = np.array([pa.get(k, 0.0) for k in keys])
            vec_b = np.array([pb.get(k, 0.0) for k in keys])
            denom = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
            if denom > 0:
                cos_sim = float(np.dot(vec_a, vec_b) / denom)
                macro_sim = (cos_sim + 1) / 2  # normalise to [0, 1]
            else:
                macro_sim = 0.5

            # Trade channel (proxy: inverse GDP size difference)
            gdp_a = abs(pa.get("gdp_growth", 1.0))
            gdp_b = abs(pb.get("gdp_growth", 1.0))
            trade_ch = 1.0 / (1.0 + abs(gdp_a - gdp_b))

            # Financial channel (proxy: debt level correlation)
            debt_a = pa.get("govt_debt_pct_gdp", 50.0)
            debt_b = pb.get("govt_debt_pct_gdp", 50.0)
            fin_ch = 1.0 - abs(debt_a - debt_b) / max(debt_a + debt_b, 1.0)

            # Composite contagion probability (weighted ensemble)
            contagion = 0.35 * macro_sim + 0.35 * trade_ch + 0.30 * fin_ch
            contagion = min(max(contagion, 0.0), 1.0)

            results.append({
                "country_a": a,
                "country_b": b,
                "contagion_probability": round(contagion, 4),
                "trade_channel": round(trade_ch, 4),
                "financial_channel": round(fin_ch, 4),
                "macro_similarity": round(macro_sim, 4),
            })

        return pd.DataFrame(results)

    # ------------------------------------------------------------------
    # Global financial stability
    # ------------------------------------------------------------------

    async def fetch_global_financial_stability(self) -> Dict[str, Any]:
        """Fetch aggregate global financial stability indicators.

        Returns
        -------
        Dict[str, Any]
            Global aggregates: GDP-weighted averages, reserve currency
            shares, and systemic risk flags.
        """
        major_economies = [
            "USA", "CHN", "DEU", "JPN", "GBR", "IND", "FRA", "ITA",
            "BRA", "CAN", "KOR", "RUS", "MEX", "ESP", "AUS", "TUR",
        ]

        weo_df = await self.fetch_weo_data(
            countries=major_economies,
            indicators=["NGDP_RPCH", "PCPIPCH", "GGXWDG_NGDP", "LUR"],
            start_year=2023,
            end_year=2026,
        )

        stability: Dict[str, Any] = {"data_sources": ["WEO"], "timestamp": pd.Timestamp.now().isoformat()}

        if not weo_df.empty:
            latest = weo_df.groupby("indicator")["value"].mean()
            stability["global_avg_gdp_growth"] = round(latest.get("gdp_growth", np.nan), 2) if pd.notna(latest.get("gdp_growth")) else None
            stability["global_avg_inflation"] = round(latest.get("inflation", np.nan), 2) if pd.notna(latest.get("inflation")) else None
            stability["global_avg_unemployment"] = round(latest.get("unemployment", np.nan), 2) if pd.notna(latest.get("unemployment")) else None
            stability["global_avg_govt_debt"] = round(latest.get("govt_debt_pct_gdp", np.nan), 2) if pd.notna(latest.get("govt_debt_pct_gdp")) else None

        # COFER currency shares
        cofer_df = await self.fetch_cofer_data()
        if not cofer_df.empty:
            latest_cofer = cofer_df.groupby("currency")["share_pct"].last().to_dict()
            stability["reserve_currency_shares"] = {
                k: round(v, 2) for k, v in latest_cofer.items()
            }
            stability["data_sources"].append("COFER")

            # Dedollarisation risk signal
            usd_share = latest_cofer.get("USD", 59.0)
            stability["dedollarisation_risk"] = (
                "elevated" if usd_share < 55.0 else "moderate" if usd_share < 59.0 else "low"
            )

        # Count crisis signals across major economies
        crisis_count = 0
        for cc in major_economies[:5]:  # sample top 5 for speed
            signals = await self.detect_currency_crisis_signals(cc)
            crisis_count += sum(1 for s in signals if s["severity"] in ("critical", "high"))
        stability["active_crisis_signals"] = crisis_count
        stability["systemic_risk_level"] = (
            "high" if crisis_count >= 5 else "moderate" if crisis_count >= 2 else "low"
        )

        return stability

    # ------------------------------------------------------------------
    # Macro risk dashboard
    # ------------------------------------------------------------------

    async def get_macro_risk_dashboard(self) -> Dict[str, Any]:
        """Build a comprehensive macro risk dashboard.

        Returns
        -------
        Dict[str, Any]
            Multi-panel dashboard with sovereign scores, crisis signals,
            contagion matrix, and global stability snapshot.
        """
        dashboard: Dict[str, Any] = {
            "generated_at": pd.Timestamp.now().isoformat(),
            "module": "IMFIntelligence",
            "panels": {},
        }

        # Panel 1: Sovereign risk heatmap (G20)
        g20 = [
            "USA", "CHN", "DEU", "JPN", "GBR", "IND", "FRA", "ITA",
            "BRA", "CAN", "KOR", "RUS", "MEX", "AUS", "TUR", "SAU",
            "ARG", "ZAF", "IDN", "NLD",
        ]
        sovereign_scores: Dict[str, Dict[str, float]] = {}
        for cc in g20:
            try:
                score = await self.compute_sovereign_risk_score(cc)
                sovereign_scores[cc] = score
            except Exception as exc:
                logger.warning("Sovereign score failed for %s: %s", cc, exc)
                sovereign_scores[cc] = {"overall_score": 50.0, "error": str(exc)}
        dashboard["panels"]["sovereign_risk_heatmap"] = sovereign_scores

        # Panel 2: Global stability snapshot
        dashboard["panels"]["global_stability"] = await self.fetch_global_financial_stability()

        # Panel 3: Reserve currency trends
        cofer = await self.fetch_cofer_data()
        if not cofer.empty:
            pivot = cofer.pivot(index="year", columns="currency", values="share_pct")
            dashboard["panels"]["reserve_currency_trends"] = pivot.to_dict()

        # Panel 4: Top contagion corridors
        pairs = [
            ("USA", "CHN"), ("DEU", "ITA"), ("JPN", "KOR"), ("GBR", "USA"),
            ("BRA", "USA"), ("MEX", "USA"), ("TUR", "DEU"), ("IND", "USA"),
        ]
        contagion_df = await self.analyze_cross_border_contagion(pairs)
        if not contagion_df.empty:
            dashboard["panels"]["contagion_corridors"] = contagion_df.to_dict("records")

        return dashboard
