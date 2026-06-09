@echo off
setlocal

cd /d "%~dp0"

echo Installing build dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo Building search.exe...
python -m PyInstaller --onefile --windowed --name search --clean main.py

if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo Copying config.json to dist folder...
copy /Y config.json dist\config.json

echo.
echo Done.
echo   dist\search.exe
echo   dist\config.json
echo.
echo data.db は初回の「登録」実行時に dist フォルダへ作成されます。
echo search_history.json も同じフォルダに保存されます。

endlocal
