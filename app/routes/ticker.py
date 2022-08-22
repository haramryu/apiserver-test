from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.requests import Request
from database.schema import Tickers
from models import CreateTicker
import models as m
from database.conn import db
from typing import List
from uuid import uuid4
from plans.rsi import Rsi, Wm

router = APIRouter(prefix='/ticker')

@router.post("/", status_code=201, response_model=m.Ticker)
async def create_ticker(request: Request, ticker: CreateTicker, session: Session = Depends(db.session)):
    """
    TICKER 등록\n
    :param request:
    :param ticker:
    :param plan:
    :param initial:
    :param session:
    :return:
    """
    logger = request.app.logger
    user = request.state.user
    
    ticker_info = ticker.dict()
    new_ticker = Tickers.create(session, auto_commit=True, user_id=user.id, **ticker_info)
    logger.info(ticker_info["ticker"])
    Rsi.appendticker(ticker_info["ticker"])
    logger.info(Rsi.tickers)

    Rsi.wsrestart(request)
    return new_ticker