"""FastAPI app. Run with: uv run uvicorn landcheck.main:app --reload"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from landcheck.config import Settings, get_settings
from landcheck.mocks import load_mock_results
from landcheck.models import AnalyzeResponse, PolygonGeometry


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    # Loaded at startup so a broken mock stops the app instead of failing later.
    mock_results = load_mock_results(settings.mocks_dir)

    app = FastAPI(title="Land Check API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/analyze")
    def analyze(parcel: PolygonGeometry) -> AnalyzeResponse:
        # Skeleton: returns mock results for any valid polygon. Real modules come later.
        return AnalyzeResponse(results=mock_results)

    return app


app = create_app()
