@echo off
cd /d "%~dp0"
set BUILD_DIR=..\PotentialPlanner_Build

echo [STEP 1] Cleaning...
if exist "%BUILD_DIR%" rd /s /q "%BUILD_DIR%"
mkdir "%BUILD_DIR%"

echo [STEP 1-1] Cleaning Python Cache...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc

echo.
echo [STEP 2] Building...
pyinstaller --clean --noconsole --onedir --name="PotentialPlanner" --distpath "%BUILD_DIR%\dist" --workpath "%BUILD_DIR%\build" --specpath "%BUILD_DIR%" --paths "src" "run.py"

echo.
echo [STEP 3] Copying Resources...
xcopy "resources" "%BUILD_DIR%\dist\PotentialPlanner\resources\" /E /I /Y /Q

echo.
echo DONE! Build saved to: %BUILD_DIR%
pause