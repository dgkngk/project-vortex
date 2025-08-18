from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseExtractor(ABC):
    """
    Abstract base class for all crypto data extractors.
    Ensures a common interface and structure for specialized extractors.
    """

    def __init__(self, api_base_url: str, target_table_name: str, historical_data_target_table_name: str):
        self.api_base_url = api_base_url
        self.target_table_name = target_table_name
        self.historical_data_target_table_name = historical_data_target_table_name

    @abstractmethod
    def get_listed_assets(self) -> List[Dict[str, Any]]:
        """
        Fetch a list of all available assets from the API.
        Returns:
            A list of dictionaries containing asset metadata (id, symbol, name, etc.).
        """
        pass

    @abstractmethod
    def get_historical_data_for_assets(self, asset_ids: List[str], **kwargs) -> Dict[str, Any]:
        """
        Fetch historical price/market data for the given assets.
        Args:
            asset_ids: List of asset identifiers.
            kwargs: Additional parameters for the request (e.g., date ranges).
        Returns:
            Dictionary keyed by asset id, with historical data.
        """
        pass

    @abstractmethod
    def get_market_data_for_assets(self, asset_ids: List[str], **kwargs) -> Dict[str, Any]:
        """
        Fetch detailed market data for the given assets (market cap, volume, etc.).
        Args:
            asset_ids: List of asset identifiers.
            kwargs: Additional request params.
        Returns:
            Dictionary keyed by asset id, with market data.
        """
        pass

    @abstractmethod
    def get_latest_data_for_assets(self, asset_ids: List[str], **kwargs) -> Dict[str, Any]:
        """
        Fetch the latest ticker/price data for the given assets.
        Args:
            asset_ids: List of asset identifiers.
        Returns:
            Dictionary keyed by asset id, with latest prices.
        """
        pass

    @abstractmethod
    def run_extraction(self):
        """
        Main method that coordinates extraction from the API.
        Should internally call other methods as needed and prepare data for transformation/loading.
        """
        pass
