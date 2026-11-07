"""Типизированные callback-данные. Короткие префиксы укладываются в лимит Telegram (64 байта)."""
from aiogram.filters.callback_data import CallbackData


class Menu(CallbackData, prefix="m"):
    to: str  # main | book | my | services | masters | contacts | contact_admin


class Svc(CallbackData, prefix="s"):
    id: int


class Mst(CallbackData, prefix="w"):
    svc: int
    id: int  # 0 = любой свободный


class Day(CallbackData, prefix="d"):
    svc: int
    mst: int
    d: str  # YYYYMMDD


class Slot(CallbackData, prefix="t"):
    svc: int
    mst: int
    d: str
    t: str  # HHMM


class Ok(CallbackData, prefix="ok"):
    svc: int
    mst: int
    d: str
    t: str


class Appt(CallbackData, prefix="a"):
    id: int


class CancelAsk(CallbackData, prefix="ca"):
    id: int


class CancelYes(CallbackData, prefix="cy"):
    id: int
