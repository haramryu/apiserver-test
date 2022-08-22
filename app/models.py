from datetime import datetime
from enum import Enum
from mimetypes import init
import string
from typing import List
from xmlrpc.client import boolean
from numpy import float64

from pydantic import Field
from pydantic.main import BaseModel
from pydantic.networks import EmailStr, IPvAnyAddress


class UserRegister(BaseModel):
    # pip install 'pydantic[email]'

    email: str = None
    pw: str = None
    upbit_access_key: str = None
    upbit_secret_key: str = None

class UserLogin(BaseModel):

    email: str = None
    pw: str = None


class SnsType(str, Enum):
    email: str = "email"
    facebook: str = "facebook"
    google: str = "google"
    kakao: str = "kakao"


class Token(BaseModel):
    Authorization: str = None

class EmailRecipients(BaseModel):
    name: str
    email: str

class SendEmail(BaseModel):
    email_to: List[EmailRecipients] = None

class KakaoMsgBody(BaseModel):
    msg: str = None

class MessageOk(BaseModel):
    message: str = Field(default="OK")

class UserToken(BaseModel):
    id: int
    email: str = None
    name: str = None
    phone_number: str = None
    profile_img: str = None
    sns_type: str = None
    upbit_access_key: str = None
    upbit_secret_key: str = None

    class Config:
        orm_mode = True

class UserMe(BaseModel):
    id: int
    email: str = None
    name: str = None
    phone_number: str = None
    profile_img: str = None
    sns_type: str = None
    upbit_access_key: str = None
    upbit_secret_key: str = None

    class Config:
        orm_mode = True

class AddApiKey(BaseModel):
    user_memo: str = None

    class Config:
        orm_mode = True


class GetApiKeyList(AddApiKey):
    id: int = None
    access_key: str = None
    created_at: datetime = None


class GetApiKeys(GetApiKeyList):
    secret_key: str = None

class CreateApiWhiteLists(BaseModel):
    ip_addr: str = None

class GetApiWhiteLists(CreateApiWhiteLists):
    id: int

    class Config:
        orm_mode = True


class CreateTicker(BaseModel):
    ticker: str = None
    plan: str = None
    initial: str = None

    class Config:
        orm_mode = True

class Ticker(CreateTicker):
    id: int # UUID
    current: str = None
    rate: str = None
    expired: bool = False
    
class TickerVolume(BaseModel):
    ticker: str = None
    volume: float
    
class Balance(BaseModel):
    currency: str = None
    balance: float
    locked: float
    avg_buy_price: float
    avg_buy_price_modified: bool
    unit_currency: str = None