"""
Extractor de LinkedIn - Datos publicos de perfiles
Usa Selenium con sesion manual del usuario.
"""
import re
import time
import random
import csv

from selenium.webdriver.common.by import By


def buscar_perfil_linkedin(username, log_callback=print):
    """Busca un perfil de LinkedIn por username/slug."""
    import requests

    log_callback(f"[LinkedIn] Buscando perfil de {username}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }

    result = {
        "username": username,
        "platform": "LinkedIn",
        "profile_url": f"https://www.linkedin.com/in/{username}",
        "found": False,
    }

    # Method 1: Try Selenium headless for LinkedIn (bypasses login redirect)
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        url = f"https://www.linkedin.com/in/{username}/"
        driver.get(url)
        time.sleep(4)

        html = driver.page_source
        current_url = driver.current_url

        # Check if we got redirected to login
        if "/login" in current_url or "/authwall" in current_url:
            # LinkedIn requires login - try extracting from what we can see
            log_callback("[LinkedIn] Redirigido a login. Extrayendo datos visibles...")

        # Extract from meta tags (LinkedIn shows some even without login)
        metas = driver.execute_script("""
            var r = {};
            var t = document.querySelector('meta[property="og:title"]');
            var d = document.querySelector('meta[property="og:description"]');
            var i = document.querySelector('meta[property="og:image"]');
            r.ogTitle = t ? t.content : null;
            r.ogDesc = d ? d.content : null;
            r.ogImage = i ? i.content : null;
            r.title = document.title;
            return r;
        """)

        title_text = metas.get("ogTitle") or metas.get("title") or ""

        # Reject login/register pages
        reject_words = ["login", "registrarse", "sign up", "sign in", "iniciar sesion",
                        "crear cuenta", "join", "authwall", "registro"]
        title_is_valid = title_text and not any(w in title_text.lower() for w in reject_words)

        # LinkedIn shows profile info in title even on authwall
        # Format: "Name - Title - LinkedIn"
        if title_is_valid and (username.lower() in title_text.lower() or "linkedin" in title_text.lower()):
            result["found"] = True
            parts = title_text.split(" - ")
            if parts:
                name = parts[0].strip()
                # Extra safety: reject if name looks like a page title
                if len(name) > 2 and not any(w in name.lower() for w in reject_words):
                    result["full_name"] = name
                if len(parts) > 1 and "linkedin" not in parts[1].lower():
                    result["headline"] = parts[1].strip()

        # Description often has bio
        og_desc = metas.get("ogDesc") or ""
        if og_desc and len(og_desc) > 10 and not any(w in og_desc.lower() for w in reject_words):
            result["found"] = True
            result["bio"] = og_desc[:500]

        # Profile pic
        og_img = metas.get("ogImage") or ""
        if og_img and "linkedin" in og_img and "logo" not in og_img.lower():
            result["profile_pic"] = og_img

        driver.quit()

    except Exception as e:
        log_callback(f"[LinkedIn] Selenium headless fallo: {e}")

    # Method 2: Fallback - Google search for LinkedIn profile
    if not result.get("found"):
        try:
            log_callback("[LinkedIn] Intentando via Google...")
            search_url = f"https://www.google.com/search?q=site:linkedin.com/in/{username}"
            resp = requests.get(search_url, headers=headers, timeout=10)

            if resp.status_code == 200:
                html = resp.text

                # Extract from Google snippet
                # Google shows: "Name - Title - LinkedIn"
                snippet_match = re.search(
                    rf'linkedin\.com/in/{re.escape(username)}.*?<h3[^>]*>(.+?)</h3>', html, re.DOTALL)
                if snippet_match:
                    result["found"] = True
                    raw_title = re.sub(r'<[^>]+>', '', snippet_match.group(1))
                    parts = raw_title.split(" - ")
                    result["full_name"] = parts[0].strip()
                    if len(parts) > 1 and "linkedin" not in parts[1].lower():
                        result["headline"] = parts[1].strip()

                # Extract description snippet
                desc_match = re.search(
                    rf'linkedin\.com/in/{re.escape(username)}.*?<span[^>]*class="[^"]*">(.+?)</span>',
                    html, re.DOTALL)
                if desc_match:
                    desc = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
                    if len(desc) > 20:
                        result["bio"] = desc[:500]

        except Exception as e2:
            log_callback(f"[LinkedIn] Google fallback error: {e2}")

    # Method 3: Direct requests as last resort
    if not result.get("found"):
        try:
            url = f"https://www.linkedin.com/in/{username}"
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            html = response.text

            # Even on redirect, check title
            title = re.search(r'<title>(.+?)</title>', html)
            if title:
                t = title.group(1)
                if username.lower() in t.lower() or ("linkedin" in t.lower() and "login" not in t.lower()):
                    result["found"] = True
                    parts = t.split(" - ")
                    result["full_name"] = parts[0].strip()
                    if len(parts) > 1 and "linkedin" not in parts[1].lower():
                        result["headline"] = parts[1].strip()

            og_title = re.search(r'property="og:title"\s+content="(.+?)"', html)
            if og_title:
                result["found"] = True
                parts = og_title.group(1).split(" - ")
                result["full_name"] = parts[0].strip()
                if len(parts) > 1 and "linkedin" not in parts[1].lower():
                    result["headline"] = parts[1].strip()

            og_desc = re.search(r'property="og:description"\s+content="(.+?)"', html)
            if og_desc:
                result["bio"] = og_desc.group(1)[:500]

            og_img = re.search(r'property="og:image"\s+content="(.+?)"', html)
            if og_img and "linkedin" in og_img.group(1):
                result["profile_pic"] = og_img.group(1)

        except Exception as e3:
            log_callback(f"[LinkedIn] Requests fallback error: {e3}")

    if result.get("found"):
        log_callback(f"[LinkedIn] Encontrado: {result.get('full_name', username)}")
    else:
        log_callback(f"[LinkedIn] Perfil no encontrado o requiere login.")

    return result


def extraer_lista_linkedin(driver, target, out_path, extract_type='followers', depth='basic',
                           log_callback=print, progress_callback=None):
    """
    Extrae conexiones/seguidores de LinkedIn.
    extract_type: 'followers', 'following' (conexiones), 'both'
    depth: 'basic' o 'full'
    """
    target = target.strip().lstrip("@")
    all_users = {}

    lists_to_extract = []
    if extract_type in ('followers', 'both'):
        lists_to_extract.append(('followers', f'https://www.linkedin.com/in/{target}/recent-activity/all/'))
    if extract_type in ('following', 'both'):
        lists_to_extract.append(('following', f'https://www.linkedin.com/search/results/people/?network=%5B%22F%22%5D'))

    for list_type, list_url in lists_to_extract:
        tipo_es = "Seguidores" if list_type == "followers" else "Conexiones"
        log_callback(f"\n[LinkedIn] Extrayendo {tipo_es} de {target}...")
        driver.get(list_url)
        time.sleep(random.uniform(4, 6))

        usuarios_en_lista = set()
        intentos_sin_nuevos = 0

        for i in range(10000):
            # LinkedIn uses various card layouts
            links = driver.find_elements(By.CSS_SELECTOR,
                'a[href*="/in/"], .entity-result__title-text a')
            nuevos = 0

            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    text = link.text.strip()

                    match = re.search(r'/in/([a-zA-Z0-9\-]+)/?', href)
                    if match and text and len(text) > 1:
                        uname = match.group(1)
                        skip = {target, "login", "signup", "feed", "mynetwork",
                                "jobs", "messaging", "notifications"}
                        if uname not in skip and uname not in usuarios_en_lista:
                            usuarios_en_lista.add(uname)
                            all_users[uname] = {
                                "username": uname,
                                "full_name": text.split("\n")[0].strip(),
                                "source": list_type,
                                "profile_url": f"https://www.linkedin.com/in/{uname}/"
                            }
                            nuevos += 1
                            log_callback(f"[{len(all_users)}] {uname} - {text.split(chr(10))[0].strip()} ({tipo_es})")
                            if progress_callback:
                                progress_callback(len(all_users), uname)
                except Exception:
                    continue

            if nuevos == 0:
                intentos_sin_nuevos += 1
                if intentos_sin_nuevos > 15:
                    log_callback(f"[LinkedIn] No se encuentran mas {tipo_es}.")
                    break
            else:
                intentos_sin_nuevos = 0

            # LinkedIn pagination: scroll or click "Next"
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(random.uniform(2, 4))

            # Try clicking next page button
            if i > 0 and i % 10 == 0:
                try:
                    next_btn = driver.find_elements(By.CSS_SELECTOR,
                        'button[aria-label="Siguiente"], button.artdeco-pagination__button--next')
                    if next_btn:
                        next_btn[0].click()
                        time.sleep(random.uniform(3, 5))
                except Exception:
                    pass

        log_callback(f"[LinkedIn] {tipo_es}: {len(usuarios_en_lista)} encontrados.")

    # --- depth=full ---
    if depth == 'full' and all_users:
        log_callback(f"\n[LinkedIn] Modo COMPLETO: visitando {len(all_users)} perfiles...")
        total = len(all_users)
        for idx, (uname, data) in enumerate(all_users.items(), 1):
            try:
                log_callback(f"[{idx}/{total}] Visitando {uname}...")
                driver.get(f"https://www.linkedin.com/in/{uname}/")
                time.sleep(random.uniform(3, 5))

                # Extract from page
                try:
                    headline_el = driver.find_elements(By.CSS_SELECTOR, '.text-body-medium')
                    if headline_el:
                        data["headline"] = headline_el[0].text.strip()
                except Exception:
                    pass

                try:
                    location_el = driver.find_elements(By.CSS_SELECTOR, '.text-body-small.inline')
                    if location_el:
                        data["location"] = location_el[0].text.strip()
                except Exception:
                    pass

                try:
                    connections_el = driver.find_elements(By.CSS_SELECTOR, '.t-bold')
                    for el in connections_el:
                        text = el.text.strip()
                        if "conexion" in text.lower() or "connection" in text.lower() or "+" in text:
                            data["connections"] = text
                            break
                except Exception:
                    pass

                if progress_callback:
                    progress_callback(idx, uname)
            except Exception as e:
                log_callback(f"[{idx}/{total}] Error en {uname}: {e}")

    # --- Save CSV ---
    try:
        with open(out_path, mode='w', newline='', encoding='utf-8') as f:
            if depth == 'full':
                fields = ["username", "source", "full_name", "headline",
                           "location", "connections", "profile_url"]
            else:
                fields = ["username", "source", "full_name", "profile_url"]
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            for uname, data in all_users.items():
                writer.writerow(data)
        log_callback(f"\n[LinkedIn] Guardados {len(all_users)} usuarios en {out_path}")
    except Exception as e:
        log_callback(f"Error al guardar CSV: {e}")
