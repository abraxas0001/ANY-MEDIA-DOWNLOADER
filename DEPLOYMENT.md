# 🔐 SECURITY & DEPLOYMENT GUIDE

## ✅ Token Security - IMPORTANT!

Your bot token is now **safely stored** in `.env` file:

```
✅ .env is in .gitignore - won't be committed
✅ Token hidden from public code
✅ Safe to push to GitHub
✅ Can share code publicly without exposing credentials
```

## 📁 Files That Are Safe to Commit

**✅ SAFE - Can commit:**
- `bot.py` - No token in code
- `requirements.txt`
- `README.md`, `QUICKSTART.md`
- `.env.example` - Template only
- `.gitignore` - Protects sensitive files
- All documentation files

**❌ NEVER COMMIT:**
- `.env` - Contains your actual token
- `.venv/` - Virtual environment
- `__pycache__/` - Python cache

## 🚀 Deploying to GitHub

**Step 1: Initialize Git (if not done)**
```powershell
git init
```

**Step 2: Add files**
```powershell
git add .
```

**Step 3: Commit**
```powershell
git commit -m "Initial commit: Telegram media downloader bot"
```

**Step 4: Push to GitHub**
```powershell
git remote add origin https://github.com/yourusername/yourrepo.git
git branch -M main
git push -u origin main
```

**Your token is SAFE!** ✅  
The `.gitignore` file prevents `.env` from being committed.

## 🖥️ Setting Up on Another Machine

**1. Clone your repo:**
```powershell
git clone https://github.com/yourusername/yourrepo.git
cd yourrepo
```

**2. Create virtual environment:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**3. Install dependencies:**
```powershell
pip install -r requirements.txt
```

**4. Create .env file:**
```powershell
Copy-Item .env.example .env
```

Then edit `.env` and add your token:
```
TELEGRAM_TOKEN=your_bot_token_here
```

**5. Run:**
```powershell
python bot.py
```

## 🌐 Deploying to Production

### Option 1: VPS (DigitalOcean, AWS, etc.)

1. SSH into your server
2. Clone repository
3. Install Python 3.8+
4. Create `.env` with your token
5. Install dependencies: `pip install -r requirements.txt`
6. Run with systemd or screen:
   ```bash
   screen -S telegram-bot
   python bot.py
   # Detach: Ctrl+A then D
   ```

### Option 2: Heroku

1. Create `Procfile`:
   ```
   worker: python bot.py
   ```

2. Set config var in Heroku dashboard:
   ```
   TELEGRAM_TOKEN=your_token_here
   ```

3. Deploy:
   ```powershell
   git push heroku main
   ```

### Option 3: Docker

1. Create `Dockerfile`:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["python", "bot.py"]
   ```

2. Build and run:
   ```bash
   docker build -t telegram-bot .
   docker run -e TELEGRAM_TOKEN=your_token telegram-bot
   ```

### Option 4: Railway (Serverless Container)

Railway builds your repo and runs a start command. High-quality YouTube muxing needs FFmpeg.

Approach A (auto-download – already implemented): first video-only merge triggers `ensure_ffmpeg()` which fetches a static build into `bin/ffmpeg`. Adds ~20MB cold-start overhead.

Approach B (bundle binary): Download a static build locally, keep only `ffmpeg`/`ffmpeg.exe` in `bin/`, commit it (if license policy acceptable). Faster cold starts.

Recommended Railway settings:
```
Start Command: python bot.py
Env Vars:
   TELEGRAM_TOKEN=<your token>
   MAX_UPLOAD_MB=50   (optional)
```

If you see “Audio merge unavailable (FFmpeg missing)” the download failed (network block). Workaround build step example:
```bash
curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o ff.tar.xz \
   && tar -xf ff.tar.xz \
   && mv ffmpeg-*-amd64-static/ffmpeg bin/ffmpeg \
   && chmod +x bin/ffmpeg
```

Ensure `bin/` is tracked (not ignored) if committing the binary.

### FFmpeg & YouTube Format Notes

- Progressive formats (e.g. itag 18 – 360p) contain multiplexed audio+video.
- High quality DASH formats (e.g. itag 137 – 1080p) are video-only; separate audio stream must be merged.
- Bot flow: detect `type == 'video_only'` → download best audio → merge with: `ffmpeg -i video -i audio -c:v copy -c:a aac -shortest merged.mp4` (no video re-encode).
- If merge fails or FFmpeg missing, silent original stream is sent with a warning.

- Why no audio on 1080p? YouTube shifted to adaptive streaming: independent video and audio tracks allow device-specific combinations. Legacy progressive streams top out at 720p (itag 22) or 360p (itag 18). Thus selecting a high resolution DASH format without merging results in silent playback.

Tip: If storage constraints matter, you can skip auto-download by placing an empty file `bin/.no_ffmpeg` and modifying `ensure_ffmpeg()` to honor it.

## 🔄 Keeping Token Updated

**To change your token:**

1. Edit `.env` file:
   ```
   TELEGRAM_TOKEN=new_token_here
   ```

2. Restart bot

**To regenerate token:**
1. Message @BotFather on Telegram
2. Use `/revoke` command
3. Update `.env` with new token

## 🛡️ Additional Security Tips

1. **Never** log your token
2. **Never** send token in messages
3. **Regenerate** token if exposed
4. **Use** environment variables in production
5. **Enable** 2FA on GitHub account
6. **Review** `.gitignore` before commits
7. **Keep** `.env.example` without real credentials

## ✨ Best Practices

- ✅ Use `.env` for all sensitive data
- ✅ Document required environment variables
- ✅ Include `.env.example` in repo
- ✅ Add `.env` to `.gitignore`
- ✅ Use different tokens for dev/prod
- ✅ Monitor bot logs for issues
- ✅ Keep dependencies updated

## 🆘 Emergency: Token Exposed!

If you accidentally commit your token:

1. **Immediately** revoke token via @BotFather
2. Generate new token
3. Update `.env` with new token
4. Remove token from Git history:
   ```powershell
   git filter-branch --force --index-filter `
   "git rm --cached --ignore-unmatch .env" `
   --prune-empty --tag-name-filter cat -- --all
   
   git push origin --force --all
   ```
5. Verify token is removed from all commits

## 📞 Support

If you need help with deployment or security:
- Check GitHub Issues
- Review Telegram Bot API documentation
- Ensure `.env` file is properly configured
