from fastapi import APIRouter

from app.api.v1.routes_auth import router as auth_router
from app.api.v1.routes_scans import scans_router, target_scans_router
from app.api.v1.routes_targets import router as targets_router

# Every v1 resource router gets included here. As new resources are
# added (findings, audit-logs -- see project roadmap), each gets its
# own routes_*.py module and one line here, keeping main.py free of
# per-resource routing detail.
api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(targets_router)
api_router.include_router(target_scans_router)
api_router.include_router(scans_router)
