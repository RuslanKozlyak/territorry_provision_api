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
  x : str
  y : Literal['before', 'after', 'delta']
  value : float