import os
from api.utils.const import DATA_PATH

def _get_file_path(project_scenario_id : int):
    file_path = f'{project_scenario_id}'
    return os.path.join(DATA_PATH, f'{file_path}.parquet')

def evaluate_effects(region_id : int, project_scenario_id : int, token : str):
  ... # TODO назначение этой штуки в том чтоб чето сделать и сохранить локально гдфку