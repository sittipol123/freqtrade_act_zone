"""
sharpeeHyperOptLoss

This module defines the alternative HyperOptLoss class which can be used for
Hyperoptimization.
"""
from datetime import datetime

from pandas import DataFrame, to_datetime
import numpy as np
from freqtrade.optimize.hyperopt import IHyperOptLoss


class SharpeHyperOptLoss(IHyperOptLoss):
    """
    Defines the loss function for hyperopt.

    This implementation uses the Sharpe Ratio calculation.
    """

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int,
                               min_date: datetime, max_date: datetime,
                               *args, **kwargs) -> float:
        """
        Objective function, returns smaller number for more optimal results.

        Uses Sharpe Ratio calculation.
        """
        # adding slippage of 0.1% per trade
        results["profit_percent"] = results["profit_percent"] - 0.001
        results["close_time_h"] = to_datetime(results["close_time"], unit="s")
        results = results.set_index("close_time_h")
        results = results.resample("D").sum()

        total_profit_per_day = results.profit_percent
        days_period = (max_date - min_date).days
        
        average_daily_return = total_profit_per_day.sum() / days_period

        if (np.std(total_profit_per_day ) != 0.):
            sharpe_ratio = (average_daily_return / np.std(total_profit_per_day )) * np.sqrt(365)
        else:
            # Define high (negative) sharpe ratio to be clear that this is NOT optimal.
            sharpe_ratio = -20.

        return -sharpe_ratio
