import os
import random
import geopandas as gpd
from api.utils import const
from . import effects_models as em
from .services import blocksnet_service, project_service, service_type_service

def _get_file_path(project_scenario_id : int):
    file_path = f'{project_scenario_id}'
    return os.path.join(const.DATA_PATH, f'{file_path}.parquet')

def _fetch_city_model(region_id : int, project_scenario_id : int, scale : em.ScaleType):
  service_types = service_type_service.get_bn_service_types(region_id)
  ...

def _get_provision_data(project_scenario_id : int, scale_type : em.ScaleType) -> list[em.ChartData]:
  #TODO its a placeholder
  service_types = service_type_service.get_bn_service_types(1)
  results = []
  for st in service_types:
    name = st.name
    before = round(random.random(),2)
    after = round(random.random(),2)
    delta = round(after - before,2)
    results.append({
      'name': name,
      'before': before,
      'after': after,
      'delta': delta
    })
  return results

def _get_transport_data(project_scenario_id : int, scale_Type : em.ScaleType) -> list[em.ChartData]:
  #TODO its a placeholder
  results = []
  for name in ['Среднее', 'Медиана', 'Мин', 'Макс']:
    before = random.randint(30,60)
    after = random.randint(30,60)
    delta = after - before
    results.append({
      'name': name,
      'before': before,
      'after': after,
      'delta': delta
    })
  return results

def get_data(project_scenario_id : int, scale_type : em.ScaleType, effect_type : em.EffectType) -> list[em.ChartData]:
  if effect_type == em.EffectType.PROVISION:
    return _get_provision_data(project_scenario_id, scale_type)
  return _get_transport_data(project_scenario_id, scale_type)

# def _gridify(gdf): # TODO remove


# def _get_provision_layer(project_gdf): # TODO неправильный вход 
#   service_types = service_type_service.get_bn_service_types(1)


# def _get_transport_layer(project_gdf): # TODO неправильный вход
#   ...

# def get_layer(project_scenario_id : int, scale_type : em.ScaleType, effect_type : em.EffectType, token : str) -> gpd.GeoDataFrame:
#   # TODO placeholder
#   project_info = project_service.get_project_info(project_scenario_id, token)
#   project_geometry = project_info['geometry']
#   project_gdf = gpd.GeoDataFrame(geometry=[project_geometry], crs=const.DEFAULT_CRS)
#   local_crs = project_gdf.estimate_utm_crs()
#   project_gdf = project_gdf.to_crs(local_crs)
#   if scale_type == em.ScaleType.CONTEXT:
#     project_gdf.geometry = project_gdf.buffer(3_000) # TODO placeholder
#   if effect_type == em.EffectType.PROVISION:
#     return _get_provision_layer(project_gdf)
#   return _get_transport_layer(project_gdf)

def evaluate_effects(project_scenario_id : int, token : str):
  project_info = project_service.get_project_info(project_scenario_id, token)
  ... # TODO назначение этой штуки в том чтоб чето сделать, сохранить локально гдфки и записать тэп в БД