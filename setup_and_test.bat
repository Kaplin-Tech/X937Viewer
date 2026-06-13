@echo off
rem One-shot: create .venv, install deps, run tests, launch the viewer.
cd /d C:\Temp\X937Viewer

echo === venv === > test_log.txt
if not exist .venv (
    py -3 -m venv .venv >> test_log.txt 2>&1 || python -m venv .venv >> test_log.txt 2>&1
)
call .venv\Scripts\activate.bat

echo === pip install === >> test_log.txt
python -m pip install --quiet --upgrade pip >> test_log.txt 2>&1
pip install --quiet -r requirements.txt >> test_log.txt 2>&1
pip list >> test_log.txt 2>&1

echo === unit tests === >> test_log.txt
python -m unittest discover tests -v >> test_log.txt 2>&1

echo === launching GUI === >> test_log.txt
start "" .venv\Scripts\pythonw.exe main.py Example\iclFile.x937
echo === done === >> test_log.txt
