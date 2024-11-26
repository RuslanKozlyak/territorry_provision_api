import os

API_TITLE = 'Effects API'
API_DESCRIPTION = 'API for assessing territory transformation effects'
EVALUATION_RESPONSE_MESSAGE = 'Evaluation started'
DEFAULT_CRS = 4326
if 'DATA_PATH' in os.environ:
  DATA_PATH = os.environ['DATA_PATH']
else:
  raise Exception('No DATA_PATH in env file')
if 'URBAN_API' in os.environ:
  URBAN_API = os.environ['URBAN_API']
else:
  raise Exception('No URBAN_API in env file')