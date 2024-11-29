from enum import Enum
from pydantic import BaseModel
from typing import Literal

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