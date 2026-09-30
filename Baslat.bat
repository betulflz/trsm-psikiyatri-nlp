@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
set "TRSM_DATA_DIR=%CD%\data"
if "%TRSM_PORT%"=="" set "TRSM_PORT=8765"

echo.
echo TRSM Demo baslatiliyor...
echo.

for /f "usebackq tokens=1-4 delims=|" %%A in (`powershell -NoProfile -Command "$os=Get-CimInstance Win32_OperatingSystem; $ram=[math]::Round($os.TotalVisibleMemorySize/1MB,1); Write-Output ($os.Caption+'|'+$os.Version+'|'+[Environment]::Is64BitOperatingSystem+'|'+$ram)"`) do (
  set "OS_NAME=%%A"
  set "OS_VERSION=%%B"
  set "IS_64=%%C"
  set "RAM_GB=%%D"
)
echo Windows: %OS_NAME% ^(%OS_VERSION%^) 
echo Sistem: %IS_64%-bit, RAM: %RAM_GB% GB

powershell -NoProfile -Command "$os=Get-CimInstance Win32_OperatingSystem; if (-not [Environment]::Is64BitOperatingSystem -or [version]$os.Version -lt [version]'10.0') { exit 1 }"
if errorlevel 1 (
  echo.
  echo Bu uygulama Windows 10 veya daha yeni, 64-bit bir bilgisayar gerektirir.
  goto :finish
)

set "PATH_RISK=0"
for /f %%A in ('powershell -NoProfile -Command "$p=(Get-Location).Path; if ($p.IndexOf('OneDrive',[System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or $p.Length -gt 60) { '1' } else { '0' }"') do set "PATH_RISK=%%A"
if "%PATH_RISK%"=="1" (
  echo.
  echo Uyari: Uygulama OneDrive'a bagli ya da cok uzun bir klasor yolunda duruyor.
  echo Bu, kurulumun yavaslamasina veya hata vermesine yol acabilir.
  echo Onerilen: TRSM_Demo klasorunu dogrudan C:\ surucusune tasiyin
  echo ^(C:\TRSM_Demo^) ve Baslat.bat'i oradan calistirin.
  echo.
  echo Yine de devam etmek icin bir tusa basin, cikmak icin pencereyi kapatin.
  pause >nul
)

powershell -NoProfile -Command "$ram=(Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize/1MB; if ($ram -lt 8) { exit 1 }"
if errorlevel 1 echo Uyari: RAM 8 GB'tan az. Qwen ozelligi yavas calisabilir; ana analiz yine calisir.

where uv >nul 2>nul
if errorlevel 1 (
  echo.
  echo Ilk kurulum icin uv araci yukleniyor...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; irm https://astral.sh/uv/install.ps1 | iex"
  set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
)
where uv >nul 2>nul
if errorlevel 1 (
  echo uv yuklenemedi. Internet baglantinizi kontrol edip tekrar deneyin.
  goto :finish
)

if not exist ".venv" echo Ilk kurulum yapiliyor, birkac dakika surebilir...
uv sync --no-dev
if errorlevel 1 (
  echo.
  echo Kurulum tamamlanamadi. Internet baglantisini ve diskte bos alan olup olmadigini kontrol edin.
  goto :finish
)

where ollama >nul 2>nul
if errorlevel 1 (
  echo Qwen olmadan devam ediliyor.
) else (
  ollama list | findstr /B /C:"qwen2.5:3b" >nul 2>nul
  if errorlevel 1 (
    echo Qwen modeli hazirlaniyor. Bu adim uzun surebilir; basarisiz olursa ana analiz yine acilir.
    ollama pull qwen2.5:3b
    if errorlevel 1 echo Qwen indirilemedi. Qwen olmadan devam ediliyor.
  )
)

start "" /b powershell -NoProfile -WindowStyle Hidden -Command "$port=$env:TRSM_PORT; $limit=(Get-Date).AddSeconds(300); while((Get-Date) -lt $limit) { try { Invoke-WebRequest -UseBasicParsing ('http://127.0.0.1:'+$port+'/api/status') -TimeoutSec 2 | Out-Null; Start-Process ('http://127.0.0.1:'+$port); exit } catch { Start-Sleep -Seconds 1 } }"
echo Uygulama aciliyor; tarayici birazdan kendiliginden acilacak.
echo Tarayici birkac dakika icinde acilmazsa tarayiciya su adresi yazin:
echo http://127.0.0.1:%TRSM_PORT%
echo Bu pencereyi kapatmayin; kapatirsaniz uygulama da kapanir.
uv run --no-sync python demo_server.py
set "APP_EXIT=%ERRORLEVEL%"
if not "%APP_EXIT%"=="0" (
  echo.
  echo Uygulama hata ile kapandi. Yukaridaki hata metninin ekran goruntusunu bize iletin.
  echo Hata metninde c10.dll veya DLL load failed geciyorsa Microsoft Visual C++ Redistributable x64 paketini kurun:
  echo https://aka.ms/vs/17/release/vc_redist.x64.exe
)

:finish
echo.
echo Kapatmak icin bir tusa basin.
pause >nul
