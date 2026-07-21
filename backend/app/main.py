from fastapi import FastAPI

from app.api.v1 import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description=(
        "PrivacyLens scans websites for observable privacy and security "
        "configurations (cookies, trackers, headers, HTTPS, consent/policy "
        "presence). It reports technical findings only and does not "
        "provide legal advice or compliance determinations."
    ),
    # Namespacing the OpenAPI/docs URLs under the API version prefix
    # keeps them consistent with every other route in the app, and
    # means a future v2 could ship its own docs at /api/v2/docs
    # alongside v1's without either page's spec changing meaning.
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """
    Basic liveness check for load balancers / container orchestrators.

    Deliberately does NOT touch the database. A health check that
    depends on the DB conflates two different failure modes — "the app
    process is down" vs. "the app is up but can't reach Postgres" — and
    an orchestrator that restarts the app container in response to a
    transient DB blip is usually the wrong reaction. A separate
    DB-inclusive *readiness* check is a reasonable Phase 2 addition.
    """
    return {"status": "ok", "service": settings.PROJECT_NAME}


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
