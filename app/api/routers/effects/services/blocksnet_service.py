import geopandas as gpd
import pandas as pd
import momepy
import networkx as nx
from loguru import logger
from pyproj.crs import CRS
from blocksnet import (AccessibilityProcessor, BlocksGenerator, City, ServiceType)
from api.utils.const import DEFAULT_CRS
from . import project_service as ps
from .. import effects_models as em

SPEED_M_MIN = 60 * 1000 / 60
GAP_TOLERANCE = 5

def _get_geoms_by_function(function_name, physical_object_types, scenario_gdf):
    valid_type_ids = {
        d['physical_object_type_id']
        for d in physical_object_types
        if function_name in d['physical_object_function']['name']
    }
    return scenario_gdf[scenario_gdf['physical_objects'].apply(
        lambda x: any(d.get('physical_object_type').get('id') in valid_type_ids for d in x))]

def _get_water(scenario_gdf, physical_object_types):
    water = _get_geoms_by_function('Водный объект', physical_object_types, scenario_gdf)
    water = water.explode(index_parts=True)
    water = water.reset_index()
    return water


def _get_roads(scenario_gdf, physical_object_types):
    roads = _get_geoms_by_function('Дорога', physical_object_types, scenario_gdf)
    merged = roads.unary_union
    if merged.geom_type == 'MultiLineString':
        roads = gpd.GeoDataFrame(geometry=list(merged.geoms), crs=roads.crs)
    else:
        roads = gpd.GeoDataFrame(geometry=[merged], crs=roads.crs)
    roads = roads.explode(index_parts=False).reset_index(drop=True)
    roads.geometry = momepy.close_gaps(roads, GAP_TOLERANCE)
    roads = roads[roads.geom_type.isin(['LineString'])]
    return roads

def _get_geoms_by_object_type_id(scenario_gdf, object_type_id):
    return scenario_gdf[scenario_gdf['physical_objects'].apply(lambda x: any(d.get('physical_object_type').get('id') == object_type_id for d in x))]

def _get_buildings(scenario_gdf, physical_object_types):
    LIVING_BUILDINGS_ID = 4
    NON_LIVING_BUILDINGS_ID = 5
    living_building = _get_geoms_by_object_type_id(scenario_gdf, LIVING_BUILDINGS_ID)
    living_building['is_living'] = True
    # print(living_building)
    non_living_buildings = _get_geoms_by_object_type_id(scenario_gdf, NON_LIVING_BUILDINGS_ID)
    non_living_buildings['is_living'] = False

    buildings = gpd.GeoDataFrame( pd.concat( [living_building, non_living_buildings], ignore_index=True) )
    # print(buildings)
    # buildings = _get_geoms_by_function('Здание', physical_object_types, scenario_gdf)
    buildings['number_of_floors'] = 1
    # buildings['is_living'] = True
    buildings['footprint_area'] = buildings.geometry.area
    buildings['build_floor_area'] = buildings['footprint_area'] * buildings['number_of_floors']
    buildings['living_area'] = buildings.geometry.area
    buildings['population'] = 0
    buildings['population'][buildings['is_living']] = 100
    buildings = buildings.reset_index()
    buildings = buildings[buildings.geometry.type != 'Point']
    return buildings[['geometry', 'number_of_floors', 'footprint_area', 'build_floor_area', 'living_area', 'population']]


def _get_services(scenario_gdf) -> gpd.GeoDataFrame | None:

    def extract_services(row):
        if isinstance(row['services'], list) and len(row['services']) > 0:
            return [
                {
                    'service_id': service['service_id'],
                    'service_type_id': service['service_type']['id'],
                    'name': service['name'],
                    'capacity_real': service['capacity_real'],
                    'geometry': row['geometry']  # Сохраняем геометрию
                }
                for service in row['services']
                if service.get('capacity_real') is not None and service['capacity_real'] > 0
            ]
        return []

    extracted_data = []
    for _, row in scenario_gdf.iterrows():
        extracted_data.extend(extract_services(row))

    if len(extracted_data) == 0:
        return None

    services_gdf = gpd.GeoDataFrame(extracted_data, crs=scenario_gdf.crs)

    services_gdf['capacity'] = services_gdf['capacity_real']
    services_gdf = services_gdf[['geometry', 'service_id', 'service_type_id', 'name', 'capacity']]

    services_gdf['area'] = services_gdf.geometry.area
    services_gdf['area'] = services_gdf['area'].apply(lambda a : a if a > 1 else 1)
    # services_gdf.loc[services_gdf.area == 0, 'area'] = 100
    # services_gdf['area'] = services_gdf

    return services_gdf


