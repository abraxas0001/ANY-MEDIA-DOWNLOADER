"""Quick test script to verify API handlers work correctly."""
import bot

# Test YouTube URL detection and API call
test_urls = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.instagram.com/reel/DNnqMf7IK-h/",
    "https://1024terabox.com/s/1sELP7cWEEN_umgEPvJ9UZg"
]

print("Testing API handlers:\n")
for url in test_urls:
    print(f"Testing: {url}")
    result = bot.handle_api_for_url(url)
    if 'error' in result:
        print(f"  ❌ Error: {result['error']}")
    else:
        print(f"  ✅ Success!")
        print(f"     File: {result.get('file_name', 'N/A')}")
        if result.get('size_bytes'):
            print(f"     Size: {bot.human_size(result['size_bytes'])}")
        print(f"     URL: {result.get('url', 'N/A')[:80]}...")
    print()
