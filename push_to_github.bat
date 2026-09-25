@echo off
echo ===================================================
echo Pushing Location-Based Business Model Recommendation
echo ===================================================

git add .
git commit -m "Sanitize codebase, fix pipeline bugs, and update gitignore"
git push origin main

echo.
echo ===================================================
echo Push complete! Press any key to exit.
echo ===================================================
pause
