# 🚀 QUICK START GUIDE

## ⚡ Super Quick Start (One Command)

```powershell
.\start_bot.ps1
```

That's it! Your bot is running. 🎉

## 📋 First Time Setup (One-time only)

**1. Install dependencies:**
```powershell
pip install -r requirements.txt
```

**2. Your token is already configured!**  
The bot reads from `.env` file automatically. ✅

## 🎨 Using Your Bot

1. **Open Telegram** and search for your bot
2. **Send** `/start` to see the beautiful welcome message
3. **Try these commands:**
   - `/help` - Detailed usage guide
   - `/about` - Bot information
   - `/supported` - See all platforms
4. **Send any media URL:**
   - `https://youtube.com/watch?v=...`
   - `https://instagram.com/reel/...`
   - `https://1024terabox.com/s/...`
5. **Get your file** or download link instantly!

## 🧪 Test Everything Works

```powershell
python test_apis.py
```

You should see:
```
✅ Success! for YouTube
✅ Success! for Instagram
✅ Success! for Terabox
```

## 🔐 Security - Token Protection

Your bot token is now stored securely in `.env` file:
- ✅ `.env` is in `.gitignore` - won't be committed
- ✅ Token is hidden from public code
- ✅ Safe to push to GitHub
- ✅ Can share code without exposing token

**To change token:**
Edit `.env` file and update `TELEGRAM_TOKEN=your_new_token`

## 🆘 Troubleshooting

**"Module not found" error:**
```powershell
pip install -r requirements.txt
```

**Bot doesn't respond:**
- Check token is correct
- Verify bot is running (you should see "Starting bot" message)
- Try `/start` command first

**API errors:**
- Wait a few seconds and try again
- Check if the URL is valid
- Some APIs may have temporary rate limits

## 📚 Need More Help?

See the full README.md for detailed documentation, features, and advanced configuration options.
