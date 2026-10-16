from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, crud, dashboard, transactions
from app.core.config import settings
from app.jobs.scheduler import job


@asynccontextmanager
async def lifespan(app: FastAPI):
    sched = None
    if settings.run_scheduler:
        sched = BackgroundScheduler()
        sched.add_job(job, "interval", hours=1)
        sched.add_job(job, "date")  # run once at startup
        sched.start()
    yield
    if sched:
        sched.shutdown(wait=False)


app = FastAPI(title="Money Tracker", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

api = APIRouter(prefix="/api/v1")
for r in (auth.router, transactions.router, crud.categories, crud.accounts, crud.budgets,
          crud.subscriptions, crud.recurring, dashboard.router):
    api.include_router(r)
app.include_router(api)


@app.get("/health")
def health():
    return {"ok": True}
