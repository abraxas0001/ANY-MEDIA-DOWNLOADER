import os
import re
import requests
import logging
import tempfile
import shutil
import time
import itertools
import subprocess
import zipfile
from io import BytesIO
from urllib.parse import quote_plus
from pathlib import Path

try:
    import telebot
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
except Exception:
    raise SystemExit('Missing dependency: install from requirements.txt')

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'), override=True)
except ImportError:
    pass  # python-dotenv is optional

LOG = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Read token from .env file or environment variable
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise SystemExit(
        '❌ TELEGRAM_TOKEN not found!\n'
        '📝 Create a .env file with: TELEGRAM_TOKEN=your_token_here\n'
        '   Or set environment variable: $env:TELEGRAM_TOKEN="your_token"'
    )

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

# Bot brand username for consistent signature
BOT_BRAND = '@TeraInstaShortsDownloaderbot'

# Backup channel for archival (optional)
BACKUP_CHANNEL_ID = os.getenv('BACKUP_CHANNEL_ID', '')

YOUTUBE_LEGACY_API = 'https://yt-vid.hazex.workers.dev/'  # retained for fallback
YOUTUBE_MULTI_API = 'https://yt-dl.hazex.workers.dev/'  # Old multi-step API
YOUTUBE_HQ_API = 'https://yt-download.hazex.workers.dev/'  # New high-quality API with format selection
TIKTOK_API = 'https://tiktok-dl.hazex.workers.dev/'
INSTA_API = 'https://insta-dl.hazex.workers.dev/'
# Additional Instagram API variants for better reliability
INSTA_API_ALT = 'https://social-dl.hazex.workers.dev/'
INSTA_API_NODE = 'https://nodejssocialdownloder.onrender.com/revangeapi/download'  # Best for albums
INSTA_SCRAPER_API = 'https://instagram-scraper-api2.p.rapidapi.com/v1/post_info'  # for captions
SOCIAL_DL_API = 'https://social-downloader.apisimpacientes.workers.dev/'
TERA_API = 'https://my-noor-queen-api.woodmirror.workers.dev/api?url='

URL_RE = re.compile(r'(https?://[^\s]+)')

# Configurable limits
MAX_UPLOAD = int(os.getenv('MAX_UPLOAD_MB', '2048')) * 1024 * 1024  # default 2GB
LOCAL_DOWNLOAD_LIMIT = MAX_UPLOAD  # do not locally download more than upload limit
DOWNLOAD_TIMEOUT = 120  # seconds

# Progress tracking for downloads
DOWNLOAD_PROGRESS = {}  # {chat_id: {'msg_id': int, 'percent': float}}


def check_aria2c_available() -> bool:
    """Check if aria2c is available locally or in PATH (unused for Railway)."""
    return False


def ensure_ffmpeg() -> str | None:
    """Ensure ffmpeg binary is available. Returns path or None.
    Strategy:
      1. If bundled ./bin/ffmpeg(.exe) exists use it.
      2. If in PATH return that.
      3. Attempt lightweight download of Windows static build (essentials) zip and extract ffmpeg(.exe).
         Only executed once; subsequent calls reuse cached binary.
    """
    is_win = os.name == 'nt'
    bin_dir = Path(__file__).parent / 'bin'
    ffmpeg_name = 'ffmpeg.exe' if is_win else 'ffmpeg'
    target = bin_dir / ffmpeg_name
    if target.exists():
        return str(target)
    existing = shutil.which('ffmpeg')
    if existing:
        return existing
    try:
        bin_dir.mkdir(exist_ok=True)
        # Use gyan.dev static build for Windows, or John Van Sickle static for Linux
        if is_win:
            url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
        else:
            # Small static build
            url = 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz'
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.content
        if is_win:
            with zipfile.ZipFile(BytesIO(data)) as zf:
                # Find ffmpeg.exe inside extracted folder /ffmpeg-*/bin/ffmpeg.exe
                exe_name = 'ffmpeg.exe'
                member = None
                for m in zf.namelist():
                    if m.lower().endswith('/bin/ffmpeg.exe'):
                        member = m
                        break
                if not member:
                    return None
                with zf.open(member) as src, open(target, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
        else:
            # For Linux extract tar.xz
            import tarfile
            with tempfile.TemporaryDirectory() as tmpd:
                tmp_path = Path(tmpd) / 'ffmpeg.tar.xz'
                with open(tmp_path, 'wb') as f:
                    f.write(data)
                with tarfile.open(tmp_path, 'r:xz') as tf:
                    member = None
                    for m in tf.getmembers():
                        if m.name.endswith('/ffmpeg') and '/bin/' in m.name:
                            member = m
                            break
                    if not member:
                        # fallback: first ffmpeg found
                        for m in tf.getmembers():
                            if m.name.endswith('/ffmpeg'):
                                member = m
                                break
                    if not member:
                        return None
                    tf.extract(member, path=bin_dir)
                    # Move to target
                    extracted_path = bin_dir / member.name
                    if extracted_path.exists():
                        shutil.move(str(extracted_path), target)
        if target.exists():
            try:
                os.chmod(target, 0o755)
            except Exception:
                pass
            return str(target)
    except Exception:
        LOG.warning('Failed to auto-download ffmpeg')
        return None
    return None


def forward_to_backup_channel(chat_id, file_id, media_type, caption, username):
    """Forward downloaded media to backup channel for archival (optional feature)."""
    if not BACKUP_CHANNEL_ID:
        return
    try:
        backup_caption = f"📥 {caption}\n👤 User: @{username}\n🆔 Chat ID: {chat_id}"
        
        if media_type == 'video':
            bot.send_video(BACKUP_CHANNEL_ID, file_id, caption=backup_caption)
        elif media_type == 'photo':
            bot.send_photo(BACKUP_CHANNEL_ID, file_id, caption=backup_caption)
        elif media_type == 'audio':
            bot.send_audio(BACKUP_CHANNEL_ID, file_id, caption=backup_caption)
        else:
            bot.send_document(BACKUP_CHANNEL_ID, file_id, caption=backup_caption)
        
        LOG.info('Media forwarded to backup channel: %s', file_id)
    except Exception as e:
        LOG.warning('Failed to forward to backup channel: %s', e)


def stream_download(url: str, dest_path: Path, max_bytes: int, progress_callback=None) -> bool:
    """Stream download the file to dest_path enforcing max_bytes; return True on success.
    progress_callback: optional function(downloaded_bytes, total_bytes) for progress updates
    """
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        LOG.warning('File exceeds max_bytes during download (%s > %s)', downloaded, max_bytes)
                        return False
                    f.write(chunk)
                    
                    # Call progress callback if provided
                    if progress_callback and total_size > 0:
                        try:
                            progress_callback(downloaded, total_size)
                        except Exception:
                            pass  # Don't let callback errors stop download
        return True
    except Exception:
        LOG.exception('Local streaming download failed for %s', url)
        return False


def fetch_json(url, params=None, timeout=30):
    """Fetch JSON with retry logic and better error handling."""
    max_retries = 2
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            LOG.warning(f'Timeout fetching {url} (attempt {attempt+1}/{max_retries})')
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
            else:
                return {'error': 'Request timeout', 'timeout': True}
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else None
            LOG.warning('HTTP error %s from %s: %s', status_code, url, str(e))
            return {'error': str(e), 'status_code': status_code}
        except requests.exceptions.ConnectionError as e:
            LOG.warning(f'Connection error fetching {url} (attempt {attempt+1}/{max_retries}): {e}')
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return {'error': 'Connection failed', 'connection_error': True}
        except Exception as e:
            LOG.exception('Failed to fetch JSON from %s', url)
            return {'error': str(e)}
    return {'error': 'All retry attempts failed'}


def find_download_entries(obj):
    """Recursively find dicts that include a 'url' field in API responses."""
    results = []
    if isinstance(obj, dict):
        if 'url' in obj and isinstance(obj['url'], str):
            results.append(obj)
        for v in obj.values():
            results.extend(find_download_entries(v))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(find_download_entries(item))
    return results


def choose_entry(entries):
    # Prefer mp4 / video entries if available, otherwise first
    if not entries:
        return None
    for ext in ('mp4', 'mkv', 'webm', 'mp3', 'm4a'):
        for e in entries:
            if e.get('extension') and e.get('extension').lower().startswith(ext):
                return e
    return entries[0]


def human_size(bytes_val):
    try:
        b = int(bytes_val)
    except Exception:
        return str(bytes_val)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if b < 1024:
            return f"{b:.2f} {unit}"
        b /= 1024.0
    return f"{b:.2f} TB"


def clean_caption(raw):
    if not raw:
        return None
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    # Remove standalone hashtag lines but keep inline non-hashtag words
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    cleaned_parts = []
    for line in lines:
        lower_line = line.lower()
        # Skip filler lines
        if line in ['.', '..', '...']:
            continue
        if 'follow' in lower_line and '@' in lower_line:
            # treat promotional follow lines as noise
            continue
        if all(part.startswith('#') for part in line.split()):
            continue
        words = [w for w in line.split() if not w.startswith('#')]
        # Remove trailing promotional patterns like 'for' 'more'
        if words and len(words) <= 3 and 'follow' in lower_line:
            continue
        if words:
            cleaned_parts.append(' '.join(words))
    cleaned = ' '.join(cleaned_parts).strip()
    if len(cleaned) == 0:
        return None
    if len(cleaned) > 1024:
        cleaned = cleaned[:1024] + '...'
    return cleaned


def extract_instagram_caption(data):
    """Attempt deep extraction of Instagram caption text from various response shapes."""
    candidates = []

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                kl = str(k).lower()
                if kl in ['caption', 'title', 'description', 'text', 'post_caption']:
                    if isinstance(v, str):
                        candidates.append(v)
                # Edge caption pattern
                if kl in ['edge_media_to_caption', 'edge_media_to_comment'] and isinstance(v, dict):
                    edges = v.get('edges', [])
                    for edge in edges:
                        if isinstance(edge, dict):
                            node = edge.get('node', {})
                            txt = node.get('text')
                            if isinstance(txt, str):
                                candidates.append(txt)
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    # Prioritize longer non-hashtag lines
    cleaned = [clean_caption(c) for c in candidates if c]
    cleaned = [c for c in cleaned if c]
    if not cleaned:
        return None
    # Prefer first meaningful sentence (split by '.')
    for c in cleaned:
        # Attempt to get first line before hashtags
        first_line = c.split('#')[0].strip()
        # Truncate at promotional follow lines
        if 'follow' in first_line.lower() and '@' in first_line.lower():
            # try next
            continue
        # Further split by newline
        first_segment = first_line.split('\n')[0].strip()
        if len(first_segment) > 3:
            return first_segment
    return cleaned[0]

def scrape_instagram_page(post_url):
    """Attempt lightweight HTML scrape to extract carousel (GraphSidecar) media URLs for /p/ posts.
    Returns (caption, [urls]). Only works for public posts; silent failure returns empty list."""
    try:
        import re, json
        post_url = post_url.split('?')[0]  # Clean URL
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'}
        r = requests.get(post_url, headers=headers, timeout=15)
        if not r.ok:
            LOG.warning('HTML scrape failed: HTTP %s', r.status_code)
            return None, []
        html = r.text
        LOG.info('Fetched HTML length: %s', len(html))
        m = re.search(r'<script type="application/json" id="__NEXT_DATA__">(.*?)</script>', html)
        data_json = None
        if m:
            LOG.info('Found __NEXT_DATA__ script')
            try:
                data_json = json.loads(m.group(1))
            except Exception as e:
                LOG.warning('Failed to parse __NEXT_DATA__: %s', e)
                data_json = None
        if not data_json:
            m2 = re.search(r'window\._sharedData\s*=\s*(\{.*?\})\s*;<', html)
            if m2:
                LOG.info('Found _sharedData script')
                try:
                    data_json = json.loads(m2.group(1))
                except Exception as e:
                    LOG.warning('Failed to parse _sharedData: %s', e)
                    data_json = None
        if not data_json:
            LOG.warning('No JSON data found in HTML')
            return None, []
        LOG.info('Successfully parsed JSON data')
        media_urls = []
        caption_text = None
        def walk(o):
            nonlocal caption_text
            if isinstance(o, dict):
                # caption extraction
                emc = o.get('edge_media_to_caption')
                if isinstance(emc, dict):
                    edges = emc.get('edges') or []
                    for edge in edges:
                        if isinstance(edge, dict):
                            node = edge.get('node', {})
                            txt = node.get('text')
                            if isinstance(txt, str) and not caption_text:
                                caption_text = txt
                if o.get('__typename') in ['GraphImage', 'GraphVideo']:
                    link = o.get('display_url') or o.get('video_url') or o.get('url')
                    if link and link not in media_urls:
                        media_urls.append(link)
                if o.get('__typename') == 'GraphSidecar':
                    children = o.get('edge_sidecar_to_children', {}).get('edges', [])
                    LOG.info('Found GraphSidecar with %s children', len(children))
                    for ch in children:
                        if isinstance(ch, dict):
                            node = ch.get('node', {})
                            link = node.get('display_url') or node.get('video_url') or node.get('url')
                            if link and link not in media_urls:
                                media_urls.append(link)
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for i in o:
                    walk(i)
        walk(data_json)
        LOG.info('Walk completed, found %s media URLs', len(media_urls))
        return clean_caption(caption_text) if caption_text else None, media_urls
    except Exception as e:
        LOG.exception('HTML scrape exception: %s', e)
        return None, []


def get_instagram_with_ytdlp_fallback(url):
    """Try Instagram API first, fallback to yt-dlp for better caption/media extraction."""
    try:
        import yt_dlp
        url = url.split('?')[0]  # Clean URL
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'retries': 2
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                caption = (info.get('description') or 
                          info.get('title') or 
                          info.get('alt_title') or "")
                
                media_urls = []
                # Check if it's a multi-image/video post
                if 'entries' in info and info['entries']:
                    for entry in info['entries']:
                        if entry and entry.get('url'):
                            media_urls.append(entry['url'])
                elif info.get('url'):
                    media_urls.append(info['url'])
                
                return caption.strip(), media_urls
    except Exception as e:
        LOG.warning('yt-dlp Instagram fallback failed: %s', e)
    return None, []


def get_terabox_with_ytdlp_fallback(url):
    """Try Terabox with yt-dlp as fallback - with aggressive retry and timeout config."""
    try:
        import yt_dlp
        url_clean = url.split('?')[0]  # Clean URL
        
        # Configure yt-dlp with retry and timeout settings + best format selection
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'format': 'best',  # Select best available quality
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
            'skip_unavailable_fragments': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_clean, download=False)
            if info:
                dl_url = info.get('url')
                if dl_url:
                    file_name = info.get('title') or os.path.basename((dl_url or '').split('?')[0]) or 'terabox_file'
                    size_bytes = info.get('filesize') or info.get('filesize_approx')
                    caption = clean_caption(info.get('description') or info.get('title'))
                    LOG.info('✅ yt-dlp Terabox fallback succeeded')
                    return {
                        'url': dl_url,
                        'size_bytes': int(size_bytes) if size_bytes else None,
                        'file_name': file_name,
                        'caption': caption,
                        'button_url': dl_url,
                        'raw_data': {'source': 'yt-dlp', 'url_clean': url_clean}
                    }
    except Exception as e:
        LOG.warning('yt-dlp Terabox fallback failed: %s', e)
    return None


