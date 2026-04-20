from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Article:
    hash: str
    category: str
    title: str
    link: str
    summary: str
    published: str
    importance: int = 0
    one_line: str = ''
    is_urgent: bool = False
    keywords: list = field(default_factory=list)
    issue: str = ''
    cause: str = ''
    economic_impact: str = ''
    affected_sectors: list = field(default_factory=list)
    sentiment: str = 'neutral'
    prediction: str = ''

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, data: dict) -> 'Article':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MarketPrediction:
    name: str
    last_close: float
    pred_close: float
    change_pct: float
    direction: str
    pred_range: dict

    def to_dict(self) -> dict:
        return self.__dict__


@dataclass
class FusedPrediction:
    kospi: dict
    usd_krw: dict
    key_sector: dict
    overall_sentiment: str
    weekly_summary: str

    def to_dict(self) -> dict:
        return self.__dict__