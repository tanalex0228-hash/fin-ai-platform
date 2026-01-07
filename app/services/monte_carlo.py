# app/services/monte_carlo.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Tuple
import numpy as np


@dataclass
class MonteCarloResult:
    params: Dict[str, Any]
    summary: Dict[str, Any]
    drawdown_series: Dict[str, list]   # keys: worst/median/best
    sample_paths: Dict[str, list]      # keys: worst/median/best


def _to_numpy(prices) -> np.ndarray:
    arr = np.asarray(prices, dtype=float)
    if arr.ndim != 1 or arr.size < 30:
        raise ValueError("prices must be 1D and length >= 30")
    if np.any(arr <= 0):
        raise ValueError("prices must be positive")
    return arr


def _log_returns(prices: np.ndarray) -> np.ndarray:
    return np.diff(np.log(prices))


def simulate_gbm_paths(
    prices,
    n_simulations: int = 2000,
    horizon: int = 252,
    seed: int | None = None
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    GBM simulation using log-return mu/sigma estimated from historical prices.
    Returns:
      paths: shape (horizon, n_simulations)
      stats: dict(mu, sigma, s0)
    """
    if n_simulations < 100 or n_simulations > 200000:
        raise ValueError("n_simulations should be between 100 and 200000")
    if horizon < 10 or horizon > 2000:
        raise ValueError("horizon should be between 10 and 2000")

    p = _to_numpy(prices)
    r = _log_returns(p)

    mu = float(np.mean(r))
    sigma = float(np.std(r, ddof=1))
    s0 = float(p[-1])

    rng = np.random.default_rng(seed)

    dt = 1.0
    z = rng.standard_normal(size=(horizon - 1, n_simulations))
    drift = (mu - 0.5 * sigma * sigma) * dt
    diffusion = sigma * np.sqrt(dt) * z

    paths = np.empty((horizon, n_simulations), dtype=float)
    paths[0, :] = s0
    paths[1:, :] = s0 * np.exp(np.cumsum(drift + diffusion, axis=0))

    return paths, {"mu": mu, "sigma": sigma, "s0": s0}


def compute_drawdown_series(paths: np.ndarray) -> np.ndarray:
    """
    drawdown = price / cummax - 1 (<= 0)
    output: shape (horizon, n_simulations)
    """
    peak = np.maximum.accumulate(paths, axis=0)
    dd = (paths / peak) - 1.0
    return dd


def summarize_drawdowns(paths: np.ndarray, dd: np.ndarray) -> Dict[str, Any]:
    """
    Return:
      max_drawdown per path (most negative)
      percentile stats
      select representative paths: worst/median/best by max_drawdown
    """
    max_dd = np.min(dd, axis=0)  # each simulation's worst drawdown (negative)
    # Sorting: worst drawdown is most negative
    order = np.argsort(max_dd)   # ascending => most negative first
    worst_i = int(order[0])
    best_i = int(order[-1])
    median_i = int(order[len(order)//2])

    def pct(x: float) -> float:
        return float(x * 100.0)

    summary = {
        "n_simulations": int(paths.shape[1]),
        "horizon": int(paths.shape[0]),
        "max_drawdown_pct": {
            "worst": pct(max_dd[worst_i]),
            "p01": pct(np.percentile(max_dd, 1)),
            "p05": pct(np.percentile(max_dd, 5)),
            "p10": pct(np.percentile(max_dd, 10)),
            "p50": pct(np.percentile(max_dd, 50)),
            "p90": pct(np.percentile(max_dd, 90)),
            "p95": pct(np.percentile(max_dd, 95)),
            "p99": pct(np.percentile(max_dd, 99)),
            "best": pct(max_dd[best_i]),
            "mean": pct(np.mean(max_dd)),
        }
    }

    drawdown_series = {
        "worst": dd[:, worst_i].tolist(),
        "median": dd[:, median_i].tolist(),
        "best": dd[:, best_i].tolist(),
    }
    sample_paths = {
        "worst": paths[:, worst_i].tolist(),
        "median": paths[:, median_i].tolist(),
        "best": paths[:, best_i].tolist(),
    }

    return {
        "summary": summary,
        "drawdown_series": drawdown_series,
        "sample_paths": sample_paths,
        "indices": {"worst": worst_i, "median": median_i, "best": best_i},
    }


def run_monte_carlo_drawdown(
    prices,
    n_simulations: int = 2000,
    horizon: int = 252,
    seed: int | None = None
) -> MonteCarloResult:
    paths, stats = simulate_gbm_paths(
        prices=prices,
        n_simulations=n_simulations,
        horizon=horizon,
        seed=seed
    )
    dd = compute_drawdown_series(paths)
    pack = summarize_drawdowns(paths, dd)

    return MonteCarloResult(
        params={
            "n_simulations": n_simulations,
            "horizon": horizon,
            "seed": seed,
            **stats
        },
        summary=pack["summary"],
        drawdown_series=pack["drawdown_series"],
        sample_paths=pack["sample_paths"]
    )
