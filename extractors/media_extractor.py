"""
Media Extractor Module - Downloads photos, videos and liked content from social profiles.
Uses Instaloader for Instagram media and Selenium for TikTok/YouTube.
"""
import os
import json
import csv
import time
import datetime
import re
import threading


def extract_instagram_media(username, session_user=None, session_file=None, 
                            include_likes=False, max_posts=50,
                            log_callback=print, progress_callback=None):
    """
    Extract photos and videos from an Instagram profile using Instaloader.
    
    Args:
        username: Target Instagram username
        session_user: Logged-in user for private/likes access
        session_file: Path to session file
        include_likes: Whether to also extract liked posts (requires login)
        max_posts: Maximum number of posts to download
        log_callback: Function for logging
        progress_callback: Function(current, total) for progress
    
    Returns:
        dict with media_dir, posts list, and likes list
    """
    import instaloader

    media_dir = os.path.join('media', username)
    os.makedirs(media_dir, exist_ok=True)

    L = instaloader.Instaloader(
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        dirname_pattern=media_dir,
        filename_pattern='{date_utc:%Y%m%d_%H%M%S}_{shortcode}'
    )

    # Try to load session for private profiles or likes
    if session_user and session_file and os.path.exists(session_file):
        try:
            L.load_session_from_file(session_user, session_file)
            log_callback(f"Sesion cargada para {session_user}")
        except Exception as e:
            log_callback(f"No se pudo cargar sesion: {e}")

    results = {
        'media_dir': media_dir,
        'posts': [],
        'likes': [],
        'errors': []
    }

    try:
        profile = instaloader.Profile.from_username(L.context, username)
        log_callback(f"Perfil: {profile.full_name} | {profile.mediacount} posts | {profile.followers} seguidores")

        # Download posts
        count = 0
        for post in profile.get_posts():
            if count >= max_posts:
                break
            try:
                post_data = {
                    'shortcode': post.shortcode,
                    'url': f'https://www.instagram.com/p/{post.shortcode}/',
                    'caption': (post.caption or '')[:200],
                    'likes': post.likes,
                    'date': post.date_utc.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_video': post.is_video,
                    'type': 'video' if post.is_video else 'photo'
                }
                
                # Download the media
                L.download_post(post, target=media_dir)
                post_data['downloaded'] = True
                results['posts'].append(post_data)
                count += 1
                
                if progress_callback:
                    progress_callback(count, min(max_posts, profile.mediacount))
                    
                log_callback(f"[{count}/{max_posts}] {'Video' if post.is_video else 'Foto'}: {post.shortcode} ({post.likes} likes)")
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                results['errors'].append(f"Error post {post.shortcode}: {str(e)}")
                log_callback(f"Error en post: {e}")

        # Download likes (requires login)
        if include_likes and L.context.is_logged_in:
            log_callback("Extrayendo contenido con Like...")
            try:
                like_count = 0
                for post in profile.get_saved_posts():  
                    if like_count >= max_posts:
                        break
                    like_data = {
                        'shortcode': post.shortcode,
                        'url': f'https://www.instagram.com/p/{post.shortcode}/',
                        'owner': post.owner_username,
                        'caption': (post.caption or '')[:200],
                        'likes': post.likes,
                        'date': post.date_utc.strftime('%Y-%m-%d %H:%M:%S'),
                        'is_video': post.is_video,
                        'type': 'video' if post.is_video else 'photo'
                    }
                    results['likes'].append(like_data)
                    like_count += 1
                    log_callback(f"Like [{like_count}]: @{post.owner_username} - {post.shortcode}")
                    time.sleep(1)
            except Exception as e:
                results['errors'].append(f"Error likes: {str(e)}")
                log_callback(f"Error al extraer likes: {e}. Nota: Requiere sesion activa.")
        elif include_likes:
            log_callback("Para extraer likes se necesita iniciar sesion en Instagram.")

    except Exception as e:
        results['errors'].append(str(e))
        log_callback(f"Error general: {e}")

    # Save results to CSV
    csv_path = os.path.join(media_dir, f'{username}_media.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['type', 'shortcode', 'url', 'caption', 'likes', 'date', 'is_video'])
        writer.writeheader()
        for p in results['posts']:
            writer.writerow({k: p.get(k, '') for k in writer.fieldnames})

    results['csv_path'] = csv_path
    return results


def extract_tiktok_media(username, max_videos=30, log_callback=print, progress_callback=None):
    """Extract video URLs from a TikTok profile using Selenium."""
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from webdriver_manager.chrome import ChromeDriverManager

    media_dir = os.path.join('media', username)
    os.makedirs(media_dir, exist_ok=True)

    results = {'media_dir': media_dir, 'posts': [], 'errors': []}

    log_callback(f"Abriendo perfil TikTok: @{username}")

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(f'https://www.tiktok.com/@{username}')
        time.sleep(5)

        # Scroll to load videos
        for scroll in range(5):
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(2)

        # Extract video links
        video_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')
        seen = set()
        count = 0

        for link in video_links:
            if count >= max_videos:
                break
            href = link.get_attribute('href')
            if href and href not in seen:
                seen.add(href)
                video_id = href.split('/video/')[-1].split('?')[0] if '/video/' in href else ''
                results['posts'].append({
                    'type': 'video',
                    'url': href,
                    'video_id': video_id,
                    'platform': 'tiktok'
                })
                count += 1
                log_callback(f"[{count}] Video: {video_id}")
                if progress_callback:
                    progress_callback(count, max_videos)

        driver.quit()
    except Exception as e:
        results['errors'].append(str(e))
        log_callback(f"Error TikTok: {e}")

    # Save CSV
    csv_path = os.path.join(media_dir, f'{username}_tiktok_media.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['type', 'url', 'video_id', 'platform'])
        writer.writeheader()
        for p in results['posts']:
            writer.writerow(p)

    results['csv_path'] = csv_path
    return results


def extract_youtube_media(channel_name, max_videos=30, log_callback=print, progress_callback=None):
    """Extract video URLs from a YouTube channel using Selenium."""
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from webdriver_manager.chrome import ChromeDriverManager

    media_dir = os.path.join('media', channel_name)
    os.makedirs(media_dir, exist_ok=True)

    results = {'media_dir': media_dir, 'posts': [], 'errors': []}

    log_callback(f"Buscando canal YouTube: {channel_name}")

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(f'https://www.youtube.com/@{channel_name}/videos')
        time.sleep(5)

        for scroll in range(3):
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(2)

        video_links = driver.find_elements(By.CSS_SELECTOR, 'a#video-title-link')
        count = 0

        for link in video_links:
            if count >= max_videos:
                break
            href = link.get_attribute('href')
            title = link.get_attribute('title') or ''
            if href:
                video_id = href.split('v=')[-1].split('&')[0] if 'v=' in href else ''
                results['posts'].append({
                    'type': 'video',
                    'url': href,
                    'title': title[:100],
                    'video_id': video_id,
                    'thumbnail': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
                    'platform': 'youtube'
                })
                count += 1
                log_callback(f"[{count}] {title[:50]}...")
                if progress_callback:
                    progress_callback(count, max_videos)

        driver.quit()
    except Exception as e:
        results['errors'].append(str(e))
        log_callback(f"Error YouTube: {e}")

    csv_path = os.path.join(media_dir, f'{channel_name}_youtube_media.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['type', 'url', 'title', 'video_id', 'thumbnail', 'platform'])
        writer.writeheader()
        for p in results['posts']:
            writer.writerow(p)

    results['csv_path'] = csv_path
    return results
