import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame

from freqtrade.strategy.interface import IStrategy

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class YoyoActionStrategy(IStrategy):
    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
    minimal_roi = {
        "0": 100
    }

    timeframe = '4h'

    # Optional order type mapping
    order_types = {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'limit',
        'stoploss_on_exchange': False
    }
    
    emaFast = 12
    emaSlow = 26
    #emaFast = 14
    #emaSlow = 84

    rsiPeriod = 14
    overBought = 80
    overSold = 30

    #stoploss = -0.20
    # Fast Trail 
    atrFast = 6
    atrFM = 0.5 # fast ATR multiplier

    # Slow Trail 
    atrSlow = 18 # Slow ATR perod
    atrSM = 2 # Slow ATR multiplier

    # Trailing stoploss
    trailing_stop = False

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ohlc4'] = (dataframe['open'] + dataframe['high'] + dataframe['low'] + dataframe['close']) / 4
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.emaFast)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.emaSlow)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsiPeriod)
        dataframe['macd'] = dataframe['ema_fast'] - dataframe['ema_slow']
        dataframe['bullish'] = dataframe['macd'] > 0
        dataframe['bearish'] = dataframe['macd'] < 0

        dataframe['sl1'] = self.atrFM*ta.ATR(dataframe.high, dataframe.low, dataframe.close,timeperiod=self.atrFast)  # Stop Loss
        dataframe['sl2'] = self.atrSM*ta.ATR(dataframe.high, dataframe.low, dataframe.close,timeperiod=self.atrSlow) 
        dataframe.dropna(inplace=True)
        dataframe['atr_stop'] = 0
        dataframe['red'] = False
        dataframe['brown'] = False
        dataframe['yellow'] = False
        dataframe['aqua'] = False
        dataframe['blue'] = False
        dataframe['green'] = False
        dataframe['long'] = False
        dataframe['preBuy'] = False
        dataframe['short'] = False
        dataframe['preSell'] = False
        dataframe['trail2'] = 0.0
        dataframe['over_sole'] = False
        dataframe['over_bought'] = False
        dataframe['bullish_last'] = False

        for index in range(len(dataframe)):
            # Green = bullish and mainSource>fast
            dataframe.green.iloc[index] = dataframe.bullish.iloc[index] and (dataframe.ohlc4.iloc[index] > dataframe.ema_fast.iloc[index])
            # Blue = bearish and mainSource>fast and mainSource>slow
            dataframe.blue.iloc[index] = dataframe.bearish.iloc[index] and dataframe.ohlc4.iloc[index] > dataframe.ema_fast.iloc[index]
            # Aqua = bearish and mainSource>fast and mainSource<slow
            dataframe.aqua.iloc[index] = dataframe.bearish.iloc[index]  and dataframe.ohlc4.iloc[index] > dataframe.ema_fast.iloc[index] and dataframe.ohlc4.iloc[index] < dataframe.ema_slow.iloc[index]
            # Yellow = bullish and mainSource<fast and mainSource>slow
            dataframe.yellow.iloc[index] = dataframe.bullish.iloc[index] and dataframe.ohlc4.iloc[index] < dataframe.ema_slow.iloc[index]
            # Brown = bullish and mainSource<fast and mainSource<slow
            dataframe.brown.iloc[index] = dataframe.bullish.iloc[index] and dataframe.ohlc4.iloc[index] < dataframe.ema_fast.iloc[index] and dataframe.ohlc4.iloc[index] < dataframe.ema_slow.iloc[index]
            # Red = bearish and mainSource<fast
            dataframe.red.iloc[index] = dataframe.bearish.iloc[index] and dataframe.ohlc4.iloc[index] < dataframe.ema_fast.iloc[index]
            # iff(SC>nz(Trail2[1],0)                                    and SC[1]>nz(Trail2[1],0)
            if dataframe.close.iloc[index] > dataframe.trail2.iloc[index - 1] and dataframe.close.iloc[index - 1] > dataframe.trail2.iloc[index - 1]:
                dataframe.trail2.iloc[index] = max(dataframe.trail2.iloc[index - 1], dataframe.close.iloc[index] - dataframe.sl2.iloc[index])
            # iff(SC<nz(Trail2[1],0)                                        and SC[1]<nz(Trail2[1],0)
            elif dataframe.close.iloc[index] < dataframe.trail2.iloc[index - 1] and dataframe.close.iloc[index - 1] < dataframe.trail2.iloc[index - 1]: 
                dataframe.trail2.iloc[index] = min(dataframe.trail2.iloc[index - 1], dataframe.close.iloc[index - 1] +  dataframe.sl2.iloc[index - 1])
            # iff(SC>nz(Trail2[1],0),    
            elif dataframe.close.iloc[index] > dataframe.trail2.iloc[index - 1]:
                dataframe.trail2.iloc[index] = dataframe.close.iloc[index] - dataframe.sl2.iloc[index]
            else:
                dataframe.trail2.iloc[index] = dataframe.close.iloc[index] + dataframe.sl2.iloc[index]
            # it can use rolling
            dataframe.long.iloc[index] = dataframe.bullish.iloc[index] and dataframe.bullish.iloc[index - 1]
            dataframe.preBuy.iloc[index] = dataframe.bullish.iloc[index] and dataframe.bullish.iloc[index - 1]

            # dataframe.preSell.iloc[index] =  dataframe.yellow.iloc[index] and ta.
            dataframe.short.iloc[index] = dataframe.bearish.iloc[index] and dataframe.bearish.iloc[index - 1]
            # dataframe.over_sole.iloc[index] = dataframe.iloc[-self.rsiPeriod:].where(dataframe.rsi.iloc[index] < 30).any() == False
            dataframe.over_sole.iloc[index] = dataframe.iloc[index-self.rsiPeriod: index].where(dataframe['rsi'] <= self.overSold).any().rsi
            dataframe.over_bought.iloc[index] = dataframe.iloc[index-self.rsiPeriod: index].where(dataframe['rsi'] >= self.overBought).any().rsi

        # greenLine = SC>Trail2
        dataframe['greenLine'] = False
        dataframe.loc[
                (
                    (dataframe["close"] > dataframe['trail2'])
                ),
                'greenLine'] = True
        dataframe['greenLine_last'] = dataframe.greenLine.shift(1)

        dataframe['short_last'] = dataframe.short.shift(1)
        dataframe['bullish_last'] = dataframe.bullish.shift(1)
        dataframe['green_last'] = dataframe.green.shift(1)
        dataframe['red_last'] = dataframe.red.shift(1)
        dataframe['hold_state'] = False

        dataframe.dropna(inplace=True)
        dataframe
        # greenLine = SC>Trail2
        dataframe['greenLine'] = False
        dataframe.loc[
                (
                    (dataframe["close"] > dataframe['trail2'])
                ),
                'greenLine'] = True
        dataframe['greenLine_last'] = dataframe.greenLine.shift(1)
        dataframe['short_last'] = dataframe.short.shift(1)
        dataframe['green_last'] = dataframe.green.shift(1)
        dataframe['red_last'] = dataframe.red.shift(1)
        dataframe['hold_state'] = False
        dataframe.dropna(inplace=True)

        # ATR IN-OUT RSI
        # dataframe.loc[(
        #     ((dataframe['green_last'] == False) & (dataframe['green'] == True)) # Green buy
        #     # | ((dataframe['greenLine'] == True) & (dataframe['blue'] == True)) # Over ATR and blue
        #     | ((dataframe['greenLine_last'] == False) & (dataframe['greenLine'] == True) & (dataframe['over_sole'] == True)) # Over ATR and RSI over sole 
        # ), 'signal_buy'] = True

        # dataframe.loc[(
        #     ((dataframe['red_last'] == False) & (dataframe['red'] == True)) # Red Sell
        #     | ((dataframe['greenLine_last'] == True) & (dataframe['greenLine'] == False) & (dataframe['over_bought'] == True)) # Stop lost ATR and RSI over bought            
        # ), 'signal_sell'] = True

        # ATR-BLUE
        # dataframe.loc[(
        #     ((dataframe['green_last'] == False) & (dataframe['green'] == True)) # Green buy
        #     | ((dataframe['greenLine'] == True) & (dataframe['blue'] == True)) # Over ATR and blue
        #     #| ((dataframe['greenLine_last'] == False) & (dataframe['greenLine'] == True)) # Over ATR and RSI over sole 
        # ), 'signal_buy'] = True

        # dataframe.loc[(
        #     ((dataframe['red_last'] == False) & (dataframe['red'] == True)) # Red Sell
        #     # | ((dataframe['greenLine_last'] == True) & (dataframe['greenLine'] == False)& (dataframe['over_bought'] == True)) # Stop lost ATR and RSI over bought            
        # ), 'signal_sell'] = True

        # RSI-BLUE-AQUA
        # dataframe.loc[(
        #     ((dataframe['green_last'] == False) & (dataframe['green'] == True)) # Green buy
        #     | ((dataframe['greenLine'] == True) & ((dataframe['blue'] == True) | (dataframe['aqua'] == True))) # Over ATR and blue AQUA
        # ), 'signal_buy'] = True

        # dataframe.loc[(
        #     ((dataframe['red_last'] == False) & (dataframe['red'] == True)) # Red Sell
        # ), 'signal_sell'] = True

        # RSI ATR-BLUE-AQUA
        # dataframe.loc[(
        #     ((dataframe['green_last'] == False) & (dataframe['green'] == True)) # Green buy
        #     | ((dataframe['greenLine'] == True) & ((dataframe['blue'] == True) | (dataframe['aqua'] == True)) ) # Over ATR and blue AQUA
        #     | (((dataframe['blue'] == True) | (dataframe['aqua'] == True)) & (dataframe['over_sole'] == True)) # RSI and blue AQUA
        # ), 'signal_buy'] = True

        # dataframe.loc[(
        #     ((dataframe['red_last'] == False) & (dataframe['red'] == True)) # Red Sell
        # ), 'signal_sell'] = True

        # RSI over sole Out ATR over bought
        # dataframe.loc[(
        #     ((dataframe['green_last'] == False) & (dataframe['green'] == True)) # Green buy
        #      | ((dataframe['over_sole'] == True) & (dataframe['blue'] == True) & dataframe['rsi'] < 50)
        #     #| ((dataframe['greenLine'] == True) & (dataframe['blue'] == True)) # Over ATR and blue
        #     #| ((dataframe['greenLine_last'] == False) & (dataframe['greenLine'] == True) & (dataframe['over_sole'] == True)) # Over ATR and RSI over sole 
        # ), 'signal_buy'] = True

        # dataframe.loc[(
        #     ((dataframe['red_last'] == False) & (dataframe['red'] == True)) # Red Sell
        #     | ((dataframe['greenLine_last'] == True) & (dataframe['greenLine'] == False) & (dataframe['over_bought'] == True)) # Stop lost ATR and RSI over bought            
        # ), 'signal_sell'] = True

        # RSI over sole Out red
        # dataframe.loc[(
        #     ((dataframe['green_last'] == False) & (dataframe['green'] == True)) # Green buy
        #      | ((dataframe['over_sole'] == True) & (dataframe['blue'] == True) & dataframe['rsi'] < 50)
        #     #| ((dataframe['greenLine'] == True) & (dataframe['blue'] == True)) # Over ATR and blue
        #     #| ((dataframe['greenLine_last'] == False) & (dataframe['greenLine'] == True) & (dataframe['over_sole'] == True)) # Over ATR and RSI over sole 
        # ), 'signal_buy'] = True

        # dataframe.loc[(
        #     ((dataframe['red_last'] == False) & (dataframe['red'] == True)) # Red Sell
        #     #| ((dataframe['greenLine_last'] == True) & (dataframe['greenLine'] == False) & (dataframe['over_bought'] == True)) # Stop lost ATR and RSI over bought            
        # ), 'signal_sell'] = True

        # RSI over sole blue&aqua + ATR blue&aqua Out red
        # dataframe.loc[(
        #     ((dataframe['green_last'] == False) & (dataframe['green'] == True)) # Green buy
        #      | ((dataframe['over_sole'] == True) & ((dataframe['blue'] == True) | (dataframe['aqua'] == True)) & dataframe['rsi'] < 50)
        #      | ((dataframe['greenLine'] == True)  & ((dataframe['blue'] == True) | (dataframe['aqua'] == True))) # Over ATR and blue
        #     #| ((dataframe['greenLine_last'] == False) & (dataframe['greenLine'] == True) & (dataframe['over_sole'] == True)) # Over ATR and RSI over sole 
        # ), 'signal_buy'] = True

        # dataframe.loc[(
        #     ((dataframe['red_last'] == False) & (dataframe['red'] == True)) # Red Sell
        #     #| ((dataframe['greenLine_last'] == True) & (dataframe['greenLine'] == False) & (dataframe['over_bought'] == True)) # Stop lost ATR and RSI over bought            
        # ),  'signal_sell'] = True

        # Green + RSI over sole blue&aqua out Red&ATR over bought 
        # dataframe.loc[(
        #     ((dataframe['green_last'] == True) & (dataframe['green'] == True)) # Green buy
        #      | ((dataframe['over_sole'] == True) & ((dataframe['blue'] == True) | (dataframe['aqua'] == True)) & dataframe['rsi'] < 50)
        #     #| ((dataframe['greenLine_last'] == False) & (dataframe['greenLine'] == True) & (dataframe['over_sole'] == True)) # Over ATR and RSI over sole 
        # ), 'signal_buy'] = True

        # dataframe.loc[(
        #     ((dataframe['red_last'] == False) & (dataframe['red'] == True)) # Red Sell
        #      | ((dataframe['greenLine_last'] == True) & (dataframe['greenLine'] == False) & (dataframe['over_bought'] == True)) # Stop lost ATR and RSI over bought            
        # ), 'signal_sell'] = True

        # Green + RSI over sole blue&aqua out Red&ATR 
        # dataframe.loc[(
        #     ((dataframe['green_last'] == False) & (dataframe['green'] == True)) # Green buy
        #     # | ((dataframe['over_sole'] == True) & (dataframe['blue'] == True) & dataframe['rsi'] < 50)
        #      | ((dataframe['greenLine'] == True) & ((dataframe['aqua'] == True) | (dataframe['blue'] == True))) # Over ATR + blue and aqua
        #     #| ((dataframe['greenLine_last'] == False) & (dataframe['greenLine'] == True) & (dataframe['over_sole'] == True)) # Over ATR and RSI over sole 
        # ), 'signal_buy'] = True

        # dataframe.loc[(
        #     ((dataframe['red_last'] == False) & (dataframe['red'] == True)) # Red Sell
        #     | ((dataframe['greenLine_last'] == True) & (dataframe['greenLine'] == False)) # Stop lost ATR and RSI over bought            
        # ), 'signal_sell'] = True

        # MACD ATR STOP
        # dataframe.loc[(
        #     ((dataframe['green_last'] == False) & (dataframe['green'] == True)) # Green buy
        # ), 'signal_buy'] = True

        # dataframe.loc[
        #         (
        #             (dataframe["signal_buy"] == True)
        #             & (dataframe['greenLine'] == True)
        #         ),
        #         'atr_stop'] =  dataframe['sl1']

        # dataframe.loc[
        #         (
        #             (dataframe["signal_buy"] == False)
        #         ),
        #         'atr_stop'] =  dataframe.atr_stop.shift(1)

        # dataframe.loc[(
        #     ((dataframe['red_last'] == False) & (dataframe['red'] == True)) # Red Sell
        #     | dataframe['atr_stop'] > dataframe['close']
        # ), 'signal_sell'] = True

        # dataframe.loc[
        #         (
        #             (dataframe["signal_sell"] == True)
        #         ),
        #         'atr_stop'] = 0

        # MACD + dobule bullish
        # dataframe.loc[(
        #     ((dataframe['green_last'] == False) & (dataframe['green'] == True)) # Green buy
        #     | ((dataframe['greenLine'] == True) & (dataframe['blue'] == True)) 
        # ), 'signal_buy'] = True

        # dataframe.loc[(
        #     ((dataframe['red_last'] == False) & (dataframe['red'] == True)) # Red Sell
        # ), 'signal_sell'] = True

        # MACD + dobule bullish + blue ATR
        dataframe.loc[(
            ((dataframe['green_last'] == False) & (dataframe['green'] == True)) # Green buy
            #| ((dataframe['bullish_last'] == True) & (dataframe['bullish'] == True)) # Dobule bullish
            #| ((dataframe['greenLine'] == True) & (dataframe['blue'] == True))  # Blue ATR
        ), 'signal_buy'] = True

        dataframe.loc[
                (
                    (dataframe["signal_buy"] == True)
                    & (dataframe['greenLine'] == True)
                ),
                'atr_stop'] =  dataframe['trail2']

        dataframe.loc[
                (
                    (dataframe["signal_buy"] == False)
                ),
                'atr_stop'] =  dataframe.atr_stop.shift(1)

        dataframe.loc[(
            ((dataframe['red_last'] == False) & (dataframe['red'] == True)) # Red Sell
            | (dataframe['atr_stop'] > dataframe['close'])
        ), 'signal_sell'] = True

        # MACD
        # dataframe.loc[(
        #     ((dataframe['green_last'] == False) & (dataframe['green'] == True)) # Green buy
        # ), 'signal_buy'] = True

        # dataframe.loc[(
        #     ((dataframe['red_last'] == False) & (dataframe['red'] == True)) # Red Sell
        # ), 'signal_sell'] = True

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['signal_buy'] == True) , 'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['signal_sell'] == True), 'sell'] = 1
        return dataframe