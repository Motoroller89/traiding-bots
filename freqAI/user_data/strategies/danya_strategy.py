import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame
from typing import Optional, Union, Dict

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter, informative,
                                IStrategy, IntParameter)

import logging

from pandas import DataFrame
import math
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.data.dataprovider import DataProvider

logger = logging.getLogger(__name__)
class DaniilAiStrategy(IStrategy):
    can_short: bool = True

    minimal_roi = {}
    timeframe = '30m'
    stoploss = -20

    startup_candle_count: int = 100

    def log(self, msg, *args, **kwargs):
        logger.info(msg, *args, **kwargs)

    def informative_pairs(self):
        return [
                ("BTC/USDT", "1d"),
                ]
    
    


    def feature_engineering_expand_all(self, dataframe: DataFrame, period, metadata: Dict, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        This function will automatically expand the defined features on the config defined
        `indicator_periods_candles`, `include_timeframes`, `include_shifted_candles`, and
        `include_corr_pairs`. In other words, a single feature defined in this function
        will automatically expand to a total of
        `indicator_periods_candles` * `include_timeframes` * `include_shifted_candles` *
        `include_corr_pairs` numbers of features added to the model.

        All features must be prepended with `%` to be recognized by FreqAI internals.

        :param df: strategy dataframe which will receive the features
        :param period: period of the indicator - usage example:
        dataframe["%-ema-period"] = ta.EMA(dataframe, timeperiod=period)
        """

        if metadata["tf"] == "1d":
            dataframe["%-raw_low"] = dataframe["low"]
            dataframe["%-raw_high"] = dataframe["high"]
            dataframe["%-raw_close"] = dataframe["close"]
        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        This function will automatically expand the defined features on the config defined
        `include_timeframes`, `include_shifted_candles`, and `include_corr_pairs`.
        In other words, a single feature defined in this function
        will automatically expand to a total of
        `include_timeframes` * `include_shifted_candles` * `include_corr_pairs`
        numbers of features added to the model.

        Features defined here will *not* be automatically duplicated on user defined
        `indicator_periods_candles`

        All features must be prepended with `%` to be recognized by FreqAI internals.

        :param df: strategy dataframe which will receive the features
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-ema-200"] = ta.EMA(dataframe, timeperiod=200)
        """      
        dataframe["%-atr-50"] = ta.ATR(dataframe, timeperiod=50) 
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        This optional function will be called once with the dataframe of the base timeframe.
        This is the final function to be called, which means that the dataframe entering this
        function will contain all the features and columns created by all other
        freqai_feature_engineering_* functions.

        This function is a good place to do custom exotic feature extractions (e.g. tsfresh).
        This function is a good place for any feature that should not be auto-expanded upon
        (e.g. day of the week).

        All features must be prepended with `%` to be recognized by FreqAI internals.

        :param df: strategy dataframe which will receive the features
        usage example: dataframe["%-day_of_week"] = (dataframe["date"].dt.dayofweek + 1) / 7
        """
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame,  metadata: Dict, **kwargs) -> DataFrame:

        """
        *Only functional with FreqAI enabled strategies*
        Required function to set the targets for the model.
        All targets must be prepended with `&` to be recognized by the FreqAI internals.

        :param df: strategy dataframe which will receive the targets
        usage example: dataframe["&-target"] = dataframe["close"].shift(-1) / dataframe["close"]
        """
        pd.set_option('display.max_columns', None)
        self.log(f"ENTER .set_freqai_targets() {metadata} {dataframe.describe()}")
        self.freqai.class_names = ["down", "up", "same"]

        

        additional_data = self.dp.get_pair_dataframe("BTC/USDT:USDT", "1d")

        
        merged_data = pd.merge(dataframe, additional_data[['date', 'low', 'high', 'close']], how='left', left_on='date', right_on='date', suffixes=("", "_1d"))

        merged_data['low_1d'].ffill(inplace=True)
        merged_data['high_1d'].ffill(inplace=True)
        merged_data['close_1d'].ffill(inplace=True)

        dataframe['low_1d'] = merged_data['low_1d']
        dataframe['high_1d'] = merged_data['high_1d']
        dataframe['close_1d'] = merged_data['close_1d']


        dataframe['atr_50'] = ta.ATR(dataframe, timeperiod=50)

        dataframe['supertrend'] = self.calculate_supertrend(dataframe)
        dataframe['&s-up_or_down'] = np.where(qtpylib.crossed_above(dataframe['close_1d'], dataframe['supertrend']), 'up',
                                      np.where(qtpylib.crossed_below(dataframe['close_1d'], dataframe['supertrend']), 'down', 'same'))

        return dataframe    

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.freqai.start(dataframe, metadata, self)

        return dataframe
            
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with entry columns populated
        """

        dataframe.loc[
            (
                (dataframe['volume'] > 0) & 
                (dataframe['do_predict'] == 1) &
                (dataframe['&s-up_or_down'] == 'up')
            ),
            'enter_long'] = 1

        dataframe.loc[
            (
                (dataframe['volume'] > 0) & 
                (dataframe['do_predict'] == 1) &
                (dataframe['&s-up_or_down'] == 'down')
            ),
            'enter_short'] = 1
#
        return dataframe
    
  
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe.loc[
            (
                (dataframe['volume'] > 0) & 
                (dataframe['do_predict'] == 1) &
                (dataframe['&s-up_or_down'] == 'down')
            ),
            'exit_long'] = 1

        dataframe.loc[
            (
                (dataframe['volume'] > 0) & 
                (dataframe['do_predict'] == 1) &
                (dataframe['&s-up_or_down'] == 'up')
            ),
            'exit_short'] = 1  
        return dataframe    
    
    
    def calculate_supertrend(self, dataframe,):
        dataframe['up_lev'] = dataframe['low_1d'] - dataframe['atr_50']
        dataframe['dn_lev'] = dataframe['high_1d'] + dataframe['atr_50']

        dataframe['up_trend'] = 0.0
        dataframe['down_trend'] = 0.0

        for i in range(1, len(dataframe)):
            dataframe.loc[dataframe.index[i], 'up_trend'] = max(dataframe['up_lev'][i], dataframe['up_trend'][i-1]) if dataframe['close_1d'][i-1] > dataframe['up_trend'][i-1] else dataframe['up_lev'][i]
            dataframe.loc[dataframe.index[i], 'down_trend'] = min(dataframe['dn_lev'][i], dataframe['down_trend'][i-1]) if dataframe['close_1d'][i-1] < dataframe['down_trend'][i-1] else dataframe['dn_lev'][i]

        dataframe['trend'] = 0
        for i in range(1, len(dataframe)):
            if  dataframe['close_1d'][i] > dataframe['down_trend'][i-1]:
                dataframe.loc[dataframe.index[i], 'trend'] = 1

            elif dataframe['close_1d'][i] < dataframe['up_trend'][i-1]:
                 dataframe.loc[dataframe.index[i], 'trend'] = -1

            else:
                if dataframe['trend'][i-1] == 0:
                    dataframe.loc[dataframe.index[i], 'trend'] = 1
                else:
                    dataframe.loc[dataframe.index[i], 'trend'] = dataframe['trend'][i-1]

        #dataframe['trend'] = np.where(dataframe['close_1d'] > dataframe['down_trend'].shift(1), 1, np.where(dataframe['close_1d'] < dataframe['up_trend'].shift(1), -1, np.where(dataframe['trend'].shift(1) == 0, 1, dataframe['trend'].shift(1))))

        dataframe['st_line'] = np.where(dataframe['trend'] == 1, dataframe['up_trend'], dataframe['down_trend'])
        return dataframe['st_line']
        


 