from datetime import datetime, date, time
from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
from sqlalchemy import UniqueConstraint, Column, Enum as SQLEnum, BigInteger
from pydantic import ConfigDict


class DealStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class DealTaskBase(SQLModel):
    date: date
    start_time: time
    end_time: time
    status: str = Field(
        default="PENDING",
        sa_column=Column(
            SQLEnum(
                "PENDING",
                "PROCESSING",
                "SUCCESS",
                "FAILED",
                name="dealstatus",
                create_constraint=True,
            )
        ),
    )


class DealTask(DealTaskBase, table=True):
    __tablename__ = "deal_tasks"
    __table_args__ = (
        UniqueConstraint("date", "start_time", "end_time", name="uq_task_period"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class DealTaskCreate(DealTaskBase):
    pass


class DealTaskRead(DealTaskBase):
    id: int
    created_at: datetime


class MT5DealBase(SQLModel):
    deal_id: int = Field(unique=True)
    action: int
    comment: str
    commission: float
    contract_size: float
    dealer: int
    digits: int
    digits_currency: int
    entry: int
    expert_id: int
    external_id: str
    fee: float
    flags: int
    gateway: str
    login: int
    market_ask: float
    market_bid: float
    market_last: float
    modification_flags: int
    obsolete_value: float
    order_id: Optional[int] = None
    position_id: int
    price: float
    price_gateway: float
    price_position: float
    price_sl: float
    price_tp: float
    profit: float
    profit_raw: float
    rate_margin: float
    rate_profit: float
    reason: int
    storage: float
    symbol: str
    tick_size: float
    tick_value: float
    time: datetime
    time_msc: int = Field(sa_column=Column(BigInteger()))
    value: float
    volume: float
    volume_closed: float
    volume_closed_ext: float
    volume_ext: float
    deal_task_id: int = Field(foreign_key="deal_tasks.id")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MT5Deal(SQLModel, table=True):
    __tablename__ = "deals"

    deal_id: int = Field(primary_key=True)
    action: int
    comment: str
    commission: float
    contract_size: float
    dealer: int
    digits: int
    digits_currency: int
    entry: int
    expert_id: int
    external_id: str
    fee: float
    flags: int
    gateway: str
    login: int
    market_ask: float
    market_bid: float
    market_last: float
    modification_flags: int
    obsolete_value: float
    order_id: Optional[int] = None
    position_id: int
    price: float
    price_gateway: float
    price_position: float
    price_sl: float
    price_tp: float
    profit: float
    profit_raw: float
    rate_margin: float
    rate_profit: float
    reason: int
    storage: float
    symbol: str
    tick_size: float
    tick_value: float
    time: datetime
    time_msc: int = Field(sa_column=Column(BigInteger()))
    value: float
    volume: float
    volume_closed: float
    volume_closed_ext: float
    volume_ext: float


class MT5DealCreate(MT5DealBase):
    pass


class MT5DealRead(MT5DealBase):
    id: int


class DealTaskResponse(SQLModel):
    success: bool
    message: str
    data: Optional[List[DealTaskRead]] = None


class ProcessDealRequest(SQLModel):
    deal_ids: List[int]


class DeleteDealRequest(SQLModel):
    deal_ids: List[int]


# FastUI Page Models
class PageContext(SQLModel):
    title: str = "Deal Data Extractor"
