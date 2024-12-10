import os
import random
import geopandas as gpd
import warnings
import pandas as pd
import numpy as np
from urllib3.exceptions import InsecureRequestWarning
from loguru import logger
from shapely import intersection
from blocksnet import (City, WeightedConnectivity, Connectivity, Provision)
from ...utils import const
from . import effects_models as em
from .services import blocksnet_service as bs, project_service as ps, service_type_service as sts

for warning in [pd.errors.PerformanceWarning, RuntimeWarning, pd.errors.SettingWithCopyWarning, InsecureRequestWarning]:
    warnings.filterwarnings(action='ignore', category=warning)

PROVISION_COLUMNS = ['provision', 'demand', 'demand_within']

def _get_file_path(project_scenario_id: int, effect_type: em.EffectType, scale_type: em.ScaleType):
    file_path = f'{project_scenario_id}_{effect_type.name}_{scale_type.name}'
    return os.path.join(const.DATA_PATH, f'{file_path}.parquet')

def _get_total_provision(gdf_orig, name):
    gdf = gdf_orig.copy()

    for column in PROVISION_COLUMNS:
        new_column = column.replace(f'{name}_', '')
        gdf = gdf.rename(columns={f'{name}_{column}': new_column})

    return round(Provision.total(gdf), 2)

def _sjoin_gdfs(gdf_before : gpd.GeoDataFrame, gdf_after : gpd.GeoDataFrame):
    gdf_before = gdf_before.to_crs(gdf_after.crs)
    # set i to identify intersections
    gdf_before['i'] = gdf_before.index
    gdf_after['i'] = gdf_after.index
    gdf_sjoin = gdf_after.sjoin(gdf_before, how='left', predicate='intersects', lsuffix='after', rsuffix='before')
    # filter nans
    gdf_sjoin = gdf_sjoin[~gdf_sjoin['i_before'].isna()]
    gdf_sjoin = gdf_sjoin[~gdf_sjoin['i_after'].isna()]
    # get intersections area and keep largest
    gdf_sjoin['area'] = gdf_sjoin.apply(lambda s : gdf_before.loc[s['i_before'], 'geometry'].intersection(gdf_after.loc[s['i_after'], 'geometry']).area, axis=1)
    gdf_sjoin = gdf_sjoin.sort_values(by='area')
    return gdf_sjoin.drop_duplicates(subset=['i_after'], keep='last')

def get_transport_layer(project_scenario_id: int, scale_type: em.ScaleType, token: str):
    project_info = ps.get_project_info(project_scenario_id, token)
    based_scenario_id = ps.get_based_scenario_id(project_info, token)

    # get both files
    before_file_path = _get_file_path(based_scenario_id, em.EffectType.TRANSPORT, scale_type)
    after_file_path = _get_file_path(project_scenario_id, em.EffectType.TRANSPORT, scale_type)

    gdf_before = gpd.read_parquet(before_file_path)
    gdf_after = gpd.read_parquet(after_file_path)

    # calculate delta
    gdf_delta = _sjoin_gdfs(gdf_before, gdf_after)
    gdf_delta = gdf_delta.rename(columns={
        'weighted_connectivity_before': 'before',
        'weighted_connectivity_after': 'after'
    })[['geometry', 'before', 'after']]
    gdf_delta['delta'] = gdf_delta['after'] - gdf_delta['before']

    # round digits
    for column in ['before', 'after', 'delta']:
        gdf_delta[column] = gdf_delta[column].apply(round)

    return gdf_delta

def get_transport_data(project_scenario_id: int, scale_type: em.ScaleType, token: str):
    project_info = ps.get_project_info(project_scenario_id, token)
    based_scenario_id = ps.get_based_scenario_id(project_info, token)

    # get both files
    before_file_path = _get_file_path(based_scenario_id, em.EffectType.TRANSPORT, scale_type)
    after_file_path = _get_file_path(project_scenario_id, em.EffectType.TRANSPORT, scale_type)

    gdf_before = gpd.read_parquet(before_file_path)
    gdf_after = gpd.read_parquet(after_file_path)

    # calculate chart data
    names_funcs = {
        'Среднее': np.mean,
        'Медиана': np.median,
        'Мин': np.min,
        'Макс': np.max
    }

    items = []
    for name, func in names_funcs.items():
        before = func(gdf_before['weighted_connectivity'])
        after = func(gdf_after['weighted_connectivity'])
        delta = after - before
        items.append({
            'name': name,
            'before': round(before),
            'after': round(after),
            'delta': round(delta)
        })
    return items

