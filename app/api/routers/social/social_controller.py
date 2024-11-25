from fastapi import APIRouter
from api.utils.auth import verify_token

router = APIRouter(prefix='/social', tags=['Social effects'])

