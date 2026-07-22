"""
Interfaz Gráfica Clásica para la Suite OSINT de Extracción de Usuarios.
"""
__author__ = "Jorge R."
__copyright__ = "Copyright 2026, Proyecto DataExtractor"
__license__ = "MIT"
__version__ = "2.0.0"

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import queue
import os
from extractors import extractor
from extractors import extractor_selenium
from extractors import extractor_tiktok
import extractors.extractor_x as extractor_x
import extractors.extractor_fb as extractor_fb
import extractors.media_extractor as media_extractor
from extractors import osint_search
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Configuración básica de CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("DataExtractor | Suite OSINT Multi-Plataforma")
        self.geometry("1100x800")
        
        # Forzar que la ventana aparezca al frente
        self.attributes('-topmost', True)
        self.after(2000, lambda: self.attributes('-topmost', False))
        
        self.log_queue = queue.Queue()
        self.driver = None

        # ===== PESTAÑAS (TABS) =====
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(pady=10, padx=20, fill="both", expand=True)

        self.tab_osint = self.tabview.add("Buscador OSINT")
        self.tab_extract = self.tabview.add("Extractor")
        self.tab_history = self.tabview.add("Historial y Dashboard")
        self.tab_media = self.tabview.add("Multimedia y Likes")
        self.tab_settings = self.tabview.add("Configuración")
        
        self._build_osint_tab()
        self._build_extract_tab()
        self._build_history_tab()
        self._build_media_tab()
        self._build_settings_tab()
        
        # ===== CONSOLA / LOGS =====
        self.log_label = ctk.CTkLabel(self, text="Logs del Sistema", font=ctk.CTkFont(weight="bold"))
        self.log_label.pack(pady=(5, 0))
        self.textbox = ctk.CTkTextbox(self, state="disabled", height=200)
        self.textbox.pack(pady=(0, 10), padx=20, fill="both", expand=True)

        self.check_queue()

    # ===================================================================
    # PESTAÑA 1: Buscador OSINT (Inteligencia de Fuentes Abiertas)
    # ===================================================================
    def _build_osint_tab(self):
        tab = self.tab_osint

        ctk.CTkLabel(tab, text="Buscar Usuario en Múltiples Redes", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 5))
        ctk.CTkLabel(tab, text="Introduce un nombre de usuario y selecciona las redes donde buscarlo.",
                     text_color="gray").pack(pady=(0, 10))

        # Campo para ingresar el nombre de usuario
        self.osint_username = ctk.CTkEntry(tab, placeholder_text="Ej: elonmusk (sin @)", width=400)
        self.osint_username.pack(pady=5)

        # Casillas de verificación para las plataformas
        check_frame = ctk.CTkFrame(tab)
        check_frame.pack(pady=10)
        
        self.osint_ig = ctk.CTkCheckBox(check_frame, text="Instagram")
        self.osint_ig.select()
        self.osint_ig.pack(side="left", padx=10)
        
        self.osint_tt = ctk.CTkCheckBox(check_frame, text="TikTok")
        self.osint_tt.select()
        self.osint_tt.pack(side="left", padx=10)
        
        self.osint_x = ctk.CTkCheckBox(check_frame, text="X (Twitter)")
        self.osint_x.select()
        self.osint_x.pack(side="left", padx=10)
        
        self.osint_fb = ctk.CTkCheckBox(check_frame, text="Facebook")
        self.osint_fb.select()
        self.osint_fb.pack(side="left", padx=10)

        # Configuración del archivo de salida
        save_frame = ctk.CTkFrame(tab)
        save_frame.pack(pady=5, padx=20, fill="x")
        self.osint_output = ctk.StringVar()
        ctk.CTkButton(save_frame, text="Guardar CSV en...", width=150,
                      command=self._choose_osint_file).pack(side="left", padx=5)
        ctk.CTkLabel(save_frame, textvariable=self.osint_output, text_color="gray").pack(side="left", fill="x")

        # Botón para iniciar la búsqueda en todas las redes
        self.btn_osint = ctk.CTkButton(tab, text="Buscar en Todas las Redes", 
                                       font=ctk.CTkFont(weight="bold", size=14),
                                       command=self._start_osint, height=40)
        self.btn_osint.pack(pady=15)

        # Cuadro de texto para mostrar los resultados en tiempo real
        self.osint_results_text = ctk.CTkTextbox(tab, state="disabled", height=150)
        self.osint_results_text.pack(pady=5, padx=20, fill="both", expand=True)

    def _choose_osint_file(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Guardar resultados OSINT como"
        )
        if filename:
            self.osint_output.set(filename)

    def _start_osint(self):
        username = self.osint_username.get().strip()
        if not username:
            messagebox.showwarning("Faltan datos", "Introduce un nombre de usuario.")
            return
        
        redes = []
        if self.osint_ig.get(): redes.append("instagram")
        if self.osint_tt.get(): redes.append("tiktok")
        if self.osint_x.get(): redes.append("x")
        if self.osint_fb.get(): redes.append("facebook")
        
        if not redes:
            messagebox.showwarning("Faltan datos", "Selecciona al menos una red social.")
            return

        out_path = self.osint_output.get().strip()
        if not out_path:
            out_path = os.path.join("Output", f"osint_{username}.csv")
            self.osint_output.set(out_path)

        self.btn_osint.configure(state="disabled", text="Buscando...")
        self.osint_results_text.configure(state="normal")
        self.osint_results_text.delete("1.0", "end")
        self.osint_results_text.configure(state="disabled")
        
        threading.Thread(target=self._run_osint, args=(username, redes, out_path), daemon=True).start()

    def _run_osint(self, username, redes, out_path):
        def log_cb(msg):
            self.log(msg)
        
        def prog_cb(count, info):
            pass

        try:
            results = osint_search.buscar_en_todas_las_redes(
                username, redes=redes, log_callback=log_cb, progress_callback=prog_cb
            )
            osint_search.guardar_resultados_osint(results, out_path, log_cb)
            
            # Show results in the text area
            self.osint_results_text.configure(state="normal")
            self.osint_results_text.delete("1.0", "end")
            
            found = results.get("found", {})
            errors = results.get("errors", {})
            
            for platform, data in found.items():
                self.osint_results_text.insert("end", f"=== {platform.upper()} ===\n")
                for key, val in data.items():
                    if key in ("profile_pic",): continue
                    display_key = key.replace("_", " ").title()
                    if isinstance(val, bool):
                        val = "Si" if val else "No"
                    elif isinstance(val, int):
                        val = f"{val:,}"
                    self.osint_results_text.insert("end", f"  {display_key}: {val}\n")
                self.osint_results_text.insert("end", "\n")
            
            for platform, error in errors.items():
                self.osint_results_text.insert("end", f"=== {platform.upper()} === (Error: {error})\n\n")
            
            self.osint_results_text.configure(state="disabled")
            
        except Exception as e:
            self.log(f"Error en la búsqueda OSINT: {e}")
        finally:
            self.btn_osint.configure(state="normal", text="Buscar en Todas las Redes")

    # ===================================================================
    # PESTAÑA 2: Extracción Avanzada de Seguidores y Amigos
    # ===================================================================
    def _build_extract_tab(self):
        tab = self.tab_extract
        
        ctk.CTkLabel(tab, text="Extractor de Datos", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 5))

        # Selector de plataforma
        ctk.CTkLabel(tab, text="Selecciona la Red Social:", font=ctk.CTkFont(weight="bold")).pack(pady=(5, 0))
        self.platform_var = ctk.StringVar(value="Instagram")
        plat_frame = ctk.CTkFrame(tab)
        plat_frame.pack(pady=5)
        for plat in ["Instagram", "TikTok", "X (Twitter)", "Facebook"]:
            ctk.CTkRadioButton(plat_frame, text=plat, variable=self.platform_var, 
                             value=plat, command=self._update_extract_ui).pack(side="left", padx=8)

        # Opciones de método de extracción
        ctk.CTkLabel(tab, text="Método de Extracción:", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 0))
        self.method_var = ctk.StringVar(value="Automatic")
        method_frame = ctk.CTkFrame(tab)
        method_frame.pack(pady=5)
        self.radio_auto = ctk.CTkRadioButton(method_frame, text="Automático (sin iniciar sesión)", 
                                              variable=self.method_var, value="Automatic", command=self._update_extract_ui)
        self.radio_auto.pack(side="left", padx=10)
        self.radio_insta = ctk.CTkRadioButton(method_frame, text="Instaloader (Solo Instagram, requiere cuenta)", 
                                               variable=self.method_var, value="Instaloader", command=self._update_extract_ui)
        self.radio_insta.pack(side="left", padx=10)
        self.radio_sel = ctk.CTkRadioButton(method_frame, text="Navegador Interactivo (Selenium)", 
                                             variable=self.method_var, value="Selenium", command=self._update_extract_ui)
        self.radio_sel.pack(side="left", padx=10)

        # Contenedor para los parámetros del objetivo
        self.ext_inputs = ctk.CTkFrame(tab)
        self.ext_inputs.pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(self.ext_inputs, text="Nombre de la Cuenta Objetivo:").pack(pady=(10, 0))
        self.ext_target = ctk.CTkEntry(self.ext_inputs, placeholder_text="Ej: elonmusk")
        self.ext_target.pack(pady=5, padx=20, fill="x")

        # Panel de Credenciales (Específico para Instagram Instaloader)
        self.cred_frame = ctk.CTkFrame(self.ext_inputs)
        self.ext_user_label = ctk.CTkLabel(self.cred_frame, text="Tu Nombre de Usuario (Usa una cuenta secundaria):")
        self.ext_user_label.pack(pady=(5, 0))
        self.ext_user = ctk.CTkEntry(self.cred_frame, placeholder_text="Tu usuario")
        self.ext_user.pack(pady=5, padx=20, fill="x")
        self.ext_pass_label = ctk.CTkLabel(self.cred_frame, text="Tu Contraseña:")
        self.ext_pass_label.pack(pady=(5, 0))
        self.ext_pass = ctk.CTkEntry(self.cred_frame, show="*")
        self.ext_pass.pack(pady=5, padx=20, fill="x")

        # Botones para controlar el Navegador Interactivo (Selenium)
        self.sel_frame = ctk.CTkFrame(self.ext_inputs)
        self.btn_open_browser = ctk.CTkButton(self.sel_frame, text="1. Abrir Navegador", command=self._open_browser)
        self.btn_open_browser.pack(pady=5, fill="x")
        ctk.CTkLabel(self.sel_frame, text="Inicia sesión, ve al perfil del usuario y abre la lista de seguidores.\nLuego presiona el botón '2. Escanear Datos' que aparecerá abajo.").pack(pady=5)

        # Ajustes de donde se guardarán los resultados
        save_frame = ctk.CTkFrame(tab)
        save_frame.pack(pady=5, padx=20, fill="x")
        self.ext_output = ctk.StringVar()
        ctk.CTkButton(save_frame, text="Guardar resultados en...", width=150, command=self._choose_ext_file).pack(side="left", padx=5)
        ctk.CTkLabel(save_frame, textvariable=self.ext_output, text_color="gray").pack(side="left", fill="x")

        # Botón principal para iniciar la magia
        self.btn_extract = ctk.CTkButton(tab, text="INICIAR EXTRACCIÓN", 
                                          font=ctk.CTkFont(weight="bold", size=14),
                                          command=self._start_extraction, height=40)
        self.btn_extract.pack(pady=10)
        
        self._update_extract_ui()

    def _choose_ext_file(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Guardar resultados como"
        )
        if filename:
            self.ext_output.set(filename)

    def _update_extract_ui(self):
        method = self.method_var.get()
        platform = self.platform_var.get()

        # Show/hide credentials
        if method == "Instaloader" and platform == "Instagram":
            self.cred_frame.pack(pady=5, padx=20, fill="x")
            self.sel_frame.pack_forget()
            self.btn_extract.configure(text="START EXTRACTION")
        elif method == "Selenium":
            self.cred_frame.pack_forget()
            self.sel_frame.pack(pady=5, padx=20, fill="x")
            self.btn_extract.configure(text="2. ESCANEAR DATOS")
        else:
            self.cred_frame.pack_forget()
            self.sel_frame.pack_forget()
            self.btn_extract.configure(text="START EXTRACTION")

        # Instaloader only available for Instagram
        if platform != "Instagram":
            if method == "Instaloader":
                self.method_var.set("Automatic")
                self._update_extract_ui()

    def _open_browser(self):
        self.log("Preparando Selenium (Navegador Automático)...")
        try:
            self.driver = extractor_selenium.configurar_driver(log_callback=self.log)
            platform = self.platform_var.get()
            if platform == "Instagram":
                self.log("Navegador abierto. Inicia sesión en Instagram, ve al perfil del objetivo y abre sus seguidores.")
            elif platform == "X (Twitter)":
                self.log("Navegador abierto. Inicia sesión en X (Twitter).")
            elif platform == "Facebook":
                self.log("Navegador abierto. Inicia sesión en Facebook.")
            else:
                self.log("Navegador abierto. Navega hasta el perfil del usuario objetivo.")
        except Exception as e:
            self.log(f"Hubo un error al abrir el navegador: {e}")

    def _start_extraction(self):
        target = self.ext_target.get().strip()
        out_path = self.ext_output.get().strip()

        if not target:
            messagebox.showwarning("Faltan datos", "Por favor, introduce la cuenta objetivo a analizar.")
            return
        if not out_path:
            out_path = os.path.join("Output", f"extract_{target}.csv")
            self.ext_output.set(out_path)

        method = self.method_var.get()
        platform = self.platform_var.get()
        self.btn_extract.configure(state="disabled")

        if method == "Instaloader":
            user = self.ext_user.get().strip()
            password = self.ext_pass.get().strip()
            if not user or not password:
                messagebox.showwarning("Faltan datos", "Para usar Instaloader, introduce tu usuario y contraseña de Instagram.")
                self.btn_extract.configure(state="normal")
                return
            threading.Thread(target=self._run_instaloader, args=(user, password, target, out_path), daemon=True).start()
        elif method == "Selenium":
            if not self.driver:
                messagebox.showwarning("Navegador no detectado", "Primero debes abrir el navegador presionando el botón '1. Abrir Navegador'.")
                self.btn_extract.configure(state="normal")
                return
            threading.Thread(target=self._run_selenium, args=(target, out_path, platform), daemon=True).start()
        else:
            # Automatic
            threading.Thread(target=self._run_auto, args=(target, out_path, platform), daemon=True).start()

    def _run_instaloader(self, user, password, target, out_path):
        self.log("--- INICIANDO EXTRACCIÓN CON INSTALOADER ---")
        extractor.extraer_seguidores(user, password, target, out_path, log_callback=self.log)
        self.log("--- EXTRACCIÓN FINALIZADA ---")
        self.btn_extract.configure(state="normal")

    def _run_selenium(self, target, out_path, platform):
        self.log(f"--- INICIANDO EXTRACCIÓN CON SELENIUM ({platform}) ---")
        if platform == "X (Twitter)":
            extractor_x.extraer_lista_seguidores_x(self.driver, target, out_path, self.log)
        elif platform == "Facebook":
            extractor_fb.extraer_amigos_fb(self.driver, target, out_path, self.log)
        else:
            extractor_selenium.extraer_seguidores_selenium(self.driver, target, out_path, log_callback=self.log)
        self.log("--- PROCESS FINISHED ---")
        self.btn_extract.configure(state="normal")

    def _run_auto(self, target, out_path, platform):
        self.log(f"--- INICIANDO EXTRACCIÓN AUTOMÁTICA ({platform}) ---")
        success = False
        if platform == "TikTok":
            success = extractor_tiktok.extraer_seguidores_tiktok(target, out_path, self.log)
        elif platform == "X (Twitter)":
            success = extractor_x.extraer_seguidores_x(target, out_path, self.log)
        elif platform == "Facebook":
            success = extractor_fb.extraer_perfil_fb(target, out_path, self.log)
        elif platform == "Instagram":
            self.log("Aviso: Instagram requiere Instaloader (te pedirá iniciar sesión) o Selenium. Por favor, cambia de método.")
        
        if success:
            self.log("--- EXTRACCIÓN COMPLETADA CON ÉXITO ---")
        else:
            self.log("--- EXTRACCIÓN FINALIZADA (hubo problemas, revisa los logs) ---")
        self.btn_extract.configure(state="normal")

    # ===================================================================
    # TAB 3: History and Statistics Dashboard
    # ===================================================================
    def _build_history_tab(self):
        tab = self.tab_history
        ctk.CTkLabel(tab, text="Panel de Analíticas e Historial", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 5))
        
        btn_refresh = ctk.CTkButton(tab, text="Actualizar Datos", command=self._load_history_data)
        btn_refresh.pack(pady=5)
        
        self.hist_frame = ctk.CTkFrame(tab)
        self.hist_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self._load_history_data()

    def _load_history_data(self):
        for widget in self.hist_frame.winfo_children():
            widget.destroy()
            
        history_file = "history.json"
        if not os.path.exists(history_file):
            ctk.CTkLabel(self.hist_frame, text="Aún no tienes ningún historial guardado.").pack(pady=20)
            return
            
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = []
            
        if not data:
            ctk.CTkLabel(self.hist_frame, text="El historial está vacío por ahora.").pack(pady=20)
            return
            
        # Count platforms
        platforms = {}
        for item in data:
            plat = item.get("platform", "Desconocida")
            platforms[plat] = platforms.get(plat, 0) + 1
            
        # Render Pie Chart
        fig, ax = plt.subplots(figsize=(5, 3), facecolor='#2b2b2b')
        ax.pie(platforms.values(), labels=platforms.keys(), autopct='%1.1f%%', textprops={'color':"w"})
        fig.patch.set_facecolor('#2b2b2b')
        
        canvas = FigureCanvasTkAgg(fig, master=self.hist_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="left", fill="both", expand=True, padx=10)
        
        # Render Text List
        list_frame = ctk.CTkScrollableFrame(self.hist_frame, width=400)
        list_frame.pack(side="right", fill="both", expand=True, padx=10)
        
        for item in reversed(data[-20:]): # Mostrar solo los 20 más recientes
            text = f"[{item.get('platform', '')}] {item.get('target', '')} ({item.get('date', '')})"
            ctk.CTkLabel(list_frame, text=text, anchor="w").pack(fill="x", pady=2)

    # ===================================================================
    # PESTAÑA MEDIA: Extracción de Fotos, Vídeos y Likes
    # ===================================================================
    def _build_media_tab(self):
        tab = self.tab_media
        ctk.CTkLabel(tab, text="Visor Multimedia y Extractor de Likes", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 5))
        ctk.CTkLabel(tab, text="Descarga publicaciones, vídeos y likes de un perfil en masa.").pack(pady=(0, 10))

        # Opciones de extracción
        opts_frame = ctk.CTkFrame(tab)
        opts_frame.pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(opts_frame, text="Cuenta Objetivo (sin @):").pack(pady=(10, 0))
        self.media_target = ctk.CTkEntry(opts_frame, placeholder_text="Ej: cristiano")
        self.media_target.pack(pady=5, padx=20, fill="x")

        self.media_likes_var = ctk.BooleanVar(value=False)
        self.media_check_likes = ctk.CTkCheckBox(opts_frame, text="Extraer también Likes (Requiere login en Instagram)", variable=self.media_likes_var)
        self.media_check_likes.pack(pady=10)

        ctk.CTkLabel(opts_frame, text="Límite de publicaciones a extraer:").pack(pady=(5,0))
        self.media_limit = ctk.CTkEntry(opts_frame, placeholder_text="Ej: 50")
        self.media_limit.insert(0, "50")
        self.media_limit.pack(pady=5, padx=20)

        # Panel de Credenciales
        self.media_cred_frame = ctk.CTkFrame(tab)
        self.media_cred_frame.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(self.media_cred_frame, text="Credenciales (Opcional para fotos, Obligatorio para Likes):").pack(pady=(5, 0))
        
        creds_inner = ctk.CTkFrame(self.media_cred_frame, fg_color="transparent")
        creds_inner.pack(pady=5)
        self.media_user = ctk.CTkEntry(creds_inner, placeholder_text="Usuario IG")
        self.media_user.pack(side="left", padx=5)
        self.media_pass = ctk.CTkEntry(creds_inner, placeholder_text="Contraseña IG", show="*")
        self.media_pass.pack(side="left", padx=5)

        # Botón
        self.btn_media = ctk.CTkButton(tab, text="INICIAR DESCARGA MULTIMEDIA", font=ctk.CTkFont(weight="bold"), command=self._start_media_extraction, height=40)
        self.btn_media.pack(pady=15)

        self.media_log = ctk.CTkTextbox(tab, state="disabled", height=150)
        self.media_log.pack(pady=10, padx=20, fill="both", expand=True)

    def _log_media(self, msg):
        self.media_log.configure(state="normal")
        self.media_log.insert("end", msg + "\n")
        self.media_log.see("end")
        self.media_log.configure(state="disabled")

    def _start_media_extraction(self):
        target = self.media_target.get().strip()
        if not target:
            messagebox.showwarning("Aviso", "Introduce la cuenta objetivo.")
            return

        try:
            limit = int(self.media_limit.get().strip() or 50)
        except:
            limit = 50

        include_likes = self.media_likes_var.get()
        user = self.media_user.get().strip()
        password = self.media_pass.get().strip()

        if include_likes and (not user or not password):
            messagebox.showwarning("Aviso", "Para extraer likes necesitas iniciar sesión en Instagram.")
            return

        self.btn_media.configure(state="disabled", text="DESCARGANDO...")
        self.media_log.configure(state="normal")
        self.media_log.delete("1.0", "end")
        self.media_log.configure(state="disabled")

        threading.Thread(target=self._run_media, args=(target, user, password, include_likes, limit), daemon=True).start()

    def _run_media(self, target, user, password, include_likes, limit):
        self._log_media("--- INICIANDO EXTRACCIÓN MULTIMEDIA (INSTAGRAM) ---")
        try:
            results = media_extractor.extract_instagram_media(
                username=target,
                session_user=user if user else None,
                session_file=os.path.join(".venv", f"session_{user}") if user else None,
                include_likes=include_likes,
                max_posts=limit,
                log_callback=self._log_media
            )
            self._log_media(f"Extracción finalizada. {len(results.get('posts', []))} elementos descargados.")
            self._log_media(f"Los archivos se han guardado en la carpeta: {results.get('media_dir', 'media/')}")
        except Exception as e:
            self._log_media(f"Error en la extracción multimedia: {e}")
        finally:
            self.btn_media.configure(state="normal", text="INICIAR DESCARGA MULTIMEDIA")

    # ===================================================================
    # PESTAÑA 4: Configuración (Ajustes Globales y Notificaciones)
    # ===================================================================
    def _build_settings_tab(self):
        tab = self.tab_settings
        ctk.CTkLabel(tab, text="Configurar Notificaciones de Telegram", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 5))
        
        self.tg_token = ctk.CTkEntry(tab, placeholder_text="Bot Token", width=400)
        self.tg_token.pack(pady=10)
        
        self.tg_chatid = ctk.CTkEntry(tab, placeholder_text="Chat ID", width=400)
        self.tg_chatid.pack(pady=10)
        
        ctk.CTkButton(tab, text="Guardar Configuración", command=self._save_settings).pack(pady=20)
        
        # Load existing
        if os.path.exists('settings.json'):
            try:
                with open('settings.json', 'r') as f:
                    s = json.load(f)
                    if 'telegram_token' in s: self.tg_token.insert(0, s['telegram_token'])
                    if 'telegram_chat_id' in s: self.tg_chatid.insert(0, s['telegram_chat_id'])
            except: pass

    def _save_settings(self):
        s = {}
        if os.path.exists('settings.json'):
            try:
                with open('settings.json', 'r') as f:
                    s = json.load(f)
            except: pass
        s['telegram_token'] = self.tg_token.get()
        s['telegram_chat_id'] = self.tg_chatid.get()
        with open('settings.json', 'w') as f:
            json.dump(s, f)
        messagebox.showinfo("Guardado", "Configuración de Telegram guardada.")

    # ===================================================================
    # Common
    # ===================================================================
    def log(self, message):
        self.log_queue.put(message)

    def check_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.textbox.configure(state="normal")
                self.textbox.insert("end", msg + "\n")
                self.textbox.see("end")
                self.textbox.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self.check_queue)

if __name__ == "__main__":
    app = App()
    app.mainloop()
