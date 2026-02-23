import pandas as pd


class DataQueue:
    """
    Bar-by-bar data feed for event-driven backtesting.
    Yields each row of a DataFrame as a named pd.Series.
    """

    def __init__(self, data: pd.DataFrame):
        self._data = data
        self._validate(data)

    def _validate(self, data: pd.DataFrame):
        required = {"close", "volume"}
        missing = required - set(data.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    def __iter__(self):
        for index in self._data.index:
            yield self._data.loc[index]

    def __len__(self):
        return len(self._data)
