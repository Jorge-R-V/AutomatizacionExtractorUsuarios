"""
Extractor de YouTube - Datos públicos de canales
Usa requests para búsqueda de perfiles y Selenium para listas.
"""
import re
import time
import random
import csv

from selenium.webdriver.common.by import By


def buscar_perfil_youtube(username, log_callback=print):
    """Busca un canal de YouTube por handle/username."""
    import requests

    log_callback(f"[YouTube] Buscando canal de @{username}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }

    # Try @handle first, then /c/ and /user/
    urls_to_try = [
        f"https://www.youtube.com/@{username}",
        f"https://www.youtube.com/c/{username}",
        f"https://www.youtube.com/user/{username}",
    ]

    for url in urls_to_try:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            html = response.text

            if response.status_code == 200 and "channelMetadataRenderer" in html:
                result = {
                    "username": username,
                    "platform": "YouTube",
                    "profile_url": url,
                    "found": True,
                }

                # Channel name
                name = re.search(r'"title":"(.+?)"', html)
                if name:
                    result["full_name"] = name.group(1)

                # Description
                desc = re.search(r'"description":"(.+?)"', html)
                if desc:
                    result["bio"] = desc.group(1)[:500].replace("\\n", " ")

                # Subscriber count from meta
                subs = re.search(r'"subscriberCountText":\{"simpleText":"(.+?)"', html)
                if subs:
                    result["subscribers"] = subs.group(1)

                # Video count
                vids = re.search(r'"videosCountText":\{"runs":\[\{"text":"(.+?)"', html)
                if vids:
                    result["videos"] = vids.group(1)

                # Country
                country = re.search(r'"country":\{"simpleText":"(.+?)"', html)
                if country:
                    result["location"] = country.group(1)

                # Avatar
                avatar = re.search(r'"avatar":\{"thumbnails":\[\{"url":"(.+?)"', html)
                if avatar:
                    result["profile_pic"] = avatar.group(1)

                # View count
                views = re.search(r'"viewCountText":\{"simpleText":"(.+?)"', html)
                if views:
                    result["total_views"] = views.group(1)

                # Join date
                joined = re.search(r'"joinedDateText":\{"runs":\[.+?"text":"(.+?)"', html)
                if joined:
                    result["joined"] = joined.group(1)

                log_callback(f"[YouTube] ✓ Encontrado: {result.get('full_name', username)} ({result.get('subscribers', '?')} suscriptores)")
                return result

        except Exception as e:
            continue

    log_callback(f"[YouTube] ✗ Canal no encontrado para '{username}'")
    return {"username": username, "platform": "YouTube", "found": False}


def extraer_lista_youtube(driver, target, out_path, extract_type='followers', depth='basic',
                          log_callback=print, progress_callback=None):
    """
    Extrae suscripciones públicas de YouTube.
    extract_type: 'followers' (no disponible), 'following' (suscripciones), 'both'
    depth: 'basic' o 'full'
    """
    target = target.strip().lstrip("@")
    all_users = {}

    # YouTube doesn't show subscriber lists publicly, only subscriptions
    lists_to_extract = []
    if extract_type in ('followers', 'both'):
        log_callback("[YouTube] ⚠ YouTube no permite ver la lista de suscriptores de un canal.")
        log_callback("[YouTube] Solo se pueden extraer las suscripciones públicas.")
    if extract_type in ('following', 'both'):
        lists_to_extract.append(('following', f'https://www.youtube.com/@{target}/channels'))

    if not lists_to_extract and extract_type == 'followers':
        # Fallback: at least try channels
        lists_to_extract.append(('following', f'https://www.youtube.com/@{target}/channels'))

    for list_type, list_url in lists_to_extract:
        log_callback(f"\n[YouTube] Extrayendo suscripciones de @{target}...")
        driver.get(list_url)
        time.sleep(random.uniform(3, 5))

        usuarios_en_lista = set()
        intentos_sin_nuevos = 0

        for i in range(10000):
            # YouTube channel cards
            links = driver.find_elements(By.CSS_SELECTOR,
                'a[href*="/@"], a[href*="/channel/"], a[href*="/c/"]')
            nuevos = 0

            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    text = link.text.strip()

                    # Extract channel handle
                    handle_match = re.search(r'/@([a-zA-Z0-9\._\-]+)', href)
                    channel_match = re.search(r'/channel/([a-zA-Z0-9\-_]+)', href)

                    uname = ""
                    if handle_match:
                        uname = handle_match.group(1)
                    elif channel_match:
                        uname = channel_match.group(1)

                    if not uname or uname == target:
                        continue

                    skip = {"feed", "about", "playlist", "watch", "shorts",
                            "trending", "gaming", "music", "sports", "news"}
                    if uname in skip:
                        continue

                    if uname not in usuarios_en_lista and len(text) > 0:
                        usuarios_en_lista.add(uname)
                        all_users[uname] = {
                            "username": uname,
                            "full_name": text.split("\n")[0].strip(),
                            "source": list_type,
                            "profile_url": href
                        }
                        nuevos += 1
                        log_callback(f"[{len(all_users)}] @{uname} - {text.split(chr(10))[0].strip()}")
                        if progress_callback:
                            progress_callback(len(all_users), uname)
                except Exception:
                    continue

            if nuevos == 0:
                intentos_sin_nuevos += 1
                if intentos_sin_nuevos > 15:
                    log_callback(f"[YouTube] No se encuentran más canales.")
                    break
            else:
                intentos_sin_nuevos = 0

            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(random.uniform(1.5, 3))

        log_callback(f"[YouTube] Suscripciones: {len(usuarios_en_lista)} encontradas.")

    # --- depth=full ---
    if depth == 'full' and all_users:
        log_callback(f"\n[YouTube] Modo COMPLETO: visitando {len(all_users)} canales...")
        total = len(all_users)
        for idx, (uname, data) in enumerate(all_users.items(), 1):
            try:
                log_callback(f"[{idx}/{total}] Visitando @{uname}...")
                profile = buscar_perfil_youtube(uname, lambda m: None)
                if profile and profile.get("found"):
                    data.update({
                        "full_name": profile.get("full_name", data.get("full_name", "")),
                        "bio": profile.get("bio", ""),
                        "subscribers": profile.get("subscribers", ""),
                        "videos": profile.get("videos", ""),
                        "total_views": profile.get("total_views", ""),
                        "location": profile.get("location", ""),
                    })
                if progress_callback:
                    progress_callback(idx, uname)
            except Exception as e:
                log_callback(f"[{idx}/{total}] Error en @{uname}: {e}")

    # --- Save CSV ---
    try:
        with open(out_path, mode='w', newline='', encoding='utf-8') as f:
            if depth == 'full':
                fields = ["username", "source", "full_name", "bio", "subscribers",
                           "videos", "total_views", "location", "profile_url"]
            else:
                fields = ["username", "source", "full_name", "profile_url"]
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            for uname, data in all_users.items():
                writer.writerow(data)
        log_callback(f"\n[YouTube] Guardados {len(all_users)} canales en {out_path}")
    except Exception as e:
        log_callback(f"Error al guardar CSV: {e}")
