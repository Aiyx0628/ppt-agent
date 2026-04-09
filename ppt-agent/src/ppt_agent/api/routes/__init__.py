from fastapi import APIRouter

from ppt_agent.api.routes.health import router as health_router
from ppt_agent.api.routes.models import router as models_router
from ppt_agent.api.routes.projects import router as projects_router

router = APIRouter()
router.include_router(health_router)
router.include_router(models_router)
router.include_router(projects_router)
