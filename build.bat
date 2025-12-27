@echo off
chcp 65001 > nul
setlocal

:: [안전장치] 배치 파일 위치(프로젝트 루트)를 기준으로 설정
cd /d "%~dp0"

:: ========================================================
:: [설정] 프로젝트 정보
:: ========================================================
set APP_NAME=PotentialPlanner
set VERSION=v1.0.0
set TARGET_DIR=%APP_NAME%_%VERSION%_Build

:: [중요] 프로그램의 시작점 (설명해주신 run.py)
set MAIN_SCRIPT=run.py

:: 리소스 및 설정 파일 경로
set RESOURCE_DIR=resources
set CONFIG_FILE=config.py
:: ========================================================

echo.
echo ========================================================
echo        %APP_NAME% %VERSION% 빌드 스크립트 (구조 반영됨)
echo ========================================================
echo.

:: 0. [사전 점검] run.py 확인
if not exist "%MAIN_SCRIPT%" (
    echo [❌ 오류] '%MAIN_SCRIPT%' 파일을 찾을 수 없습니다.
    echo          현재 폴더 위치: %cd%
    pause
    exit /b
)

:: 1. [청소] 기존 빌드 폴더 삭제
echo [1/4] 🧹 기존 빌드 폴더 청소 중...
if exist "%TARGET_DIR%" rd /s /q "%TARGET_DIR%"
mkdir "%TARGET_DIR%"

:: 2. [빌드] PyInstaller 실행
echo [2/4] 🔨 EXE 파일 생성 중 (진입점: %MAIN_SCRIPT%)...

:: --onedir: 폴더 형태로 출력 (디버깅 용이)
:: --paths "src": src 폴더를 라이브러리 경로로 추가 (import 인식용)
pyinstaller --clean --noconsole --onedir ^
 --name="%APP_NAME%" ^
 --distpath "%TARGET_DIR%\dist" ^
 --workpath "%TARGET_DIR%\build" ^
 --specpath "%TARGET_DIR%" ^
 --paths "src" ^
 "%MAIN_SCRIPT%"

if %errorlevel% neq 0 (
    echo [❌ 빌드 실패] PyInstaller 실행 중 오류 발생.
    pause
    exit /b
)

:: 3. [복사] 리소스 폴더 복사
echo [3/4] 📦 리소스 폴더 복사 중...

if exist "%RESOURCE_DIR%" (
    xcopy "%RESOURCE_DIR%" "%TARGET_DIR%\dist\%APP_NAME%\%RESOURCE_DIR%\" /E /I /Y /Q
    echo    -> resources 복사 완료
) else (
    echo [⚠️ 경고] resources 폴더가 없습니다. 이미지 로드 에러가 날 수 있습니다.
)

:: 4. [복사] config.py 설정 파일 복사
echo [4/4] ⚙️ 설정 파일(config.py) 복사 중...

if exist "%CONFIG_FILE%" (
    copy "%CONFIG_FILE%" "%TARGET_DIR%\dist\%APP_NAME%\" > nul
    echo    -> config.py 복사 완료
) else (
    echo [⚠️ 정보] config.py가 없습니다. 필요 없다면 무시하세요.
)

echo.
echo ========================================================
echo        🎉 빌드 성공!
echo.
echo        실행 파일 위치:
echo        %TARGET_DIR%\dist\%APP_NAME%\%APP_NAME%.exe
echo ========================================================
echo.
pause