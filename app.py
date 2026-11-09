"""Enzonic entry point for the Reeves API.

The host discovers FastAPI applications from the repository root. Keep the
actual API and its configuration in reeves_api.app.
"""
from fastapi import FastAPI

from reeves_api.app import app as reeves_app

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/", reeves_app)
