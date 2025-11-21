# YouTube Update - Architecture & Data Flow Diagram

## Overall Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER SENDS YOUTUBE LINK                      │
│                                                                 │
│  User: https://www.youtube.com/watch?v=TJPFYs_88-g            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  handle_message(msg)                            │
│         - Extract URL from message                              │
│         - Validate format                                       │
│         - Send "Processing..." message                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  handle_api_for_url(url)                        │
│         - Detect platform (YouTube detected!)                   │
│         - Route to process_youtube()                            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
        ╔══════════════════════════════════════════════════╗
        ║         process_youtube(url)  ← NEW LOGIC        ║
        ║        (Lines 271-500 in bot.py)                ║
        ╚══════════════════════════════════════════════════╝
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
    TRY 1         TRY 2           TRY 3
    ─────         ─────           ─────
    Legacy        Multi-Step       yt-dlp
    API           API              Library


┌─────────────────────────────────────────────────────────────────┐
│                     TRY 1: LEGACY API                           │
│            yt-vid.hazex.workers.dev                            │
└─────────────────────────────────────────────────────────────────┘

    REQUEST:
    https://yt-vid.hazex.workers.dev/?url=<youtube_url>
             │
             ▼
    RESPONSE (JSON):
    {
      "error": false,
      "title": "...",
      "video_with_audio": [         ← Array
        {"height": 360, "url": "..."},
        {"height": 240, "url": "..."}
      ],
      "video_only": [               ← Array
        {"height": 1080, "url": "..."},
        {"height": 720, "url": "..."}
      ],
      "audio": [                    ← Array
        {"bitrate": 132527, "url": "..."}
      ]
    }
             │
             ▼
    PARSE VIDEO_WITH_AUDIO ARRAY:
    ┌──────────────────────────────┐
    │ for item in video_with_audio:│
    │ ├─ Extract height: 360       │
    │ ├─ Extract url               │
    │ ├─ Extract extension: mp4    │
    │ └─ Create normalized entry   │
    └──────────────────────────────┘
      result = {
        'type': 'video_with_audio',
        'height': 360,
        'url': 'https://...',
        'label': 'mp4 (360p) 70.7 MB',
        'size_bytes': 74230321
      }
             │
             ▼
    PARSE VIDEO_ONLY ARRAY:
    ┌──────────────────────────────┐
    │ for item in video_only:      │
    │ ├─ Extract height: 1080      │
    │ ├─ Extract url               │
    │ ├─ Extract extension: mp4    │
    │ └─ Create normalized entry   │
    └──────────────────────────────┘
      results = [
        {'type': 'video_only', 'height': 1080, 'label': 'mp4 (1080p) 232.9 MB'},
        {'type': 'video_only', 'height': 720, 'label': 'mp4 (720p) 60.8 MB'},
        ...
      ]
             │
             ▼
    PARSE AUDIO ARRAY:
    ┌──────────────────────────────┐
    │ for item in audio:           │
    │ ├─ Extract bitrate: 132527   │
    │ ├─ Extract url               │
    │ ├─ Extract extension: m4a    │
    │ └─ Create normalized entry   │
    └──────────────────────────────┘
      results = [
        {'type': 'audio', 'label': 'm4a (132kb/s) 20.2 MB'},
        {'type': 'audio', 'label': 'm4a (33kb/s) 5 MB'},
        ...
      ]
             │
             ▼
    ╔════════════════════════════════════╗
    ║  NORMALIZE ALL ENTRIES             ║
    ║  SORT BY:                          ║
    ║  1. Type priority                  ║
    ║     video_with_audio (0)           ║
    ║     video_only (1)                 ║
    ║     audio (2)                      ║
    ║  2. Resolution (descending)        ║
    ║     1080p > 720p > 480p > ...      ║
    ╚════════════════════════════════════╝
             │
             ▼
    FINAL SORTED LIST:
    [
      {type: 'video_with_audio', height: 360, label: 'mp4 (360p) 70.7 MB'}  ← BEST
      {type: 'video_only', height: 1080, label: 'mp4 (1080p) 232.9 MB'},
      {type: 'video_only', height: 720, label: 'mp4 (720p) 60.8 MB'},
      {type: 'video_only', height: 480, label: 'mp4 (480p) 33.4 MB'},
      {type: 'video_only', height: 360, label: 'mp4 (360p) 23 MB'},
      {type: 'video_only', height: 240, label: 'mp4 (240p) 13 MB'},
      {type: 'audio', label: 'm4a (132kb/s) 20.2 MB'},
      {type: 'audio', label: 'm4a (33kb/s) 5 MB'}
    ]
             │
             ▼
    ✅ SUCCESS! Return to handle_message()


