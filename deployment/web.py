"""Serve MurderBench with the existing UNCEN FastAPI runtime."""
import os
from pathlib import Path
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

root = Path(os.environ['MURDERBENCH_SITE_ROOT']).resolve(strict=True)
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['murderbench.com', 'www.murderbench.com', '127.0.0.1', 'localhost'])
app.mount('/', StaticFiles(directory=root, html=True), name='murderbench')
