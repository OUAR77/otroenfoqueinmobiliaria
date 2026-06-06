import os
import sys

if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)

import uvicorn
from main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8022, log_level="info")