┌─────────────────────────────────────────────────────────────────┐
│  If Legacy API fails → TRY 2: Multi-Step API (get/create/check) │
│  If Multi-Step fails → TRY 3: yt-dlp library fallback            │
│  If all fail → Return error message                              │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│           RETURN TO handle_message() + Display to User           │
└─────────────────────────────────────────────────────────────────┘
             │
             ▼
    ╔════════════════════════════════════╗
    ║  BUILD INLINE KEYBOARD             ║
    ║  (Quality buttons for Telegram)    ║
    ╚════════════════════════════════════╝
             │
      ┌──────┴──────┐
      │             │
      ▼             ▼
   For each    For best
   quality:    quality:
   ─────────   ──────────
   Button      Button 1:
   group 1:    [📤 Upload Best]
   ────────    (Callback to handle_yt_upload_callback)
   [mp4 (360p) 70.7 MB]     → URL button
   [mp4 (1080p) 232.9 MB]   → URL button
   [mp4 (720p) 60.8 MB]     → URL button
   ...
   [m4a (132kb/s) 20.2 MB]  → URL button
             │
             ▼
    ╔════════════════════════════════════╗
    ║  SEND MESSAGE TO USER              ║
    ║  With all buttons                  ║
    ╚════════════════════════════════════╝
             │
             ▼
    Telegram Chat:
    ┌─────────────────────────────────────┐
    │ ✅ Formats Ready                    │
    │ Title: How Every SPIDER-MAN ...     │
    │                                     │
    │ [mp4 (360p) 70.7 MB]        [↓]    │
    │ [mp4 (1080p) 232.9 MB]      [↓]    │
    │ [mp4 (720p) 60.8 MB]        [↓]    │
    │ ...                                 │
    │                                     │
    │ [📤 Upload Best] [⬇️ Download Now] │
    └─────────────────────────────────────┘
             │
      ┌──────┴───────────────────┐
      │ User clicks button        │ 
      │ (any option)              │
      ▼                           ▼
   If URL button:          If Upload Best:
   ──────────────          ─────────────
   Opens external          Calls handle_yt
   download link           _upload_callback()
   in browser              ├─ Sends video file
                           │  to chat directly
                           └─ Shows progress
```

---

## Data Structure Transformations

### Step 1: Raw API Response
```json
{
  "video_with_audio": [
    {
      "label": "mp4 (360p)",
      "type": "video_with_audio",
      "height": 360,
      "extension": "mp4",
      "url": "https://redirector.googlevideo.com/...?clen=74230321"
    }
  ],
  ...
}
```

### Step 2: Extract Size from clen Parameter
```python
if size_bytes is None and 'clen=' in item['url']:
    clen_match = re.search(r'clen=(\d+)', item['url'])
    if clen_match:
        size_bytes = int(clen_match.group(1))  # 74230321 bytes
```

### Step 3: Normalized Entry
```python
{
  'url': 'https://redirector.googlevideo.com/...?clen=74230321',
  'extension': 'mp4',
  'resolution': '360p',
  'size_bytes': 74230321,
  'label': 'mp4 (360p) 70.7 MB',  # ← Formatted for display
  'type': 'video_with_audio',
  'height': 360,
  'raw': {...}
}
```

### Step 4: Human-Readable Label
```
Input:  74230321 bytes
        ↓
        74230321 / 1024 = 72490.55 KB
        ↓
        72490.55 / 1024 = 70.79 MB
        ↓
Output: "70.7 MB"
```

---

## Size Extraction Pipeline

```
URL from API:
https://...?expire=1756004907&...&clen=74230321&...&dur=1313.483&...
                                    ▲
                            Size indicator
                                    │