def _roads_to_graph(roads):
    roads.to_parquet(f'roads_{len(roads)}.parquet')
    graph = momepy.gdf_to_nx(roads)
    graph.graph['crs'] = CRS.to_epsg(roads.crs)
    graph = nx.DiGraph(graph)
    for _, _, data in graph.edges(data=True):
        geometry = data['geometry']
        data['time_min'] = geometry.length / SPEED_M_MIN
        # data['weight'] = data['mm_len'] / 1000 / 1000
        # data['length_meter'] = data['mm_len'] / 1000
    for n, data in graph.nodes(data=True):
        graph.nodes[n]['x'] = n[0]  # Assign X coordinate to node
        graph.nodes[n]['y'] = n[1]

    return graph

def _get_boundaries(project_info : dict, scale : em.ScaleType) -> gpd.GeoDataFrame:
    if scale == em.ScaleType.PROJECT:
        boundaries = gpd.GeoDataFrame(geometry=[project_info['geometry']])
    else:
        boundaries = gpd.GeoDataFrame(geometry=[project_info['context']])
    boundaries = boundaries.set_crs(DEFAULT_CRS)
    local_crs = boundaries.estimate_utm_crs()
    return boundaries.to_crs(local_crs)

def _generate_blocks(boundaries_gdf : gpd.GeoDataFrame, roads_gdf : gpd.GeoDataFrame, scenario_gdf : gpd.GeoDataFrame, physical_object_types : dict) -> gpd.GeoDataFrame:
    water_gdf = _get_water(scenario_gdf, physical_object_types).to_crs(boundaries_gdf.crs)

    blocks_generator = BlocksGenerator(
        boundaries=boundaries_gdf,
        roads=roads_gdf if len(roads_gdf)>0 else None,
        water=water_gdf if len(water_gdf)>0 else None
    )
    blocks = blocks_generator.run()
    blocks['land_use'] = None  # TODO ЗАмнить на норм land_use?? >> здесь должен быть этап определения лендюза по тому что есть в бд
    return blocks

def _calculate_acc_mx(blocks_gdf : gpd.GeoDataFrame, roads_gdf : gpd.GeoDataFrame) -> pd.DataFrame:
    accessibility_processor = AccessibilityProcessor(blocks=blocks_gdf)
    graph = _roads_to_graph(roads_gdf)
    accessibility_matrix = accessibility_processor.get_accessibility_matrix(graph=graph)
    return accessibility_matrix

def _update_buildings(city : City, scenario_gdf : gpd.GeoDataFrame, physical_object_types : dict) -> None:
    buildings_gdf = _get_buildings(scenario_gdf, physical_object_types).copy().to_crs(city.crs)
    buildings_gdf = buildings_gdf[buildings_gdf.geom_type.isin(['Polygon', 'MultiPolygon'])]
    city.update_buildings(buildings_gdf)

def _update_services(city : City, service_types : list[ServiceType], scenario_gdf : gpd.GeoDataFrame) -> None:
    # reset service types
    city._service_types = {}
    for st in service_types:
        city.add_service_type(st)
    # filter services and add to the model if exist
    services_gdf = _get_services(scenario_gdf)
    if services_gdf is None:
        return
    services_gdf = services_gdf.to_crs(city.crs).copy()
    service_type_dict = {service.code: service for service in service_types}
    for service_type_code, st_gdf in services_gdf.groupby('service_type_id'):
        gdf = st_gdf.copy().to_crs(city.crs)
        gdf.geometry = gdf.representative_point()
        service_type = service_type_dict.get(str(service_type_code), None)
        if service_type is not None:
            city.update_services(service_type, gdf)

def fetch_city_model(project_info: dict,
                      scenario_gdf: gpd.GeoDataFrame,
                      physical_object_types: dict,
                      service_types: list,
                      scale: em.ScaleType):
    
    # getting boundaries for our model
    boundaries_gdf = _get_boundaries(project_info, scale)
    local_crs = boundaries_gdf.crs

    # clipping scenario objects
    scenario_gdf = scenario_gdf.to_crs(local_crs)
    scenario_gdf = scenario_gdf.clip(boundaries_gdf)

    roads_gdf = _get_roads(scenario_gdf, physical_object_types)

    # generating blocks layer
    blocks_gdf = _generate_blocks(boundaries_gdf, roads_gdf, scenario_gdf, physical_object_types)

    # calculating accessibility matrix
    acc_mx = _calculate_acc_mx(blocks_gdf, roads_gdf)

    # initializing city model
    city = City(
        blocks=blocks_gdf,
        acc_mx=acc_mx,
    )

    # updating buildings layer
    _update_buildings(city, scenario_gdf, physical_object_types)

    # updating service types
    _update_services(city, service_types, scenario_gdf)

    return city
