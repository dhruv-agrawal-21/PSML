@echo off
REM This script helps you test MySQL connection and create the database

echo ============================================
echo MySQL Connection Test and Setup
echo ============================================
echo.

echo Enter your MySQL credentials:
set /p DB_USER="Enter MySQL Username (default: root): "
if "%DB_USER%"=="" set DB_USER=root

set /p DB_PASSWORD="Enter MySQL Password: "

set /p DB_HOST="Enter MySQL Host (default: localhost): "
if "%DB_HOST%"=="" set DB_HOST=localhost

set /p DB_PORT="Enter MySQL Port (default: 3306): "
if "%DB_PORT%"=="" set DB_PORT=3306

echo.
echo Testing connection to MySQL...
mysql -u %DB_USER% -p%DB_PASSWORD% -h %DB_HOST% -P %DB_PORT% -e "SELECT VERSION();"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ Connection successful!
    echo.
    echo Creating database...
    mysql -u %DB_USER% -p%DB_PASSWORD% -h %DB_HOST% -P %DB_PORT% -e "CREATE DATABASE IF NOT EXISTS requirement_approval CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    echo ✓ Database created!
    echo.
    echo Update your .env file with these credentials:
    echo DB_USER=%DB_USER%
    echo DB_PASSWORD=%DB_PASSWORD%
    echo DB_HOST=%DB_HOST%
    echo DB_PORT=%DB_PORT%
) else (
    echo.
    echo ✗ Connection failed! Check your credentials.
)

pause
