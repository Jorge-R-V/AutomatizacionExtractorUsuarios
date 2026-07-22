"""
Lanzador de Escritorio para la Suite OSINT de Extracción de Usuarios.
"""
__author__ = "Jorge R."
__copyright__ = "Copyright 2026, Proyecto DataExtractor"
__license__ = "MIT"
__version__ = "2.0.0"

import webview
from app import app

def iniciar_aplicacion_escritorio():
    """
    Arranca nuestro servidor web Flask y lo envuelve en una ventana nativa de Windows.
    Así el usuario siente que es un programa normal y no una página web.
    """
    # Creamos la ventana principal del programa y la conectamos a nuestro servidor 'app'
    ventana = webview.create_window(
        title='DataExtractor | Suite OSINT Multi-Plataforma',
        url=app, 
        width=1400,
        height=900,
        min_size=(1000, 700),
        text_select=True,  # Permite al usuario copiar el texto de los resultados
        confirm_close=True # Avisa al usuario si intenta cerrar mientras extraemos datos
    )
    
    # Arrancamos el motor gráfico del navegador incrustado
    webview.start(
        debug=True, # Activar si necesitamos ver la consola de errores (F12)
        private_mode=True # Modo incógnito para evitar bloqueos internos de Windows (Error 0x800700AA)
    )

if __name__ == '__main__':
    try:
        print("Iniciando DataExtractor en modo Escritorio...")
        iniciar_aplicacion_escritorio()
    except Exception as error_capturado:
        import traceback
        import os
        # Si algo falla gravemente, guardamos el error en un archivo para poder arreglarlo
        with open("desktop_error.txt", "w") as archivo_error:
            archivo_error.write(traceback.format_exc())
        print("\n=== ERROR CRÍTICO ===")
        traceback.print_exc()
        input("\nHa ocurrido un fallo. Presiona ENTER para salir...")
