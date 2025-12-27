@echo off
cd /d "%~dp0"

echo [STEP 1] Cleaning...
if exist "PotentialPlanner_Build" rd /s /q "PotentialPlanner_Build"
mkdir "PotentialPlanner_Build"

echo [STEP 2] Building...
pyinstaller --clean --noconsole --onedir --name="PotentialPlanner" --distpath "PotentialPlanner_Build\dist" --workpath "PotentialPlanner_Build\build" --specpath "PotentialPlanner_Build" --paths "src" "run.py"

echo [STEP 3] Copying Resources...
xcopy "resources" "PotentialPlanner_Build\dist\PotentialPlanner\resources\" /E /I /Y /Q
copy "config.py" "PotentialPlanner_Build\dist\PotentialPlanner\"

echo.
echo DONE!
pause