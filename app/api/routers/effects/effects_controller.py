import os
from loguru import logger
from uuid import uuid4
from blocksnet.models import ServiceType
from fastapi import APIRouter, BackgroundTasks, Depends
from ...utils import auth, const, decorators
from . import effects_models as em
from . import effects_service as es
from .services import service_type_service as sts

router = APIRouter(prefix='/effects', tags=['Effects'])

def on_startup(): # TODO оценка базовых сценариев
    if not os.path.exists(const.DATA_PATH):
        logger.info(f'Creating data folder at {const.DATA_PATH}')
        os.mkdir(const.DATA_PATH)

tasks = {}

@router.get('/service_types')
def get_service_types(region_id: int) -> list[ServiceType]:
    return sts.get_bn_service_types(region_id)

@router.get('/provision_layer')
@decorators.gdf_to_geojson
def get_provision_layer(project_scenario_id: int, scale_type: em.ScaleType, service_type_id: int,
                        token: str = Depends(auth.verify_token)):
    return es.get_provision_layer(project_scenario_id, scale_type, service_type_id, token)

@router.get('/provision_data')
def get_provision_data(project_scenario_id: int, scale_type: em.ScaleType, token: str = Depends(auth.verify_token)):
    return es.get_provision_data(project_scenario_id, scale_type, token)

@router.get('/transport_layer')
@decorators.gdf_to_geojson
def get_transport_layer(project_scenario_id: int, scale_type: em.ScaleType, token: str = Depends(auth.verify_token)):
    return es.get_transport_layer(project_scenario_id, scale_type, token)

@router.get('/transport_data')
def get_transport_data(project_scenario_id: int, scale_type: em.ScaleType, token: str = Depends(auth.verify_token)):
    return es.get_transport_data(project_scenario_id, scale_type, token)

def _evaluate_effects_task(task_id : str, *args, **kwargs):
    tasks[task_id] = 'pending'
    try:
        es.evaluate_effects(*args, **kwargs)
        tasks[task_id] = 'success'
    except:
        tasks[task_id] = 'error'

@router.get('/connectivity_layer')
@decorators.gdf_to_geojson
def get_transport_layer(project_scenario_id: int, scale_type: em.ScaleType, token: str = Depends(auth.verify_token)):
    return es.get_connectivity_layer(project_scenario_id, scale_type, token)

@router.get('/connectivity_data')
def get_transport_data(project_scenario_id: int, scale_type: em.ScaleType, token: str = Depends(auth.verify_token)):
    return es.get_connectivity_data(project_scenario_id, scale_type, token)

def _evaluate_effects_task(task_id : str, *args, **kwargs):
    tasks[task_id] = 'pending'
    try:
        es.evaluate_effects(*args, **kwargs)
        tasks[task_id] = 'success'
    except Exception as e:
        logger.error(e)
        tasks[task_id] = 'error'

@router.post('/evaluate')
def evaluate(background_tasks: BackgroundTasks, project_scenario_id: int, token: str = Depends(auth.verify_token)):
    task_id = str(uuid4())
    background_tasks.add_task(_evaluate_effects_task, task_id, project_scenario_id, token)
    return {'task_id' : task_id }

@router.delete('/evaluation')
def delete_evaluation(project_scenario_id : int):
    try:
        es.delete_evaluation(project_scenario_id)
        return 'oke'
    except:
        return 'oops'