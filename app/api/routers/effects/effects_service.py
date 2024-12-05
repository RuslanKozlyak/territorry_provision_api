import os
import random
import geopandas as gpd
from blocksnet import BlocksGenerator, AccessibilityProcessor, Provision, City, Connectivity

from api.utils import const
from . import effects_models as em
from .services import blocksnet_service, project_service, service_type_service
from .services.blocksnet_service import *
from .services.project_service import *
from .services.project_service import *
from .services.project_service import _get_scenarios_by_project_id

PROVISION_COLUMNS = ['provision', 'demand', 'demand_within']

def _get_file_path(project_scenario_id : int, effect_type : em.EffectType, scale_type : em.ScaleType):
  file_path = f'{project_scenario_id}_{effect_type.name}_{scale_type.name}'
  return os.path.join(const.DATA_PATH, f'{file_path}.parquet')

def _fetch_city_model(region_id : int, project_scenario_id : int, token: str, scale : em.ScaleType):
  region_id = project_info['region_id']
  service_types = service_type_service.get_bn_service_types(region_id)
  physical_object_types = get_physical_object_types()
  scenario_gdf = get_scenario_gdf(project_scenario_id, token)
  
  boundaries = get_boundaries(scenario_gdf)
  water = get_water(scenario_gdf, physical_object_types)
  roads = get_roads(scenario_gdf, physical_object_types)
  buildings = get_buildings(scenario_gdf, physical_object_types)
  services = get_services(service_types, scenario_gdf)
  local_crs = 32636

  scenario_gdf.to_crs(local_crs, inplace=True)
  boundaries.to_crs(local_crs, inplace=True)
  water.to_crs(local_crs, inplace=True)
  roads.to_crs(local_crs, inplace=True)
  buildings.to_crs(local_crs, inplace=True)
  services.to_crs(local_crs, inplace=True)

  blocks_generator = BlocksGenerator(
      boundaries=boundaries,
      roads=roads,
      water=water
  )
  blocks = blocks_generator.run()
  blocks['land_use'] = 'residential'

  ap = AccessibilityProcessor(blocks=blocks)
  graph = roads_to_graph(roads)
  accessibility_matrix = ap.get_accessibility_matrix(graph=graph)

  city = City(
      blocks=blocks,
      acc_mx=accessibility_matrix,
  )
  city.update_buildings(buildings)

  for st in service_types:
      city.add_service_type(st)
      
  grouped = services.groupby('service_type_id')
  service_type_dict = {service.code: service for service in service_types}

  for service_type_code, sub_gdf in grouped:
      sub_gdf['geometry'] = sub_gdf.geometry.centroid
      service_type = service_type_dict.get(str(service_type_code), None)
      if service_type is not None:
          city.update_services(service_type, sub_gdf)
          
  return city

def _get_provision_data(project_scenario_id : int, scale_type : em.ScaleType) -> list[em.ChartData]:
  #TODO its a placeholder
  based_file_path = _get_file_path(project_scenario_id)
  file_path = _get_file_path(project_scenario_id)

  gdf_before = gpd.read_parquet(based_file_path)
  gdf_after = gpd.read_parquet(file_path)


  service_types = service_type_service.get_bn_service_types(1)
  results = []
  for st in service_types:
    name = st.name

    before = round(Provision.total(gdf_before[[f'{name}_provision']]),2)
    after = round(gdf_after[[f'{name}_provision']],2)
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

def get_transport_layer(project_scenario_id : int, scale_type : em.ScaleType, token : str):
  ... # TODO найти файл нужный и вернуть дельту в сравнении с базовым сценарием

def get_transport_data(project_scenario_id : int, scale_type : em.ScaleType, token : str):
  ... # TODO найти нужный файл и вернуть дельту как тут:
  # [
  #   {
  #     "name": "Среднее",
  #     "before": 44,
  #     "after": 36,
  #     "delta": -8
  #   },
  #   {
  #     "name": "Медиана",
  #     "before": 33,
  #     "after": 60,
  #     "delta": 27
  #   },
  #   {
  #     "name": "Мин",
  #     "before": 40,
  #     "after": 31,
  #     "delta": -9
  #   },
  #   {
  #     "name": "Макс",
  #     "before": 38,
  #     "after": 54,
  #     "delta": 16
  #   }
  # ]

def get_provision_layer(project_scenario_id : int, scale_type : em.ScaleType, service_type_id : int, token : str):
  ... # TODO найти файл нужный и вернуть дельту в сравнении с базовым сценарием

def get_provision_data(project_scenario_id : int, scale_type : em.ScaleType, token : str):
  ... # TODO найти нужный файл и вернуть дельту в сравнении с базовым сценарием
  # [
  #   {
  #     "name": "Школа",
  #     "before": 1,
  #     "after": 0,
  #     "delta": -1
  #   },
  #   ...
  # ]

def _evaluate_transport(project_scenario_id : int, city_model : City):
  logger.info('Evaluating transport')
  conn = Connectivity(city_model=city_model, verbose=False)
  conn_gdf = conn.calculate()
  file_path = _get_file_path(project_scenario_id, em.EffectType.PROVISION)
  conn_gdf.to_parquet(file_path)

def _evaluate_provision(project_scenario_id : int, city_model : City):
  logger.info('Evaluating provision')
  blocks_gdf = city_model.get_blocks_gdf()[['geometry']]

  for st in city_model.service_types:
    prov = Provision(city_model=city_model, verbose=False)
    prov_gdf = prov.calculate(st)
    for column in PROVISION_COLUMNS:
      blocks_gdf[f'{st.name}_{column}'] = prov_gdf[column]

  file_path = _get_file_path(project_scenario_id, em.EffectType.PROVISION)
  blocks_gdf.to_parquet(file_path)
  logger.success('Provision successfully evaluated!')

def evaluate_effects(project_scenario_id : int, token : str):
  # TODO проверяем, является ли этот сценарий базовым. 
  # Если не является, проверяем, посчитан ли у нас базовый и считаем его
  logger.info('Fetching project info')
  project_info = project_service.get_project_info(project_scenario_id, token)
  logger.info('Fetching region service types')
  service_types = service_type_service.get_bn_service_types(1)

  logger.info('Fetching city model')
  project_model = _fetch_city_model(project_info['region_id'], project_scenario_id, token, em.ScaleType.PROJECT)
  context_model = _fetch_city_model() # TODO boundaries заменить на context_geometry из project_info

  _evaluate_transport(project_scenario_id, project_model)
  _evaluate_provision(project_scenario_id, project_model)
  
  