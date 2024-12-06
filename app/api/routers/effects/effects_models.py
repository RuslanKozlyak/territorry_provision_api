from enum import Enum
from typing import Literal

from pydantic import BaseModel


class EffectType(Enum):
  TRANSPORT='Транспорт'
  PROVISION='Обеспеченность'

class ScaleType(Enum):
  PROJECT='Проект'
  CONTEXT='Контекст'

class ChartData(BaseModel):
  name : str
  before : float
  after : float
  delta : float