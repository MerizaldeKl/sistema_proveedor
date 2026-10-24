"""Lectura y escritura de los datos del sistema en archivos JSON."""

import json
import os


class GestorJSON:
    """Lee y guarda una lista de diccionarios. Es la única parte que toca el disco."""

    def __init__(self, ruta):
        """Prepara la ruta del archivo y crea su carpeta si hace falta."""
        self.ruta = ruta
        carpeta = os.path.dirname(ruta)
        if carpeta and not os.path.exists(carpeta):
            os.makedirs(carpeta)

    def leer(self):
        """Lee una lista desde JSON; devuelve una lista vacía si no puede leerla."""
        # Devuelve SIEMPRE una lista: vacía si el archivo no existe o está dañado
        if not os.path.exists(self.ruta):
            return []
        try:
            with open(self.ruta, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
            return datos if isinstance(datos, list) else []
        except (json.JSONDecodeError, OSError):
            # Capturamos errores concretos, nunca un "except:" pelado
            return []

    def guardar(self, datos):
        """Escribe una lista de datos como JSON y avisa si pudo guardarla."""
        try:
            with open(self.ruta, "w", encoding="utf-8") as archivo:
                json.dump(datos, archivo, ensure_ascii=False, indent=2)
            return True
        except (TypeError, OSError):
            return False