python -m venv .venv
call .venv/Scripts/activate
pip install -r requirements.txt
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller --onedir --clean --name VTVV-Connector --noconsole main.py --add-data "./fonts:fonts"
if exist .venv rmdir /s /q .venv