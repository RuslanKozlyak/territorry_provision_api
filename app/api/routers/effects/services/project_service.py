import requests
import shapely
import json
from loguru import logger
from api.utils.const import URBAN_API

def _get_scenario_by_id(scenario_id : int, token : str) -> dict:
  res = requests.get(URBAN_API + f'/api/v1/scenarios/{scenario_id}', headers={'Authorization': f'Bearer {token}'})
  res.raise_for_status()
  return res.json()

def _get_project_territory_by_id(project_id : int, token : str) -> dict:
  res = requests.get(URBAN_API + f'/api/v1/projects/{project_id}/territory', headers={'Authorization': f'Bearer {token}'})
  res.raise_for_status()
  return res.json()

def _get_project_by_id(project_id : int, token : str) -> dict:
  res = requests.get(URBAN_API + f'/api/v1/projects/{project_id}', headers={'Authorization': f'Bearer {token}'})
  res.raise_for_status()
  return res.json()

def _get_territory_by_id(territory_id : int) -> dict:
  res = requests.get(URBAN_API + f'/api/v1/territory/{territory_id}')
  res.raise_for_status()
  return res.json()

def _get_context_geometry(territories_ids : list[int]):
  geometries = []
  for territory_id in territories_ids:
    territory = _get_territory_by_id(territory_id)
    geom_json = json.dumps(territory['geometry']) 
    geometry = shapely.from_geojson(geom_json)
    geometries.append(geometry)
  return shapely.unary_union(geometries)

def get_project_info(project_scenario_id : int, token : str) -> dict:
  """
  Fetch project data
  """
  scenario_info = _get_scenario_by_id(project_scenario_id, token)
  is_based = scenario_info['is_based'] # является ли сценарий базовым для проекта
  project_id = scenario_info['project']['project_id']

  project_info = _get_project_by_id(project_id, token)
  context_ids = project_info['properties']['context']

  project_territory = _get_project_territory_by_id(project_id, token)
  region_id = project_territory['project']['region']['id']
  project_geometry = json.dumps(project_territory['geometry'])

  return {
    'project_id' : project_id,
    'region_id': region_id,
    'is_based': is_based,
    'geometry': shapely.from_geojson(project_geometry),
    'context': _get_context_geometry(context_ids)
  }