@echo off
chcp 65001 > nul
setlocal

:: ========================================================
:: [설정] 변수 정의 (여기만 바꾸면 다 바뀝니다)
:: ========================================================
set APP_NAME=PotentialPlanner
set VERSION=v1.0.0
set TARGET_DIR=%APP_NAME%_%VERSION%_Build

set RESOURCE_DIR=presets
:: ========================================================

echo.
echo ========================================================
echo        %APP_NAME% %VERSION% 빌드 스크립트
echo ========================================================
echo.

:: 1. [청소] 통합 빌드 폴더가 이미 있다면 삭제
echo [1/3] 🧹 기존 빌드 폴더("%TARGET_DIR%") 청소 중...
if exist "%TARGET_DIR%" rd /s /q "%TARGET_DIR%"

:: 폴더 생성
mkdir "%TARGET_DIR%"

:: 2. [빌드] PyInstaller 실행 (경로 옵션 추가됨)
echo [2/3] 🔨 EXE 파일 생성 중...
:: --distpath: exe가 나올 폴더 위치
:: --workpath: 임시 build 폴더 위치
:: --specpath: .spec 파일이 생길 위치
pyinstaller --clean --noconsole --onedir ^
 --name="%APP_NAME%_%VERSION%" ^
 --distpath "%TARGET_DIR%\dist" ^
 --workpath "%TARGET_DIR%\build" ^
 --specpath "%TARGET_DIR%" ^
 app/main.py

:: 3. [복사] 리소스 폴더 복사
echo [3/3] 📦 리소스 파일 복사 중...

:: templates 복사
xcopy "templates" "%TARGET_DIR%\dist\%APP_NAME%_%VERSION%\templates\" /E /I /Y /Q

:: presets 복사
xcopy "%RESOURCE_DIR%" "%TARGET_DIR%\dist\%APP_NAME%_%VERSION%\%RESOURCE_DIR%\" /E /I /Y /Q

echo.
echo ========================================================
echo        🎉 빌드 완료!
echo        결과물 위치: \%TARGET_DIR%\dist\%APP_NAME%_%VERSION%
echo ========================================================
echo.
pause