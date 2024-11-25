import os

API_TITLE = 'Effects API'
API_DESCRIPTION = 'API for assessing territory transformation effects'
EVALUATION_RESPONSE_MESSAGE = 'Evaluation started'
if 'DATA_PATH' in os.environ:
  DATA_PATH = os.environ['DATA_PATH']
else:
  raise Exception('No DATA_PATH in env file')