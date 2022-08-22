from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.requests import Request
from models import Ticker, CreateTicker, TickerVolume, Balance
from database.conn import db
from typing import List

import pyupbit
from pydantic import parse_obj_as

router = APIRouter(prefix='/upbit')

@router.get("/topvolume", response_model=List[TickerVolume])
async def get_top_volume(request: Request, limit: int):
    """
    UPBIT 거래량 상위 코인 조회\n
    :param request:
    :param limit:
    :return:
    """
    tickers = pyupbit.get_tickers(fiat="KRW")
    ticker_value = {}
    try:
        for ticker in tickers:
            ohlcv = pyupbit.get_ohlcv(ticker)
            print("ticker: ", ticker, "value: ", ohlcv["value"][-1])
            ticker_value[f"{ticker}"] = ohlcv["value"][-1]
    except:
        pass
    sorted_ticker_value = sorted(ticker_value.items(), key = lambda item: item[1], reverse=True)
    limit = limit if limit <= len(sorted_ticker_value) else len(sorted_ticker_value)
    sorted_ticker_value = sorted_ticker_value[:limit]
    dict_ticker_value = [{'ticker': t, 'volume': v} for t, v in sorted_ticker_value]
    return parse_obj_as(List[TickerVolume], dict_ticker_value)

@router.get("/balances", response_model=List[Balance])
async def get_balances(request: Request):
    """
    현재 코인 및 현금 보유량
    :param request:
    :return:
    """
    access_key = request.state.user.upbit_access_key
    secret_key = request.state.user.upbit_secret_key
    upbit = pyupbit.Upbit(access_key, secret_key)

    return upbit.get_balances()
