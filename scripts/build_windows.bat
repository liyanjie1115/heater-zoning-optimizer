@echo off
setlocal
cd /d %~dp0\..
python -m PyInstaller --clean --noconfirm heater_zoning_optimizer.spec
echo.
echo Build completed.
echo Check the dist directory:
echo %cd%\dist
endlocal
