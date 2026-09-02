python -m venv .venv
call .venv/Scripts/activate
pip install -r requirements.txt
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller --onedir --clean --name VRCT-TTS --noconsole --icon "./img/icon.ico" main.py --add-data "./fonts:fonts" --add-data "./img/icon.ico:img" --hidden-import=_cffi_backend --hidden-import=miniaudio
if exist .venv rmdir /s /q .venv