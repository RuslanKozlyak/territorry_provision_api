from fastapi import APIRouter, Depends, BackgroundTasks
from api.utils import auth, const, decorators
from blocksnet.models import ServiceType
from . import effects_service as es, effects_models as em

router = APIRouter(prefix='/effects', tags=['Effects'])

@router.get('/scale_type')
def get_scale_type() -> list[str]:
  return list(em.ScaleType)

@router.get('/effect_type')
def get_effect_type() -> list[str]:
  return list(em.EffectType)

@router.get('/service_types')
def get_service_types(region_id : int) -> list[ServiceType]:
  return es._get_bn_service_types(region_id)

@router.get('/layer')
@decorators.gdf_to_geojson
def get_spatial_layer(project_scenario_id : int, scale_type : em.ScaleType, effect_type : em.EffectType):
  return es.get_layer(project_scenario_id, scale_type, effect_type)

@router.get('/data')
def get_chart_data(project_scenario_id : int, scale_type : em.ScaleType, effect_type : em.EffectType) -> list[em.ChartData]:
  return es.get_data(project_scenario_id, scale_type, effect_type)

@router.post('/evaluate')
def evaluate(background_tasks : BackgroundTasks, region_id : int, project_scenario_id : int, token : str = Depends(auth.verify_token)):
  background_tasks.add_task(es.evaluate_effects, region_id, project_scenario_id, token)
  return const.EVALUATION_RESPONSE_MESSAGE
