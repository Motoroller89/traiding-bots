import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame
from typing import Optional, Union

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter, informative,
                                IStrategy, IntParameter)


from pandas import DataFrame
import math
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.data.dataprovider import DataProvider


class DaniilStrategyLong(IStrategy):
    can_short: bool = True

    minimal_roi = {}
    timeframe = '30m'
    stoploss = -20


    def informative_pairs(self):
        return [
                ("BTC/USDT", "1d"),
                ]
    
    @property
    def plot_config(self):
        main_plot_config = {
            'supertrend': {
                'color': 'green',  #
                'style': 'line',   
                'title': 'SuperTrend'  
            }
        }

        
        subplots_config = {
        }

        return {'main_plot': main_plot_config, 'subplots': subplots_config}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:       
        additional_data = self.dp.get_pair_dataframe("BTC/USDT", "1d")
        
        merged_data = pd.merge(dataframe, additional_data[['date', 'low', 'high', 'close']], how='left', left_on='date', right_on='date', suffixes=("", "_1d"))

        merged_data['low_1d'].ffill(inplace=True)
        merged_data['high_1d'].ffill(inplace=True)
        merged_data['close_1d'].ffill(inplace=True)

        dataframe['low_1d'] = merged_data['low_1d']
        dataframe['high_1d'] = merged_data['high_1d']
        dataframe['close_1d'] = merged_data['close_1d']


        dataframe['atr_50'] = ta.ATR(dataframe, timeperiod=50)

        dataframe['supertrend'] = self.calculate_supertrend(dataframe)
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
        
        
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        """
        Based on TA indicators, populates the entry signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with entry columns populated
        """

        #dataframe.loc[
        #    (
        #        (qtpylib.crossed_above(dataframe['close_1d'],dataframe['supertrend']))
    #
        #    ),
        #    'enter_long'] = 1

        dataframe.loc[
            (
               (qtpylib.crossed_below(dataframe['close_1d'],dataframe['supertrend']))
            ),
            'enter_short'] = 1
#
        return dataframe
    
  
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        #additional_data = self.dp.get_pair_dataframe("BTC/USDT", "1d")

        #dataframe.loc[
        #    (
        #        (qtpylib.crossed_below(dataframe['close_1d'],dataframe['supertrend'])) 
        #    ),  
        #    'exit_long'] = 1   
        dataframe.loc[
            (
                (qtpylib.crossed_above(dataframe['close_1d'],dataframe['supertrend']))
            ),
            'exit_short'] = 1   
        return dataframe    



 