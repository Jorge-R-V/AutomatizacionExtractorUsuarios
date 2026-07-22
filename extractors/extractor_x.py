"""
Extractor de datos públicos de perfiles de X (Twitter).
Utiliza Selenium para navegar al perfil público y extraer
información visible sin necesidad de autenticación para perfiles públicos.
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
import json


def _crear_driver_x(headless=True, log_callback=print):
    """Crea un driver de Chrome configurado para X."""
    log_callback("[X] Configurando navegador...")
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

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    return driver


def buscar_perfil_x(username, log_callback=print):
    """Busca un perfil público de X y devuelve sus datos públicos."""
    username = username.strip().lstrip("@")
    log_callback(f"[X] Buscando perfil: @{username}...")

    driver = None
    try:
        driver = _crear_driver_x(headless=True, log_callback=log_callback)
        url = f"https://x.com/{username}"
        driver.get(url)
        time.sleep(random.uniform(3, 5))

        # Check if account exists
        page_source = driver.page_source
        if "This account doesn" in page_source or "Esta cuenta no existe" in page_source:
            log_callback(f"[X] La cuenta @{username} no existe.")
            return None
        if "Account suspended" in page_source or "Cuenta suspendida" in page_source:
            log_callback(f"[X] La cuenta @{username} está suspendida.")
            return None

        profile = {
            "platform": "X (Twitter)",
            "username": username,
            "full_name": "",
            "bio": "",
            "location": "",
            "website": "",
            "join_date": "",
            "followers": 0,
            "following": 0,
            "tweets": 0,
            "verified": False,
            "profile_pic": "",
            "profile_url": f"https://x.com/{username}",
        }

        # Extract from page source using JSON-LD or meta tags
        profile = _extract_from_meta(driver, profile)
        profile = _extract_from_page(driver, profile)

        if profile["full_name"] or profile["followers"] > 0:
            log_callback(f"[X] Perfil encontrado: @{username} ({profile['full_name']})")
            return profile
        else:
            log_callback(f"[X] No se pudieron extraer datos del perfil @{username}.")
            return None

    except Exception as e:
        log_callback(f"[X] Error: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def _extract_from_meta(driver, profile):
    """Extrae datos de las meta tags del perfil."""
    try:
        # og:title usually has the name
        metas = driver.find_elements(By.CSS_SELECTOR, 'meta[property="og:title"]')
        for meta in metas:
            content = meta.get_attribute("content")
            if content:
                # Format: "Name (@username) / X"
                name_match = re.match(r'^(.+?)\s*\(@', content)
                if name_match:
                    profile["full_name"] = name_match.group(1).strip()

        # og:description usually has the bio
        metas = driver.find_elements(By.CSS_SELECTOR, 'meta[property="og:description"]')
        for meta in metas:
            content = meta.get_attribute("content")
            if content:
                profile["bio"] = content

        # og:image for profile pic
        metas = driver.find_elements(By.CSS_SELECTOR, 'meta[property="og:image"]')
        for meta in metas:
            content = meta.get_attribute("content")
            if content and "profile_images" in content:
                profile["profile_pic"] = content

    except Exception:
        pass
    return profile


def _extract_from_page(driver, profile):
    """Extrae datos del DOM de la página del perfil."""
    html = driver.page_source

    # Extract follower/following counts from page source
    # X typically renders these in the page
    try:
        # Try finding follower links
        links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/verified_followers"], a[href*="/followers"]')
        for link in links:
            text = link.text
            count = _parse_count(text)
            if count is not None:
                profile["followers"] = count

        links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/following"]')
        for link in links:
            text = link.text
            count = _parse_count(text)
            if count is not None:
                profile["following"] = count
    except Exception:
        pass

    # Fallback: regex on HTML
    try:
        followers_match = re.search(r'"followers_count"\s*:\s*(\d+)', html)
        if followers_match:
            profile["followers"] = int(followers_match.group(1))

        following_match = re.search(r'"friends_count"\s*:\s*(\d+)', html)
        if following_match:
            profile["following"] = int(following_match.group(1))

        tweets_match = re.search(r'"statuses_count"\s*:\s*(\d+)', html)
        if tweets_match:
            profile["tweets"] = int(tweets_match.group(1))

        verified_match = re.search(r'"verified"\s*:\s*(true|false)', html)
        if verified_match:
            profile["verified"] = verified_match.group(1) == "true"

        location_match = re.search(r'"location"\s*:\s*"([^"]*)"', html)
        if location_match and location_match.group(1):
            profile["location"] = location_match.group(1)

    except Exception:
        pass

    return profile


def _parse_count(text):
    """Convierte texto como '1.5M Followers' a número."""
    if not text:
        return None
    text = text.strip().split()[0]
    text = text.replace(",", "").replace(".", "")

    multipliers = {"K": 1000, "M": 1000000, "B": 1000000000,
                   "k": 1000, "m": 1000000, "mil": 1000}

    for suffix, mult in multipliers.items():
        if text.endswith(suffix):
            try:
                return int(float(text[:-len(suffix)]) * mult)
            except ValueError:
                return None
    try:
        return int(text)
    except ValueError:
        return None


def extraer_seguidores_x(username, output_file, log_callback=print, progress_callback=None):
    """
    Extrae la información pública del perfil de X.
    Para obtener la lista de seguidores se requiere interacción manual vía Selenium.
    """
    profile = buscar_perfil_x(username, log_callback)
    if not profile:
        log_callback("[X] No se pudo obtener información del perfil.")
        return False

    try:
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Campo', 'Valor'])
            for key, value in profile.items():
                writer.writerow([key, value])

        log_callback(f"[X] Datos del perfil guardados en {output_file}")
        if progress_callback:
            progress_callback(1, username)
        return True

    except Exception as e:
        log_callback(f"[X] Error al guardar datos: {e}")
        return False


def extraer_lista_seguidores_x(driver, username, output_file, log_callback=print, progress_callback=None):
    """
    Extrae la lista de seguidores de X usando Selenium con sesión manual.
    El usuario debe haber iniciado sesión previamente en el navegador.
    """
    username = username.strip().lstrip("@")
    url = f"https://x.com/{username}/followers"

    log_callback(f"[X] Navegando a seguidores de @{username}...")
    driver.get(url)
    time.sleep(random.uniform(3, 5))

    usuarios = set()
    intentos_sin_nuevos = 0

    try:
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Username', 'Full Name'])

            for i in range(500):  # Max 500 scrolls
                html = driver.page_source

                # Find usernames in follower list cells
                cells = driver.find_elements(By.CSS_SELECTOR, '[data-testid="UserCell"]')
                nuevos = 0

                for cell in cells:
                    try:
                        links = cell.find_elements(By.CSS_SELECTOR, 'a[role="link"]')
                        uname = ""
                        fname = ""
                        for link in links:
                            href = link.get_attribute("href") or ""
                            if "/status/" not in href and href.startswith("https://x.com/"):
                                uname_candidate = href.replace("https://x.com/", "").strip("/")
                                if uname_candidate and uname_candidate != username:
                                    uname = uname_candidate
                                    # Try to get full name from the cell
                                    spans = cell.find_elements(By.CSS_SELECTOR, 'span')
                                    for span in spans:
                                        text = span.text.strip()
                                        if text and not text.startswith("@") and len(text) > 1:
                                            fname = text
                                            break
                                    break

                        if uname and uname not in usuarios:
                            usuarios.add(uname)
                            writer.writerow([uname, fname])
                            f.flush()
                            nuevos += 1
                            log_callback(f"[{len(usuarios)}] @{uname} - {fname}")
                            if progress_callback:
                                progress_callback(len(usuarios), uname)

                    except Exception:
                        continue

                if nuevos == 0:
                    intentos_sin_nuevos += 1
                    if intentos_sin_nuevos > 10:
                        log_callback("[X] No se encontraron más seguidores nuevos.")
                        break
                else:
                    intentos_sin_nuevos = 0

                # Scroll
                driver.execute_script("window.scrollBy(0, 600);")
                time.sleep(random.uniform(1.5, 3))

        log_callback(f"[X] Extracción completada. Total: {len(usuarios)} seguidores.")
        return True

    except Exception as e:
        log_callback(f"[X] Error durante la extracción: {e}")
        return False


def extraer_lista_x(driver, target, out_path, extract_type='followers', depth='basic',
                    log_callback=print, progress_callback=None):
    """
    Extrae seguidores y/o seguidos de X (Twitter).
    extract_type: 'followers', 'following', 'both'
    depth: 'basic' (solo usernames) o 'full' (visita cada perfil)
    """
    target = target.strip().lstrip("@")
    all_users = {}

    lists_to_extract = []
    if extract_type in ('followers', 'both'):
        lists_to_extract.append(('followers', f'https://x.com/{target}/followers'))
    if extract_type in ('following', 'both'):
        lists_to_extract.append(('following', f'https://x.com/{target}/following'))

    for list_type, list_url in lists_to_extract:
        tipo_es = "Seguidores" if list_type == "followers" else "Seguidos"
        log_callback(f"\n[X] Extrayendo {tipo_es} de @{target}...")
        driver.get(list_url)
        time.sleep(random.uniform(3, 5))

        usuarios_en_lista = set()
        intentos_sin_nuevos = 0

        for i in range(10000):
            cells = driver.find_elements(By.CSS_SELECTOR, '[data-testid="UserCell"]')
            nuevos = 0

            for cell in cells:
                try:
                    links = cell.find_elements(By.CSS_SELECTOR, 'a[role="link"]')
                    uname = ""
                    fname = ""
                    for link in links:
                        href = link.get_attribute("href") or ""
                        if "/status/" not in href and href.startswith("https://x.com/"):
                            uname_candidate = href.replace("https://x.com/", "").strip("/")
                            if uname_candidate and uname_candidate != target:
                                uname = uname_candidate
                                spans = cell.find_elements(By.CSS_SELECTOR, 'span')
                                for span in spans:
                                    text = span.text.strip()
                                    if text and not text.startswith("@") and len(text) > 1:
                                        fname = text
                                        break
                                break

                    if uname and uname not in usuarios_en_lista:
                        usuarios_en_lista.add(uname)
                        all_users[uname] = {"username": uname, "full_name": fname, "source": list_type}
                        nuevos += 1
                        log_callback(f"[{len(all_users)}] @{uname} - {fname} ({tipo_es})")
                        if progress_callback:
                            progress_callback(len(all_users), uname)
                except Exception:
                    continue

            if nuevos == 0:
                intentos_sin_nuevos += 1
                if intentos_sin_nuevos > 15:
                    log_callback(f"[X] No se encuentran más {tipo_es}.")
                    break
            else:
                intentos_sin_nuevos = 0

            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(random.uniform(1.5, 3))

        log_callback(f"[X] {tipo_es}: {len(usuarios_en_lista)} encontrados.")

    # --- depth=full: visitar cada perfil ---
    if depth == 'full' and all_users:
        log_callback(f"\n[X] Modo COMPLETO: visitando {len(all_users)} perfiles...")
        total = len(all_users)
        for idx, (uname, data) in enumerate(all_users.items(), 1):
            try:
                log_callback(f"[{idx}/{total}] Visitando @{uname}...")
                profile = buscar_perfil_x(uname, lambda m: None)  # Silent
                if profile:
                    data.update({
                        "full_name": profile.get("full_name", data.get("full_name", "")),
                        "bio": profile.get("bio", ""),
                        "followers": profile.get("followers", 0),
                        "following": profile.get("following", 0),
                        "tweets": profile.get("tweets", 0),
                        "verified": profile.get("verified", False),
                        "location": profile.get("location", ""),
                    })
                if progress_callback:
                    progress_callback(idx, uname)
            except Exception as e:
                log_callback(f"[{idx}/{total}] Error en @{uname}: {e}")

    # --- Guardar CSV ---
    try:
        import csv as csv_mod
        with open(out_path, mode='w', newline='', encoding='utf-8') as f:
            if depth == 'full':
                fields = ["username", "source", "full_name", "bio", "followers",
                           "following", "tweets", "verified", "location"]
            else:
                fields = ["username", "source", "full_name"]
            writer = csv_mod.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            for uname, data in all_users.items():
                writer.writerow(data)
        log_callback(f"\n[X] Guardados {len(all_users)} usuarios en {out_path}")
    except Exception as e:
        log_callback(f"Error al guardar CSV: {e}")
