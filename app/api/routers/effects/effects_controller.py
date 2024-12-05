from fastapi import APIRouter, Depends, BackgroundTasks

from blocksnet.models import ServiceType
from . import effects_service as es, effects_models as em
from .services import service_type_service as sts
from ...utils import auth, decorators, const

router = APIRouter(prefix='/effects', tags=['Effects'])

@router.get('/scale_type')
def get_scale_type() -> list[str]:
  return list(em.ScaleType)

@router.get('/effect_type')
def get_effect_type() -> list[str]:
  return list(em.EffectType)

@router.get('/service_types')
def get_service_types(region_id : int) -> list[ServiceType]:
  return sts.get_bn_service_types(region_id)

@router.get('/transport_layer')
@decorators.gdf_to_geojson
def get_transport_layer(project_scenario_id : int, scale_type : em.ScaleType, token : str = Depends(auth.verify_token)):
  return es.get_transport_layer(project_scenario_id, scale_type, token)

@router.get('/provision_layer')
@decorators.gdf_to_geojson
def get_provision_layer(project_scenario_id : int, scale_type : em.ScaleType, service_type_id : int, token : str = Depends(auth.verify_token)):
  return es.get_provision_layer(project_scenario_id, scale_type, service_type_id, token)

@router.get('/transport_data')
@decorators.gdf_to_geojson
def get_transport_data():
  ...

@router.get('/provision_data')
@decorators.gdf_to_geojson
def get_provision_data():
  ...

@router.get('/data')
def get_chart_data(project_scenario_id : int, scale_type : em.ScaleType, effect_type : em.EffectType) -> list[em.ChartData]:
  return es.get_data(project_scenario_id, scale_type, effect_type)

@router.post('/evaluate')
def evaluate(background_tasks : BackgroundTasks, project_scenario_id : int, token : str = Depends(auth.verify_token)):
  background_tasks.add_task(es.evaluate_effects, project_scenario_id, token)
  return const.EVALUATION_RESPONSE_MESSAGE
