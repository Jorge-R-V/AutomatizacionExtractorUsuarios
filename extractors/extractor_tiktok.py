"""
Extractor de datos públicos de perfiles de TikTok.
Utiliza requests + BeautifulSoup para obtener información pública visible
en la página de perfil de TikTok sin necesidad de autenticación.
"""
import requests
import json
import re
import csv
import time
import random


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def buscar_perfil_tiktok(username, log_callback=print):
    """Busca un perfil público de TikTok y devuelve sus datos públicos."""
    username = username.strip().lstrip("@")
    url = f"https://www.tiktok.com/@{username}"
    log_callback(f"[TikTok] Buscando perfil: @{username}...")

    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        response = session.get(url, timeout=15)

        if response.status_code == 404:
            log_callback(f"[TikTok] Perfil @{username} no encontrado.")
            return None

        if response.status_code != 200:
            log_callback(f"[TikTok] Error HTTP {response.status_code} al acceder al perfil.")
            return None

        # TikTok embeds profile data in a JSON script tag
        html = response.text

        # Try to extract the SIGI_STATE or __UNIVERSAL_DATA_FOR_REHYDRATION__
        data = _extract_json_data(html)
        if data:
            profile = _parse_profile_data(data, username)
            if profile:
                log_callback(f"[TikTok] Perfil encontrado: @{profile.get('username', username)}")
                return profile

        # Fallback: regex extraction from raw HTML
        profile = _extract_from_html_fallback(html, username)
        if profile:
            log_callback(f"[TikTok] Perfil encontrado (modo alternativo): @{username}")
            return profile

        log_callback(f"[TikTok] No se pudieron extraer datos del perfil @{username}.")
        return None

    except requests.exceptions.Timeout:
        log_callback(f"[TikTok] Tiempo de espera agotado al conectar con TikTok.")
        return None
    except requests.exceptions.ConnectionError:
        log_callback(f"[TikTok] Error de conexión con TikTok.")
        return None
    except Exception as e:
        log_callback(f"[TikTok] Error inesperado: {e}")
        return None


