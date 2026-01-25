import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from backend.scitus.strategies.VotingStrategy import VotingStrategy
from backend.scitus.strategies.CompositeStrategy import CompositeStrategy
from backend.core.enums.SignalTypes import SignalTypes
from backend.core.enums.StrategyConfigs import StrategyConfigs

@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
    return pd.DataFrame({
        'close': [100, 102, 104, 103, 105]
    }, index=dates)

@pytest.fixture
def mock_strategy_factory():
    # Patch the class where it is imported/used. 
    # Since VotingStrategy imports it inside the method, we patch the module path where StrategyFactory lives
    # or patch 'backend.scitus.StrategyFactory.StrategyFactory' which is what is imported.
    with patch('backend.scitus.StrategyFactory.StrategyFactory') as MockFactory:
        yield MockFactory

def test_voting_strategy_consensus(sample_data, mock_strategy_factory):
    # Setup mocks
    strat1 = MagicMock()
    # 3 BUY, 2 SELL
    strat1.generate_signal.return_value = pd.DataFrame({'signal': [1, 1, 1, -1, -1]}, index=sample_data.index)
    
    strat2 = MagicMock()
    # 1 BUY, 4 SELL
    strat2.generate_signal.return_value = pd.DataFrame({'signal': [1, -1, -1, -1, -1]}, index=sample_data.index)
    
    mock_strategy_factory.create_strategy.side_effect = [strat1, strat2]
    
    # We use "MACD" as the type because VotingStrategy does StrategyConfigs[type]
    # "MACD" is a valid member of StrategyConfigs.
    config = {
        "strategies": [{"type": "MACD"}, {"type": "MACD"}], 
        "min_votes": 2
    }
    
    vs = VotingStrategy(config)
    result = vs.generate_signal(sample_data)
    
    # Logic Trace:
    # Row 0: 1, 1 -> 2 votes for BUY -> BUY (1)
    # Row 1: 1, -1 -> 1 vote BUY, 1 vote SELL -> HOLD (0) (min_votes=2)
    # Row 2: 1, -1 -> 1 vote BUY, 1 vote SELL -> HOLD (0)
    # Row 3: -1, -1 -> 2 votes SELL -> SELL (-1)
    # Row 4: -1, -1 -> 2 votes SELL -> SELL (-1)
    
    expected = [SignalTypes.BUY.value, SignalTypes.HOLD.value, SignalTypes.HOLD.value, SignalTypes.SELL.value, SignalTypes.SELL.value]
    np.testing.assert_array_equal(result['signal'].values, expected)

def test_composite_strategy_filtering(sample_data, mock_strategy_factory):
    # Primary: BUY, BUY, SELL, SELL, HOLD
    primary = MagicMock()
    primary.generate_signal.return_value = pd.DataFrame({'signal': [1, 1, -1, -1, 0]}, index=sample_data.index)
    
    # Filter: BUY, SELL, BUY, SELL, BUY
    filt = MagicMock()
    filt.generate_signal.return_value = pd.DataFrame({'signal': [1, -1, 1, -1, 1]}, index=sample_data.index)
    
    mock_strategy_factory.create_strategy.side_effect = [primary, filt]
    
    config = {
        "primary_strategy": {"type": "MACD"},
        "filter_strategies": [{"type": "MACD"}]
    }
    
    cs = CompositeStrategy(config)
    result = cs.generate_signal(sample_data)
    
    # Logic Trace:
    # Row 0: Pri=1 (BUY). Filt=1 (BUY). Match? Yes. -> BUY
    # Row 1: Pri=1 (BUY). Filt=-1 (SELL). Match? No. -> HOLD
    # Row 2: Pri=-1 (SELL). Filt=1 (BUY). Match? No. -> HOLD
    # Row 3: Pri=-1 (SELL). Filt=-1 (SELL). Match? Yes. -> SELL
    # Row 4: Pri=0 (HOLD). -> HOLD
    
    expected = [SignalTypes.BUY.value, SignalTypes.HOLD.value, SignalTypes.HOLD.value, SignalTypes.SELL.value, SignalTypes.HOLD.value]
    np.testing.assert_array_equal(result['signal'].values, expected)
