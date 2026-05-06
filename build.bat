@echo off
title adhahi_bot — Build Script
color 0A

echo.
echo  ================================================
echo   adhahi.dz Bot — EXE Builder
echo  ================================================
echo.

:: ── Check Python ─────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Make sure Python is in your PATH.
    pause & exit /b 1
)

:: ── Check icon.ico ───────────────────────────────────────────────
if not exist icon.ico (
    echo  [WARNING] icon.ico not found — will use default icon.
    set ICON_FLAG=
) else (
    echo  [OK] icon.ico found.
    set ICON_FLAG=--icon=icon.ico --add-data "icon.ico;."
)
echo.

:: ── Install / upgrade dependencies ───────────────────────────────
echo  [1/3] Installing dependencies ...
pip install --quiet --upgrade selenium webdriver-manager pyinstaller
if errorlevel 1 (
    echo  [ERROR] pip install failed.
    pause & exit /b 1
)
echo        Done.
echo.

:: ── Clean previous build ─────────────────────────────────────────
echo  [2/3] Cleaning previous build ...
if exist build            rmdir /s /q build
if exist dist             rmdir /s /q dist
if exist adhahi_bot.spec  del /q adhahi_bot.spec
echo        Done.
echo.

:: ── Build ────────────────────────────────────────────────────────
echo  [3/3] Building EXE (this takes a minute) ...
echo.

pyinstaller ^
  --onedir ^
  --windowed ^
  --name "adhahi_bot" ^
  %ICON_FLAG% ^
  --collect-all selenium ^
  --collect-all webdriver_manager ^
  adhahi_gui.py

if errorlevel 1 (
    echo.
    echo  [ERROR] Build failed. See output above.
    pause & exit /b 1
)

:: ── Done ─────────────────────────────────────────────────────────
echo.
echo  ================================================
echo   BUILD COMPLETE!
echo  ================================================
echo.
echo   Your EXE is in:   dist\adhahi_bot\adhahi_bot.exe
echo.
echo   IMPORTANT: share the entire dist\adhahi_bot\ folder,
echo   not just the .exe on its own.
echo.
echo   ChromeDriver downloads automatically on first run.
echo.
pause
