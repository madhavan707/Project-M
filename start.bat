@echo off
title Aadhaar Extractor & Google Sheets Pipeline
echo =======================================================
echo Starting 100%% Free Aadhaar Extractor & Pipeline...
echo =======================================================
echo.
echo Running server on http://127.0.0.1:8000
start http://127.0.0.1:8000
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
pause
