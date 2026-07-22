"""
Sherlock Mode - Comprueba si un username existe en 100+ plataformas.
Usa peticiones HTTP paralelas con ThreadPoolExecutor.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# Diccionario de plataformas: nombre -> {url_template, method, error_indicators}
# url_template usa {} como placeholder para el username
# method: 'status' (200=found), 'text' (buscar texto en response)
PLATFORMS = {
    # Social Media
    "Instagram": {"url": "https://www.instagram.com/{}/", "method": "status", "codes": [200]},
    "Twitter/X": {"url": "https://x.com/{}", "method": "status", "codes": [200]},
    "TikTok": {"url": "https://www.tiktok.com/@{}", "method": "status", "codes": [200]},
    "Facebook": {"url": "https://www.facebook.com/{}", "method": "status", "codes": [200]},
    "LinkedIn": {"url": "https://www.linkedin.com/in/{}", "method": "status", "codes": [200]},
    "YouTube": {"url": "https://www.youtube.com/@{}", "method": "status", "codes": [200]},
    "Pinterest": {"url": "https://www.pinterest.com/{}/", "method": "status", "codes": [200]},
    "Snapchat": {"url": "https://www.snapchat.com/add/{}", "method": "status", "codes": [200]},
    "Reddit": {"url": "https://www.reddit.com/user/{}", "method": "status", "codes": [200]},
    "Tumblr": {"url": "https://{}.tumblr.com", "method": "status", "codes": [200]},
    "VK": {"url": "https://vk.com/{}", "method": "status", "codes": [200]},

    # Dev / Tech
    "GitHub": {"url": "https://github.com/{}", "method": "status", "codes": [200]},
    "GitLab": {"url": "https://gitlab.com/{}", "method": "status", "codes": [200]},
    "Bitbucket": {"url": "https://bitbucket.org/{}/", "method": "status", "codes": [200]},
    "Stack Overflow": {"url": "https://stackoverflow.com/users/?tab=accounts&SearchTerm={}", "method": "text", "find": "user-details"},
    "Dev.to": {"url": "https://dev.to/{}", "method": "status", "codes": [200]},
    "Codepen": {"url": "https://codepen.io/{}", "method": "status", "codes": [200]},
    "HackerRank": {"url": "https://www.hackerrank.com/{}", "method": "status", "codes": [200]},
    "LeetCode": {"url": "https://leetcode.com/{}/", "method": "status", "codes": [200]},
    "Replit": {"url": "https://replit.com/@{}", "method": "status", "codes": [200]},
    "NPM": {"url": "https://www.npmjs.com/~{}", "method": "status", "codes": [200]},
    "PyPI": {"url": "https://pypi.org/user/{}/", "method": "status", "codes": [200]},
    "Docker Hub": {"url": "https://hub.docker.com/u/{}", "method": "status", "codes": [200]},
    "Kaggle": {"url": "https://www.kaggle.com/{}", "method": "status", "codes": [200]},
    "Hackernews": {"url": "https://news.ycombinator.com/user?id={}", "method": "text", "find": "created:"},
    "SourceForge": {"url": "https://sourceforge.net/u/{}/profile/", "method": "status", "codes": [200]},

    # Gaming
    "Steam": {"url": "https://steamcommunity.com/id/{}", "method": "text", "find": "profile_page"},
    "Twitch": {"url": "https://www.twitch.tv/{}", "method": "status", "codes": [200]},
    "Roblox (Forums)": {"url": "https://www.roblox.com/user.aspx?username={}", "method": "status", "codes": [200]},
    "Xbox Gamertag": {"url": "https://xboxgamertag.com/search/{}", "method": "status", "codes": [200]},
    "Chess.com": {"url": "https://www.chess.com/member/{}", "method": "status", "codes": [200]},
    "Lichess": {"url": "https://lichess.org/@/{}", "method": "status", "codes": [200]},

    # Media / Content
    "Spotify": {"url": "https://open.spotify.com/user/{}", "method": "status", "codes": [200]},
    "SoundCloud": {"url": "https://soundcloud.com/{}", "method": "status", "codes": [200]},
    "Bandcamp": {"url": "https://{}.bandcamp.com", "method": "status", "codes": [200]},
    "Medium": {"url": "https://medium.com/@{}", "method": "status", "codes": [200]},
    "Vimeo": {"url": "https://vimeo.com/{}", "method": "status", "codes": [200]},
    "Flickr": {"url": "https://www.flickr.com/people/{}/", "method": "status", "codes": [200]},
    "500px": {"url": "https://500px.com/p/{}", "method": "status", "codes": [200]},
    "Dribbble": {"url": "https://dribbble.com/{}", "method": "status", "codes": [200]},
    "Behance": {"url": "https://www.behance.net/{}", "method": "status", "codes": [200]},
    "DeviantArt": {"url": "https://www.deviantart.com/{}", "method": "status", "codes": [200]},
    "Wattpad": {"url": "https://www.wattpad.com/user/{}", "method": "status", "codes": [200]},
    "Goodreads": {"url": "https://www.goodreads.com/{}", "method": "status", "codes": [200]},
    "Last.fm": {"url": "https://www.last.fm/user/{}", "method": "status", "codes": [200]},
    "Mixcloud": {"url": "https://www.mixcloud.com/{}/", "method": "status", "codes": [200]},

    # Communication
    "Telegram": {"url": "https://t.me/{}", "method": "text", "find": "tgme_page_title"},
    "Keybase": {"url": "https://keybase.io/{}", "method": "status", "codes": [200]},
    "Mastodon (social)": {"url": "https://mastodon.social/@{}", "method": "status", "codes": [200]},
    "Bluesky": {"url": "https://bsky.app/profile/{}.bsky.social", "method": "status", "codes": [200]},
    "Discord (bio)": {"url": "https://discord.com/users/{}", "method": "status", "codes": [200]},

    # Business / Professional
    "About.me": {"url": "https://about.me/{}", "method": "status", "codes": [200]},
    "Gravatar": {"url": "https://en.gravatar.com/{}", "method": "status", "codes": [200]},
    "Linktree": {"url": "https://linktr.ee/{}", "method": "status", "codes": [200]},
    "Patreon": {"url": "https://www.patreon.com/{}", "method": "status", "codes": [200]},
    "Ko-fi": {"url": "https://ko-fi.com/{}", "method": "status", "codes": [200]},
    "BuyMeACoffee": {"url": "https://www.buymeacoffee.com/{}", "method": "status", "codes": [200]},
    "Fiverr": {"url": "https://www.fiverr.com/{}", "method": "status", "codes": [200]},
    "Freelancer": {"url": "https://www.freelancer.com/u/{}", "method": "status", "codes": [200]},
    "Upwork": {"url": "https://www.upwork.com/freelancers/~{}", "method": "status", "codes": [200]},
    "ProductHunt": {"url": "https://www.producthunt.com/@{}", "method": "status", "codes": [200]},
    "AngelList": {"url": "https://angel.co/u/{}", "method": "status", "codes": [200]},
    "Crunchbase": {"url": "https://www.crunchbase.com/person/{}", "method": "status", "codes": [200]},

    # Forums / Communities
    "HackerOne": {"url": "https://hackerone.com/{}", "method": "status", "codes": [200]},
    "BugCrowd": {"url": "https://bugcrowd.com/{}", "method": "status", "codes": [200]},
    "Quora": {"url": "https://www.quora.com/profile/{}", "method": "status", "codes": [200]},
    "Disqus": {"url": "https://disqus.com/by/{}/", "method": "status", "codes": [200]},
    "Imgur": {"url": "https://imgur.com/user/{}", "method": "status", "codes": [200]},
    "9GAG": {"url": "https://9gag.com/u/{}", "method": "status", "codes": [200]},
    "SlideShare": {"url": "https://www.slideshare.net/{}", "method": "status", "codes": [200]},
    "Instructables": {"url": "https://www.instructables.com/member/{}/", "method": "status", "codes": [200]},
    "Itch.io": {"url": "https://{}.itch.io", "method": "status", "codes": [200]},
    "AniList": {"url": "https://anilist.co/user/{}", "method": "status", "codes": [200]},
    "MyAnimeList": {"url": "https://myanimelist.net/profile/{}", "method": "status", "codes": [200]},
    "Letterboxd": {"url": "https://letterboxd.com/{}/", "method": "status", "codes": [200]},
    "Trakt": {"url": "https://trakt.tv/users/{}", "method": "status", "codes": [200]},
    "Duolingo": {"url": "https://www.duolingo.com/profile/{}", "method": "status", "codes": [200]},

    # Misc
    "Gravatar (API)": {"url": "https://gravatar.com/{}.json", "method": "status", "codes": [200]},
    "WordPress": {"url": "https://{}.wordpress.com", "method": "status", "codes": [200]},
    "Blogger": {"url": "https://{}.blogspot.com", "method": "status", "codes": [200]},
    "NameMC (Minecraft)": {"url": "https://namemc.com/profile/{}", "method": "status", "codes": [200]},
    "Roblox": {"url": "https://www.roblox.com/users/profile?username={}", "method": "text", "find": "profile-header"},
    "Cash App": {"url": "https://cash.app/${}", "method": "status", "codes": [200]},
    "Venmo": {"url": "https://account.venmo.com/u/{}", "method": "status", "codes": [200]},
    "Ebay": {"url": "https://www.ebay.com/usr/{}", "method": "status", "codes": [200]},
    "Etsy": {"url": "https://www.etsy.com/shop/{}", "method": "status", "codes": [200]},
    "Giphy": {"url": "https://giphy.com/{}", "method": "status", "codes": [200]},
    "Tenor": {"url": "https://tenor.com/users/{}", "method": "status", "codes": [200]},
    "IFTTT": {"url": "https://ifttt.com/p/{}", "method": "status", "codes": [200]},
    "Notion": {"url": "https://notion.so/@{}", "method": "status", "codes": [200]},
    "Substack": {"url": "https://{}.substack.com", "method": "status", "codes": [200]},
    "Hashnode": {"url": "https://hashnode.com/@{}", "method": "status", "codes": [200]},
    "HuggingFace": {"url": "https://huggingface.co/{}", "method": "status", "codes": [200]},
    "Unsplash": {"url": "https://unsplash.com/@{}", "method": "status", "codes": [200]},
    "Pexels": {"url": "https://www.pexels.com/@{}", "method": "status", "codes": [200]},
    "Pixabay": {"url": "https://pixabay.com/users/{}-0/", "method": "status", "codes": [200]},
    "Figma": {"url": "https://www.figma.com/@{}", "method": "status", "codes": [200]},
    "Canva": {"url": "https://www.canva.com/p/{}/", "method": "status", "codes": [200]},
    "Thingiverse": {"url": "https://www.thingiverse.com/{}/designs", "method": "status", "codes": [200]},
    "Cults3D": {"url": "https://cults3d.com/en/users/{}", "method": "status", "codes": [200]},
    "Thangs": {"url": "https://thangs.com/designer/{}", "method": "status", "codes": [200]},
    "Strava": {"url": "https://www.strava.com/athletes/{}", "method": "status", "codes": [200]},
    "Clubhouse": {"url": "https://www.clubhouse.com/@{}", "method": "status", "codes": [200]},
    "Periscope": {"url": "https://www.periscope.tv/{}/", "method": "status", "codes": [200]},
    "Rumble": {"url": "https://rumble.com/user/{}", "method": "status", "codes": [200]},
    "BitChute": {"url": "https://www.bitchute.com/channel/{}/", "method": "status", "codes": [200]},
    "Odysee": {"url": "https://odysee.com/@{}", "method": "status", "codes": [200]},
    "Coub": {"url": "https://coub.com/{}", "method": "status", "codes": [200]},
    "F3": {"url": "https://f3.cool/{}/", "method": "status", "codes": [200]},
    "Gab": {"url": "https://gab.com/{}", "method": "status", "codes": [200]},
    "Minds": {"url": "https://www.minds.com/{}", "method": "status", "codes": [200]},
    "Gettr": {"url": "https://gettr.com/user/{}", "method": "status", "codes": [200]},
    "Truth Social": {"url": "https://truthsocial.com/@{}", "method": "status", "codes": [200]},
    "Threads": {"url": "https://www.threads.net/@{}", "method": "status", "codes": [200]},
    "Zhihu": {"url": "https://www.zhihu.com/people/{}", "method": "status", "codes": [200]},
    "Weibo": {"url": "https://weibo.com/n/{}", "method": "status", "codes": [200]},
    "Bilibili": {"url": "https://space.bilibili.com/{}", "method": "status", "codes": [200]},
    "NicoNico": {"url": "https://www.nicovideo.jp/user/{}", "method": "status", "codes": [200]},
    "Pixiv": {"url": "https://www.pixiv.net/users/{}", "method": "status", "codes": [200]},
}

# Common headers to avoid blocks
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _check_single(platform_name, platform_info, username):
    """Check if username exists on a single platform."""
    url = platform_info["url"].format(username)
    method = platform_info.get("method", "status")
    start = time.time()

    try:
        resp = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        elapsed = round((time.time() - start) * 1000)  # ms

        found = False
        if method == "status":
            valid_codes = platform_info.get("codes", [200])
            found = resp.status_code in valid_codes
            # Extra check: some sites return 200 but with "not found" content
            if found:
                body = resp.text.lower()
                not_found_indicators = [
                    "page not found", "user not found", "profile not found",
                    "no existe", "404", "cuenta no encontrada",
                    "this account doesn", "sorry, this page",
                    "usuario no encontrado", "doesn't exist",
                    "this page is not available",
                ]
                for indicator in not_found_indicators:
                    if indicator in body[:3000]:
                        found = False
                        break
        elif method == "text":
            find_text = platform_info.get("find", "")
            found = find_text.lower() in resp.text.lower() and resp.status_code == 200

        return {
            "platform": platform_name,
            "url": url,
            "found": found,
            "response_time": elapsed,
            "status_code": resp.status_code,
        }

    except requests.exceptions.Timeout:
        return {
            "platform": platform_name,
            "url": url,
            "found": False,
            "response_time": 8000,
            "status_code": 0,
            "error": "timeout",
        }
    except Exception as e:
        return {
            "platform": platform_name,
            "url": url,
            "found": False,
            "response_time": 0,
            "status_code": 0,
            "error": str(e)[:100],
        }


def check_username(username, platforms=None, max_workers=20,
                   log_callback=None, progress_callback=None):
    """
    Check if a username exists across multiple platforms.

    Args:
        username: Username to check (without @).
        platforms: List of platform names to check. None = all.
        max_workers: Number of parallel threads.
        log_callback: Function to log messages.
        progress_callback: Function(checked_count, total, platform_name, found).

    Returns:
        dict with results summary and per-platform details.
    """
    username = username.strip().lstrip("@")

    if platforms:
        targets = {k: v for k, v in PLATFORMS.items() if k in platforms}
    else:
        targets = PLATFORMS

    total = len(targets)
    results = []
    found_count = 0
    checked = 0

    if log_callback:
        log_callback(f"[Sherlock] Comprobando @{username} en {total} plataformas...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_check_single, name, info, username): name
            for name, info in targets.items()
        }

        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            checked += 1

            if result["found"]:
                found_count += 1
                if log_callback:
                    log_callback(f"[{checked}/{total}] ENCONTRADO: {result['platform']} -> {result['url']}")

            if progress_callback:
                progress_callback(checked, total, result["platform"], result["found"])

    # Sort: found first, then alphabetically
    results.sort(key=lambda x: (not x["found"], x["platform"]))

    if log_callback:
        log_callback(f"[Sherlock] Completado: {found_count}/{total} plataformas encontradas.")

    return {
        "username": username,
        "total_checked": total,
        "total_found": found_count,
        "results": results,
    }


def get_platform_count():
    """Returns the number of platforms available."""
    return len(PLATFORMS)