def get_provision_layer(project_scenario_id: int, scale_type: em.ScaleType, service_type_id: int, token: str):
    project_info = ps.get_project_info(project_scenario_id, token)
    based_scenario_id = ps.get_based_scenario_id(project_info, token)

    service_types = sts.get_bn_service_types(project_info['region_id'])
    service_type = list(filter(lambda x: x.code == str(service_type_id), service_types))[0]

    before_file_path = _get_file_path(based_scenario_id, em.EffectType.PROVISION, scale_type)
    after_file_path = _get_file_path(project_scenario_id, em.EffectType.PROVISION, scale_type)

    gdf_before = gpd.read_parquet(before_file_path)
    gdf_after = gpd.read_parquet(after_file_path)

    provision_column = f'{service_type.name}_provision'

    # calculate delta
    gdf_delta = _sjoin_gdfs(gdf_before, gdf_after)
    gdf_delta = gdf_delta.rename(columns={
        f'{provision_column}_before': 'before',
        f'{provision_column}_after': 'after'
    })[['geometry', 'before', 'after']]
    gdf_delta['delta'] = gdf_delta['after'] - gdf_delta['before']

    for column in ['before', 'after', 'delta']:
        gdf_delta[column] = gdf_delta[column].apply(lambda v : round(v,2))

    return gdf_delta


def get_provision_data(project_scenario_id: int, scale_type: em.ScaleType, token: str) -> list[em.ChartData]:
    project_info = ps.get_project_info(project_scenario_id, token)
    based_scenario_id = ps.get_based_scenario_id(project_info, token)

    before_file_path = _get_file_path(based_scenario_id, em.EffectType.PROVISION, scale_type)
    after_file_path = _get_file_path(project_scenario_id, em.EffectType.PROVISION, scale_type)

    gdf_before = gpd.read_parquet(before_file_path)
    gdf_after = gpd.read_parquet(after_file_path)

    service_types = sts.get_bn_service_types(project_info['region_id'])
    results = []
    for st in service_types:
        name = st.name

        before = _get_total_provision(gdf_before, name)
        after = _get_total_provision(gdf_after, name)
        delta = after - before

        results.append({
            'name': name,
            'before': round(before,2),
            'after': round(after,2),
            'delta': round(delta,2)
        })
    return results

def _evaluate_transport(project_scenario_id: int, city_model: City, scale: em.ScaleType):
    logger.info('Evaluating transport')
    conn = WeightedConnectivity(city_model=city_model, verbose=False)
    # conn = Connectivity(city_model=city_model, verbose=False)
    conn_gdf = conn.calculate()
    file_path = _get_file_path(project_scenario_id, em.EffectType.TRANSPORT, scale)
    conn_gdf.to_parquet(file_path)
    logger.success('Transport successfully evaluated!')


def _evaluate_provision(project_scenario_id: int, city_model: City, scale: em.ScaleType):
    logger.info('Evaluating provision')
    blocks_gdf = city_model.get_blocks_gdf()[['geometry']]

    for st in city_model.service_types:
        prov = Provision(city_model=city_model, verbose=False)
        prov_gdf = prov.calculate(st)
        for column in PROVISION_COLUMNS:
            blocks_gdf[f'{st.name}_{column}'] = prov_gdf[column]

    file_path = _get_file_path(project_scenario_id, em.EffectType.PROVISION, scale)
    blocks_gdf.to_parquet(file_path)
    logger.success('Provision successfully evaluated!')

def _evaluation_exists(project_scenario_id : int, token : str):
    exists = True
    for effect_type in list(em.EffectType):
        for scale_type in list(em.ScaleType):
            file_path = _get_file_path(project_scenario_id, effect_type, scale_type)
            if not os.path.exists(file_path):
                exists = False
    return exists

def evaluate_effects(project_scenario_id: int, token: str, reevaluate : bool = True):
    logger.info(f'Fetching {project_scenario_id} project info')
    
    project_info = ps.get_project_info(project_scenario_id, token)
    based_scenario_id = ps.get_based_scenario_id(project_info, token)
    # if scenario isnt based, evaluate the based scenario
    if project_scenario_id != based_scenario_id:
        evaluate_effects(based_scenario_id, token, reevaluate=False)
    
    # if scenario exists and doesnt require reevaluation, we return
    exists = _evaluation_exists(project_scenario_id, token)
    if exists and not reevaluate:
        logger.info(f'{project_scenario_id} evaluation already exists')
        return
    
    logger.info('Fetching region service types')
    service_types = sts.get_bn_service_types(project_info['region_id'])
    logger.info('Fetching physical object types')
    physical_object_types = ps.get_physical_object_types()
    logger.info('Fetching scenario objects')
    scenario_gdf = ps.get_scenario_objects(project_scenario_id, token)

    logger.info('Fetching project model')
    project_model = bs.fetch_city_model(project_info=project_info,
                                      service_types=service_types,
                                      physical_object_types=physical_object_types,
                                      scenario_gdf=scenario_gdf,
                                      scale=em.ScaleType.PROJECT)

    logger.info('Fetching context model')
    context_model = bs.fetch_city_model(project_info=project_info,
                                      service_types=service_types,
                                      physical_object_types=physical_object_types,
                                      scenario_gdf=scenario_gdf,
                                      scale=em.ScaleType.CONTEXT)
    
    _evaluate_transport(project_scenario_id, project_model, em.ScaleType.PROJECT)
    _evaluate_provision(project_scenario_id, project_model, em.ScaleType.PROJECT)

    _evaluate_transport(project_scenario_id, context_model, em.ScaleType.CONTEXT)
    _evaluate_provision(project_scenario_id, context_model, em.ScaleType.CONTEXT)

    logger.success(f'{project_scenario_id} evaluated successfully')
