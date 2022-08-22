from audioop import avg
import threading
from time import sleep, time
from datetime import datetime, timedelta
from xmlrpc.client import boolean
from anyio import BusyResourceError
from numpy import False_
from starlette.requests import Request
from loguru import logger

from pandas import DataFrame, Series
import pyupbit
from pyupbit import WebSocketManager
import enum

class Status(enum.Enum):
    READY=enum.auto()
    UNDER_LOW_LIMIT_1=enum.auto()
    UNDER_LOW_LIMIT_2=enum.auto()
    UNDER_LOW_LIMIT_3=enum.auto()
    BUY_1=enum.auto()
    BUY_2=enum.auto()
    BUY_3=enum.auto()
    CUT=enum.auto()
    OVER_HIGH_LIMIT=enum.auto()
    SELL_1=enum.auto()
    SELL_2=enum.auto()
    SELL_ALL=enum.auto()

class Rsi(threading.Thread):
    flag_break: bool = False
    tickers: list = []
    # lower25: dict = {}
    # lower40: dict = {}
    # higher60: dict = {}
    # higher70: dict = {} 
    # buyflag: dict = {}
    low_value: dict = {}
    mid_value: dict = {}
    high_value: dict = {}
    buy_time: dict = {}
    sell_time: dict = {}
    cut_time: dict = {}
    flag_cut: dict = {}
    flag_sell: dict = {}
    status: dict = {}
    curr_price: dict = {}
    volume_power: dict = {}
    flag_vol_pwr_inc: dict = {}
    flag_vol_pwr_dec: dict = {}
    avg_buy_price: dict = {}
    ma5: dict = {}
    initial_low_value = 28
    initial_mid_value = 45 # prev: 50
    initial_high_value = 50 # prev: 50
    upbit: pyupbit.Upbit
    
    def __init__(self, request: Request):
        threading.Thread.__init__(self, name='Rsi')
        self.request = request
        access_key = request.state.user.upbit_access_key
        secret_key = request.state.user.upbit_secret_key
        Rsi.upbit = pyupbit.Upbit(access_key, secret_key)
        self.logger = request.app.logger
    
    def run(self):
        now = datetime.now()
        reset_time = datetime(now.year, now.month, now.day) + timedelta(1)
        self.flag_day = True

        self.getavgprices()
        self.logger.info("Rsi.avg_buy_price" + str(Rsi.avg_buy_price))
        self.getma5s()
        self.logger.info("Rsi.ma5" + str(Rsi.ma5))

        while not Rsi.flag_break:
            now = datetime.now()
            if reset_time < now < reset_time + timedelta(seconds=30):
                self.flag_day = False
            elif reset_time + timedelta(hours=7) < now < reset_time + timedelta(hours=7) + timedelta(seconds=30):
                self.flag_day = True
                reset_time = datetime(now.year, now.month, now.day) + timedelta(1)

            for ticker in Rsi.tickers:
                elapsed_buy = time() - Rsi.buy_time[ticker]
                elapsed_sell = time() - Rsi.sell_time[ticker]
                # if Rsi.curr_price[ticker] > Rsi.ma5[ticker]: 
                try:
                    if not Rsi.curr_price[ticker]:
                        self.logger.info(f"{ticker} PASS")
                        continue

                    curr_rsi = self.calcrsi(ticker)
                    if Rsi.status[ticker] == Status.READY:
                        if curr_rsi <= Rsi.low_value[ticker]:
                            Rsi.status[ticker] = Status.UNDER_LOW_LIMIT_1
                            self.logger.info(f"{ticker} READY → UNDER_LOW_LIMIT_1")
                        elif curr_rsi >= Rsi.high_value[ticker]:
                            self.logger.info(f"{ticker} READY → OVER_HIGH_LIMIT")
                            Rsi.flag_sell[ticker] = False
                            Rsi.status[ticker] = Status.OVER_HIGH_LIMIT
                        self.logger.info(f"{ticker} status: {Rsi.status[ticker]} rsi: {curr_rsi} high: {Rsi.high_value[ticker]} low: {Rsi.low_value[ticker]}")
                    elif Rsi.status[ticker] == Status.UNDER_LOW_LIMIT_1:
                        if curr_rsi <= Rsi.low_value[ticker]:
                            Rsi.low_value[ticker] -= 1
                        elif curr_rsi >= Rsi.low_value[ticker] + 5:
                            res = self.buy(ticker)
                            # self.logger.info(res)
                            self.logger.info(f"{ticker} UNDER_LOW_LIMIT_1 → BUY_1 \n {str(res)}")
                            Rsi.status[ticker] = Status.BUY_1
                        self.logger.info(f"{ticker} status: {Rsi.status[ticker]} rsi: {curr_rsi} low: {Rsi.low_value[ticker]}")
                            
                    elif Rsi.status[ticker] == Status.BUY_1:
                        self.logger.info(f"{ticker} status: {Rsi.status[ticker]} rsi: {curr_rsi} high: {Rsi.high_value[ticker]} low: {Rsi.low_value[ticker]}")
                        self.logger.info(f"{ticker} curr_price: {Rsi.curr_price[ticker]} avg_price: {Rsi.avg_buy_price[ticker]}")
                        if curr_rsi <= Rsi.low_value[ticker]:
                            self.logger.info(f"{ticker} BUY_1 → UNDER_LOW_LIMIT_2")
                            Rsi.status[ticker] = Status.UNDER_LOW_LIMIT_2
                        elif curr_rsi >= Rsi.high_value[ticker]:
                            self.logger.info(f"{ticker} BUY_1 → OVER_HIGH_LIMIT")
                            Rsi.flag_sell[ticker] = False
                            Rsi.status[ticker] = Status.OVER_HIGH_LIMIT
                        if Rsi.curr_price[ticker] <= Rsi.avg_buy_price[ticker] * (1 - 0.02):
                            res = self.sell(ticker, True)
                            # self.logger.info(res)
                            self.logger.info(f"{ticker} is low price. \n {str(res)}")
                            Rsi.status[ticker] = Status.READY
                    elif Rsi.status[ticker] == Status.UNDER_LOW_LIMIT_2:
                        self.logger.info(f"{ticker} status: {Rsi.status[ticker]} rsi: {curr_rsi} high: {Rsi.high_value[ticker]} low: {Rsi.low_value[ticker]}")
                        self.logger.info(f"{ticker} curr_price: {Rsi.curr_price[ticker]} avg_price: {Rsi.avg_buy_price[ticker]}")
                        if curr_rsi <= Rsi.low_value[ticker]:
                            Rsi.low_value[ticker] -= 1
                        elif curr_rsi >= Rsi.low_value[ticker] + 5:
                            res = self.buy(ticker)
                            # self.logger.info(res)
                            self.logger.info(f"{ticker} UNDER_LOW_LIMIT_2 → BUY_2")
                            Rsi.status[ticker] = Status.BUY_2
                        elif curr_rsi >= Rsi.high_value[ticker]:
                            self.logger.info(f"{ticker} UNDER_LOW_LIMIT_2 → OVER_HIGH_LIMIT")
                            Rsi.flag_sell[ticker] = False
                            Rsi.status[ticker] = Status.OVER_HIGH_LIMIT
                        if Rsi.curr_price[ticker] <= Rsi.avg_buy_price[ticker] * (1 - 0.02):
                            res = self.sell(ticker, True)
                            # self.logger.info(res)
                            self.logger.info(f"{ticker} is low price. \n {str(res)}")
                            Rsi.status[ticker] = Status.READY
                    elif Rsi.status[ticker] == Status.BUY_2:
                        self.logger.info(f"{ticker} status: {Rsi.status[ticker]} rsi: {curr_rsi} high: {Rsi.high_value[ticker]} low: {Rsi.low_value[ticker]}")
                        self.logger.info(f"{ticker} curr_price: {Rsi.curr_price[ticker]} avg_price: {Rsi.avg_buy_price[ticker]}")
                        if curr_rsi <= Rsi.low_value[ticker]:
                            Rsi.status[ticker] = Status.UNDER_LOW_LIMIT_3
                        elif curr_rsi >= Rsi.high_value[ticker]:
                            self.logger.info(f"{ticker} BUY_2 → OVER_HIGH_LIMIT")
                            Rsi.flag_sell[ticker] = False
                            Rsi.status[ticker] = Status.OVER_HIGH_LIMIT
                        if Rsi.curr_price[ticker] <= Rsi.avg_buy_price[ticker] * (1 - 0.02):
                            res = self.sell(ticker, True)
                            # self.logger.info(res)
                            self.logger.info(f"{ticker} is low price. \n {str(res)}")
                            Rsi.status[ticker] = Status.READY
                    elif Rsi.status[ticker] == Status.UNDER_LOW_LIMIT_3:
                        self.logger.info(f"{ticker} status: {Rsi.status[ticker]} rsi: {curr_rsi} high: {Rsi.high_value[ticker]} low: {Rsi.low_value[ticker]}")
                        self.logger.info(f"{ticker} curr_price: {Rsi.curr_price[ticker]} avg_price: {Rsi.avg_buy_price[ticker]}")
                        if curr_rsi <= Rsi.low_value[ticker]:
                            Rsi.low_value[ticker] -= 1
                        elif curr_rsi >= Rsi.low_value[ticker] + 5:
                            res = self.buy(ticker)
                            # self.logger.info(res)
                            self.logger.info(f"{ticker} UNDER_LOW_LIMIT_3 → BUY_3")
                            Rsi.status[ticker] = Status.BUY_3
                        elif curr_rsi >= Rsi.high_value[ticker]:
                            self.logger.info(f"{ticker} UNDER_LOW_LIMIT_3 → OVER_HIGH_LIMIT")
                            Rsi.flag_sell[ticker] = False
                            Rsi.status[ticker] = Status.OVER_HIGH_LIMIT
                        if Rsi.curr_price[ticker] <= Rsi.avg_buy_price[ticker] * (1 - 0.02):
                            res = self.sell(ticker, True)
                            # self.logger.info(res)
                            self.logger.info(f"{ticker} is low price. \n {str(res)}")
                            Rsi.status[ticker] = Status.READY
                    elif Rsi.status[ticker] == Status.BUY_3:
                        self.logger.info(f"{ticker} status: {Rsi.status[ticker]} rsi: {curr_rsi} high: {Rsi.high_value[ticker]} low: {Rsi.low_value[ticker]}")
                        self.logger.info(f"{ticker} curr_price: {Rsi.curr_price[ticker]} avg_price: {Rsi.avg_buy_price[ticker]}")
                        if curr_rsi <= Rsi.low_value[ticker]:
                            Rsi.status[ticker] = Status.CUT
                            Rsi.mid_value[ticker] = Rsi.initial_mid_value
                            Rsi.flag_cut[ticker] = False
                            self.logger.info(f"{ticker} BUY_3 → CUT")
                        elif curr_rsi >= Rsi.high_value[ticker]:
                            self.logger.info(f"{ticker} BUY_3 → OVER_HIGH_LIMIT")
                            Rsi.flag_sell[ticker] = False
                            Rsi.status[ticker] = Status.OVER_HIGH_LIMIT
                        if Rsi.curr_price[ticker] <= Rsi.avg_buy_price[ticker] * (1 - 0.02):
                            res = self.sell(ticker, True)
                            # self.logger.info(res)
                            self.logger.info(f"{ticker} is low price. \n {str(res)}")
                            Rsi.status[ticker] = Status.READY
                    elif Rsi.status[ticker] == Status.CUT:
                        elapsed_cut = time() - Rsi.cut_time[ticker]
                        if curr_rsi >= Rsi.mid_value[ticker]:
                            Rsi.mid_value[ticker] += 1
                            Rsi.flag_cut[ticker] = True
                            self.logger.info(f"{ticker} status: {Rsi.status[ticker]} rsi: {curr_rsi} mid: {Rsi.mid_value[ticker]}")
                        elif Rsi.flag_cut[ticker] and curr_rsi <= Rsi.mid_value[ticker] - 5:
                            res = self.sell(ticker, True)
                            # self.logger.info(res)
                            self.logger.info(f"{ticker} CUT → READY \n {str(res)}")
                            Rsi.status[ticker] = Status.READY
                        if elapsed_cut > 60 * 5:
                            Rsi.mid_value[ticker] -= 1
                            Rsi.cut_time[ticker] = time()
                    elif Rsi.status[ticker] == Status.OVER_HIGH_LIMIT:
                        if curr_rsi >= Rsi.high_value[ticker]:
                            Rsi.high_value[ticker] += 1
                            Rsi.flag_sell[ticker] = True
                            self.logger.info(f"{ticker} status: {Rsi.status[ticker]} rsi: {curr_rsi} high: {Rsi.high_value[ticker]}")
                        elif Rsi.flag_sell[ticker] and curr_rsi <= Rsi.high_value[ticker] -3:
                            res = self.sell(ticker)
                            self.logger.info(f"{ticker} OVER_HIGH_LIMIT → SELL_1 \n {str(res)}")
                            Rsi.status[ticker] = Status.SELL_1

                    elif Rsi.status[ticker] == Status.SELL_1:
                        self.logger.info(f"{ticker} status: {Rsi.status[ticker]} rsi: {curr_rsi} high: {Rsi.high_value[ticker]} low: {Rsi.low_value[ticker]}")
                        if curr_rsi >= Rsi.high_value[ticker] + 10:
                            res = self.sell(ticker)
                            # self.logger.info(res)
                            self.logger.info(f"{ticker} SELL_1 → SELL_2 \n {str(res)}")
                            Rsi.status[ticker] = Status.SELL_2
                        elif curr_rsi <= Rsi.high_value[ticker] - 5:
                            Rsi.status[ticker] = Status.READY
                            Rsi.high_value[ticker] = Rsi.initial_high_value
                            self.logger.info(f"{ticker} SELL_1 → READY")
                    elif Rsi.status[ticker] == Status.SELL_2:
                        self.logger.info(f"{ticker} status: {Rsi.status[ticker]} rsi: {curr_rsi} high: {Rsi.high_value[ticker]} low: {Rsi.low_value[ticker]}")
                        if curr_rsi >= Rsi.high_value[ticker] + 20:
                            res = self.sell(ticker, True)
                            # self.logger.info(res)
                            self.logger.info(f"{ticker} SELL_2 → READY \n {str(res)}")
                            Rsi.status[ticker] = Status.READY
                        elif curr_rsi <= Rsi.high_value[ticker] + 5:
                            Rsi.status[ticker] = Status.READY
                            Rsi.high_value[ticker] = Rsi.initial_high_value
                            self.logger.info(f"{ticker} SELL_2 → READY")
                        
                except TypeError as e:
                    continue
                except Exception as e:
                    self.logger.info(e)
                if elapsed_buy > 30 * 60:
                    if Rsi.low_value[ticker] >= Rsi.initial_low_value + 10:
                        Rsi.low_value[ticker] = Rsi.initial_low_value + 10
                    else:
                        Rsi.low_value[ticker] += 1
                    Rsi.buy_time[ticker] = time()

                if elapsed_sell > 10 * 60:
                    if Rsi.high_value[ticker] <= Rsi.initial_high_value - 10:
                        Rsi.high_value[ticker] = Rsi.initial_high_value - 10
                    else:
                        Rsi.high_value[ticker] -= 1
                    Rsi.sell_time[ticker] = time()
                sleep(0.15)
    
    def calcrsi(self, ticker: str):
        ohlc = pyupbit.get_ohlcv(ticker, interval="minute1")
        try:
            close = ohlc["close"]
        except TypeError as e:
            raise e
        delta = close.diff()
        
        ups, downs = delta.copy(), delta.copy()
        ups[ups < 0] = 0
        downs[downs > 0] = 0
        
        period = 14
        au = ups.ewm(com = period-1, min_periods=period).mean()
        ad = downs.abs().ewm(com = period-1, min_periods=period).mean()
        
        RS = au/ad
        RSI = Series(100 - (100/(1+RS)))
        
        return RSI.iloc[-1]

    def calcma5(self, ticker: str):
        df = pyupbit.get_ohlcv(ticker)
        close = df['close']
        ma = close.rolling(5).mean()
        return ma[-2]
        
    @classmethod     
    def setflagbreak(cls, flag: bool):
        cls.flag_break = flag

    def buy(self, ticker):
        Rsi.buy_time[ticker] = time()
        Rsi.low_value[ticker] = Rsi.initial_low_value
        try:
            balance, req = Rsi.upbit.get_balance("KRW", True)
            if not self.flag_day:
                self.logger.info("NOT IN DAY TIME")
                return
            elif balance < 10000:
                return # 에러메시지 정의하기
            elif balance < 20000:
                res = Rsi.upbit.buy_market_order(ticker, balance)
            elif balance < 50000:
                res = Rsi.upbit.buy_market_order(ticker, balance * 0.4)
            elif balance < 100000:
                res = Rsi.upbit.buy_market_order(ticker, balance * 0.3)
            else:
                res = Rsi.upbit.buy_market_order(ticker, balance * 0.2)
        except TypeError as e:
            return e
        
        self.getavgprices()
        return res

    def sell(self, ticker: str, all_flag: bool = False):
        self.logger.info("Rsi.avg_buy_price" + str(Rsi.avg_buy_price))
        try:
            amount = Rsi.upbit.get_balance(ticker)
            current_price = pyupbit.get_current_price(ticker)
            total_price = amount * current_price
            if total_price < 20000 or all_flag:
                res = Rsi.upbit.sell_market_order(ticker, amount)
            elif total_price < 50000:
                res = Rsi.upbit.sell_market_order(ticker, amount * 0.7)
            elif total_price < 100000:
                res = Rsi.upbit.sell_market_order(ticker, amount * 0.6)
            else:
                res = Rsi.upbit.sell_market_order(ticker, amount * 0.5)
        except TypeError as e:
            return e
        Rsi.sell_time[ticker] = time()

        self.getavgprices()
        return res

    @staticmethod
    def appendticker(ticker):
        Rsi.tickers.append(ticker)
        # Rsi.lower25[ticker] = False
        # Rsi.lower40[ticker] = False
        # Rsi.higher60[ticker] = False
        # Rsi.higher70[ticker] = False
        # Rsi.buyflag[ticker] = False
        Rsi.low_value[ticker] = Rsi.initial_low_value
        Rsi.mid_value[ticker] = Rsi.initial_mid_value
        Rsi.high_value[ticker] = Rsi.initial_high_value
        Rsi.buy_time[ticker] = time()
        Rsi.sell_time[ticker] = time()
        Rsi.cut_time[ticker] = time()
        Rsi.status[ticker] = Status.READY
        Rsi.curr_price[ticker] = 0
        Rsi.volume_power[ticker] = 0.0
        Rsi.ma5[ticker] = 0.0
        Rsi.flag_cut[ticker] = False
        Rsi.flag_sell[ticker] = False
        Rsi.flag_vol_pwr_inc[ticker] = False
        Rsi.flag_vol_pwr_dec[ticker] = False
    
    @staticmethod
    def wsstart(request: Request):
        wm = Wm(request)
        wm.setDaemon(True)
        wm.start()
        
    @staticmethod
    def wsrestart(request: Request):
        Wm.setflag
        wm = Wm(request)
        wm.setDaemon(True)
        wm.start()
    
    def getavgprices(self):
        balances = Rsi.upbit.get_balances()
        self.logger.info(balances)
        for ticker in Rsi.tickers:
            try:
                Rsi.avg_buy_price[ticker] = float(list(filter(lambda x: x['currency'] == ticker.split('-')[1], balances))[0]['avg_buy_price'])
            except Exception as e:
                Rsi.avg_buy_price[ticker] = 0
                self.logger.info(f"{ticker} : " + str(e))
                pass
    def getma5s(self):
        for ticker in Rsi.tickers:
            try:
                Rsi.ma5[ticker] = self.calcma5(ticker)
            except Exception as e:
                self.logger.info(e)
                pass

