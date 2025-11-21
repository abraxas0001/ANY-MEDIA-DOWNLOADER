# YouTube API Update - Quality Parsing

## Overview
Updated the YouTube section of the bot to properly handle the `yt-vid.hazex.workers.dev` API response structure with separate quality arrays.

## API Response Structure (from yt-vid.hazex)
The legacy YouTube API returns media in three distinct arrays:

```json
{
  "error": false,
  "title": "Video Title",
  "duration": "1313",
  "thumbnail": "https://...",
  "video_with_audio": [
    {
      "label": "mp4 (360p)",
      "type": "video_with_audio",
      "width": 640,
      "height": 360,
      "extension": "mp4",
      "fps": 24,
      "url": "https://..."
    }
  ],
  "video_only": [
    {
      "label": "mp4 (1080p)",
      "type": "video_only",
      "width": 1920,
      "height": 1080,
      "extension": "mp4",
      "fps": 24,
      "url": "https://..."
    },
    {
      "label": "mp4 (720p)",
      "type": "video_only",
      ...
    }
  ],
  "audio": [
    {
      "label": "m4a (132kb/s)",
      "type": "audio",
      "extension": "m4a",
      "bitrate": 131527,
      "url": "https://..."
    }
  ]
}
```

## Updated `process_youtube()` Function

### Key Changes:
1. **Primary API**: Now tries `yt-vid.hazex.workers.dev` (legacy API) first
2. **Structured Parsing**: Extracts items from `video_with_audio`, `video_only`, and `audio` arrays separately
3. **Intelligent Sorting**: Prioritizes formats by:
   - Type priority: `video_with_audio` > `video_only` > `audio`
   - Resolution: Highest resolution first (extracted from `height` field)
4. **Rich Labels**: Quality buttons show both resolution and file size
   - Example: `mp4 (360p) 70.7 MB`
   - Example: `m4a (132kb/s) 20.2 MB`
5. **Size Extraction**: Intelligently extracts file sizes from:
   - `size_bytes` field (if present)
   - `clen=` URL parameter (Google Video CDN standard)
6. **Fallback Chain**: 
   - Primary: Legacy API (yt-vid.hazex) → Parses `video_with_audio/video_only/audio`
   - Secondary: Multi-step API (yt-dl.hazex) → Legacy fallback method
   - Tertiary: yt-dlp → Last resort if both APIs fail

### User Experience:
When a user sends a YouTube/Shorts link, they now see:
- ✅ **Best quality button** (📤 Upload Best) - Sends the highest-quality video directly
- ✅ **All available formats** as clickable buttons with sizes
- ✅ **Quality labels** showing resolution and file size
- ✅ **Shorts support** - Works identically to regular videos

### Example Quality Button Layout:
```
mp4 (360p) 70.7 MB   ← Direct link
mp4 (1080p) 232.9 MB ← Direct link
mp4 (720p) 60.8 MB   ← Direct link
mp4 (480p) 33.4 MB   ← Direct link
m4a (132kb/s) 20.2 MB ← Audio only

[📤 Upload Best]     ← Sends highest quality here
[⬇️ Download Now]    ← Downloads best quality
```

## Supported Platforms via this API:
- ✅ YouTube Videos (all resolutions)
- ✅ YouTube Shorts
- ✅ YouTube Music videos
- ✅ Any video served through YouTube CDN

## Configuration
No additional configuration needed. The bot automatically:
- Detects YouTube/Shorts links
- Routes to appropriate parser
- Extracts all available qualities
- Presents user with formatted options

## Testing
To test the YouTube functionality:

1. **Regular Video**:
   ```
   https://www.youtube.com/watch?v=TJPFYs_88-g
   ```

2. **Shorts**:
   ```
   https://www.youtube.com/shorts/ABC123
   ```

3. **Expected Result**:
   - Bot displays multiple quality options
   - Each option shows resolution and file size
   - All options are clickable download links
   - "Upload Best" button sends highest quality to chat

## Error Handling
If the legacy API fails:
1. Tries multi-step API (get_task → create_task → check_task)
2. Falls back to yt-dlp for format extraction
3. Returns user-friendly error message if all fail

## Backward Compatibility
✅ All existing functionality preserved
✅ Instagram, TikTok, Terabox handlers unchanged
✅ Caption extraction unchanged
✅ Backup channel forwarding unchanged
