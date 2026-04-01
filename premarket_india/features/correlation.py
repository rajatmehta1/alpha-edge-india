"""20-day rolling correlation matrix with anomaly detection."""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger

from features.models import CorrelationMatrix, CorrelationAnomaly


_ASSETS = ["Nifty", "BankNifty", "Brent", "USD/INR", "VIX", "DowJ", "Gold"]

# Column mapping from macro_history dicts to our asset names
_COLUMN_MAP = {
    "nifty": "Nifty",
    "banknifty": "BankNifty",
    "brent": "Brent",
    "usdinr": "USD/INR",
    "vix": "VIX",
    "dow": "DowJ",
    "gold": "Gold",
}

# Known historical mean correlations (heuristic baselines)
_HISTORICAL_MEANS = {
    ("Nifty", "BankNifty"): 0.92,
    ("Nifty", "DowJ"): 0.55,
    ("Nifty", "Brent"): -0.15,
    ("Nifty", "USD/INR"): -0.45,
    ("Nifty", "VIX"): -0.75,
    ("Nifty", "Gold"): 0.10,
    ("BankNifty", "DowJ"): 0.50,
    ("Brent", "USD/INR"): 0.30,
}


def compute_correlation_matrix(
    macro_history: list[dict],
    rolling_window: int = 20,
) -> CorrelationMatrix:
    """Build 20-day rolling correlation matrix and detect anomalies.

    Parameters
    ----------
    macro_history : list[dict]
        Daily macro data points, each dict should have keys matching _COLUMN_MAP.
    rolling_window : int
        Window for rolling correlation (default 20 days).
    """
    logger.info("Computing correlation matrix")

    if not macro_history or len(macro_history) < rolling_window:
        logger.warning(f"Insufficient macro history ({len(macro_history)} rows) for {rolling_window}-day correlation")
        return CorrelationMatrix(
            assets=_ASSETS,
            matrix=[[1.0 if i == j else 0.0 for j in range(len(_ASSETS))] for i in range(len(_ASSETS))],
        )

    # Build DataFrame
    df = pd.DataFrame(macro_history)

    # Rename columns to standardized names
    rename_map = {}
    for raw_col, asset_name in _COLUMN_MAP.items():
        if raw_col in df.columns:
            rename_map[raw_col] = asset_name
    df = df.rename(columns=rename_map)

    # Keep only assets that exist in data
    available = [a for a in _ASSETS if a in df.columns]
    if len(available) < 2:
        logger.warning("Fewer than 2 assets available for correlation")
        return CorrelationMatrix(assets=_ASSETS, matrix=[[1.0 if i == j else 0.0 for j in range(len(_ASSETS))] for i in range(len(_ASSETS))])

    # Use returns for correlation (more stationary than levels)
    returns = df[available].pct_change().dropna()
    if len(returns) < rolling_window:
        logger.warning("Not enough return data for rolling correlation")
        corr = returns.corr()
    else:
        # Use last `rolling_window` days
        tail = returns.tail(rolling_window)
        corr = tail.corr()

    # Build full matrix aligned to _ASSETS order
    matrix: list[list[float]] = []
    for i, a1 in enumerate(_ASSETS):
        row: list[float] = []
        for j, a2 in enumerate(_ASSETS):
            if a1 == a2:
                row.append(1.0)
            elif a1 in corr.columns and a2 in corr.columns:
                val = corr.loc[a1, a2]
                row.append(round(float(val), 3) if not np.isnan(val) else 0.0)
            else:
                row.append(0.0)
        matrix.append(row)

    # Detect anomalies
    anomalies: list[CorrelationAnomaly] = []

    # Compute long-term rolling correlations for z-score
    if len(returns) >= 60:
        long_corrs: dict[tuple[str, str], list[float]] = {}
        for window_end in range(rolling_window, len(returns) + 1):
            window = returns.iloc[window_end - rolling_window:window_end]
            wc = window.corr()
            for a1 in available:
                for a2 in available:
                    if a1 >= a2:
                        continue
                    key = (a1, a2)
                    val = wc.loc[a1, a2] if a1 in wc.columns and a2 in wc.columns else np.nan
                    if not np.isnan(val):
                        long_corrs.setdefault(key, []).append(val)

        for (a1, a2), vals in long_corrs.items():
            if len(vals) < 10:
                continue
            series = np.array(vals)
            mean_corr = float(np.mean(series))
            std_corr = float(np.std(series))
            current_corr = series[-1]

            if std_corr > 0:
                z = (current_corr - mean_corr) / std_corr
                if abs(z) > 2.0:
                    direction = "strengthening" if z > 0 else "weakening"
                    hist_mean = _HISTORICAL_MEANS.get((a1, a2), mean_corr)
                    anomalies.append(CorrelationAnomaly(
                        asset_pair=f"{a1}/{a2}",
                        current_corr=round(current_corr, 3),
                        historical_mean=round(hist_mean, 3),
                        z_score=round(z, 2),
                        direction=direction,
                        interpretation=f"{a1}/{a2} correlation is {direction} (z={z:.1f}), deviating from norm",
                    ))

    anomalies.sort(key=lambda a: abs(a.z_score), reverse=True)

    return CorrelationMatrix(
        assets=_ASSETS,
        matrix=matrix,
        anomalies=anomalies[:5],
    )
