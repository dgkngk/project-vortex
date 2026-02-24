from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd

from backend.scitus.BaseStrategy import BaseStrategy
from backend.scitus.backtest.BaseBacktester import BaseBacktester
from backend.scitus.backtest.BacktestResult import BacktestResult
from backend.scitus.backtest.MetricsCalculator import MetricsCalculator

@dataclass
class TrainTestSplit:
    """Represents a single walk-forward train/test split."""
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    train_data: pd.DataFrame
    test_data: pd.DataFrame

@dataclass
class MonteCarloResult:
    """Stores the result of a Monte Carlo simulation on trade outcomes."""
    confidence_intervals: Dict[str, Tuple[float, float]]
    means: Dict[str, float]

@dataclass
class WalkForwardResult:
    """Aggregated results across all walk-forward out-of-sample periods."""
    splits_results: List[Dict[str, Any]]
    aggregate_metrics: Dict[str, float]
    oos_equity_curve: pd.Series

class WalkForwardValidator:
    """
    Implements walk-forward validation for trading strategies.
    Segments data into sliding train/test windows, allowing continuous
    out-of-sample performance evaluation while retaining an untouched
    out-of-sample reserve for final go/no-go testing.
    """

    def __init__(self, oos_reserve_pct: float = 0.2):
        """
        Args:
            oos_reserve_pct: Fraction of data to hold out as OOS reserve (default 0.2 = 20%).
                             This data is never used during walk-forward splits.
        """
        if not 0.0 <= oos_reserve_pct < 1.0:
            raise ValueError(f"oos_reserve_pct must be in [0.0, 1.0), got {oos_reserve_pct}")
        self.oos_reserve_pct = oos_reserve_pct

    def generate_splits(
        self,
        data: pd.DataFrame,
        train_window: int,
        test_window: int,
        step: int
    ) -> List[TrainTestSplit]:
        """
        Generate walk-forward train/test splits.
        Holds out the most recent 20% of data as the OOS Reserve Rule.
        """
        splits = []
        n_bars = len(data)

        if n_bars == 0:
            return splits

        # OOS Reserve Rule — hold out recent data, untouched by optimization
        reserve_idx = int(n_bars * (1.0 - self.oos_reserve_pct))
        wf_data = data.iloc[:reserve_idx]

        min_required = train_window + test_window
        if len(wf_data) < min_required:
            raise ValueError(
                f"After reserving {self.oos_reserve_pct:.0%} OOS data, only {len(wf_data)} bars remain. "
                f"Need at least {min_required} (train_window={train_window} + test_window={test_window})."
            )

        start_idx = 0
        while start_idx + train_window + test_window <= len(wf_data):
            train_end_idx = start_idx + train_window
            test_start_idx = train_end_idx
            test_end_idx = test_start_idx + test_window

            train_data = wf_data.iloc[start_idx:train_end_idx]
            test_data = wf_data.iloc[test_start_idx:test_end_idx]

            splits.append(
                TrainTestSplit(
                    train_start=train_data.index[0],
                    train_end=train_data.index[-1],
                    test_start=test_data.index[0],
                    test_end=test_data.index[-1],
                    train_data=train_data,
                    test_data=test_data
                )
            )
            start_idx += step

        return splits

    def validate(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        backtester: BaseBacktester,
        train_window: int,
        test_window: int,
        step: int
    ) -> WalkForwardResult:
        """
        Run walk-forward validation and aggregate Out-Of-Sample metrics.

        Training responsibility: This method does NOT train the strategy
        on each split's train_data. The caller must either:
          1. Pass a strategy that self-trains inside generate_signal(), or
          2. Pre-train the strategy externally and use this only for OOS evaluation.

        Args:
            strategy: An instance of BaseStrategy that will generate signals.
            data: Total available historical data OHLCV.
            backtester: An instantiated backtester (e.g., VectorizedBacktester).
            train_window: Number of bars for training buffer.
            test_window: Number of bars to predict/backtest forward.
            step: Slide size for window forward step.
        """
        splits = self.generate_splits(data, train_window, test_window, step)

        split_results = []
        oos_returns_list = []
        oos_positions_list = []
        oos_trades_list = []

        for split in splits:
            # 1. Strategy Evaluation on Test Box 
            # (Assuming the strategy internal state was optimized on split.train_data)
            signals_df = strategy.generate_signal(split.test_data)
            
            # Allow strategy to either return Series of signals or DataFrame with 'signal' column
            if isinstance(signals_df, pd.DataFrame) and 'signal' in signals_df.columns:
                signals = signals_df['signal']
            else:
                signals = signals_df  # Treat as Series

            # 2. Backtest on Out-of-Sample segment
            result = backtester.run(split.test_data, signals=signals)

            split_results.append({
                "train_start": split.train_start,
                "train_end": split.train_end,
                "test_start": split.test_start,
                "test_end": split.test_end,
                "result": result
            })

            # 3. Accumulate Time Series and Trades
            oos_returns_list.append(result.returns)
            oos_positions_list.append(result.positions)
            
            if isinstance(result.trades, pd.DataFrame) and not result.trades.empty:
                oos_trades_list.append(result.trades)

        # 4. Aggregate OOS Metrics
        if oos_returns_list:
            stitched_returns = pd.concat(oos_returns_list).replace([np.inf, -np.inf], np.nan).fillna(0)
            stitched_positions = pd.concat(oos_positions_list)
            
            # Derive continuous Equity curve from stitched consecutive returns
            initial_cap = getattr(backtester, 'initial_capital', 10000.0)
            stitched_equity = (1 + stitched_returns).cumprod() * initial_cap

            # Stitch all trades for win rate and profit factor estimations
            all_trades = pd.concat(oos_trades_list, ignore_index=True) if oos_trades_list else pd.DataFrame()

            aggregate_metrics = MetricsCalculator.calculate(
                returns=stitched_returns,
                equity=stitched_equity,
                positions=stitched_positions,
                trades_df=all_trades
            )
        else:
            stitched_equity = pd.Series(dtype=float)
            aggregate_metrics = {}

        return WalkForwardResult(
            splits_results=split_results,
            aggregate_metrics=aggregate_metrics,
            oos_equity_curve=stitched_equity
        )

    def monte_carlo(
        self,
        trades: pd.DataFrame,
        n_simulations: int = 1000
    ) -> MonteCarloResult:
        """
        Shuffle trade order randomly to simulate sequence-of-returns robustness.
        Uses vectorized numpy operations for performance.
        Returns confidence intervals for final total simulated PnL.
        """
        if trades is None or trades.empty or "pnl" not in trades.columns:
            return MonteCarloResult(confidence_intervals={}, means={})

        pnls = trades["pnl"].dropna().values
        if len(pnls) == 0:
            return MonteCarloResult(confidence_intervals={}, means={})

        # Vectorized: tile PnLs into a matrix, shuffle each row, then sum
        rng = np.random.default_rng()
        matrix = np.tile(pnls, (n_simulations, 1))
        rng.permuted(matrix, axis=1, out=matrix)
        simulated_totals = matrix.sum(axis=1)

        return MonteCarloResult(
            confidence_intervals={
                "total_return_95_ci": (
                    float(np.percentile(simulated_totals, 2.5)),
                    float(np.percentile(simulated_totals, 97.5))
                )
            },
            means={
                "total_return_mean": float(np.mean(simulated_totals))
            }
        )
