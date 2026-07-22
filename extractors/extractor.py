import instaloader
import time
import random
import csv
import os
from instaloader.exceptions import LoginRequiredException, ProfileNotExistsException, ConnectionException, BadCredentialsException

def login_instagram(L, usuario_secundario, contrasena, log_callback=print):
    """Maneja el login verificando que la sesión sea VÁLIDA."""
    archivo_sesion = f"session_{usuario_secundario}"
    intentar_login = False
    
    if os.path.exists(archivo_sesion):
        try:
            L.load_session_from_file(usuario_secundario, filename=archivo_sesion)
            log_callback("Verificando validez de la sesión guardada...")
            L.test_login() 
            log_callback("Sesión válida y activa.")
        except Exception as e:
            log_callback(f"La sesión guardada ya no es válida: {e}")
            os.remove(archivo_sesion) # Borramos la sesión muerta
            intentar_login = True
    else:
        intentar_login = True

    if intentar_login:
        log_callback(f"Iniciando sesión nueva para {usuario_secundario}...")
        try:
            L.login(usuario_secundario, contrasena)
            L.save_session_to_file(filename=archivo_sesion)
            log_callback("Nueva sesión iniciada y guardada correctamente.")
            time.sleep(5)
        except BadCredentialsException:
            log_callback("ERROR: Contraseña incorrecta. Por favor, revísala.")
            return False
        except Exception as e:
            log_callback(f"Error crítico al iniciar sesión: {e}")
            return False
    return True

def obtener_perfil_robusto(L, username, log_callback=print):
    """Estrategia para encontrar el perfil una vez logueados corectamente."""
    username = username.strip()
    try:
        log_callback(f"Buscando perfil '{username}'...")
        return instaloader.Profile.from_username(L.context, username)
    except ProfileNotExistsException:
        # Si falla el directo, intentamos buscarlo un poco más despacio
        time.sleep(2)
        try:
            for hit in instaloader.TopSearchResults(L.context, username).get_profiles():
                if hit.username.lower() == username.lower():
                    return hit
        except Exception:
            pass
        return None

def extraer_seguidores(usuario_secundario, contrasena, cuenta_objetivo, output_file, log_callback=print, progress_callback=None):
    L = instaloader.Instaloader()
    
    if not login_instagram(L, usuario_secundario, contrasena, log_callback):
        return False

    try:
        perfil = obtener_perfil_robusto(L, cuenta_objetivo, log_callback)
        
        if not perfil:
            log_callback(f"ERROR: No se encuentra '{cuenta_objetivo}'.")
            return False

        if perfil.is_private and not perfil.followed_by_viewer:
            log_callback(f"ERROR: '{cuenta_objetivo}' es PRIVADA y no la sigues.")
            return False

        with open(output_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Username', 'Full Name', 'User ID', 'Is Verified', 'Is Private'])
            
            log_callback(f"Extrayendo seguidores de {perfil.username}...")
            
            contador = 0
            # Usamos un try-except dentro del bucle por si Instagram nos corta a mitad
            try:
                for seguidor in perfil.get_followers():
                    datos = [seguidor.username, seguidor.full_name, seguidor.userid, seguidor.is_verified, seguidor.is_private]
                    writer.writerow(datos)
                    file.flush()
                    contador += 1
                    
                    msg = f"[{contador}] {seguidor.username}"
                    log_callback(msg)
                    if progress_callback:
                        progress_callback(contador, seguidor.username)
                        
                    time.sleep(random.uniform(4, 7)) # Pausa para seguridad
            except Exception as e:
                log_callback(f"\nLa extracción se detuvo inesperadamente: {e}")
                log_callback("Se han guardado los datos obtenidos hasta ahora.")

        return True

    except Exception as e:
        log_callback(f"Error inesperado: {e}")
        return False