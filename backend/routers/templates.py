from fastapi import APIRouter
from services.templates import list_templates

router = APIRouter(tags=["templates"])


@router.get("/templates")
def get_templates():
    return {"templates": list_templates()}
