@echo off
chcp 65001 > nul
echo.
echo ========================================================
echo        Potential Planner v1.0.0 빌드 스크립트
echo ========================================================
echo.

:: 1. [청소] 기존 빌드 잔해물 삭제
echo [1/3] 기존 빌드 폴더 청소 중...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "PotentialPlanner.spec" del "PotentialPlanner.spec"
if exist "PotentialPlanner_v1.0.0.spec" del "PotentialPlanner_v1.0.0.spec"

:: 2. [빌드] PyInstaller 실행
echo [2/3] EXE 파일 생성 중... (시간이 좀 걸립니다)
:: --clean: 캐시 삭제, --noconsole: 검은창 숨김, --onedir: 폴더 형태
pyinstaller --clean --noconsole --onedir --name="PotentialPlanner_v1.0.0" app/main.py

:: 3. [복사] 리소스 폴더(templates, builds) 복사
echo [3/3] 리소스 파일 복사 중...

:: templates 폴더 복사
xcopy "templates" "dist\PotentialPlanner_v1.0.0\templates\" /E /I /Y /Q
:: builds 폴더 복사
xcopy "presets" "dist\PotentialPlanner_v1.0.0\presets\" /E /I /Y /Q

echo.
echo ========================================================
echo        빌드 완료! dist 폴더를 확인하세요.
echo ========================================================
echo.
pause