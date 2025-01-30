
import pandas as pd
import requests
from api.utils import const
from blocksnet.models import ServiceType

def _get_service_types(region_id : int) -> pd.DataFrame:
  res = requests.get(const.URBAN_API + f'/api/v1/territory/{region_id}/service_types')
  res.raise_for_status()
  df = pd.DataFrame(res.json())
  return df.set_index('service_type_id')

def _get_normatives(region_id : int) -> pd.DataFrame:
  res = requests.get(const.URBAN_API + f'/api/v1/territory/{region_id}/normatives', params={'year': const.NORMATIVES_YEAR})
  res.raise_for_status()
  df = pd.DataFrame(res.json())
  df['service_type_id'] = df['service_type'].apply(lambda st : st['id'])
  return df.set_index('service_type_id')

def get_bn_service_types(region_id : int) -> list[ServiceType]:
  """
  Befriend normatives and service types into BlocksNet format
  """
  db_service_types_df = _get_service_types(region_id)
  db_normatives_df = _get_normatives(region_id)
  service_types_df = db_service_types_df.merge(db_normatives_df, left_index=True, right_index=True)
  # filter by minutes not null
  service_types_df = service_types_df[~service_types_df['time_availability_minutes'].isna()]
  # filter by capacity not null
  service_types_df = service_types_df[~service_types_df['services_capacity_per_1000_normative'].isna()]
  
  service_types = []
  for _, row in service_types_df.iterrows():
    service_type = ServiceType(
      code=row['code'], 
      name=row['name'], 
      accessibility=row['time_availability_minutes'],
      demand=row['services_capacity_per_1000_normative'],
      land_use = [], #TODO
      bricks = [] #TODO
    )
    service_types.append(service_type)
  return service_types