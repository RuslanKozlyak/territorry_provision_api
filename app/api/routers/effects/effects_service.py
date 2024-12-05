import os
import random
import geopandas as gpd
from blocksnet import BlocksGenerator, AccessibilityProcessor, Provision, City

from app.api.utils import const
from . import effects_models as em
from .services import blocksnet_service, project_service, service_type_service
from .services.blocksnet_service import *
from .services.project_service import *
from .services.project_service import *
from .services.project_service import _get_scenarios_by_project_id


def _get_file_path(project_scenario_id : int, is_based: bool):
    file_path = f'{project_scenario_id}'
    if is_based:
      file_path += 'based'
    return os.path.join(const.DATA_PATH, f'{file_path}.parquet')

def _fetch_city_model(region_id : int, project_scenario_id : int, token: str, scale : em.ScaleType):
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
  based_file_path = _get_file_path(project_scenario_id, is_based=True)
  file_path = _get_file_path(project_scenario_id, is_based=False)

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
  # TODO назначение этой штуки в том чтоб чето сделать, сохранить локально гдфки и записать тэп в БД
  project_info = project_service.get_project_info(project_scenario_id, token)
  service_types = service_type_service.get_bn_service_types(1)

  scenarios = _get_scenarios_by_project_id(project_info['project_id'], token)
  based_scenario = list(filter(lambda x: x['is_based'], scenarios))[0]['scenario_id']

  city_before = _fetch_city_model(project_info['region_id'], based_scenario, token, 1)
  city_after = _fetch_city_model(project_info['region_id'], project_scenario_id, token, 1)
  gdf_before = city_before.get_blocks_gdf()[['geometry']]
  gdf_after = city_after.get_blocks_gdf()[['geometry']]

  for st in service_types:
    prov = Provision(city_model=city_before)
    prov_before = prov.calculate(st)

    prov = Provision(city_model=city_after)
    prov_after = prov.calculate(st)

    gdf_before[f'{st.name}_provision'] = prov_before['provision']
    gdf_after[f'{st.name}_provision'] = prov_after['provision']

  based_file_path = _get_file_path(project_scenario_id, is_based=True)
  file_path = _get_file_path(project_scenario_id, is_based=False)
  gdf_before.to_parquet(based_file_path)
  gdf_after.to_parquete(file_path)
  
  