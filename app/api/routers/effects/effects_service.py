import os
import random
import requests
import shapely
import json
import pandas as pd
import geopandas as gpd
from blocksnet.models import ServiceType
from api.utils import const
from . import effects_models as em

def _get_file_path(project_scenario_id : int):
    file_path = f'{project_scenario_id}'
    return os.path.join(const.DATA_PATH, f'{file_path}.parquet')

def _get_service_types(region_id : int) -> pd.DataFrame:
  res = requests.get(const.URBAN_API + f'/api/v1/territory/{region_id}/service_types')
  res.raise_for_status()
  df = pd.DataFrame(res.json())
  return df.set_index('service_type_id')

def _get_normatives(region_id : int) -> pd.DataFrame:
  res = requests.get(const.URBAN_API + f'/api/v1/territory/{region_id}/normatives')
  res.raise_for_status()
  df = pd.DataFrame(res.json())
  df['service_type_id'] = df['service_type'].apply(lambda st : st['id'])
  return df.set_index('service_type_id')

def _get_bn_service_types(region_id : int) -> list[ServiceType]:
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

def _fetch_city_model(region_id : int, project_scenario_id : int, scale : em.ScaleType):
  service_types = _get_bn_service_types(region_id)
  ...

def _get_provision_data(project_scenario_id : int, scale_type : em.ScaleType) -> list[em.ChartData]:
  #TODO its a placeholder
  service_types = _get_bn_service_types(1)
  results = []
  for st in service_types:
    x = st.name
    before = round(random.random(),2)
    after = round(random.random(),2)
    delta = round(after - before,2)
    for y, value in {'before': before, 'after': after, 'delta': delta}.items():
      results.append({'x' : x, 'y' : y, 'value' : value})
  return results

def _get_transport_data(project_scenario_id : int, scale_Type : em.ScaleType) -> list[em.ChartData]:
  #TODO its a placeholder
  results = []
  for x in ['Среднее', 'Медиана', 'Мин', 'Макс']:
    before = random.randint(30,60)
    after = random.randint(30,60)
    delta = after - before
    for y, value in {'before': before, 'after': after, 'delta': delta}.items():
      results.append({'x' : x, 'y' : y, 'value' : value})
  return results

def get_data(project_scenario_id : int, scale_type : em.ScaleType, effect_type : em.EffectType) -> list[em.ChartData]:
  if effect_type == em.EffectType.PROVISION:
    return _get_provision_data(project_scenario_id, scale_type)
  return _get_transport_data(project_scenario_id, scale_type)

def _get_scenario_by_id(scenario_id : int, token : str) -> dict:
  res = requests.get(const.URBAN_API + f'/api/v1/scenarios/{scenario_id}', headers={'Authorization': f'Bearer {token}'})
  res.raise_for_status()
  return res.json()

def _get_project_by_id(project_id : int, token : str) -> dict:
  res = requests.get(const.URBAN_API + f'/api/v1/projects/{project_id}/territory', headers={'Authorization': f'Bearer {token}'})
  res.raise_for_status()
  return res.json()

def _fetch_project_geometry(project_scenario_id : int, token : str) -> shapely.BaseGeometry:
  """
  Fetch project geometry (not context tho)
  """
  project_id = _get_scenario_by_id(project_scenario_id, token)['project']['project_id']
  project_info = _get_project_by_id(project_id, token)
  geometry_json = json.dumps(project_info['geometry'])
  return shapely.from_geojson(geometry_json)

def get_layer(project_scenario_id : int, scale_type : em.ScaleType, effect_type : em.EffectType) -> gpd.GeoDataFrame:
  ...

def evaluate_effects(region_id : int, project_scenario_id : int, token : str):
  ... # TODO назначение этой штуки в том чтоб чето сделать, сохранить локально гдфки и записать тэп в БД