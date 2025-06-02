python -m venv .venv
call .venv/Scripts/activate
pip install -r requirements.txt
pyinstaller --onedir --clean --name VTVV-Connector --noconsole main.py --add-data "./fonts:fonts"
if exist .venv rmdir /s /q .venv