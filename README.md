# Telegram Media Downloader Bot

A Telegram bot that downloads media from YouTube, Instagram, Terabox, and other platforms. Send a URL and get the file instantly or a download link.

## ✅ Tested & Working

All API handlers have been tested and verified working for:
- ✅ YouTube videos
- ✅ Instagram reels
- ✅ Terabox/1024terabox links
- ✅ Generic social media URLs (fallback)

## 🌐 Railway Deployment

**Quick Deploy (1 min):**

1. Push this repo to GitHub
2. Go to [Railway.app](https://railway.app)
3. Create new project → Import from GitHub
4. Add environment variable:
   ```
   TELEGRAM_TOKEN=your_bot_token_here
   ```
5. Deploy!

The bot auto-installs FFmpeg on first run for video-only merging.

**1. Install dependencies:**
```powershell
pip install -r requirements.txt
```

**2. Configure your bot token:**

The bot now uses a `.env` file for secure token storage. Your token is already configured in `.env` file.

> ⚠️ **Important:** The `.env` file is already in `.gitignore` - it's safe to push to GitHub!

**3. Run the bot:**
```powershell
.\start_bot.ps1
```

Or manually:
```powershell
python .\bot.py
```

You should see:
```
INFO:__main__:Starting bot
```

## 📱 How to Use

1. Open Telegram and search for your bot
2. Send `/start` to see the welcome message
3. Send any media URL:
   - YouTube: `https://youtube.com/watch?v=...`
   - Instagram: `https://instagram.com/reel/...`
   - Terabox: `https://1024terabox.com/s/...`
4. The bot will:
   - Send the file directly (if ≤ 50 MB)
   - Send a download link (if > 50 MB)

## 🎯 Bot Commands

- `/start` - Show artistic welcome message with usage guide
- `/help` - Detailed help and FAQ
- `/about` - Bot information and statistics  
- `/supported` - List all supported platforms

## ✨ Features

- 🚀 **Instant downloads** for multiple platforms
- 📦 **Smart file handling** - sends files directly or provides links
- 🎯 **Format selection** - automatically chooses best video quality
- 📊 **File info** - shows filename and size
- 🔄 **Fallback support** - generic API for other platforms
- 🎨 **Beautiful UI** - artistic messages with emojis
- 🔐 **Secure** - token stored safely in .env file
- 📝 **Detailed logging** - tracks all downloads

## Supported Platforms

| Platform | API Endpoint |
|----------|-------------|
| YouTube | `yt-vid.hazex.workers.dev` |
| Instagram | `insta-dl.hazex.workers.dev` |
| Terabox | `my-noor-queen-api.woodmirror.workers.dev` |
| Others | `social-dl.hazex.workers.dev` (fallback) |

## Project Structure

```
ANY MEDIA DOWNLOADER/
├── bot.py              # Main bot script
├── requirements.txt    # Python dependencies
├── test_apis.py        # API test script
└── README.md          # This file
```

## Testing

Run the test script to verify all APIs work:
```powershell
python test_apis.py
```

## Configuration

The bot reads configuration from environment variables:
- `TELEGRAM_TOKEN` (required) - Your Telegram bot token from @BotFather

## Technical Details

- **File size limit**: 50 MB (Telegram bot API limit for direct uploads)
- **Timeout**: 30 seconds per API request
- **Polling mode**: Long polling with 60-second timeout
- **Error handling**: Automatic fallback to link sharing if upload fails

## Security Notes

⚠️ **Keep your bot token private!**
- Never commit tokens to source control
- Use environment variables or a `.env` file
- Regenerate token if accidentally exposed

## Future Improvements

Potential enhancements you can add:
- 📱 Inline format selection (multiple quality options)
- 💾 File caching to avoid re-downloading
- 🌐 Webhook mode for production deployment
- 📈 Progress tracking for large downloads
- 🎬 Playlist/album support
- 🔐 User authentication and rate limiting

## Troubleshooting

**Bot doesn't respond:**
- Check token is set correctly
- Verify bot is running (`INFO:__main__:Starting bot`)
- Check internet connection

**API errors:**
- APIs may have rate limits or temporary outages
- Try again after a few seconds
- Check if the URL is valid and accessible

**File too large:**
- Bot will send a direct download link instead
- Consider implementing chunked uploads for 50-200 MB files

## License

Free to use and modify for personal or commercial projects.