def process_youtube(url):
    """Use new high-quality YouTube API with format selection (360p-1440p), then legacy API, then yt-dlp fallback."""
    # Try new high-quality API first (supports 360, 480, 720, 1080, 1440)
    LOG.info('YouTube: Trying HQ API first...')
    try:
        # Step 1: Get video info and hash
        get_resp = fetch_json(YOUTUBE_HQ_API, params={'function': 'get_task', 'url': url})
        LOG.info(f'YouTube HQ API get_task response: {get_resp}')
        
        if get_resp and not get_resp.get('error'):
            video_hash = get_resp.get('hash')
            title = get_resp.get('title', 'YouTube Video')
            thumbnail = get_resp.get('thumbnail')
            
            if video_hash:
                LOG.info(f'YouTube HQ API: Got hash {video_hash}, fetching qualities...')
                # Step 2: Create tasks for different quality formats
                formats_to_try = ['1440', '1080', '720', '480', '360']  # Try highest first
                qualities = []
                
                for fmt in formats_to_try:
                    try:
                        # Create task with specific format
                        create_resp = fetch_json(YOUTUBE_HQ_API, params={'function': 'create_task', 'hash': video_hash, 'format': fmt})
                        if create_resp and not create_resp.get('error'):
                            task_id = create_resp.get('task_id')
                            if task_id:
                                # Check task status - may need multiple attempts
                                for attempt in range(3):
                                    time.sleep(1)  # Wait for task processing
                                    check_resp = fetch_json(YOUTUBE_HQ_API, params={'function': 'check_task', 'task_id': task_id})
                                    if check_resp and check_resp.get('status') == 'completed':
                                        download_url = check_resp.get('download_url')
                                        if download_url:
                                            size_bytes = check_resp.get('file_size')
                                            qualities.append({
                                                'url': download_url,
                                                'extension': 'mp4',
                                                'resolution': f'{fmt}p',
                                                'size_bytes': size_bytes,
                                                'label': f'{fmt}p' + (f' {human_size(size_bytes)}' if size_bytes else ''),
                                                'type': 'video_with_audio',
                                                'has_audio': True,
                                                'height': int(fmt),
                                                'raw': check_resp
                                            })
                                            LOG.info(f'YouTube HQ API: Got {fmt}p quality')
                                            break
                                    elif check_resp and check_resp.get('status') == 'processing':
                                        continue  # Retry
                                    else:
                                        break  # Failed or other status
                    except Exception as e:
                        LOG.warning(f'YouTube HQ API: Failed to get {fmt}p - {e}')
                        continue
                
                if qualities:
                    # Sort by height descending (best quality first)
                    qualities.sort(key=lambda q: q['height'], reverse=True)
                    best_entry = qualities[0]
                    
                    safe_title = (title or 'youtube_video').replace(' ', '_')[:80]
                    inferred_file = f"{safe_title}_{best_entry.get('resolution')}.mp4"
                    caption = clean_caption(title)
                    
                    LOG.info(f'YouTube HQ API: Successfully parsed {len(qualities)} qualities')
                    return {
                        'url': best_entry['url'],
                        'size_bytes': best_entry.get('size_bytes'),
                        'file_name': inferred_file,
                        'caption': caption,
                        'qualities': qualities,
                        'best_index': 0,
                        'thumbnail': thumbnail,
                        'raw_entry': best_entry['raw'],
                        'raw_data': get_resp
                    }
                else:
                    LOG.warning('YouTube HQ API: No qualities extracted, falling back to legacy')
            else:
                LOG.warning('YouTube HQ API: No hash received, falling back to legacy')
    except Exception as e:
        LOG.warning(f'YouTube HQ API failed: {e}')
    
    # Fallback to legacy API (yt-vid.hazex) which has structured video_with_audio/video_only/audio arrays
    LOG.info('YouTube: Using legacy API fallback')
    legacy = fetch_json(YOUTUBE_LEGACY_API, params={'url': url})
    if legacy and not legacy.get('error'):
        # Parse legacy API response with video_with_audio, video_only, audio structure
        normalized = []
        title = legacy.get('title', 'YouTube Video')
        thumbnail = legacy.get('thumbnail') or legacy.get('thumb') or legacy.get('image')  # Extract thumbnail URL
        
        # Process video_with_audio (combined video + audio) - highest priority
        video_with_audio = legacy.get('video_with_audio', [])
        if isinstance(video_with_audio, list):
            for item in video_with_audio:
                if not isinstance(item, dict) or not item.get('url'):
                    continue
                res = item.get('label', '')  # e.g., "mp4 (360p)"
                height = item.get('height')
                width = item.get('width')
                ext = item.get('extension', 'mp4').lower()
                size_bytes = item.get('size_bytes')
                
                # Parse size from clen if available
                if size_bytes is None and 'clen=' in item.get('url', ''):
                    try:
                        clen_match = re.search(r'clen=(\d+)', item['url'])
                        if clen_match:
                            size_bytes = int(clen_match.group(1))
                    except Exception:
                        pass
                
                # Build label: resolution + size
                label_parts = [res] if res else [f"{height}p" if height else "Video"]
                if size_bytes:
                    label_parts.append(human_size(size_bytes))
                label = ' '.join(label_parts)
                
                normalized.append({
                    'url': item['url'],
                    'extension': ext,
                    'resolution': f"{height}p" if height else res,
                    'size_bytes': size_bytes,
                    'label': label,
                    'type': 'video_with_audio',
                    'has_audio': True,
                    'height': height or 0,
                    'raw': item
                })
        
        # Process video_only (video stream without audio) - secondary
        video_only = legacy.get('video_only', [])
        if isinstance(video_only, list):
            for item in video_only:
                if not isinstance(item, dict) or not item.get('url'):
                    continue
                res = item.get('label', '')
                height = item.get('height')
                ext = item.get('extension', 'mp4').lower()
                size_bytes = item.get('size_bytes')
                
                if size_bytes is None and 'clen=' in item.get('url', ''):
                    try:
                        clen_match = re.search(r'clen=(\d+)', item['url'])
                        if clen_match:
                            size_bytes = int(clen_match.group(1))
                    except Exception:
                        pass
                
                label_parts = [res] if res else [f"{height}p" if height else "Video (no audio)"]
                if size_bytes:
                    label_parts.append(human_size(size_bytes))
                label = ' '.join(label_parts)
                
                normalized.append({
                    'url': item['url'],
                    'extension': ext,
                    'resolution': f"{height}p" if height else res,
                    'size_bytes': size_bytes,
                    'label': label,
                    'type': 'video_only',
                    'has_audio': False,
                    'height': height or 0,
                    'raw': item
                })
        
        # Process audio-only options
        audio = legacy.get('audio', [])
        if isinstance(audio, list):
            for item in audio:
                if not isinstance(item, dict) or not item.get('url'):
                    continue
                res = item.get('label', '')
                bitrate = item.get('bitrate')
                ext = item.get('extension', 'm4a').lower()
                size_bytes = item.get('size_bytes')
                
                if size_bytes is None and 'clen=' in item.get('url', ''):
                    try:
                        clen_match = re.search(r'clen=(\d+)', item['url'])
                        if clen_match:
                            size_bytes = int(clen_match.group(1))
                    except Exception:
                        pass
                
                label_parts = [res or f"Audio {ext.upper()}"] 
                if size_bytes:
                    label_parts.append(human_size(size_bytes))
                label = ' '.join(label_parts)
                
                normalized.append({
                    'url': item['url'],
                    'extension': ext,
                    'resolution': 'Audio',
                    'size_bytes': size_bytes,
                    'label': label,
                    'type': 'audio',
                    'has_audio': True,
                    'height': 0,
                    'raw': item
                })
        
        if normalized:
            # Choose best: video_with_audio (prefer highest resolution), then video_only
            # Sort by: type priority (video_with_audio first), then by height descending
            def sort_key(item):
                type_priority = {'video_with_audio': 0, 'video_only': 1, 'audio': 2}
                return (type_priority.get(item['type'], 3), -(item['height']))
            
            normalized.sort(key=sort_key)
            best_entry = normalized[0]
            best_index = normalized.index(best_entry)
            
            safe_title = (title or 'youtube_video').replace(' ', '_')[:80]
            inferred_file = f"{safe_title}_{best_entry.get('resolution') or 'video'}.mp4"
            caption = clean_caption(legacy.get('title')) or clean_caption(legacy.get('description'))
            
            LOG.info('YouTube: parsed %d qualities from legacy API', len(normalized))
            return {
                'url': best_entry['url'],
                'size_bytes': best_entry['size_bytes'],
                'file_name': inferred_file,
                'caption': caption,
                'qualities': normalized,
                'best_index': best_index,
                'thumbnail': thumbnail,  # Add thumbnail URL
                'raw_entry': best_entry['raw'],
                'raw_data': legacy
            }
    
    # Fallback to multi-step API (get_task -> create_task -> check_task)
    base = YOUTUBE_MULTI_API
    get_resp = fetch_json(base, params={'function': 'get_task', 'url': url})
    if get_resp.get('error'):
        # Try yt-dlp fallback as last resort
        LOG.warning('YouTube APIs failed, using yt-dlp fallback')
        try:
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',  # Prefer best quality with audio
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    formats = info.get('formats', [])
                    normalized = []
                    for f in formats:
                        if not f.get('url'):
                            continue
                        vcodec = f.get('vcodec')
                        acodec = f.get('acodec')
                        if vcodec == 'none' and acodec == 'none':
                            continue
                        if vcodec != 'none' and (acodec and acodec != 'none'):
                            ftype = 'video_with_audio'
                            has_audio = True
                        elif vcodec != 'none' and (not acodec or acodec == 'none'):
                            ftype = 'video_only'
                            has_audio = False
                        elif acodec and acodec != 'none' and (not vcodec or vcodec == 'none'):
                            ftype = 'audio'
                            has_audio = True
                        else:
                            ftype = 'unknown'
                            has_audio = False
                        normalized.append({
                            'url': f['url'],
                            'extension': f.get('ext', 'mp4'),
                            'resolution': f"{f.get('height', '?')}p" if f.get('height') else f.get('format_note', ''),
                            'size_bytes': f.get('filesize') or f.get('filesize_approx'),
                            'label': f"{f.get('height', '?')}p ({human_size(f.get('filesize') or f.get('filesize_approx') or 0)})",
                            'type': ftype,
                            'has_audio': has_audio,
                            'height': f.get('height') or 0,
                            'raw': f
                        })
                    if normalized:
                        best = max(normalized, key=lambda x: x['raw'].get('height', 0) if x['raw'].get('height') else 0)
                        return {
                            'url': best['url'],
                            'size_bytes': best['size_bytes'],
                            'file_name': f"{info.get('title', 'video')[:80]}.mp4",
                            'caption': clean_caption(info.get('title')),
                            'qualities': normalized,
                            'best_index': normalized.index(best),
                            'raw_entry': best['raw'],
                            'raw_data': info
                        }
        except Exception as e:
            LOG.warning('yt-dlp fallback also failed: %s', e)
        return {'error': get_resp.get('error')}
    
    hash_val = get_resp.get('hash') or get_resp.get('video_hash') or get_resp.get('data', {}).get('hash')
    title = get_resp.get('title') or get_resp.get('video_title') or get_resp.get('data', {}).get('title')
    if not hash_val:
        return {'error': 'No hash returned from get_task'}

    # Step 2: create_task
    create_resp = fetch_json(base, params={'function': 'create_task', 'hash': hash_val})
    if create_resp.get('error'):
        return {'error': create_resp.get('error')}
    task_id = create_resp.get('task_id') or create_resp.get('id') or create_resp.get('data', {}).get('task_id')
    if not task_id:
        return {'error': 'No task_id returned from create_task'}

    # Step 3: poll check_task
    start = time.time()
    final_resp = None
    while time.time() - start < 90:
        chk = fetch_json(base, params={'function': 'check_task', 'task_id': task_id})
        if chk.get('error'):
            return {'error': chk.get('error')}
        status = chk.get('status') or chk.get('state') or chk.get('data', {}).get('status')
        if status and str(status).lower() in ['finished', 'success', 'completed', 'done']:
            final_resp = chk
            break
        entries_probe = find_download_entries(chk)
        if entries_probe:
            final_resp = chk
            break
        time.sleep(2)
    if final_resp is None:
        return {'error': 'Timeout waiting for YouTube task to finish'}

    entries = find_download_entries(final_resp)
    if not entries and isinstance(final_resp, dict):
        for key in ['formats', 'qualities', 'videos', 'data']:
            maybe = final_resp.get(key)
            if isinstance(maybe, list):
                for item in maybe:
                    if isinstance(item, dict) and 'url' in item:
                        entries.append(item)
    if not entries:
        return {'error': 'No downloadable formats found', 'raw': final_resp}

    def score(e):
        ext = (e.get('extension') or e.get('ext') or '').lower()
        res = e.get('resolution') or e.get('quality') or e.get('qualityLabel') or ''
        num = 0
        m = re.search(r'(\d{3,4})p', str(res))
        if m:
            num = int(m.group(1))
        bonus = 10000 if 'mp4' in ext else 0
        return num + bonus

    normalized = []
    for e in entries:
        url_e = e.get('url')
        if not url_e:
            continue
        ext = (e.get('extension') or e.get('ext') or 'mp4').lower()
        res = e.get('resolution') or e.get('quality') or e.get('qualityLabel') or ''
        size_e = None
        for size_key in ['size_bytes', 'filesize', 'filesize_approx', 'size']:
            val = e.get(size_key)
            if val:
                try:
                    size_e = int(val)
                    break
                except Exception:
                    pass
        label = res or ext
        if size_e:
            label += f" ({human_size(size_e)})"
        vcodec = e.get('vcodec')
        acodec = e.get('acodec')
        if vcodec and vcodec != 'none' and acodec and acodec != 'none':
            ftype = 'video_with_audio'
            has_audio = True
        elif vcodec and vcodec != 'none' and (not acodec or acodec == 'none'):
            ftype = 'video_only'
            has_audio = False
        elif acodec and acodec != 'none' and (not vcodec or vcodec == 'none'):
            ftype = 'audio'
            has_audio = True
        else:
            ftype = 'unknown'
            has_audio = False
        normalized.append({
            'url': url_e,
            'extension': ext,
            'resolution': res,
            'size_bytes': size_e,
            'label': label,
            'type': ftype,
            'has_audio': has_audio,
            'height': e.get('height') or 0,
            'raw': e
        })
    if not normalized:
        return {'error': 'No valid YouTube formats'}
    best_entry = sorted(normalized, key=lambda e: score(e['raw']), reverse=True)[0]
    best_index = normalized.index(best_entry)
    safe_title = (title or 'youtube_video').replace(' ', '_')[:80]
    inferred_file = f"{safe_title}_{best_entry.get('resolution') or 'video'}.mp4"
    caption = clean_caption(title) or clean_caption(best_entry['raw'].get('title')) or clean_caption(get_resp.get('description'))
    return {
        'url': best_entry['url'],
        'size_bytes': best_entry['size_bytes'],
        'file_name': inferred_file,
        'caption': caption,
        'qualities': normalized,
        'best_index': best_index,
        'raw_entry': best_entry['raw'],
        'raw_data': final_resp
    }
