@echo off
echo Cleaning git cached files...

:: Untrack specific heavy folders and files that should not be tracked
git rm -r --cached "frontend/node_modules" 2>nul
git rm -r --cached ".pytest_cache" 2>nul
git rm -r --cached ".hypothesis" 2>nul
git rm -r --cached ".env" 2>nul
git rm -r --cached ".env.local" 2>nul
git rm -r --cached ".env.development" 2>nul
git rm -r --cached ".env.test" 2>nul
git rm -r --cached ".env.production" 2>nul
git rm -r --cached "backend/__pycache__" 2>nul
git rm -r --cached "infra/.terraform" 2>nul

echo Re-adding files (respecting .gitignore)...
git add .

echo Committing...
git commit -m "chore: remove tracked files that are now in .gitignore"

echo Pushing to branch product...
git push origin product

echo Done!
pause