def _extract_json_data(html):
    """Intenta extraer el JSON embebido en el HTML de TikTok."""
    # Pattern 1: __UNIVERSAL_DATA_FOR_REHYDRATION__
    match = re.search(
        r'<script\s+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"\s*type="application/json">\s*({.*?})\s*</script>',
        html, re.DOTALL
    )
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Pattern 2: SIGI_STATE
    match = re.search(r'window\[\'SIGI_STATE\'\]\s*=\s*({.*?});', html, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Pattern 3: Generic JSON-LD
    match = re.search(r'<script type="application/ld\+json">\s*({.*?})\s*</script>', html, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return None


def _parse_profile_data(data, username):
    """Parsea los datos JSON para extraer la info del perfil."""
    profile = {
        "platform": "TikTok",
        "username": username,
        "full_name": "",
        "bio": "",
        "followers": 0,
        "following": 0,
        "likes": 0,
        "videos": 0,
        "verified": False,
        "profile_pic": "",
        "profile_url": f"https://www.tiktok.com/@{username}",
    }

    # Navigate different possible JSON structures
    try:
        # __UNIVERSAL_DATA_FOR_REHYDRATION__ structure
        if "__DEFAULT_SCOPE__" in data:
            user_detail = data["__DEFAULT_SCOPE__"].get("webapp.user-detail", {})
            user_info = user_detail.get("userInfo", {})
            user = user_info.get("user", {})
            stats = user_info.get("stats", {})

            profile["username"] = user.get("uniqueId", username)
            profile["full_name"] = user.get("nickname", "")
            profile["bio"] = user.get("signature", "")
            profile["verified"] = user.get("verified", False)
            profile["profile_pic"] = user.get("avatarLarger", "")
            profile["followers"] = stats.get("followerCount", 0)
            profile["following"] = stats.get("followingCount", 0)
            profile["likes"] = stats.get("heartCount", 0)
            profile["videos"] = stats.get("videoCount", 0)
            return profile
    except (KeyError, TypeError):
        pass

    try:
        # SIGI_STATE structure
        if "UserModule" in data:
            users = data["UserModule"].get("users", {})
            stats_dict = data["UserModule"].get("stats", {})

            user_key = username.lower()
            for key in users:
                if key.lower() == user_key:
                    user = users[key]
                    s = stats_dict.get(key, {})
                    profile["username"] = user.get("uniqueId", username)
                    profile["full_name"] = user.get("nickname", "")
                    profile["bio"] = user.get("signature", "")
                    profile["verified"] = user.get("verified", False)
                    profile["profile_pic"] = user.get("avatarLarger", "")
                    profile["followers"] = s.get("followerCount", 0)
                    profile["following"] = s.get("followingCount", 0)
                    profile["likes"] = s.get("heartCount", 0)
                    profile["videos"] = s.get("videoCount", 0)
                    return profile
    except (KeyError, TypeError):
        pass

    return None


def _extract_from_html_fallback(html, username):
    """Intento de extracción por regex si no se encuentra JSON."""
    profile = {
        "platform": "TikTok",
        "username": username,
        "full_name": "",
        "bio": "",
        "followers": 0,
        "following": 0,
        "likes": 0,
        "videos": 0,
        "verified": False,
        "profile_pic": "",
        "profile_url": f"https://www.tiktok.com/@{username}",
    }

    # Try to extract follower count
    followers_match = re.search(r'"followerCount"\s*:\s*(\d+)', html)
    if followers_match:
        profile["followers"] = int(followers_match.group(1))

    following_match = re.search(r'"followingCount"\s*:\s*(\d+)', html)
    if following_match:
        profile["following"] = int(following_match.group(1))

    likes_match = re.search(r'"heartCount"\s*:\s*(\d+)', html)
    if likes_match:
        profile["likes"] = int(likes_match.group(1))

    nickname_match = re.search(r'"nickname"\s*:\s*"([^"]*)"', html)
    if nickname_match:
        profile["full_name"] = nickname_match.group(1)

    bio_match = re.search(r'"signature"\s*:\s*"([^"]*)"', html)
    if bio_match:
        profile["bio"] = bio_match.group(1)

    # Only return if we extracted at least something meaningful
    if profile["followers"] > 0 or profile["full_name"]:
        return profile

    return None


def extraer_seguidores_tiktok(username, output_file, log_callback=print, progress_callback=None):
    """
    Extrae la información pública del perfil de TikTok.
    NOTA: TikTok no expone la lista de seguidores públicamente en la web.
    Solo se puede obtener la información del perfil objetivo.
    """
    profile = buscar_perfil_tiktok(username, log_callback)
    if not profile:
        log_callback("[TikTok] No se pudo obtener información del perfil.")
        return False

    try:
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Campo', 'Valor'])
            for key, value in profile.items():
                writer.writerow([key, value])

        log_callback(f"[TikTok] Datos del perfil guardados en {output_file}")
        if progress_callback:
            progress_callback(1, username)
        return True

    except Exception as e:
        log_callback(f"[TikTok] Error al guardar datos: {e}")
        return False


def extraer_lista_tiktok(driver, target, out_path, extract_type='followers', depth='basic',
                         log_callback=print, progress_callback=None):
    """
    Extrae seguidores y/o seguidos de TikTok usando Selenium con sesión activa.
    extract_type: 'followers', 'following', 'both'
    depth: 'basic' (solo usernames) o 'full' (visita cada perfil)
    """
    import csv as csv_mod
    from selenium.webdriver.common.by import By
    import time as t
    import random as rnd

    target = target.strip().lstrip("@")
    all_users = {}

    lists_to_extract = []
    if extract_type in ('followers', 'both'):
        lists_to_extract.append(('followers', 'Seguidores'))
    if extract_type in ('following', 'both'):
        lists_to_extract.append(('following', 'Seguidos'))

    for list_type, tipo_es in lists_to_extract:
        log_callback(f"\n[TikTok] Extrayendo {tipo_es} de @{target}...")

        # Navigate to profile first
        driver.get(f"https://www.tiktok.com/@{target}")
        t.sleep(rnd.uniform(3, 5))

        # Try clicking on the followers/following count link
        try:
            if list_type == 'followers':
                # Click on followers count
                follower_link = driver.find_elements(
                    By.CSS_SELECTOR,
                    'a[href*="/followers"], [data-e2e="followers-count"]'
                )
                if follower_link:
                    follower_link[0].click()
                    t.sleep(2)
            else:
                following_link = driver.find_elements(
                    By.CSS_SELECTOR,
                    'a[href*="/following"], [data-e2e="following-count"]'
                )
                if following_link:
                    following_link[0].click()
                    t.sleep(2)
        except Exception as e:
            log_callback(f"[TikTok] No se pudo abrir el popup de {tipo_es}: {e}")
            log_callback(f"[TikTok] Intentando por URL directa...")
            # Fallback: navigate directly
            if list_type == 'followers':
                driver.get(f"https://www.tiktok.com/@{target}/followers")
            else:
                driver.get(f"https://www.tiktok.com/@{target}/following")
            t.sleep(rnd.uniform(3, 5))

        # Now scroll and extract usernames
        usuarios_en_lista = set()
        intentos_sin_nuevos = 0

        for i in range(10000):
            html = driver.page_source

            # Extract usernames from links and JSON
            matches = re.findall(r'href="/@([a-zA-Z0-9\._]+)"', html)
            matches += re.findall(r'"uniqueId":"([a-zA-Z0-9\._]+)"', html)

            blacklist = {target, "explore", "foryou", "following", "live"}
            nuevos = 0

            for uname in matches:
                if uname in blacklist:
                    continue
                if 2 < len(uname) < 30 and uname not in usuarios_en_lista:
                    usuarios_en_lista.add(uname)
                    all_users[uname] = {"username": uname, "source": list_type}
                    nuevos += 1
                    log_callback(f"[{len(all_users)}] @{uname} ({tipo_es})")
                    if progress_callback:
                        progress_callback(len(all_users), uname)

            # Scroll in the dialog or page
            driver.execute_script("""
                var dialogs = document.querySelectorAll('[class*="DivUserListBody"], [class*="follower"], [role="dialog"] div');
                dialogs.forEach(d => {
                    if(d.scrollHeight > d.clientHeight) d.scrollBy(0, 500);
                });
                window.scrollBy(0, 500);
            """)
            t.sleep(rnd.uniform(1.5, 3))

            if nuevos == 0:
                intentos_sin_nuevos += 1
                if intentos_sin_nuevos > 15:
                    log_callback(f"[TikTok] No se encuentran más {tipo_es}.")
                    break
            else:
                intentos_sin_nuevos = 0

        log_callback(f"[TikTok] {tipo_es}: {len(usuarios_en_lista)} encontrados.")

    # --- depth=full: visitar cada perfil ---
    if depth == 'full' and all_users:
        log_callback(f"\n[TikTok] Modo COMPLETO: visitando {len(all_users)} perfiles...")
        total = len(all_users)
        for idx, (uname, data) in enumerate(all_users.items(), 1):
            try:
                log_callback(f"[{idx}/{total}] Visitando @{uname}...")
                profile = buscar_perfil_tiktok(uname, lambda m: None)  # Silent
                if profile:
                    data.update({
                        "full_name": profile.get("full_name", ""),
                        "bio": profile.get("bio", ""),
                        "followers": profile.get("followers", 0),
                        "following": profile.get("following", 0),
                        "likes": profile.get("likes", 0),
                        "videos": profile.get("videos", 0),
                        "verified": profile.get("verified", False),
                    })
                if progress_callback:
                    progress_callback(idx, uname)
            except Exception as e:
                log_callback(f"[{idx}/{total}] Error en @{uname}: {e}")

    # --- Guardar CSV ---
    try:
        with open(out_path, mode='w', newline='', encoding='utf-8') as f:
            if depth == 'full':
                fields = ["username", "source", "full_name", "bio", "followers",
                           "following", "likes", "videos", "verified"]
            else:
                fields = ["username", "source"]
            writer = csv_mod.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            for uname, data in all_users.items():
                writer.writerow(data)
        log_callback(f"\n[TikTok] Guardados {len(all_users)} usuarios en {out_path}")
    except Exception as e:
        log_callback(f"Error al guardar CSV: {e}")
