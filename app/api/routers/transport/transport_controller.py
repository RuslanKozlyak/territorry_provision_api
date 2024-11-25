from fastapi import APIRouter, Depends, BackgroundTasks
from api.utils.auth import verify_token
from api.utils.const import EVALUATION_RESPONSE_MESSAGE
from api.utils.decorators import gdf_to_geojson
from . import transport_service as ts

router = APIRouter(prefix='/transport', tags=['Transport effects'])

@router.get('/layer')
def get_transport_layer(project_scenario_id : int):
  return ts.get_layer(project_scenario_id)

@router.get('/data')
def get_transport_data(project_scenario_id : int):
  return ts.get_data(project_scenario_id)

@router.post('/evaluate')
def evaluate_transport(background_tasks : BackgroundTasks, region_id : int, project_scenario_id : int, token : str = Depends(verify_token)):
  background_tasks.add_task(ts.evaluate_effects, region_id, project_scenario_id, token)
  return EVALUATION_RESPONSE_MESSAGE
