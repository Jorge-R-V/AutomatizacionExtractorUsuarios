"""
Extractor de datos públicos de perfiles de Facebook / Meta.
Utiliza Selenium para navegar a perfiles públicos de Facebook
y extraer la información visible sin autenticación cuando sea posible.
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
import re
import random


def _crear_driver_fb(headless=True, log_callback=print):
    """Crea un driver de Chrome configurado para Facebook."""
    log_callback("[Facebook] Configurando navegador...")
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--lang=es-ES")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    return driver


def buscar_perfil_fb(username, log_callback=print):
    """Busca un perfil público de Facebook y devuelve datos públicos."""
    username = username.strip().lstrip("@")
    log_callback(f"[Facebook] Buscando perfil: {username}...")

    driver = None
    try:
        driver = _crear_driver_fb(headless=True, log_callback=log_callback)
        url = f"https://www.facebook.com/{username}"
        driver.get(url)
        time.sleep(random.uniform(4, 6))

        page_source = driver.page_source

        # Check if profile exists
        if "page you requested was not found" in page_source.lower() or \
           "la página que solicitaste no se encontró" in page_source.lower() or \
           "content isn't available" in page_source.lower():
            log_callback(f"[Facebook] Perfil '{username}' no encontrado.")
            return None

        profile = {
            "platform": "Facebook",
            "username": username,
            "full_name": "",
            "bio": "",
            "category": "",
            "likes": 0,
            "followers": 0,
            "website": "",
            "verified": False,
            "profile_pic": "",
            "profile_url": f"https://www.facebook.com/{username}",
        }

        # Extract from meta tags
        profile = _extract_meta_fb(driver, profile)

        # Extract from page content
        profile = _extract_page_fb(driver, profile)

        if profile["full_name"]:
            log_callback(f"[Facebook] Perfil encontrado: {profile['full_name']}")
            return profile
        else:
            log_callback(f"[Facebook] No se pudieron extraer datos del perfil '{username}'.")
            return None

    except Exception as e:
        log_callback(f"[Facebook] Error: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def _extract_meta_fb(driver, profile):
    """Extrae datos de meta tags de Facebook."""
    try:
        # og:title
        metas = driver.find_elements(By.CSS_SELECTOR, 'meta[property="og:title"]')
        for meta in metas:
            content = meta.get_attribute("content")
            if content:
                profile["full_name"] = content.strip()

        # og:description
        metas = driver.find_elements(By.CSS_SELECTOR, 'meta[property="og:description"]')
        for meta in metas:
            content = meta.get_attribute("content")
            if content:
                profile["bio"] = content.strip()

        # og:image
        metas = driver.find_elements(By.CSS_SELECTOR, 'meta[property="og:image"]')
        for meta in metas:
            content = meta.get_attribute("content")
            if content:
                profile["profile_pic"] = content

        # Title tag
        title = driver.title
        if title and " | Facebook" in title:
            profile["full_name"] = title.replace(" | Facebook", "").strip()

    except Exception:
        pass
    return profile


def _extract_page_fb(driver, profile):
    """Extrae datos del DOM de la página de Facebook."""
    html = driver.page_source

    try:
        # Extract follower/like counts from page text
        # Facebook pages often show "X people like this" or "X followers"
        followers_patterns = [
            r'([\d,.]+)\s*(?:seguidores|followers)',
            r'"follower_count"\s*:\s*(\d+)',
            r'"followers_count"\s*:\s*(\d+)',
        ]
        for pattern in followers_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                count_str = match.group(1).replace(",", "").replace(".", "")
                try:
                    profile["followers"] = int(count_str)
                    break
                except ValueError:
                    continue

        likes_patterns = [
            r'([\d,.]+)\s*(?:personas indicaron que les gusta|people like this|likes)',
            r'"page_likers"\s*:\s*(\d+)',
        ]
        for pattern in likes_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                count_str = match.group(1).replace(",", "").replace(".", "")
                try:
                    profile["likes"] = int(count_str)
                    break
                except ValueError:
                    continue

        # Category
        category_match = re.search(r'"category"\s*:\s*"([^"]*)"', html)
        if category_match:
            profile["category"] = category_match.group(1)

        # Website
        website_match = re.search(r'"website"\s*:\s*"([^"]*)"', html)
        if website_match:
            profile["website"] = website_match.group(1)

    except Exception:
        pass

    return profile


def extraer_perfil_fb(username, output_file, log_callback=print, progress_callback=None):
    """Extrae la información pública del perfil de Facebook."""
    profile = buscar_perfil_fb(username, log_callback)
    if not profile:
        log_callback("[Facebook] No se pudo obtener información del perfil.")
        return False

    try:
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Campo', 'Valor'])
            for key, value in profile.items():
                writer.writerow([key, value])

        log_callback(f"[Facebook] Datos del perfil guardados en {output_file}")
        if progress_callback:
            progress_callback(1, username)
        return True

    except Exception as e:
        log_callback(f"[Facebook] Error al guardar datos: {e}")
        return False


def extraer_amigos_fb(driver, username, output_file, log_callback=print, progress_callback=None):
    """
    Extrae la lista de amigos/seguidores de Facebook con sesión manual.
    El usuario debe haber iniciado sesión previamente en el navegador.
    """
    username = username.strip().lstrip("@")
    url = f"https://www.facebook.com/{username}/friends"

    log_callback(f"[Facebook] Navegando a amigos de {username}...")
    driver.get(url)
    time.sleep(random.uniform(4, 6))

    usuarios = set()
    intentos_sin_nuevos = 0

    try:
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Username/Profile URL', 'Full Name'])

            for i in range(300):  # Max 300 scrolls
                # Find friend cards/links
                links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="facebook.com/"]')

                nuevos = 0
                for link in links:
                    try:
                        href = link.get_attribute("href") or ""
                        text = link.text.strip()

                        # Filter only profile links (not posts, photos, etc.)
                        if not text or len(text) < 2:
                            continue
                        if "/friends" in href or "/photos" in href or "/videos" in href:
                            continue
                        if "/groups/" in href or "/events/" in href or "/marketplace/" in href:
                            continue

                        # Extract username from URL
                        profile_match = re.match(r'https?://(?:www\.)?facebook\.com/([a-zA-Z0-9.]+)/?$', href)
                        if profile_match:
                            uname = profile_match.group(1)
                            if uname not in ["friends", "photos", "videos", "about", "posts", username]:
                                key = uname
                                if key not in usuarios:
                                    usuarios.add(key)
                                    writer.writerow([uname, text])
                                    f.flush()
                                    nuevos += 1
                                    log_callback(f"[{len(usuarios)}] {uname} - {text}")
                                    if progress_callback:
                                        progress_callback(len(usuarios), uname)

                    except Exception:
                        continue

                if nuevos == 0:
                    intentos_sin_nuevos += 1
                    if intentos_sin_nuevos > 10:
                        log_callback("[Facebook] No se encontraron más amigos/seguidores.")
                        break
                else:
                    intentos_sin_nuevos = 0

                # Scroll
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(random.uniform(2, 4))

        log_callback(f"[Facebook] Extracción completada. Total: {len(usuarios)}")
        return True

    except Exception as e:
        log_callback(f"[Facebook] Error durante la extracción: {e}")
        return False


def extraer_lista_fb(driver, target, out_path, extract_type='followers', depth='basic',
                     log_callback=print, progress_callback=None):
    """
    Extrae seguidores y/o amigos de Facebook.
    extract_type: 'followers', 'following' (amigos), 'both'
    depth: 'basic' (solo usernames) o 'full' (visita cada perfil)
    """
    target = target.strip().lstrip("@")
    all_users = {}

    lists_to_extract = []
    if extract_type in ('followers', 'both'):
        lists_to_extract.append(('followers', f'https://www.facebook.com/{target}/followers'))
    if extract_type in ('following', 'both'):
        lists_to_extract.append(('following', f'https://www.facebook.com/{target}/friends'))

    for list_type, list_url in lists_to_extract:
        tipo_es = "Seguidores" if list_type == "followers" else "Amigos/Seguidos"
        log_callback(f"\n[Facebook] Extrayendo {tipo_es} de {target}...")
        driver.get(list_url)
        time.sleep(random.uniform(4, 6))

        usuarios_en_lista = set()
        intentos_sin_nuevos = 0

        for i in range(10000):
            links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="facebook.com/"]')
            nuevos = 0

            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    text = link.text.strip()

                    if not text or len(text) < 2:
                        continue
                    if any(x in href for x in ["/friends", "/photos", "/videos",
                                                "/groups/", "/events/", "/marketplace/",
                                                "/followers", "/login", "/watch",
                                                "/hashtag", "/pages", "/stories"]):
                        continue

                    profile_match = re.match(
                        r'https?://(?:www\.)?facebook\.com/([a-zA-Z0-9.]+)/?(?:\?.*)?$', href)
                    if profile_match:
                        uname = profile_match.group(1)
                        skip = {"friends", "photos", "videos", "about", "posts",
                                "followers", "following", "reels", target,
                                "login", "watch", "marketplace", "groups"}
                        if uname not in skip and uname not in usuarios_en_lista:
                            usuarios_en_lista.add(uname)
                            all_users[uname] = {"username": uname, "full_name": text, "source": list_type}
                            nuevos += 1
                            log_callback(f"[{len(all_users)}] {uname} - {text} ({tipo_es})")
                            if progress_callback:
                                progress_callback(len(all_users), uname)
                except Exception:
                    continue

            if nuevos == 0:
                intentos_sin_nuevos += 1
                if intentos_sin_nuevos > 15:
                    log_callback(f"[Facebook] No se encuentran más {tipo_es}.")
                    break
            else:
                intentos_sin_nuevos = 0

            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(random.uniform(2, 4))

        log_callback(f"[Facebook] {tipo_es}: {len(usuarios_en_lista)} encontrados.")

    # --- depth=full: visitar cada perfil ---
    if depth == 'full' and all_users:
        log_callback(f"\n[Facebook] Modo COMPLETO: visitando {len(all_users)} perfiles...")
        total = len(all_users)
        for idx, (uname, data) in enumerate(all_users.items(), 1):
            try:
                log_callback(f"[{idx}/{total}] Visitando {uname}...")
                profile = buscar_perfil_fb(uname, lambda m: None)  # Silent
                if profile:
                    data.update({
                        "full_name": profile.get("full_name", data.get("full_name", "")),
                        "bio": profile.get("bio", ""),
                        "followers": profile.get("followers", 0),
                        "likes": profile.get("likes", 0),
                        "category": profile.get("category", ""),
                        "website": profile.get("website", ""),
                    })
                if progress_callback:
                    progress_callback(idx, uname)
            except Exception as e:
                log_callback(f"[{idx}/{total}] Error en {uname}: {e}")

    # --- Guardar CSV ---
    try:
        with open(out_path, mode='w', newline='', encoding='utf-8') as f:
            if depth == 'full':
                fields = ["username", "source", "full_name", "bio", "followers",
                           "likes", "category", "website"]
            else:
                fields = ["username", "source", "full_name"]
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            for uname, data in all_users.items():
                writer.writerow(data)
        log_callback(f"\n[Facebook] Guardados {len(all_users)} usuarios en {out_path}")
    except Exception as e:
        log_callback(f"Error al guardar CSV: {e}")