┌───────────────────────────────────┘
│
▼
Regex search: r'clen=(\d+)'
│
▼
Extract: 74230321
│
▼
Convert to int: 74230321 (bytes)
│
▼
Call human_size(74230321)
│
▼
74230321 / 1024 / 1024 = 70.79 MB
│
▼
Format: "70.7 MB"
│
▼
Display: "[mp4 (360p) 70.7 MB]"
```

---

## Quality Button Rendering

```
Final Normalized List (sorted):
┌──────────────────────────────────────────────┐
│ 1. {type: 'video_with_audio', height: 360} │ ← BEST
│ 2. {type: 'video_only', height: 1080}      │
│ 3. {type: 'video_only', height: 720}       │
│ 4. {type: 'video_only', height: 480}       │
│ 5. {type: 'video_only', height: 360}       │
│ 6. {type: 'video_only', height: 240}       │
│ 7. {type: 'audio', bitrate: 132527}        │
│ 8. {type: 'audio', bitrate: 67760}         │
└──────────────────────────────────────────────┘
             │
    Telegram Keyboard:
             │
    InlineKeyboardMarkup()
    ├─ Row 1: [mp4 (360p) 70.7 MB]  (direct URL link)
    ├─ Row 2: [mp4 (1080p) 232.9 MB] (direct URL link)
    ├─ Row 3: [mp4 (720p) 60.8 MB]   (direct URL link)
    ├─ Row 4: [mp4 (480p) 33.4 MB]   (direct URL link)
    ├─ Row 5: [mp4 (360p) 23 MB]     (direct URL link)
    ├─ Row 6: [mp4 (240p) 13 MB]     (direct URL link)
    ├─ Row 7: [m4a (132kb/s) 20.2 MB] (direct URL link)
    ├─ Row 8: [m4a (67kb/s) 8 MB]    (direct URL link)
    │
    ├─ Row 9: [📤 Upload Best]  (callback: ytupload:sessionid:0)
    └─ Row 10: [⬇️ Download Now] (URL to best quality)
```

---

## Error Handling Flow

```
send YouTube URL
        │
        ▼
Call process_youtube()
        │
    ┌───┴───┐
    │       │
    YES     NO (error)
    │       │
    ▼       ▼
Success  Try API 2
(return) (multi-step)
         │
      ┌──┴───┐
      │      │
      YES    NO (error)
      │      │
      ▼      ▼
   Success Try API 3
   (return) (yt-dlp)
            │
         ┌──┴───┐
         │      │
         YES    NO (error)
         │      │
         ▼      ▼
      Success Return error
      (return) to user
               │
               ▼
            Show user-friendly
            error message:
            
            ❌ Download Failed
            
            Error: Could not fetch video
            
            Possible Solutions:
            • Check if URL is correct
            • Ensure content is public
            • Try again later
            ...
```

---

## Performance Timeline

```
T=0ms    └─ User sends URL
T=100ms  └─ bot.py receives message
T=200ms  └─ URL extracted and validated
T=300ms  └─ process_youtube() called
T=400ms  └─ HTTP request to legacy API sent
T=1000ms └─ Response received from API
T=1100ms └─ Parse video_with_audio array (50ms)
T=1150ms └─ Parse video_only array (50ms)
T=1200ms └─ Parse audio array (50ms)
T=1250ms └─ Normalize all entries (50ms)
T=1300ms └─ Sort by priority & resolution (50ms)
T=1350ms └─ Return to handle_message()
T=1400ms └─ Build Telegram keyboard (100ms)
T=1500ms └─ Send message to user

Total: ~1.5 seconds from URL to quality buttons displayed
```

---

## Code Execution Path

```
handle_message(msg)
├─ Extract URL
├─ Create processing message
├─ Call handle_api_for_url(url)
│  ├─ Detect 'youtube.com' or 'youtu.be'
│  ├─ Call process_youtube(url)
│  │  ├─ fetch_json(YOUTUBE_LEGACY_API, params)
│  │  │  ├─ requests.get() → API call
│  │  │  └─ r.json() → Parse response
│  │  │
│  │  ├─ if legacy_success:
│  │  │  ├─ Iterate video_with_audio[]
│  │  │  ├─ Iterate video_only[]
│  │  │  ├─ Iterate audio[]
│  │  │  ├─ Normalize all entries
│  │  │  ├─ Sort by (type_priority, -height)
│  │  │  └─ return result with qualities
│  │  │
│  │  ├─ else:
│  │  │  ├─ Try multi-step API
│  │  │  ├─ else try yt-dlp
│  │  │  └─ else return error
│  │  │
│  │  └─ return result
│  │
│  └─ return result
│
├─ if result.qualities:
│  ├─ Build InlineKeyboardMarkup()
│  ├─ Add buttons for each quality
│  ├─ Add Upload Best button (callback)
│  ├─ Edit processing message with keyboard
│  └─ return (user sees quality buttons)
│
└─ else:
   ├─ Show error or send file
   └─ return
```

This diagram shows exactly how the new YouTube parser transforms raw API responses into a beautiful, interactive quality selection interface!