class Wm(threading.Thread):
    flag: bool = False
    wm: WebSocketManager
    logger: logger
    volume_power: dict

    def __init__(self, request: Request):
        threading.Thread.__init__(self, name='WebsocketManager')
        Wm.logger = request.app.logger
        try:
            Wm.wm = WebSocketManager("ticker", Rsi.tickers)
            Wm.flag = True
        except Exception as e:
            Wm.logger.info(e)
    def __del__(self):
        Wm.wm.terminate()
    def run(self):
        while Wm.flag:
            now = datetime.now()
            data = Wm.wm.get()
        
            try:
                Rsi.curr_price[data['code']] = data['trade_price']
                Rsi.volume_power[data['code']] = data['acc_bid_volume'] / data['acc_ask_volume'] * 100
            except TypeError as e:
                continue
            except Exception as e:
                continue
    @classmethod
    def setflag(cls):
        cls.flag = False

    def addvolumepower(self, ticker, volumepower):
        self.volume_power[ticker].append(volumepower)

        if len(self.volume_power[ticker]) == 61:
            increase_cnt = 0
            decrease_cnt = 0
            s = Series(self.volume_power[ticker])
            if s[-1] > s[-2]: 
                increase_cnt += 1
            else:
                decrease_cnt += 1
            ma5 = s.rolling(5).mean()
            if ma5[-1] > ma5[-2]: 
                increase_cnt += 1
            else:
                decrease_cnt += 1
            ma20 = s.rolling(20).mean()
            if ma20[-1] > ma20[-2]: 
                increase_cnt += 1
            else:
                decrease_cnt += 1
            ma60 = s.rolling(60).mean()
            if ma60[-1] > ma60[-2]: 
                increase_cnt += 1
            else:
                decrease_cnt += 1

            if increase_cnt >= 3:
                Rsi.flag_vol_pwr_inc[ticker] = True
                Rsi.flag_vol_pwr_dec[ticker] = False
            elif decrease_cnt >= 3:
                Rsi.flag_vol_pwr_inc[ticker] = False
                Rsi.flag_vol_pwr_dec[ticker] = True

            del self.volume_power[ticker][0]