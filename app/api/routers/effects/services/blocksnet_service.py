import geopandas as gpd
import momepy
import networkx as nx

from app.api.routers.effects.services.project_service import *


def get_scenario_gdf(project_scenario_id, token):
    context_with_obj = get_context_with_obj_by_id(project_scenario_id, token)
    scenario_gdf = gpd.GeoDataFrame.from_features(context_with_obj["features"])
    scenario_gdf.set_crs(epsg=4326,inplace=True)
    return scenario_gdf

def get_geoms_by_function(function_name, physical_object_types, scenario_gdf):
    valid_type_ids = {
        d['physical_object_type_id']
        for d in physical_object_types
        if function_name in d['physical_object_function']['name']
    }
    return scenario_gdf[scenario_gdf['physical_objects'].apply(lambda x: any(d.get('physical_object_type_id') in valid_type_ids for d in x))]

def get_boundaries(scenario_gdf: gpd.GeoDataFrame):
    united_geometry = scenario_gdf.geometry.unary_union
    convex_hull = united_geometry.convex_hull
    boundaries = gpd.GeoDataFrame(geometry=[convex_hull])
    boundaries = boundaries.set_crs(epsg=4326)
    return boundaries

def get_water(scenario_gdf, physical_object_types):
    water = get_geoms_by_function('Водный объект', physical_object_types, scenario_gdf)
    water = water.explode(index_parts=True)
    water = water.reset_index()
    return water

def get_roads(scenario_gdf, physical_object_types):
    roads = get_geoms_by_function('Дорога', physical_object_types, scenario_gdf)
    merged = roads.unary_union
    if merged.geom_type == 'MultiLineString':
        roads = gpd.GeoDataFrame(geometry=list(merged.geoms),crs = roads.crs)
    else:
        roads = gpd.GeoDataFrame(geometry=[merged],crs = roads.crs)
    roads = roads.reset_index()
    return roads

def get_buildings(scenario_gdf, physical_object_types):
    buildings = get_geoms_by_function('Здание', physical_object_types, scenario_gdf)
    buildings['number_of_floors'] = 1
    buildings['is_living'] = True
    buildings['footprint_area'] = buildings.geometry.area
    buildings['build_floor_area'] =  buildings.geometry.area
    buildings['living_area'] =  buildings.geometry.area
    buildings['population'] = 100
    buildings = buildings.reset_index()
    buildings = buildings[buildings.geometry.type != 'Point']
    return buildings

def get_services(service_types,scenario_gdf):

    def extract_services(row):
        if isinstance(row['services'], list) and len(row['services']) > 0:
            return [
                {
                    'service_id': service['service_id'],
                    'service_type_id': service['service_type_id'],
                    'territory_type_id': service['territory_type_id'],
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

    services_gdf = gpd.GeoDataFrame(extracted_data, crs=scenario_gdf.crs)

    services_gdf['capacity'] = services_gdf['capacity_real']
    services_gdf = services_gdf[['geometry', 'service_id', 'service_type_id', 'territory_type_id', 'name', 'capacity']]

    services_gdf['area'] = services_gdf.geometry.area
    services_gdf.loc[services_gdf.area == 0, 'area'] = 100

    return services_gdf


def roads_to_graph(roads):
    graph = momepy.gdf_to_nx(roads)
    graph.graph['crs'] = roads.crs
    graph = nx.DiGraph(graph)
    for e1,e2,data in graph.edges(data=True):

        data['time_min'] = data['mm_len']/1000 / 1000
        data['weight'] = data['mm_len']/1000 / 1000
        data['length_meter'] = data['mm_len']/1000
    for node,data in graph.nodes(data=True):
        graph.nodes[node]['x'] = node[0]  # Assign X coordinate to node
        graph.nodes[node]['y'] = node[1]
        
    return graph