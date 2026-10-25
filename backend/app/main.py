"""FastAPI application composition. Models, business logic and routes live in modules."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.db import engine, Base
from app.models import Scenario, PlannedFlight, Aircraft, Run, Airport, Audit, FlightAircraftAssignment
from app.operations import models as operation_models
from app.operations.router import router as operations_router, initialize_demo_infrastructure
from app.operations.catalog import catalog_router
from app.routers.core import router as core_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv('AIRPORTOPS_SCHEMA_MODE', 'local') == 'local':
        Base.metadata.create_all(engine)
    with Session(engine) as db:
        initialize_demo_infrastructure(db)
    yield

app = FastAPI(title='AirportOps API', version='0.9.0', description='Airport operations and deterministic playback', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(','), allow_credentials=False, allow_methods=['GET','POST','PATCH','DELETE'], allow_headers=['Content-Type'])

app.include_router(core_router)
app.include_router(operations_router)
app.include_router(catalog_router)