# Session store for YouTube format selections
FORMAT_SESSIONS = {}
SESSION_COUNTER = itertools.count(1)



def handle_api_for_url(url):
    """Pick which API to call and return a dict with file info or error."""
    lower = url.lower()
    data = None
    # YouTube (videos & shorts)
    if 'youtube.com' in lower or 'youtu.be' in lower:
        yt_result = process_youtube(url)
        if yt_result.get('error'):
            LOG.warning('Multi-step YouTube API failed: %s; trying legacy', yt_result.get('error'))
            legacy = fetch_json(YOUTUBE_LEGACY_API, params={'url': url})
            if legacy and not legacy.get('error'):
                data = legacy
            else:
                return yt_result
        else:
            return yt_result
    elif 'tiktok.com' in lower:
        data = fetch_json(TIKTOK_API, params={'url': url})
        if not data or data.get('error'):
            return {'error': data.get('error') if isinstance(data, dict) else 'TikTok API error'}
        result_block = data.get('result') or {}
        entries = []
        dl = result_block.get('download_url', {})
        if isinstance(dl, dict):
            if dl.get('without_watermark'):
                entries.append({'url': dl.get('without_watermark'), 'extension': 'mp4', 'variant': 'nowm'})
            if dl.get('with_watermark'):
                entries.append({'url': dl.get('with_watermark'), 'extension': 'mp4', 'variant': 'wm'})
        if result_block.get('audio'):
            entries.append({'url': result_block.get('audio'), 'extension': 'mp3', 'variant': 'audio'})
        if not entries:
            return {'error': 'No TikTok media URLs found', 'raw': data}
        preferred = None
        for e in entries:
            if e.get('variant') == 'nowm':
                preferred = e
                break
        if not preferred:
            preferred = entries[0]
        file_title = result_block.get('title') or result_block.get('profile_name') or 'tiktok_video'
        variant_suffix = '' if preferred.get('variant') == 'nowm' else '_' + preferred.get('variant')
        file_name = (file_title.replace(' ', '_')[:80] + variant_suffix + '.' + (preferred.get('extension') or 'mp4'))
        caption = clean_caption(result_block.get('title')) or clean_caption(file_title)
        return {'url': preferred.get('url'), 'size_bytes': None, 'file_name': file_name, 'caption': caption, 'raw_entry': preferred, 'raw_data': data}
    elif 'instagram.com' in lower:
        is_reel = '/reel/' in url.lower()
        is_post = '/p/' in url.lower()
        # First try yt-dlp for albums/carousels (best multi-item support)
        LOG.info('Trying yt-dlp first for Instagram (best for albums/carousels)')
        ytdlp_caption, ytdlp_media = get_instagram_with_ytdlp_fallback(url)
        # Reels: force single video behavior
        if is_reel:
            chosen = None
            if ytdlp_media:
                chosen = ytdlp_media[0]
            # If no media from yt-dlp, proceed with API attempts below
            if chosen:
                return {
                    'url': chosen,
                    'file_name': os.path.basename(chosen.split('?')[0]) or 'instagram_reel.mp4',
                    'size_bytes': None,
                    'caption': clean_caption(ytdlp_caption) if ytdlp_caption else None,
                    'is_video': True,
                    'is_image': False,
                    'raw_data': {'source': 'yt-dlp', 'type': 'reel'}
                }
        # Posts (potential carousel) - if multiple items from yt-dlp treat as album
        if not is_reel and ytdlp_media and len(ytdlp_media) > 1:
            LOG.info('yt-dlp found %s media items (album/carousel)', len(ytdlp_media))
            items = []
            for idx, media_url in enumerate(ytdlp_media, start=1):
                items.append({
                    'url': media_url,
                    'file_name': os.path.basename(media_url.split('?')[0]) or f'instagram_media_{idx}.jpg',
                    'size_bytes': None,
                    'is_image': any(media_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']),
                    'is_video': any(media_url.lower().endswith(ext) for ext in ['.mp4', '.mov', '.webm'])
                })
            return {
                'items': items,
                'caption': clean_caption(ytdlp_caption) if ytdlp_caption else None,
                'raw_data': {'source': 'yt-dlp', 'item_count': len(items), 'type': 'post_carousel'}
            }
        
        # Try multiple Instagram API resolvers for single items
        data = None
        for api_url in [INSTA_API_NODE, INSTA_API, INSTA_API_ALT, SOCIAL_DL_API]:
            try:
                resp = fetch_json(api_url, params={'url': url})
            except Exception as e:
                LOG.warning('Instagram API exception at %s: %s', api_url, e)
                resp = {'error': str(e)}
            # Consider response usable if it has no error and contains any URL entries
            if resp and not resp.get('error'):
                probe = find_download_entries(resp)
                if probe:
                    data = resp
                    LOG.info('Instagram resolved via %s', api_url)
                    break
                # Some APIs return images/videos arrays
                if isinstance(resp, dict) and (resp.get('images') or resp.get('videos')):
                    data = resp
                    LOG.info('Instagram resolved (images/videos) via %s', api_url)
                    break
            else:
                LOG.warning('Instagram API returned error from %s: %s', api_url, (resp or {}).get('error'))
        
        # If APIs failed but yt-dlp got something, use it
        if not data or data.get('error'):
            if ytdlp_media:
                LOG.info('APIs failed, using yt-dlp result (%s items)', len(ytdlp_media))
                items = []
                for idx, media_url in enumerate(ytdlp_media, start=1):
                    items.append({
                        'url': media_url,
                        'file_name': os.path.basename(media_url.split('?')[0]) or f'instagram_media_{idx}.jpg',
                        'size_bytes': None,
                        'is_image': any(media_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']),
                        'is_video': any(media_url.lower().endswith(ext) for ext in ['.mp4', '.mov', '.webm'])
                    })
                return {
                    'items': items,
                    'caption': clean_caption(ytdlp_caption) if ytdlp_caption else None,
                    'raw_data': {'source': 'yt-dlp', 'item_count': len(items)}
                }
            data = {'error': 'All Instagram APIs failed'}
        
        # Try to fetch caption from alternate source or use yt-dlp caption
        caption_text = ytdlp_caption if ytdlp_caption else None
        if not caption_text:
            try:
                # Extract post code from URL (e.g., /reel/ABC/ or /p/ABC/)
                import re
                match = re.search(r'/(p|reel|tv)/([A-Za-z0-9_-]+)', url)
                if match:
                    shortcode = match.group(2)
                    # Simple public caption scraper
                    caption_url = f'https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis'
                    caption_resp = requests.get(caption_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                    if caption_resp.ok:
                        caption_json = caption_resp.json()
                        # Navigate through Instagram's JSON structure
                        items = caption_json.get('items', [])
                        if items and len(items) > 0:
                            item = items[0]
                            caption_obj = item.get('caption')
                            if caption_obj and isinstance(caption_obj, dict):
                                caption_text = caption_obj.get('text')
            except Exception:
                LOG.warning('Could not fetch Instagram caption from alternate source')
        
        # Store caption in data for later extraction
        if caption_text and isinstance(data, dict):
            if 'result' not in data:
                data['result'] = {}
            if isinstance(data['result'], dict):
                data['result']['caption'] = caption_text
            else:
                data['caption'] = caption_text

        # Collect explicit Instagram media arrays (images/videos) if present
        explicit_items = []
        if isinstance(data, dict):
            img_list = data.get('images') or (isinstance(data.get('result'), dict) and data['result'].get('images'))
            vid_list = data.get('videos') or (isinstance(data.get('result'), dict) and data['result'].get('videos'))
            def parse_size(raw_size):
                # raw_size may be like '159.9 KB' or bytes int; we standardize
                if raw_size is None:
                    return None, None
                if isinstance(raw_size, (int, float)):
                    return int(raw_size), human_size(int(raw_size))
                if isinstance(raw_size, str):
                    s = raw_size.strip()
                    try:
                        # Extract number and unit
                        import re
                        m = re.match(r'(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB)', s, re.I)
                        if m:
                            num = float(m.group(1))
                            unit = m.group(2).upper()
                            mult = {'B':1,'KB':1024,'MB':1024**2,'GB':1024**3,'TB':1024**4}[unit]
                            bytes_val = int(num * mult)
                            return bytes_val, human_size(bytes_val)
                    except Exception:
                        pass
                    return None, s  # keep original string for display
                return None, None
            if isinstance(img_list, list):
                for idx, im in enumerate(img_list, start=1):
                    if isinstance(im, dict) and im.get('url'):
                        size_bytes, size_text = parse_size(im.get('size') or im.get('filesize'))
                        explicit_items.append({
                            'url': im['url'],
                            'file_name': os.path.basename(im['url'].split('?')[0]) or f'instagram_image_{idx}.jpg',
                            'size_bytes': size_bytes,
                            'size_text': size_text,
                            'is_image': True,
                            'is_video': False
                        })
            if isinstance(vid_list, list):
                for idx, vd in enumerate(vid_list, start=1):
                    if isinstance(vd, dict) and vd.get('url'):
                        size_bytes, size_text = parse_size(vd.get('size') or vd.get('filesize'))
                        explicit_items.append({
                            'url': vd['url'],
                            'file_name': os.path.basename(vd['url'].split('?')[0]) or f'instagram_video_{idx}.mp4',
                            'size_bytes': size_bytes,
                            'size_text': size_text,
                            'is_image': False,
                            'is_video': True
                        })
        # If explicit items gathered, attach so downstream album logic can use them
        if explicit_items:
            data.setdefault('result', {})
            if isinstance(data['result'], dict):
                data['result']['__explicit_items'] = explicit_items
    elif '1024tera' in lower or 'terabox' in lower or '1024' in lower:
        # Try multiple Terabox APIs with aggressive fallback chain and retries
        apis_to_try = [
            ('Noor API', TERA_API + quote_plus(url), {'timeout': 30}),
            ('SOCIAL_DL API', SOCIAL_DL_API, {'timeout': 30, 'params': {'url': url}}),
        ]
        
        for api_name, api_url_or_base, kwargs in apis_to_try:
            for attempt in range(2):  # 2 attempts per API
                try:
                    LOG.info(f'Terabox: Attempt {attempt+1} with {api_name}...')
                    
                    if 'params' in kwargs:
                        data = fetch_json(api_url_or_base, **kwargs)
                    else:
                        data = fetch_json(api_url_or_base, **kwargs)
                    
                    if data:
                        LOG.info(f'{api_name} response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}')
                    
                    # Process successful API response (skip if error or status_code present)
                    if isinstance(data, dict) and not data.get('error') and not data.get('status_code'):
                        # Try multiple possible response keys
                        dl = data.get('proxy_url') or data.get('download_link') or data.get('url') or data.get('directUrl')
                        if dl:
                            file_name = data.get('file_name') or data.get('filename') or data.get('title') or os.path.basename((dl or '').split('?')[0]) or 'terabox_file'
                            size_bytes = None
                            try:
                                if data.get('size_bytes') is not None:
                                    size_bytes = int(data.get('size_bytes'))
                                elif data.get('size') is not None:
                                    size_bytes = int(data.get('size'))
                            except Exception:
                                size_bytes = None
                            caption = clean_caption(data.get('title') or data.get('file_name') or data.get('filename'))
                            LOG.info(f'✅ Terabox: {api_name} succeeded on attempt {attempt+1}')
                            return {
                                'url': dl,
                                'size_bytes': size_bytes,
                                'file_name': file_name,
                                'caption': caption,
                                'button_url': dl,
                                'raw_entry': {'download_link': data.get('download_link'), 'proxy_url': data.get('proxy_url')},
                                'raw_data': data
                            }
                except Exception as e:
                    LOG.warning(f'Terabox {api_name} attempt {attempt+1} failed: {e}')
                    if attempt == 0:
                        time.sleep(1)  # Wait before retry
                    continue
        
        # Try yt-dlp as final fallback (3rd attempt)
        LOG.info('Terabox: Trying yt-dlp as final fallback...')
        for yt_attempt in range(2):
            try:
                ytdlp_result = get_terabox_with_ytdlp_fallback(url)
                if ytdlp_result:
                    LOG.info(f'✅ Terabox: yt-dlp fallback succeeded on attempt {yt_attempt+1}')
                    return ytdlp_result
            except Exception as e:
                LOG.warning(f'Terabox yt-dlp attempt {yt_attempt+1} failed: {e}')
                if yt_attempt == 0:
                    time.sleep(1)
        
        return {'error': 'Terabox: All APIs failed. The link may be invalid, expired, or service temporarily unavailable. Try again shortly.'}
    else:
        # Primary generic multi-platform fallback
        data = fetch_json(SOCIAL_DL_API, params={'url': url})

    if not data:
        return {'error': 'Empty response from API'}
    if isinstance(data, dict) and data.get('error'):
        return {'error': data.get('error')}

    # Collect download entries
    entries = find_download_entries(data)
    if not entries and isinstance(data, dict) and 'download_link' in data:
        entries = [{'url': data.get('download_link'), 'file_name': data.get('file_name'), 'size_bytes': data.get('size_bytes')}]

    entry = choose_entry(entries)
    if not entry:
        return {'error': 'No downloadable entry found in API response', 'raw': data}

    url_ = entry.get('url') or entry.get('download_link')
    file_name = entry.get('file_name') or entry.get('fileName') or entry.get('filename') or os.path.basename((url_ or '').split('?')[0]) or 'file'
    size_bytes = None
    for size_field in ['size_bytes', 'size', 'filesize', 'filesize_approx', 'formattedSize']:
        sval = entry.get(size_field)
        if sval:
            try:
                size_bytes = int(sval)
                break
            except Exception:
                continue

    # Caption extraction
    caption = None
    if 'instagram.com' in lower:
        caption = extract_instagram_caption(data)
        # Also check result.caption directly
        if not caption and isinstance(data, dict):
            result_obj = data.get('result', {})
            if isinstance(result_obj, dict):
                caption = result_obj.get('caption')
        if not caption:
            caption = data.get('caption') if isinstance(data, dict) else None
        # Try result block if main extraction failed
        if not caption and isinstance(data, dict):
            result_block = data.get('result')
            if result_block:
                caption = extract_instagram_caption(result_block)
        # Debug logging for Instagram
        if not caption:
            LOG.warning('Instagram caption not found. Checking data structure...')
            LOG.warning('Data keys: %s', list(data.keys()) if isinstance(data, dict) else 'not a dict')
            if isinstance(data, dict) and 'result' in data:
                LOG.warning('Result keys: %s', list(data.get('result', {}).keys()) if isinstance(data.get('result'), dict) else 'not a dict')
    if not caption and isinstance(data, dict):
        for field in ['caption', 'title', 'description', 'text', 'post_caption', 'video_title']:
            val = data.get(field)
            if isinstance(val, str):
                caption = val
                break
        # Check result block
        if not caption and 'result' in data:
            result_obj = data.get('result')
            if isinstance(result_obj, dict):
                for field in ['caption', 'title', 'description', 'text', 'post_caption', 'video_title']:
                    val = result_obj.get(field)
                    if isinstance(val, str):
                        caption = val
                        break
    if not caption:
        for field in ['caption', 'title', 'description', 'text', 'post_caption', 'video_title']:
            val = entry.get(field)
            if isinstance(val, str):
                caption = val
                break
    caption = clean_caption(caption)

    result_obj = {'url': url_, 'size_bytes': size_bytes, 'file_name': file_name, 'caption': caption, 'raw_entry': entry, 'raw_data': data}

    # Instagram album support: multiple media items
    if 'instagram.com' in lower:
        # Always check for multiple entries (album/carousel)
        items = []
        # Prefer explicitly extracted items (with size info) if present
        explicit_items = None
        if isinstance(data, dict):
            rb = data.get('result')
            if isinstance(rb, dict):
                explicit_items = rb.get('__explicit_items')
        if explicit_items:
            items.extend(explicit_items)
        else:
            for e in entries:
                media_url = e.get('url') or e.get('download_link')
                if not media_url:
                    continue
                fname_e = e.get('file_name') or e.get('fileName') or e.get('filename') or os.path.basename(media_url.split('?')[0])
                size_e = None
                size_text = None
                for sf in ['size_bytes', 'size', 'filesize', 'filesize_approx']:
                    val = e.get(sf)
                    if val:
                        try:
                            size_e = int(val)
                            size_text = human_size(size_e)
                            break
                        except Exception:
                            # keep raw string as size_text
                            if isinstance(val, str):
                                size_text = val
                ext_lower = fname_e.lower()
                url_lower = media_url.lower()
                is_video = any(ext in url_lower or ext_lower.endswith(ext) for ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v'])
                is_image = any(ext in url_lower or ext_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']) or not is_video
                items.append({
                    'url': media_url,
                    'file_name': fname_e,
                    'size_bytes': size_e,
                    'size_text': size_text,
                    'is_video': is_video,
                    'is_image': is_image
                })
        
        # Deduplicate items by URL (some APIs return duplicates for single posts)
        if items:
            unique_items = []
            seen_urls = set()
            for item in items:
                # Normalize URL (remove query params for comparison)
                base_url = item['url'].split('?')[0] if item.get('url') else None
                if base_url and base_url not in seen_urls:
                    seen_urls.add(base_url)
                    unique_items.append(item)
            items = unique_items

        # Fallback scrape if still single item and looks like a /p/ post that might be a carousel
        if (not items or len(items) == 1) and '/p/' in url:
            LOG.info('Attempting HTML scrape for /p/ post (current items: %s)', len(items) if items else 0)
            sc_cap, sc_media = scrape_instagram_page(url)
            LOG.info('HTML scrape returned %s media URLs', len(sc_media) if sc_media else 0)
            if sc_media and len(sc_media) > 1:
                LOG.info('HTML scrape recovered %s carousel items', len(sc_media))
                items = []
                for idx, media_url in enumerate(sc_media, start=1):
                    items.append({
                        'url': media_url,
                        'file_name': os.path.basename(media_url.split('?')[0]) or f'instagram_media_{idx}.jpg',
                        'size_bytes': None,
                        'size_text': None,
                        'is_image': any(media_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']),
                        'is_video': any(media_url.lower().endswith(ext) for ext in ['.mp4', '.mov', '.webm'])
                    })
                if sc_cap and not result_obj.get('caption'):
                    result_obj['caption'] = clean_caption(sc_cap)
        
        # If multiple items OR single item, use items structure (safer)
        if items:
            LOG.info('Instagram: found %s unique media items', len(items))
            # If only one media item (video OR image), treat as single direct item
            if len(items) == 1:
                single = items[0]
                result_obj['url'] = single.get('url')
                result_obj['file_name'] = single.get('file_name') or result_obj.get('file_name') or 'instagram_media'
                if single.get('size_bytes'):
                    result_obj['size_bytes'] = single.get('size_bytes')
                elif single.get('size_text'):
                    try:
                        m = re.match(r'(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB)', single['size_text'], re.I)
                        if m:
                            num = float(m.group(1)); unit = m.group(2).upper()
                            mult = {'B':1,'KB':1024,'MB':1024**2,'GB':1024**3,'TB':1024**4}[unit]
                            result_obj['size_bytes'] = int(num * mult)
                    except Exception:
                        pass
                # Mark if it's image or video for proper sending
                result_obj['is_image'] = single.get('is_image', False)
                result_obj['is_video'] = single.get('is_video', False)
            else:
                # For multi-item albums, preserve items list
                result_obj['items'] = items
                # Annotate album for downstream captioning (first item gets album header)
                result_obj['album_count'] = len(items)

    return result_obj


@bot.message_handler(commands=['start'])
def cmd_start(msg):
    welcome_art = """
╔═══════════════════════════════════════╗
║  🎬 <b>MEDIA DOWNLOADER BOT</b> 🎬   ║
╚═══════════════════════════════════════╝

<b>Welcome to your personal media downloader!</b>

<b>📥 Supported Platforms:</b>
    • 🎥 YouTube Videos & Shorts
    • 🎵 TikTok (No-Watermark, Audio)
    • 📸 Instagram Reels & Posts
    • 📦 Terabox Files
    • 🌐 Many Other Platforms

<b>✨ Enhanced Features:</b>
    • 🎯 Multiple quality options for YouTube
    • 📝 Original captions from posts
    • 📸 Instagram album support (all photos/videos)
    • 🖼️ Direct inline media display
    • 💾 Automatic backup archival
    • ⚡ Fast downloads with yt-dlp fallback
    • 🔧 Smart caption extraction

<b>🚀 How to Use:</b>
  1️⃣ Copy any media URL
  2️⃣ Send it to me
  3️⃣ Get your file instantly!

<b>💡 Example:</b>
    <code>https://youtube.com/watch?v=...</code>
    <code>https://vt.tiktok.com/...</code>
  <code>https://instagram.com/reel/...</code>
  <code>https://1024terabox.com/s/...</code>

<b>📋 Commands:</b>
  /start - Show this message
  /help - Get detailed help
  /about - About this bot
  /supported - List all platforms

<i>✨ Just send me a link and watch the magic happen!</i>
"""
    bot.reply_to(msg, welcome_art)


@bot.message_handler(commands=['help'])
def cmd_help(msg):
    help_text = """
<b>📚 HOW TO USE THIS BOT</b>

<b>Step 1:</b> Copy a media URL
    • YouTube: <code>https://youtube.com/watch?v=xyz</code>
    • TikTok: <code>https://vt.tiktok.com/ABC</code>
  • Instagram: <code>https://instagram.com/reel/abc</code>
  • Terabox: <code>https://1024terabox.com/s/xyz</code>

<b>Step 2:</b> Paste and send the URL to me

<b>Step 3:</b> Receive your file!
  • Files under 2GB → Sent directly
  • Larger files → Download link provided

<b>⚙️ Features:</b>
    ✅ Multiple quality options (YouTube)
    ✅ No-watermark TikTok videos
  ✅ Fast processing
  ✅ High-quality downloads
  ✅ No ads or watermarks
  ✅ Free forever

<b>❓ Common Issues:</b>

<b>Q:</b> Bot not responding?
<b>A:</b> Check if URL is valid and publicly accessible

<b>Q:</b> Download failed?
<b>A:</b> Some platforms have restrictions. Try again later.

<b>Q:</b> File too large?
<b>A:</b> You'll receive a direct download link instead

<b>💬 Need more help?</b>
Use /supported to see all platforms
"""
    bot.reply_to(msg, help_text)


@bot.message_handler(commands=['about'])
def cmd_about(msg):
    about_text = """
<b>🤖 ABOUT THIS BOT</b>

<b>Name:</b> Media Downloader Bot
<b>Version:</b> 1.0.0
<b>Status:</b> ✅ Online

<b>🎯 Purpose:</b>
Download media from multiple platforms instantly!

<b>🔧 Technology:</b>
  • Python + Telegram Bot API
  • Multiple API integrations
  • Real-time processing

<b>📊 Statistics:</b>
  • Platforms supported: 4+
  • File size limit: 2GB direct upload
  • Processing time: ~5-10 seconds

<b>🔐 Privacy:</b>
  • No data stored
  • No user tracking
  • Secure downloads

<b>👨‍💻 Developer:</b> Open Source Project
<b>📅 Last Updated:</b> November 2025

<i>Made with ❤️ for seamless media downloads</i>
"""
    bot.reply_to(msg, about_text)


@bot.message_handler(commands=['supported'])
def cmd_supported(msg):
    platforms_text = """
<b>🌐 SUPPORTED PLATFORMS</b>

<b>✅ Fully Supported:</b>

<b>1. YouTube</b> 🎥
  • Videos (all qualities)
  • Music videos
  • Shorts
  <code>https://youtube.com/watch?v=...</code>
  <code>https://youtu.be/...</code>

<b>2. TikTok</b> 🎵
    • No-watermark video
    • Watermark video
    • Audio (mp3)
    <code>https://vt.tiktok.com/...</code>
    <code>https://www.tiktok.com/@user/video/...</code>

<b>3. Instagram</b> 📸
  • Reels
  • Posts (photo/video)
  • IGTV
  <code>https://instagram.com/reel/...</code>
  <code>https://instagram.com/p/...</code>

<b>4. Terabox</b> 📦
  • Shared files
  • Large file support
  <code>https://1024terabox.com/s/...</code>
  <code>https://terabox.com/s/...</code>

<b>5. Other Platforms</b> 🌐
  • Twitter/X videos
  • Facebook videos
  • TikTok (some regions)
  • And more...

<b>💡 Tip:</b> Just send any media URL and I'll try to download it!

<b>⚠️ Note:</b> Some platforms may have regional or privacy restrictions.
"""
    bot.reply_to(msg, platforms_text)


@bot.callback_query_handler(func=lambda call: call.data.startswith('ytupload:'))
def handle_yt_upload_callback(call):
    """Handle YouTube upload button callback."""
    try:
        parts = call.data.split(':')
        session_id = int(parts[1])
        best_index = int(parts[2])
        
        if session_id not in FORMAT_SESSIONS:
            bot.answer_callback_query(call.id, "❌ Session expired. Please send the URL again.", show_alert=True)
            return
        
        qualities = FORMAT_SESSIONS[session_id]
        best = qualities[best_index]
        
        chat_id = call.message.chat.id
        username = call.from_user.username or call.from_user.first_name or 'User'
        
        # Build download button
        kb_dl = InlineKeyboardMarkup()
        kb_dl.add(InlineKeyboardButton("⬇️ Download Now", url=best['url']))
        
        # Update message to show upload in progress
        bot.edit_message_text(
            f"<b>📤 Uploading best quality...</b>\n\nIf upload takes too long, use the button below:",
            chat_id,
            call.message.message_id,
            reply_markup=kb_dl
        )
        
        dl_url = best['url']
        fname = f"video_{best.get('resolution', 'best')}.mp4"
        size_bytes = best.get('size_bytes')
        base_caption = f"<b>✅ YouTube Video</b>\n<b>Quality:</b> {best.get('resolution') or best.get('extension')}"
        caption = base_caption + "\n\n<i>Downloaded by @TeraInstaShortsDownloaderbot</i>"

        # If selected format is video_only, attempt mux with best available audio
        if best.get('type') == 'video_only':
            audio_candidates = [q for q in qualities if q.get('type') == 'audio']
            if audio_candidates:
                # Choose highest bitrate/size audio
                audio_best = sorted(audio_candidates, key=lambda a: a.get('size_bytes') or 0, reverse=True)[0]
                bot.edit_message_text(
                    f"<b>🔄 Merging video + audio...</b>\n\n<code>{best.get('resolution')}</code> + <code>{audio_best.get('extension')}</code>",
                    chat_id,
                    call.message.message_id,
                    reply_markup=kb_dl
                )
                ffmpeg_path = ensure_ffmpeg()
                if not ffmpeg_path:
                    # Cannot mux; fallback to sending silent video
                    caption += "\n<b>⚠️ Audio merge unavailable (FFmpeg missing)</b>"
                else:
                    try:
                        with tempfile.TemporaryDirectory() as tmpdir:
                            tmpdirp = Path(tmpdir)
                            vpath = tmpdirp / 'video.mp4'
                            apath = tmpdirp / f"audio.{audio_best.get('extension','m4a')}"
                            okv = stream_download(dl_url, vpath, LOCAL_DOWNLOAD_LIMIT)
                            oka = stream_download(audio_best['url'], apath, LOCAL_DOWNLOAD_LIMIT)
                            if okv and oka and vpath.exists() and apath.exists():
                                out_path = tmpdirp / 'merged.mp4'
                                cmd = [ffmpeg_path, '-y', '-i', str(vpath), '-i', str(apath), '-c:v', 'copy', '-c:a', 'aac', '-shortest', str(out_path)]
                                try:
                                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
                                except Exception:
                                    pass
                                if out_path.exists():
                                    caption = base_caption + f"\n<b>Audio merged:</b> {audio_best.get('extension').upper()}" + "\n\n<i>Downloaded by @TeraInstaShortsDownloaderbot</i>"
                                    with open(out_path, 'rb') as f:
                                        bot.send_video(chat_id, f, caption=caption, supports_streaming=True)
                                    bot.delete_message(chat_id, call.message.message_id)
                                    bot.answer_callback_query(call.id)
                                    return
                            # If merge failed, append warning and fall through to normal handling
                            caption += "\n<b>⚠️ Merge failed; sending original (silent) stream.</b>"
                    except Exception:
                        LOG.warning('Muxing failed', exc_info=True)
                        caption += "\n<b>⚠️ Merge error; sending original (silent) stream.</b>"
            else:
                caption += "\n<b>⚠️ Selected stream has no audio track.</b>"

        try:
            # Try remote upload first for small files
            if size_bytes and size_bytes <= MAX_UPLOAD and best.get('type') != 'video_only':
                try:
                    bot.send_video(chat_id, dl_url, caption=caption, supports_streaming=True)
                    bot.delete_message(chat_id, call.message.message_id)
                except Exception:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        temp_path = Path(tmpdir) / fname
                        ok = stream_download(dl_url, temp_path, LOCAL_DOWNLOAD_LIMIT)
                        if ok and temp_path.exists():
                            with open(temp_path, 'rb') as f:
                                bot.send_video(chat_id, f, caption=caption, supports_streaming=True)
                            bot.delete_message(chat_id, call.message.message_id)
                        else:
                            bot.edit_message_text(
                                caption + "\n\n<b>⚠️ Could not upload. Use Download Now button above.</b>",
                                chat_id,
                                call.message.message_id,
                                reply_markup=kb_dl
                            )
            else:
                # For video_only or large files, perform local download attempt (silent if no merge)
                with tempfile.TemporaryDirectory() as tmpdir:
                    temp_path = Path(tmpdir) / fname
                    ok = stream_download(dl_url, temp_path, LOCAL_DOWNLOAD_LIMIT)
                    if ok and temp_path.exists() and (best.get('type') != 'video_only'):
                        with open(temp_path, 'rb') as f:
                            bot.send_video(chat_id, f, caption=caption, supports_streaming=True)
                        bot.delete_message(chat_id, call.message.message_id)
                    else:
                        bot.edit_message_text(
                            caption + "\n\n<b>⚠️ File too large or silent; use Download button.</b>",
                            chat_id,
                            call.message.message_id,
                            reply_markup=kb_dl
                        )
        except Exception:
            LOG.exception('Upload failed in callback')
            bot.edit_message_text(
                caption + "\n\n<b>⚠️ Upload failed. Use Download Now button.</b>",
                chat_id,
                call.message.message_id,
                reply_markup=kb_dl
            )
        
        bot.answer_callback_query(call.id)
    except Exception:
        LOG.exception('Error in callback handler')
        bot.answer_callback_query(call.id, "❌ Error processing request", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('ytaudio:'))
def handle_yt_audio_callback(call):
    """Handle YouTube audio extraction callback."""
    try:
        parts = call.data.split(':')
        session_id = int(parts[1])
        
        if session_id not in FORMAT_SESSIONS:
            bot.answer_callback_query(call.id, "❌ Session expired. Please send the URL again.", show_alert=True)
            return
        
        qualities = FORMAT_SESSIONS[session_id]
        # Get the original URL from the first quality entry
        original_url = qualities[0].get('raw', {}).get('url') if qualities else None
        
        if not original_url:
            bot.answer_callback_query(call.id, "❌ Could not retrieve original URL", show_alert=True)
            return
        
        chat_id = call.message.chat.id
        username = call.from_user.username or call.from_user.first_name or 'User'
        
        # Update message to show audio extraction in progress
        bot.edit_message_text(
            f"<b>🎵 Extracting audio...</b>\n\n<i>This may take a moment...</i>",
            chat_id,
            call.message.message_id
        )
        
        try:
            import yt_dlp
            # Attempt ffmpeg availability early (for postprocessors)
            ffmpeg_path = ensure_ffmpeg()
            
            # Create temp directory for download
            with tempfile.TemporaryDirectory() as tmpdir:
                output_template = os.path.join(tmpdir, '%(title)s.%(ext)s')
                
                # Try to get audio without FFmpeg conversion first
                ydl_opts = {
                    'format': 'bestaudio[ext=m4a]/bestaudio/best',
                    'outtmpl': output_template,
                    'quiet': True,
                    'no_warnings': True,
                }
                
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(original_url, download=True)
                        title = info.get('title', 'audio')
                        
                        # Find the downloaded audio file
                        audio_files = list(Path(tmpdir).glob('*.*'))
                        if audio_files:
                            audio_path = audio_files[0]
                            caption = f"<b>🎵 YouTube Audio</b>\n<b>Title:</b> {title}\n\n<i>Downloaded by @TeraInstaShortsDownloaderbot</i>"
                            
                            # Send as audio
                            with open(audio_path, 'rb') as f:
                                bot.send_audio(
                                    chat_id,
                                    f,
                                    caption=caption,
                                    title=title,
                                    performer="YouTube"
                                )
                            
                            bot.delete_message(chat_id, call.message.message_id)
                            bot.answer_callback_query(call.id, "✅ Audio extracted successfully!")
                        else:
                            raise Exception("No audio file downloaded")
                
                except Exception as e:
                    # If direct audio download failed, try with FFmpeg conversion
                    LOG.warning(f"Direct audio download failed: {e}, trying with FFmpeg conversion")
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'postprocessors': ([{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }] if ffmpeg_path else []),
                        'outtmpl': output_template,
                        'quiet': True,
                        'no_warnings': True,
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(original_url, download=True)
                        title = info.get('title', 'audio')
                        
                        # Find the downloaded MP3 file
                        mp3_files = list(Path(tmpdir).glob('*.mp3'))
                        if mp3_files:
                            mp3_path = mp3_files[0]
                            caption = f"<b>🎵 YouTube Audio (MP3)</b>\n<b>Title:</b> {title}\n\n<i>Downloaded by @TeraInstaShortsDownloaderbot</i>"
                            
                            # Send as audio
                            with open(mp3_path, 'rb') as f:
                                bot.send_audio(
                                    chat_id,
                                    f,
                                    caption=caption,
                                    title=title,
                                    performer="YouTube"
                                )
                            
                            bot.delete_message(chat_id, call.message.message_id)
                            bot.answer_callback_query(call.id, "✅ Audio extracted successfully!")
                        else:
                            bot.edit_message_text(
                                f"<b>❌ Audio extraction failed</b>\n\nNo audio file was generated.",
                                chat_id,
                                call.message.message_id
                            )
                            bot.answer_callback_query(call.id, "❌ Extraction failed", show_alert=True)
        
        except Exception as e:
            LOG.exception('Audio extraction failed')
            error_msg = str(e)
            
            # Check if video has no audio track
            if 'requested format is not available' in error_msg.lower() or 'no audio' in error_msg.lower():
                bot.edit_message_text(
                    f"<b>❌ Video has no audio</b>\n\n<i>This YouTube video doesn't contain an audio track or the audio format is not available for extraction.</i>",
                    chat_id,
                    call.message.message_id
                )
                bot.answer_callback_query(call.id, "❌ Video has no audio", show_alert=True)
            elif 'ffmpeg' in error_msg.lower() or 'ffprobe' in error_msg.lower():
                bot.edit_message_text(
                    f"<b>❌ Audio extraction failed</b>\n\n<i>FFmpeg is not installed. Attempting to download in original format...</i>",
                    chat_id,
                    call.message.message_id
                )
                # Try one more time without postprocessor
                try:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        output_template = os.path.join(tmpdir, '%(title)s.%(ext)s')
                        ydl_opts = {
                            'format': 'bestaudio',
                            'outtmpl': output_template,
                            'quiet': True,
                            'no_warnings': True,
                        }
                        
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(original_url, download=True)
                            title = info.get('title', 'audio')
                            
                            audio_files = list(Path(tmpdir).glob('*.*'))
                            if audio_files:
                                audio_path = audio_files[0]
                                caption = f"<b>🎵 YouTube Audio</b>\n<b>Title:</b> {title}\n\n<i>Downloaded by @TeraInstaShortsDownloaderbot</i>"
                                
                                with open(audio_path, 'rb') as f:
                                    bot.send_audio(
                                        chat_id,
                                        f,
                                        caption=caption,
                                        title=title,
                                        performer="YouTube"
                                    )
                                
                                bot.delete_message(chat_id, call.message.message_id)
                                bot.answer_callback_query(call.id, "✅ Audio downloaded!")
                            else:
                                raise Exception("No audio file")
                except Exception as final_e:
                    LOG.exception('Final audio attempt failed')
                    bot.edit_message_text(
                        f"<b>❌ Audio download failed</b>\n\n<i>Error: {str(final_e)[:80]}</i>",
                        chat_id,
                        call.message.message_id
                    )
                    bot.answer_callback_query(call.id, "❌ Download failed", show_alert=True)
            elif 'timed out' in error_msg.lower() or 'timeout' in error_msg.lower():
                bot.edit_message_text(
                    f"<b>❌ Network timeout during audio extraction</b>\n\n<i>Please try again; connection was interrupted.</i>",
                    chat_id,
                    call.message.message_id
                )
                bot.answer_callback_query(call.id, "❌ Network timeout", show_alert=True)
            elif '403' in error_msg or '410' in error_msg or 'copyright' in error_msg.lower():
                bot.edit_message_text(
                    f"<b>❌ Audio unavailable</b>\n\n<i>Restricted or copyright-protected stream prevented extraction.</i>",
                    chat_id,
                    call.message.message_id
                )
                bot.answer_callback_query(call.id, "❌ Restricted", show_alert=True)
            else:
                bot.edit_message_text(
                    f"<b>❌ Audio extraction failed</b>\n\n<i>Error: {error_msg[:100]}</i>",
                    chat_id,
                    call.message.message_id
                )
                bot.answer_callback_query(call.id, "❌ Extraction failed", show_alert=True)
    
    except Exception:
        LOG.exception('Error in audio callback handler')
        bot.answer_callback_query(call.id, "❌ Error processing request", show_alert=True)


@bot.message_handler(func=lambda m: True)
def handle_message(msg):
    text = (msg.text or '').strip()
    m = URL_RE.search(text)
    if not m:
        help_msg = (
            "<b>🤔 I need a valid URL!</b>\n\n"
            "Please send me a media link from:\n"
            "• YouTube\n"
            "• Instagram\n"
            "• Terabox\n"
            "• Or other platforms\n\n"
            "<b>Example:</b>\n"
            "<code>https://youtube.com/watch?v=xyz</code>\n\n"
            "💡 Use /help for more information"
        )
        bot.reply_to(msg, help_msg)
        return

    url = m.group(1)
    chat_id = msg.chat.id
    user = msg.from_user
    username = user.username or user.first_name or 'User'
    
    LOG.info('Processing URL from @%s: %s', username, url)
    
    # Send processing message with animation
    processing_msg = bot.send_message(
        chat_id, 
        f"<b>⏳ Processing your request...</b>\n\n🔍 Analyzing URL\n⚙️ Fetching data\n📥 Preparing download\n\n<i>Please wait...</i>"
    )

    # Resolve URL with robust error handling to avoid crashing the bot
    try:
        result = handle_api_for_url(url)
    except Exception as e:
        LOG.exception('Fatal error while resolving URL: %s', e)
        # Best-effort Instagram fallback using yt-dlp
        if 'instagram.com' in url.lower():
            cap_fb, media_fb = get_instagram_with_ytdlp_fallback(url)
            if media_fb:
                items = [{
                    'url': mu,
                    'file_name': os.path.basename(mu.split('?')[0]) or 'instagram_media.mp4',
                    'size_bytes': None,
                    'is_image': any(mu.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']),
                    'is_video': any(mu.lower().endswith(ext) for ext in ['.mp4', '.mov', '.webm'])
                } for mu in media_fb]
                result = {'items': items, 'caption': clean_caption(cap_fb) if cap_fb else None}
            else:
                result = {'error': 'Unexpected error while resolving Instagram link'}
        else:
            result = {'error': 'Unexpected error while resolving link'}
    # Special YouTube multi-quality selection flow
    if result.get('qualities'):
        qualities = result['qualities']
        best_index = result.get('best_index', 0)
        title_caption = result.get('caption') or 'YouTube Video'
        session_id = next(SESSION_COUNTER)
        FORMAT_SESSIONS[session_id] = qualities

        kb = InlineKeyboardMarkup()
        # Download best quality button (top priority)
        kb.add(InlineKeyboardButton("⬇️ Download Now", callback_data=f"ytupload:{session_id}:{best_index}"))
        # Audio extraction button
        kb.add(InlineKeyboardButton("🎵 Extract Audio (MP3)", callback_data=f"ytaudio:{session_id}"))
        
        # Add inline quality buttons for direct upload (limit to top 8)
        for i, q in enumerate(qualities[:8]):
            txt = q['resolution'] or q['extension']
            if q.get('size_bytes'):
                txt += f" {human_size(q['size_bytes'])}"
            if i == best_index:
                txt += " ⭐"
            # Use callback_data for inline upload instead of external URL
            kb.add(InlineKeyboardButton(txt, callback_data=f"ytupload:{session_id}:{i}"))

        bot.edit_message_text(
            f"<b>✅ Formats Ready</b>\n<b>📝 Title:</b> {title_caption}\n\n<b>🎬 Download Options:</b>\nClick <b>Download Now</b> for best quality or choose a specific quality below. ⭐ marks best quality.\n\n<b>💡 Tip:</b> Use <b>Extract Audio</b> to get MP3.",
            chat_id,
            processing_msg.message_id,
            reply_markup=kb
        )
        return
    
    if 'error' in result:
        error_msg = (
            f"<b>❌ Download Failed</b>\n\n"
            f"<b>Error:</b> {result.get('error')}\n\n"
            f"<b>💡 Possible Solutions:</b>\n"
            f"• Check if the URL is correct\n"
            f"• Ensure the content is public\n"
            f"• Try again in a few moments\n"
            f"• Use /supported to see available platforms\n\n"
            f"<i>If the issue persists, the platform may be temporarily unavailable.</i>"
        )
        bot.edit_message_text(error_msg, chat_id, processing_msg.message_id)
        return

    # If Instagram album or multi-item result
    if isinstance(result, dict) and result.get('items'):
        items = result.get('items') or []
        original_caption = result.get('caption')
        # Prepare caption for the album (multi-item only reaches here)
        main_caption = None
        if original_caption:
            main_caption = f"<b>📝</b> {original_caption}\n\n<i>📸 Album ({len(items)} items)</i>\n<i>Downloaded by {BOT_BRAND}</i>"
        else:
            main_caption = f"<b>📸 Album ({len(items)} items)</b>\n<i>Downloaded by {BOT_BRAND}</i>"

        try:
            bot.delete_message(chat_id, processing_msg.message_id)
        except Exception:
            pass

        # Multi-item branch
        if result.get('items'):
            multi_items = result['items']
            for idx, it in enumerate(multi_items, start=1):
                u = it.get('url')
                if not u:
                    LOG.warning('Album item %s has no URL, skipping', idx)
                    continue
                fname = it.get('file_name') or 'file'
                size_bytes = it.get('size_bytes')
                size_text = it.get('size_text')
                is_video = it.get('is_video')
                is_image = it.get('is_image')
                if is_video is None and is_image is None:
                    url_lower = u.lower(); fname_lower = fname.lower()
                    if any(ext in url_lower or fname_lower.endswith(ext) for ext in ['.mp4','.mov','.avi','.mkv','.webm','.flv','.m4v']):
                        is_video, is_image = True, False
                    elif any(ext in url_lower or fname_lower.endswith(ext) for ext in ['.jpg','.jpeg','.png','.webp','.gif']):
                        is_video, is_image = False, True
                    else:
                        is_video = 'video' in url_lower; is_image = not is_video
                per_caption = main_caption if idx == 1 and main_caption else None
                if per_caption and size_text and idx == 1:
                    per_caption += f"\n<b>📊 Size:</b> {size_text}"
                try:
                    if is_image:
                        LOG.info('Sending Instagram image %s/%s as photo', idx, len(multi_items))
                        sent_msg = bot.send_photo(chat_id, u, caption=per_caption)
                        if idx == 1:
                            try:
                                forward_to_backup_channel(chat_id, sent_msg.photo[-1].file_id, 'photo', per_caption or 'Instagram Album', username)
                            except Exception:
                                pass
                    elif is_video:
                        over_limit_known = bool(size_bytes and size_bytes > MAX_UPLOAD)
                        if over_limit_known:
                            kb = InlineKeyboardMarkup()
                            kb.add(InlineKeyboardButton('⬇️ Download', url=u))
                            extra = ""
                            if size_text:
                                extra = f"\n<b>📊 Size:</b> {size_text}\n<b>⚠️ Too large for auto-upload.</b>"
                            bot.send_message(chat_id, (per_caption or '') + extra, reply_markup=kb)
                            continue
                        
                        sent_successfully = False
                        try:
                            sent_msg = bot.send_video(chat_id, u, caption=per_caption, supports_streaming=True)
                            sent_successfully = True
                            if idx == 1:
                                try:
                                    forward_to_backup_channel(chat_id, sent_msg.video.file_id, 'video', per_caption or 'Instagram Album', username)
                                except Exception:
                                    pass
                        except Exception:
                            LOG.warning('Remote send failed for album video item %s; attempting local upload', idx)
                        
                        if not sent_successfully:
                            with tempfile.TemporaryDirectory() as tmpdir:
                                temp_path = Path(tmpdir) / fname
                                ok = stream_download(u, temp_path, LOCAL_DOWNLOAD_LIMIT)
                                if ok and temp_path.exists():
                                    try:
                                        with open(temp_path, 'rb') as f:
                                            sent_msg = bot.send_video(chat_id, f, caption=per_caption, supports_streaming=True)
                                            sent_successfully = True
                                            if idx == 1:
                                                try:
                                                    forward_to_backup_channel(chat_id, sent_msg.video.file_id, 'video', per_caption or 'Instagram Album', username)
                                                except Exception:
                                                    pass
                                    except Exception:
                                        LOG.exception('Local upload failed for album video item %s', idx)
                                        sent_successfully = False
                                if not sent_successfully:
                                    kb = InlineKeyboardMarkup(); kb.add(InlineKeyboardButton('⬇️ Download', url=u))
                                    bot.send_message(chat_id, per_caption or '', reply_markup=kb)
                    else:
                        kb = InlineKeyboardMarkup(); kb.add(InlineKeyboardButton('⬇️ Download', url=u))
                        bot.send_message(chat_id, per_caption or '', reply_markup=kb)
                except Exception:
                    LOG.exception('Failed to send album item %s', idx)
                    kb = InlineKeyboardMarkup(); kb.add(InlineKeyboardButton('⬇️ Download', url=u))
                    try: bot.send_message(chat_id, per_caption or '', reply_markup=kb)
                    except Exception: pass
            return

    # Single-item flow
    dl_url = result.get('url')
    fname = result.get('file_name') or 'file'
    size_bytes = result.get('size_bytes')
    size_text = result.get('size_text')
    original_caption = result.get('caption')

    # Prepare caption with emoji and formatting
    caption_lines = []
    
    # Always show original post caption if available (prioritize over filename)
    if original_caption:
        caption_lines.append(f"<b>📝 {original_caption}</b>\n")
    elif 'instagram.com' in url.lower():
        # Clean label for Instagram when no caption
        caption_lines.append(f"<b>📸 Instagram Media</b>\n")
    else:
        caption_lines.append(f"<b>✅ Download Ready!</b>\n")
        caption_lines.append(f"<b>📁 File:</b> <code>{fname}</code>")
    
    size_display = None
    if size_bytes:
        size_display = human_size(size_bytes)
    elif size_text:
        size_display = size_text
    elif result.get('size_label'):
        size_display = result.get('size_label')

    if size_display:
        caption_lines.append(f"<b>📊 Size:</b> {size_display}")
    caption_lines.append(f"\n<i>Downloaded by {BOT_BRAND}</i>")
    caption = '\n'.join(caption_lines)

    # Detect if it's a video/image file
    is_image = result.get('is_image', False)
    is_video = result.get('is_video', False)
    
    # Fallback to extension-based detection if flags not set
    if not is_image and not is_video:
        is_video = fname.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v'))
        is_image = fname.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))

    try:
        bot.delete_message(chat_id, processing_msg.message_id)
    except Exception:
        pass

    # Prepare optional inline button (e.g., Terabox proxy link)
    button_url = result.get('button_url')
    kb_opt = None
    if button_url:
        kb_opt = InlineKeyboardMarkup()
        label_size = size_display or 'Download'
        kb_opt.add(InlineKeyboardButton(f"⬇️ {label_size}", url=button_url))

    # Decide if we can attempt an upload (allow when size unknown)
    size_known = size_bytes is not None
    can_upload = (size_bytes is None) or (size_bytes <= MAX_UPLOAD)

    if can_upload:
        # Add Download Now button during upload
        kb_upload = InlineKeyboardMarkup()
        kb_upload.add(InlineKeyboardButton("⬇️ Download Now", url=(button_url or dl_url)))
        upload_msg = bot.send_message(chat_id, "<b>📤 Uploading...</b>\n\n<i>Taking too long? Use Download Now button below.</i>", reply_markup=kb_upload)
        try:
            # First attempt: remote URL send
            if is_image:
                sent_msg = bot.send_photo(chat_id, dl_url, caption=caption, reply_markup=kb_opt)
                # Forward to backup channel
                try:
                    forward_to_backup_channel(chat_id, sent_msg.photo[-1].file_id, 'photo', caption, username)
                except Exception:
                    pass
            elif is_video:
                sent_msg = bot.send_video(chat_id, dl_url, caption=caption, supports_streaming=True, reply_markup=kb_opt)
                # Forward to backup channel
                try:
                    forward_to_backup_channel(chat_id, sent_msg.video.file_id, 'video', caption, username)
                except Exception:
                    pass
            else:
                sent_msg = bot.send_document(chat_id, dl_url, caption=caption, reply_markup=kb_opt)
                # Forward to backup channel
                try:
                    forward_to_backup_channel(chat_id, sent_msg.document.file_id, 'document', caption, username)
                except Exception:
                    pass
            bot.delete_message(chat_id, upload_msg.message_id)
        except Exception:
            LOG.warning('Remote upload failed, attempting local download then upload')
            # Local download fallback with progress tracking
            last_update = [0]  # Mutable to track last update time
            
            def progress_update(downloaded, total):
                """Update message with download progress"""
                import time
                current_time = time.time()
                # Update every 2 seconds to avoid rate limiting
                if current_time - last_update[0] < 2:
                    return
                last_update[0] = current_time
                
                percent = (downloaded / total * 100) if total > 0 else 0
                downloaded_mb = downloaded / (1024 * 1024)
                total_mb = total / (1024 * 1024)
                
                try:
                    bot.edit_message_text(
                        f"<b>📥 Downloading...</b>\n\n"
                        f"Progress: {percent:.1f}%\n"
                        f"Size: {downloaded_mb:.1f} MB / {total_mb:.1f} MB",
                        chat_id,
                        upload_msg.message_id,
                        reply_markup=kb_upload
                    )
                except Exception:
                    pass  # Ignore edit errors
            
            with tempfile.TemporaryDirectory() as tmpdir:
                temp_path = Path(tmpdir) / fname
                ok = stream_download(dl_url, temp_path, LOCAL_DOWNLOAD_LIMIT, progress_callback=progress_update)
                if ok and temp_path.exists():
                    try:
                        with open(temp_path, 'rb') as f:
                            if is_image:
                                sent_msg = bot.send_photo(chat_id, f, caption=caption, reply_markup=kb_opt)
                                # Forward to backup channel
                                try:
                                    forward_to_backup_channel(chat_id, sent_msg.photo[-1].file_id, 'photo', caption, username)
                                except Exception:
                                    pass
                            elif is_video:
                                sent_msg = bot.send_video(chat_id, f, caption=caption, supports_streaming=True, reply_markup=kb_opt)
                                # Forward to backup channel
                                try:
                                    forward_to_backup_channel(chat_id, sent_msg.video.file_id, 'video', caption, username)
                                except Exception:
                                    pass
                            else:
                                sent_msg = bot.send_document(chat_id, f, caption=caption, reply_markup=kb_opt)
                                # Forward to backup channel
                                try:
                                    forward_to_backup_channel(chat_id, sent_msg.document.file_id, 'document', caption, username)
                                except Exception:
                                    pass
                        bot.delete_message(chat_id, upload_msg.message_id)
                    except Exception:
                        LOG.exception('Local re-upload failed; falling back to link button')
                        bot.delete_message(chat_id, upload_msg.message_id)
                        kb = InlineKeyboardMarkup()
                        kb.add(InlineKeyboardButton("⬇️ Download", url=button_url or dl_url))
                        bot.send_message(chat_id, caption + "\n\n<b>⚠️ Could not upload file directly</b>", reply_markup=kb)
                else:
                    bot.delete_message(chat_id, upload_msg.message_id)
                    kb = InlineKeyboardMarkup()
                    kb.add(InlineKeyboardButton("⬇️ Download", url=button_url or dl_url))
                    bot.send_message(chat_id, caption + "\n\n<b>⚠️ Could not fetch file for upload</b>", reply_markup=kb)
    else:
        # Large file or unknown size: send button only
        kb = InlineKeyboardMarkup()
        label_size = size_display or ('Download' if not size_known else human_size(size_bytes))
        kb.add(InlineKeyboardButton(f"⬇️ {label_size}", url=(button_url or dl_url)))
        extra = "\n\n<b>⚠️ File too large for direct upload</b>" if size_known and size_bytes > MAX_UPLOAD else ""
        bot.send_message(chat_id, caption + extra, reply_markup=kb)


if __name__ == '__main__':
    LOG.info('Starting bot')
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
