import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import accounts_ext, ai, attachments, auth, crud, dashboard, goals, insights, transactions
from app.core.config import settings
from app.jobs.scheduler import job, reset_demo


@asynccontextmanager
async def lifespan(app: FastAPI):
    if len(settings.secret_key) < 32 or settings.secret_key.startswith("dev-secret"):
        logging.getLogger(__name__).warning("SECRET_KEY is short or the development default; set a random 32+ character value in production")
    sched = None
    if settings.run_scheduler:
        sched = BackgroundScheduler()
        sched.add_job(job, "interval", hours=1)
        sched.add_job(job, "date")  # run once at startup
        if settings.demo_mode:
            sched.add_job(reset_demo, "date")
            sched.add_job(reset_demo, "interval", hours=24)
        sched.start()
    yield
    if sched:
        sched.shutdown(wait=False)


app = FastAPI(title="Pursely", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

api = APIRouter(prefix="/api/v1")
for r in (auth.router, transactions.router, crud.categories, crud.accounts, crud.budgets,
          crud.subscriptions, crud.recurring, dashboard.router, accounts_ext.router, goals.router,
          insights.router, attachments.router, ai.router):
    api.include_router(r)
app.include_router(api)


@app.get("/health")
def health():
    return {"ok": True}
