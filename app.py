"""
Unified Production Entry Point for Render / Koyeb / Local deployment.
Executes the unified FastAPI + Aiogram 3 application in main.py on a single worker.
"""

import os
import uvicorn
from config import PORT

if __name__ == "__main__":
    port = int(os.environ.get("PORT", PORT or 8080))
    # Run single worker (--workers 1) to respect the 500-600 MB RAM budget
    uvicorn.run("main:app", host="0.0.0.0", port=port, workers=1)
