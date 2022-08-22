from cgitb import text
from datetime import datetime, timedelta
import string
from time import sleep

import bcrypt
import jwt
from fastapi import APIRouter, Depends
from sqlalchemy import false, true

from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from starlette.requests import Request

import models
from common.consts import JWT_SECRET, JWT_ALGORITHM
from database.conn import db
from database.schema import Users, Tickers
from models import SnsType, Token, UserToken, UserRegister, UserLogin

from loguru import logger
import threading

from plans.rsi import Rsi, Wm

router = APIRouter(prefix="/auth")

@router.post("/register/{sns_type}", status_code=201, response_model=Token)
async def register(sns_type: SnsType, reg_info: models.UserRegister, session: Session = Depends(db.session)):
    """
    회원가입 API\n
    :param sns_type:
    :param reg_info:
    :param session:
    :return:
    """
    if sns_type == SnsType.email:
        is_exist = await is_email_exist(reg_info.email)
        if not reg_info.email or not reg_info.pw:
            return JSONResponse(status_code=400, content=dict(msg="Email and PW must be provided"))
        if is_exist:
            return JSONResponse(status_code=400, content=dict(msg="EMAIL_EXISTS"))
        hash_pw = bcrypt.hashpw(reg_info.pw.encode("utf-8"), bcrypt.gensalt())
        new_user = Users.create(session, auto_commit=True, pw=hash_pw, email=reg_info.email, upbit_access_key=reg_info.upbit_access_key, upbit_secret_key=reg_info.upbit_secret_key)
        token = dict(Authorization=f"Bearer {create_access_token(data=UserToken.from_orm(new_user).dict(exclude={'pw','marketing_agree'}),)}")
        return token
    return JSONResponse(status_code=400, content=dict(msg="NOT_SUPPORTED"))

@router.post("/login/{sns_type}", status_code=200, response_model=Token)
async def login(request: Request, sns_type: SnsType, user_info: UserLogin):
    if sns_type == SnsType.email:
        is_exist = await is_email_exist(user_info.email)
        if not user_info.email or not user_info.pw:
            return JSONResponse(status_code=400, content=dict(msg="Email and PW must be provided"))
        if not is_exist:
            return JSONResponse(status_code=400, content=dict(msg="NO_MATCH_USER"))
        user = Users.get(email=user_info.email)
        is_verified = bcrypt.checkpw(user_info.pw.encode("utf-8"), user.pw.encode("utf-8"))
        if not is_verified:
            return JSONResponse(status_code=400, content=dict(msg="NO_MATCH_USER"))
        token = dict(Authorization=f"Bearer {create_access_token(data=UserToken.from_orm(user).dict(exclude={'pw','marketing_agree'}),)}")
        # RSI 쓰레드 생성하는 부분
        request.state.user = user
        rsi = Rsi(request)
        rsi.setDaemon(True)
        rsi.start()

        tickers = Tickers.filter(user_id=user.id).all()
        request.app.logger.info("tickers: " + str(tickers))

        for t in tickers:
            Rsi.appendticker(t.ticker)
        
        request.app.logger.info("ticker list: " + str(Rsi.tickers))

        Rsi.wsstart(request)
        return token
    return JSONResponse(status_code=400, content=dict(msg="NOT_SUPPORTED"))

async def is_email_exist(email: str):
    get_email = Users.get(email=email)
    if get_email:
        return True
    return False

def create_access_token(*, data: dict = None, expires_delta: int = None):
    to_encode = data.copy()
    if expires_delta:
        to_encode.update({"exp": datetime.utcnow() + timedelta(hours=expires_delta)})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt