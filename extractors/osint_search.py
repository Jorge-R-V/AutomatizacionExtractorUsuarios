"""
Buscador OSINT Multi-Plataforma.
Busca un nombre de usuario en Instagram, TikTok, X (Twitter) y Facebook
simultáneamente y devuelve los perfiles encontrados.
"""
import threading
import time
import csv
import json
import os

from extractors import extractor_tiktok
from extractors import extractor_x
from extractors import extractor_fb
from extractors import extractor_linkedin
from extractors import extractor_youtube


def _parse_ig_count(text):
    """Convierte contadores de Instagram tipo '1.2M', '500K', '3,456' a entero."""
    text = text.strip().replace(",", "").replace(".", "")
    multiplier = 1
    if text.upper().endswith("M"):
        # Ojo: si ya quitamos el punto, "12M" de "1.2M" → 12 * 100000 = 1200000
        text = text[:-1]
        multiplier = 1000000
        # Si el original tenía decimales, ajustar
    elif text.upper().endswith("K"):
        text = text[:-1]
        multiplier = 1000
    try:
        val = float(text) * multiplier
        return int(val)
    except ValueError:
        return 0

def buscar_en_todas_las_redes(username, redes=None, log_callback=print, progress_callback=None):
    """
    Busca un nombre de usuario en múltiples redes sociales.
    
    Args:
        username: El nombre de usuario a buscar (sin @).
        redes: Lista de redes donde buscar. Ejemplo: ['instagram', 'tiktok', 'x', 'facebook'].
                Si es None, busca en todas.
        log_callback: Función para reportar mensajes de log.
        progress_callback: Función para reportar progreso (count, platform).
    
    Returns:
        dict con los resultados por plataforma.
    """
    if redes is None:
        redes = ['instagram', 'tiktok', 'x', 'facebook', 'linkedin', 'youtube']
    
    username = username.strip().lstrip("@")
    resultados = {}
    errores = {}
    hilos = []
    lock = threading.Lock()
    
    total_redes = len(redes)
    completadas = [0]
    
    log_callback(f"=== BÚSQUEDA OSINT MULTI-PLATAFORMA ===")
    log_callback(f"Objetivo: @{username}")
    log_callback(f"Redes seleccionadas: {', '.join(r.upper() for r in redes)}")
    log_callback(f"{'='*40}")
    
    def buscar_instagram():
        import re
        log_callback(f"[Instagram] Buscando perfil @{username}...")

        # ---- MÉTODO PRINCIPAL: Selenium headless (sin credenciales) ----
        driver = None
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager.chrome import ChromeDriverManager

            log_callback("[Instagram] Configurando navegador...")
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

            url = f"https://www.instagram.com/{username}/"
            driver.get(url)
            import time
            time.sleep(5)

            # Verificar si el perfil existe
            title = driver.title
            if "Page Not Found" in title or "not found" in title.lower():
                log_callback(f"[Instagram] Perfil @{username} no existe.")
                with lock:
                    errores['instagram'] = "Perfil no encontrado"
                return

            # Extraer datos de meta tags renderizadas
            metas = driver.execute_script("""
                var r = {};
                var t = document.querySelector('meta[property="og:title"]');
                var d = document.querySelector('meta[property="og:description"]');
                var i = document.querySelector('meta[property="og:image"]');
                var desc = document.querySelector('meta[name="description"]');
                r.ogTitle = t ? t.content : null;
                r.ogDesc = d ? d.content : (desc ? desc.content : null);
                r.ogImage = i ? i.content : null;
                return r;
            """)

            datos = {
                "platform": "Instagram",
                "username": username,
                "full_name": "",
                "bio": "",
                "followers": 0,
                "following": 0,
                "posts": 0,
                "is_private": False,
                "is_verified": False,
                "external_url": "",
                "profile_pic": metas.get("ogImage", "") or "",
                "profile_url": f"https://www.instagram.com/{username}/",
            }

            # Parsear og:title → nombre
            og_title = metas.get("ogTitle", "")
            if og_title:
                name_m = re.match(r'^(.+?)\s*[\(@]', og_title)
                if name_m:
                    datos["full_name"] = name_m.group(1).strip()
                else:
                    datos["full_name"] = og_title.split("•")[0].strip()

            # Parsear og:description → stats + bio
            og_desc = metas.get("ogDesc", "")
            if og_desc:
                # Formato: "670M seguidores, 647 siguiendo, 4,099 publicaciones - bio..."
                # O en inglés: "670M Followers, 647 Following, 4,099 Posts - bio..."
                stats_m = re.search(r'([\d,.]+[KkMm]?)\s*(?:seguidores|followers)', og_desc, re.IGNORECASE)
                if stats_m:
                    datos["followers"] = _parse_ig_count(stats_m.group(1))
                stats_m = re.search(r'([\d,.]+[KkMm]?)\s*(?:siguiendo|following)', og_desc, re.IGNORECASE)
                if stats_m:
                    datos["following"] = _parse_ig_count(stats_m.group(1))
                stats_m = re.search(r'([\d,.]+[KkMm]?)\s*(?:publicaciones|posts)', og_desc, re.IGNORECASE)
                if stats_m:
                    datos["posts"] = _parse_ig_count(stats_m.group(1))
                # Bio: después del guion que sigue a las stats
                bio_m = re.search(r'(?:publicaciones|posts)\s*[-–—]\s*(.+)', og_desc, re.IGNORECASE)
                if bio_m:
                    bio_text = bio_m.group(1).strip()
                    # Limpiar sufijo "Ver fotos y vídeos..."
                    bio_text = re.sub(r'\s*[-–—]?\s*Ver fotos.*$', '', bio_text, flags=re.IGNORECASE)
                    datos["bio"] = bio_text

            # Verificado y privado desde el HTML renderizado
            page_src = driver.page_source
            if '"is_verified":true' in page_src or '"isVerified":true' in page_src:
                datos["is_verified"] = True
            if '"is_private":true' in page_src:
                datos["is_private"] = True

            if datos["full_name"] or datos["followers"] > 0:
                with lock:
                    resultados['instagram'] = datos
                log_callback(f"[Instagram] Perfil encontrado: @{username} ({datos['full_name']})")
                log_callback(f"[Instagram] {datos['followers']:,} seguidores, {datos['posts']:,} publicaciones")
                log_callback(f"[Instagram] \u2713 Perfil encontrado")
                return
            else:
                log_callback("[Instagram] Selenium no extrajo datos suficientes.")
                with lock:
                    errores['instagram'] = "No se pudieron extraer datos"

        except Exception as e:
            log_callback(f"[Instagram] Error: {e}")
            with lock:
                errores['instagram'] = str(e)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            with lock:
                completadas[0] += 1
                if progress_callback:
                    progress_callback(completadas[0], f"Instagram ({completadas[0]}/{total_redes})")
    
    def buscar_tiktok():
        try:
            datos = extractor_tiktok.buscar_perfil_tiktok(username, log_callback)
            with lock:
                if datos:
                    resultados['tiktok'] = datos
                    log_callback(f"[TikTok] ✓ Perfil encontrado")
                else:
                    errores['tiktok'] = "No encontrado"
                    log_callback(f"[TikTok] ✗ No se encontró el perfil")
        except Exception as e:
            with lock:
                errores['tiktok'] = str(e)
            log_callback(f"[TikTok] ✗ Error: {e}")
        finally:
            with lock:
                completadas[0] += 1
                if progress_callback:
                    progress_callback(completadas[0], f"TikTok ({completadas[0]}/{total_redes})")
    
    def buscar_x():
        try:
            datos = extractor_x.buscar_perfil_x(username, log_callback)
            with lock:
                if datos:
                    resultados['x'] = datos
                    log_callback(f"[X] ✓ Perfil encontrado")
                else:
                    errores['x'] = "No encontrado"
                    log_callback(f"[X] ✗ No se encontró el perfil")
        except Exception as e:
            with lock:
                errores['x'] = str(e)
            log_callback(f"[X] ✗ Error: {e}")
        finally:
            with lock:
                completadas[0] += 1
                if progress_callback:
                    progress_callback(completadas[0], f"X ({completadas[0]}/{total_redes})")
    
    def buscar_facebook():
        try:
            datos = extractor_fb.buscar_perfil_fb(username, log_callback)
            with lock:
                if datos:
                    resultados['facebook'] = datos
                    log_callback(f"[Facebook] ✓ Perfil encontrado")
                else:
                    errores['facebook'] = "No encontrado"
                    log_callback(f"[Facebook] ✗ No se encontró el perfil")
        except Exception as e:
            with lock:
                errores['facebook'] = str(e)
            log_callback(f"[Facebook] ✗ Error: {e}")
        finally:
            with lock:
                completadas[0] += 1
                if progress_callback:
                    progress_callback(completadas[0], f"Facebook ({completadas[0]}/{total_redes})")
    
    def buscar_linkedin():
        try:
            datos = extractor_linkedin.buscar_perfil_linkedin(username, log_callback)
            with lock:
                if datos and datos.get('found'):
                    resultados['linkedin'] = datos
                    log_callback(f"[LinkedIn] ✓ Perfil encontrado")
                else:
                    errores['linkedin'] = "No encontrado"
                    log_callback(f"[LinkedIn] ✗ No se encontró el perfil")
        except Exception as e:
            with lock:
                errores['linkedin'] = str(e)
            log_callback(f"[LinkedIn] ✗ Error: {e}")
        finally:
            with lock:
                completadas[0] += 1
                if progress_callback:
                    progress_callback(completadas[0], f"LinkedIn ({completadas[0]}/{total_redes})")

    def buscar_youtube():
        try:
            datos = extractor_youtube.buscar_perfil_youtube(username, log_callback)
            with lock:
                if datos and datos.get('found'):
                    resultados['youtube'] = datos
                    log_callback(f"[YouTube] ✓ Canal encontrado")
                else:
                    errores['youtube'] = "No encontrado"
                    log_callback(f"[YouTube] ✗ No se encontró el canal")
        except Exception as e:
            with lock:
                errores['youtube'] = str(e)
            log_callback(f"[YouTube] ✗ Error: {e}")
        finally:
            with lock:
                completadas[0] += 1
                if progress_callback:
                    progress_callback(completadas[0], f"YouTube ({completadas[0]}/{total_redes})")

    # Map de funciones
    funciones = {
        'instagram': buscar_instagram,
        'tiktok': buscar_tiktok,
        'x': buscar_x,
        'facebook': buscar_facebook,
        'linkedin': buscar_linkedin,
        'youtube': buscar_youtube,
    }
    
    # Lanzar hilos para búsqueda paralela
    for red in redes:
        if red in funciones:
            t = threading.Thread(target=funciones[red], daemon=True)
            hilos.append(t)
            t.start()
    
    # Esperar a que todos terminen
    for t in hilos:
        t.join(timeout=60)  # Max 60 seconds per platform
    
    log_callback(f"\n{'='*40}")
    log_callback(f"RESULTADOS: {len(resultados)} perfiles encontrados de {total_redes} redes buscadas.")
    if errores:
        log_callback(f"ERRORES: {', '.join(errores.keys())}")
    
    return {
        "username": username,
        "found": resultados,
        "errors": errores,
        "total_found": len(resultados),
        "total_searched": total_redes
    }


def guardar_resultados_osint(resultados, output_file, log_callback=print):
    """Guarda los resultados de la búsqueda OSINT en un CSV unificado."""
    try:
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Plataforma', 'Campo', 'Valor'])
            
            for plataforma, datos in resultados.get("found", {}).items():
                for campo, valor in datos.items():
                    writer.writerow([plataforma.upper(), campo, valor])
                writer.writerow([])  # Separator
        
        log_callback(f"Resultados guardados en {output_file}")
        return True
    except Exception as e:
        log_callback(f"Error al guardar: {e}")
        return False
