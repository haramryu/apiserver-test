from dataclasses import asdict
from typing import Optional

import uvicorn
from fastapi import FastAPI, Depends
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from common.consts import EXCEPT_PATH_LIST, EXCEPT_PATH_REGEX
from database.conn import db
from common.config import conf
from middlewares.token_validator import access_control
from middlewares.trusted_hosts import TrustedHostMiddleware
from routes import index, auth, users, upbit, ticker

from utils.cusotm_logger import CustomizeLogger
from pathlib import Path
from fastapi import Request
import logging

logger = logging.getLogger(__name__)

config_path=Path(__file__).with_name("logging_config.json")

API_KEY_HEADER = APIKeyHeader(name="Authorization", auto_error=False)

def create_app():
    """
    앱 함수 실행
    :return:
    """
    c = conf()
    app = FastAPI()
    conf_dict = asdict(c)
    db.init_app(app, **conf_dict)
    # 데이터 베이스 이니셜라이즈

    # 레디스 이니셜라이즈

    # 미들웨어 정의
    app.add_middleware(middleware_class=BaseHTTPMiddleware, dispatch=access_control)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=conf().ALLOW_SITE,
        allow_credentials=True,
        
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=conf().TRUSTED_HOSTS, except_path=["/health"])
    # 라우터 정의
    app.include_router(index.router)
    app.include_router(auth.router, tags=["Authentication"], prefix="/api")
    app.include_router(upbit.router, tags=["Upbit"], prefix="/api", dependencies=[Depends(API_KEY_HEADER)])
    app.include_router(ticker.router, tags=["Tickers"], prefix="/api"                      , dependencies=[Depends(API_KEY_HEADER)])
    # if conf().DEBUG:
    #     app.include_router(services.router, tags=["Services"], prefix="/api", dependencies=[Depends(API_KEY_HEADER)])
    # else:
    #     app.include_router(services.router, tags=["Services"], prefix="/api")
    app.include_router(users.router, tags=["Users"], prefix="/api", dependencies=[Depends(API_KEY_HEADER)])
    
    logger = CustomizeLogger.make_logger(config_path)
    app.logger = logger

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)