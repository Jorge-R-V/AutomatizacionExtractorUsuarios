from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
import os
import re
import random

def configurar_driver(log_callback=print):
    log_callback("Abriendo Google Chrome...")
    chrome_options = Options()
    
    # Configuraciones críticas si estamos corriendo dentro de Docker (sin pantalla)
    if os.environ.get("DOCKER") == "1":
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        log_callback("Modo Docker: Chrome iniciado en modo Headless (invisible).")
    else:
        # Para que el navegador no se cierre inmediatamente si hay un error en local
        chrome_options.add_experimental_option("detach", True)
        
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def extraer_seguidores_selenium(driver, cuenta_objetivo, output_file, log_callback=print, progress_callback=None):
    lista_usuarios = set()
    log_callback("\nESCANEANDO CADA RINCÓN DEL CÓDIGO... (Buscando patrones)")
    
    try:
        with open(output_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Username'])
            
            for i in range(200):
                # OBTENEMOS TODO EL HTML
                html = driver.page_source
                
                # PATRONES DE BÚSQUEDA MÚLTIPLES:
                matches = re.findall(r'href="/([a-zA-Z0-9\._]+)/"', html)
                matches += re.findall(r'"username":"([a-zA-Z0-9\._]+)"', html)
                
                nuevos = 0
                for uname in matches:
                    if uname not in ["reels", "explore", "direct", "accounts", "emails", "legal", "about", "p", "tv", "tags", cuenta_objetivo]:
                        if 3 < len(uname) < 30 and uname not in lista_usuarios:
                            lista_usuarios.add(uname)
                            writer.writerow([uname])
                            file.flush()
                            nuevos += 1
                            
                            log_callback(f"[{len(lista_usuarios)}] {uname}")
                            if progress_callback:
                                progress_callback(len(lista_usuarios), uname)
                
                # SCROLL AGRESIVO
                driver.execute_script("window.scrollBy(0, 600);")
                driver.execute_script(
                    "document.querySelectorAll('div[role=\"dialog\"] div').forEach(d => {"
                    "if(d.scrollHeight > d.clientHeight) d.scrollBy(0, 600);"
                    "});"
                )
                
                time.sleep(random.uniform(2, 4))
                
                # Si no hay nada nuevo, forzamos un scroll interactivo
                if nuevos == 0 and i > 5:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    except Exception as e:
        log_callback(f"Error: {e}")
    finally:
        log_callback(f"\nEXTRACCIÓN COMPLETADA. Resultados temporales guardados.")


def extraer_lista_ig(driver, target, out_path, extract_type='followers', depth='basic',
                     log_callback=print, progress_callback=None):
    """
    Extrae seguidores y/o seguidos de Instagram.
    extract_type: 'followers', 'following', 'both'
    depth: 'basic' (solo usernames) o 'full' (visita cada perfil)
    """
    target = target.strip().lstrip("@")
    all_users = {}  # {username: {data}}

    lists_to_extract = []
    if extract_type in ('followers', 'both'):
        lists_to_extract.append(('followers', f'https://www.instagram.com/{target}/followers/'))
    if extract_type in ('following', 'both'):
        lists_to_extract.append(('following', f'https://www.instagram.com/{target}/following/'))

    for list_type, list_url in lists_to_extract:
        tipo_es = "Seguidores" if list_type == "followers" else "Seguidos"
        log_callback(f"\n[Instagram] Extrayendo {tipo_es} de @{target}...")
        driver.get(list_url)
        time.sleep(3)

        # Scroll the dialog popup
        lista_usuarios = set()
        intentos_sin_nuevos = 0

        for i in range(10000):  # Sin límite efectivo
            html = driver.page_source

            # Buscar usernames en el HTML
            matches = re.findall(r'href="/([a-zA-Z0-9\._]+)/"', html)
            matches += re.findall(r'"username":"([a-zA-Z0-9\._]+)"', html)

            blacklist = {"reels", "explore", "direct", "accounts", "emails",
                         "legal", "about", "p", "tv", "tags", "stories",
                         "reel", target}
            nuevos = 0
            for uname in matches:
                if uname in blacklist:
                    continue
                if 3 < len(uname) < 30 and uname not in lista_usuarios:
                    lista_usuarios.add(uname)
                    all_users[uname] = {"username": uname, "source": list_type}
                    nuevos += 1
                    log_callback(f"[{len(lista_usuarios)}] @{uname} ({tipo_es})")
                    if progress_callback:
                        progress_callback(len(all_users), uname)

            # Scroll en el dialog de seguidores
            driver.execute_script("""
                document.querySelectorAll('div[role="dialog"] div').forEach(d => {
                    if(d.scrollHeight > d.clientHeight) d.scrollBy(0, 600);
                });
            """)
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(random.uniform(1.5, 3))

            if nuevos == 0:
                intentos_sin_nuevos += 1
                if intentos_sin_nuevos > 15:
                    log_callback(f"[Instagram] No se encuentran más {tipo_es}.")
                    break
            else:
                intentos_sin_nuevos = 0

        log_callback(f"[Instagram] {tipo_es}: {len(lista_usuarios)} encontrados.")

    # --- Si es depth=full, visitar cada perfil ---
    if depth == 'full' and all_users:
        log_callback(f"\n[Instagram] Modo COMPLETO: visitando {len(all_users)} perfiles...")
        total = len(all_users)
        for idx, (uname, data) in enumerate(all_users.items(), 1):
            try:
                log_callback(f"[{idx}/{total}] Visitando @{uname}...")
                driver.get(f"https://www.instagram.com/{uname}/")
                time.sleep(random.uniform(2, 4))

                metas = driver.execute_script("""
                    var r = {};
                    var t = document.querySelector('meta[property="og:title"]');
                    var d = document.querySelector('meta[property="og:description"]');
                    r.ogTitle = t ? t.content : '';
                    r.ogDesc = d ? d.content : '';
                    return r;
                """)

                og_title = metas.get("ogTitle", "")
                if og_title:
                    name_m = re.match(r'^(.+?)\s*[\(@]', og_title)
                    data["full_name"] = name_m.group(1).strip() if name_m else og_title.split("•")[0].strip()

                og_desc = metas.get("ogDesc", "")
                if og_desc:
                    s = re.search(r'([\d,.]+[KkMm]?)\s*(?:seguidores|followers)', og_desc, re.IGNORECASE)
                    if s: data["followers"] = s.group(1)
                    s = re.search(r'([\d,.]+[KkMm]?)\s*(?:siguiendo|following)', og_desc, re.IGNORECASE)
                    if s: data["following"] = s.group(1)
                    s = re.search(r'([\d,.]+[KkMm]?)\s*(?:publicaciones|posts)', og_desc, re.IGNORECASE)
                    if s: data["posts"] = s.group(1)
                    bio_m = re.search(r'(?:publicaciones|posts)\s*[-–—]\s*(.+)', og_desc, re.IGNORECASE)
                    if bio_m:
                        bio = re.sub(r'\s*[-–—]?\s*Ver fotos.*$', '', bio_m.group(1), flags=re.IGNORECASE)
                        data["bio"] = bio.strip()

                if progress_callback:
                    progress_callback(idx, uname)
            except Exception as e:
                log_callback(f"[{idx}/{total}] Error en @{uname}: {e}")

    # --- Guardar CSV ---
    try:
        with open(out_path, mode='w', newline='', encoding='utf-8') as f:
            if depth == 'full':
                fields = ["username", "source", "full_name", "followers", "following", "posts", "bio"]
            else:
                fields = ["username", "source"]
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            for uname, data in all_users.items():
                writer.writerow(data)
        log_callback(f"\n[Instagram] Guardados {len(all_users)} usuarios en {out_path}")
    except Exception as e:
        log_callback(f"Error al guardar CSV: {e}")
