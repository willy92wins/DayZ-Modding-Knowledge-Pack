@echo off
REM [DESIGN] Build + deploy + launch a single DayZDiag in OFFLINE mode (no server).
REM Fastest way to eyeball objects/models. Not in DAYZ_INFRA.md — validate in-game.
setlocal
set MOD=__MODNAME__
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dayz-test.ps1" -Mod %MOD% -Mode offline -Build %*
echo.
pause
