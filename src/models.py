from datetime import datetime, date, time
from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
from sqlalchemy import (
    UniqueConstraint,
    Column,
    Enum as SQLEnum,
    BigInteger,
    Integer,
    String,
    Float,
    DateTime,
    Numeric,
    CheckConstraint,
)
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
    deals: List["MT5Deal"] = Relationship(back_populates="deal_task")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class DealTaskCreate(DealTaskBase):
    pass


class DealTaskRead(DealTaskBase):
    id: int
    created_at: datetime


class MT5DealBase(SQLModel):
    deal_id: int = Field(sa_column=Column(Numeric(20, 0), unique=True))
    action: int = Field(sa_column=Column(Integer))
    comment: str = Field(sa_column=Column(String(32)))
    commission: float = Field(sa_column=Column(Float))
    contract_size: float = Field(sa_column=Column(Float))
    dealer: int = Field(sa_column=Column(Numeric(20, 0)))
    digits: int = Field(sa_column=Column(Integer))
    digits_currency: int = Field(sa_column=Column(Integer))
    entry: int = Field(sa_column=Column(Integer))
    expert_id: int = Field(sa_column=Column(Numeric(20, 0)))
    external_id: str = Field(sa_column=Column(String(32)))
    fee: float = Field(sa_column=Column(Float))
    flags: int = Field(sa_column=Column(Numeric(20, 0)))
    gateway: str = Field(sa_column=Column(String(16)))
    login: int = Field(sa_column=Column(Numeric(20, 0)))
    market_ask: float = Field(sa_column=Column(Float))
    market_bid: float = Field(sa_column=Column(Float))
    market_last: float = Field(sa_column=Column(Float))
    modification_flags: int = Field(sa_column=Column(Integer))
    obsolete_value: float = Field(sa_column=Column(Float))
    order_id: Optional[int] = Field(default=None, sa_column=Column(Numeric(20, 0)))
    position_id: int = Field(sa_column=Column(Numeric(20, 0)))
    price: float = Field(sa_column=Column(Float))
    price_gateway: float = Field(sa_column=Column(Float))
    price_position: float = Field(sa_column=Column(Float))
    price_sl: float = Field(sa_column=Column(Float))
    price_tp: float = Field(sa_column=Column(Float))
    profit: float = Field(sa_column=Column(Float))
    profit_raw: float = Field(sa_column=Column(Float))
    rate_margin: float = Field(sa_column=Column(Float))
    rate_profit: float = Field(sa_column=Column(Float))
    reason: int = Field(sa_column=Column(Integer))
    storage: float = Field(sa_column=Column(Float))
    symbol: str = Field(sa_column=Column(String(32)))
    tick_size: float = Field(sa_column=Column(Float))
    tick_value: float = Field(sa_column=Column(Float))
    time: datetime = Field(sa_column=Column(DateTime))
    time_msc: int = Field(sa_column=Column(Numeric(20, 0)))
    value: float = Field(sa_column=Column(Float))
    volume: int = Field(sa_column=Column(Numeric(20, 0)))
    volume_closed: int = Field(sa_column=Column(Numeric(20, 0)))
    volume_closed_ext: int = Field(sa_column=Column(Numeric(20, 0)))
    volume_ext: int = Field(sa_column=Column(Numeric(20, 0)))
    deal_task_id: int = Field(foreign_key="deal_tasks.id", ondelete="CASCADE")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MT5Deal(SQLModel, table=True):
    __tablename__ = "deals"
    __table_args__ = (
        # Add check constraints for unsigned values
        CheckConstraint("deal_id >= 0", name="ck_deal_id_unsigned"),
        CheckConstraint("dealer >= 0", name="ck_dealer_unsigned"),
        CheckConstraint("login >= 0", name="ck_login_unsigned"),
        CheckConstraint("expert_id >= 0", name="ck_expert_id_unsigned"),
        CheckConstraint("flags >= 0", name="ck_flags_unsigned"),
        CheckConstraint("position_id >= 0", name="ck_position_id_unsigned"),
        CheckConstraint("volume >= 0", name="ck_volume_unsigned"),
        CheckConstraint("volume_closed >= 0", name="ck_volume_closed_unsigned"),
        CheckConstraint("volume_closed_ext >= 0", name="ck_volume_closed_ext_unsigned"),
        CheckConstraint("volume_ext >= 0", name="ck_volume_ext_unsigned"),
    )

    deal_id: int = Field(sa_column=Column(Numeric(20, 0), primary_key=True))
    action: int = Field(sa_column=Column(Integer))
    comment: str = Field(sa_column=Column(String(32)))
    commission: float = Field(sa_column=Column(Float))
    contract_size: float = Field(sa_column=Column(Float))
    dealer: int = Field(sa_column=Column(Numeric(20, 0)))
    digits: int = Field(sa_column=Column(Integer))
    digits_currency: int = Field(sa_column=Column(Integer))
    entry: int = Field(sa_column=Column(Integer))
    expert_id: int = Field(sa_column=Column(Numeric(20, 0)))
    external_id: str = Field(sa_column=Column(String(32)))
    fee: float = Field(sa_column=Column(Float))
    flags: int = Field(sa_column=Column(Numeric(20, 0)))
    gateway: str = Field(sa_column=Column(String(16)))
    login: int = Field(sa_column=Column(Numeric(20, 0)))
    market_ask: float = Field(sa_column=Column(Float))
    market_bid: float = Field(sa_column=Column(Float))
    market_last: float = Field(sa_column=Column(Float))
    modification_flags: int = Field(sa_column=Column(Integer))
    obsolete_value: float = Field(sa_column=Column(Float))
    order_id: Optional[int] = Field(default=None, sa_column=Column(Numeric(20, 0)))
    position_id: int = Field(sa_column=Column(Numeric(20, 0)))
    price: float = Field(sa_column=Column(Float))
    price_gateway: float = Field(sa_column=Column(Float))
    price_position: float = Field(sa_column=Column(Float))
    price_sl: float = Field(sa_column=Column(Float))
    price_tp: float = Field(sa_column=Column(Float))
    profit: float = Field(sa_column=Column(Float))
    profit_raw: float = Field(sa_column=Column(Float))
    rate_margin: float = Field(sa_column=Column(Float))
    rate_profit: float = Field(sa_column=Column(Float))
    reason: int = Field(sa_column=Column(Integer))
    storage: float = Field(sa_column=Column(Float))
    symbol: str = Field(sa_column=Column(String(32)))
    tick_size: float = Field(sa_column=Column(Float))
    tick_value: float = Field(sa_column=Column(Float))
    time: datetime = Field(sa_column=Column(DateTime))
    time_msc: int = Field(sa_column=Column(Numeric(20, 0)))
    value: float = Field(sa_column=Column(Float))
    volume: int = Field(sa_column=Column(Numeric(20, 0)))
    volume_closed: int = Field(sa_column=Column(Numeric(20, 0)))
    volume_closed_ext: int = Field(sa_column=Column(Numeric(20, 0)))
    volume_ext: int = Field(sa_column=Column(Numeric(20, 0)))
    deal_task_id: int = Field(foreign_key="deal_tasks.id", ondelete="CASCADE")
    deal_task: DealTask = Relationship(back_populates="deals")


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
