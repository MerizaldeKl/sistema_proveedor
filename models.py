"""Clases que representan los datos de clientes, productos y ventas.

Cada objeto puede convertirse a diccionario para guardarse en un archivo JSON.
"""

from datetime import date


# =====================================================================
# CLASE BASE: lo que los tres modelos comparten
# =====================================================================
class ModeloBase:
    """Padre de todos los modelos. Guarda el id y define el comportamiento común."""

    def __init__(self, id_registro):
        """Guarda el identificador común que tiene cada registro."""
        self.id = int(id_registro)

    # ---- ÚNICO MÉTODO DE CLASE DEL PROYECTO ----
    @classmethod
    def desde_diccionario(cls, datos):
        """Diccionario -> objeto. Escrito UNA vez y usado por los tres modelos.
        cls es la clase que llamó: Cliente, Producto o Venta."""
        datos = dict(datos)                 # copia, para no tocar el original
        id_registro = datos.pop("id")       # saco el id
        return cls(id_registro, **datos)    # el resto son los campos del modelo

    # ---- MÉTODOS DE INSTANCIA ----
    def a_diccionario(self):
        """Convierte los datos comunes del objeto en un diccionario."""
        # Objeto -> diccionario. Cada hijo agrega sus campos.
        return {"id": self.id}

    def etiqueta(self):
        """Devuelve un nombre breve que las clases hijas pueden personalizar."""
        # POLIMORFISMO: cada hijo la reescribe a su manera
        return f"registro {self.id}"

    def __str__(self):
        """Define el texto que aparece al imprimir el objeto con print()."""
        # Lo que se ve al hacer print(objeto). Llama a etiqueta(),
        # así que cada modelo se imprime distinto sin cambiar esta línea.
        return f"[{self.id}] {self.etiqueta()}"


# =====================================================================
# HERENCIA: Persona es la base de Cliente (y mañana, de Estudiante)
# =====================================================================
class Persona(ModeloBase):
    """Todo lo que tiene una persona del sistema."""

    def __init__(self, id_registro, nombre, apellido, email):
        """Crea una persona con identificador, nombre, apellido y correo."""
        super().__init__(id_registro)      # el padre guarda el id
        self.nombre = nombre
        self.apellido = apellido
        self.email = email

    def nombre_completo(self):
        """Une el nombre y el apellido para mostrarlos juntos."""
        return f"{self.nombre} {self.apellido}"

    def a_diccionario(self):
        """Agrega nombre, apellido y correo al diccionario del registro base."""
        datos = super().a_diccionario()    # {"id": ...} que arma el padre
        datos["nombre"] = self.nombre
        datos["apellido"] = self.apellido
        datos["email"] = self.email
        return datos

    def etiqueta(self):
        """Usa el nombre completo como etiqueta de la persona."""
        return self.nombre_completo()


class Cliente(Persona):
    """Cliente ES UNA Persona, con teléfono y ciudad."""

    def __init__(self, id_registro, nombre, apellido, email, telefono="", ciudad=""):
        """Crea un cliente y añade sus datos de contacto y ubicación."""
        super().__init__(id_registro, nombre, apellido, email)
        self.telefono = telefono
        self.ciudad = ciudad

    def a_diccionario(self):
        """Incluye teléfono y ciudad además de los datos heredados de Persona."""
        datos = super().a_diccionario()    # reutiliza lo de Persona
        datos["telefono"] = self.telefono
        datos["ciudad"] = self.ciudad
        return datos

    def etiqueta(self):
        """Prepara un resumen del cliente con nombre, correo y ciudad."""
        # Sobrescribe y EXTIENDE la del padre
        return f"{super().etiqueta()} · {self.email} · {self.ciudad or 'sin ciudad'}"


# =====================================================================
# ÚNICA CLASE CON ATRIBUTOS Y MÉTODOS ESTÁTICOS
# =====================================================================
class Producto(ModeloBase):
    """Producto ES UN ModeloBase. Aquí viven los ejemplos de lo estático."""

    # ATRIBUTOS ESTÁTICOS (de clase): existen una sola vez, no por objeto
    STOCK_MINIMO = 5          # regla del negocio, igual para todos los productos
    IVA = 0.15                # 15 %
    total_creados = 0         # contador compartido

    def __init__(self, id_registro, nombre, precio, stock=0):
        """Crea un producto y convierte precio y existencias a números."""
        super().__init__(id_registro)
        self.nombre = nombre
        self.precio = float(precio)
        self.stock = int(stock)
        Producto.total_creados += 1        # se modifica en la CLASE, no en self

    # MÉTODOS ESTÁTICOS: reglas que no necesitan ningún producto concreto
    @staticmethod
    def es_precio_valido(valor):
        """Indica si el valor puede convertirse a un precio mayor que cero."""
        try:
            return float(valor) > 0
        except (TypeError, ValueError):
            return False

    @staticmethod
    def con_iva(monto):
        """Devuelve el monto con el porcentaje de IVA configurado en la clase."""
        return round(monto * (1 + Producto.IVA), 2)

    # MÉTODOS DE INSTANCIA: necesitan los datos de ESTE producto
    def stock_bajo(self):
        """Indica si las existencias están en el mínimo o por debajo."""
        return self.stock <= Producto.STOCK_MINIMO

    def hay_stock(self, cantidad):
        """Comprueba que la cantidad pedida sea positiva y esté disponible."""
        return 0 < cantidad <= self.stock

    def descontar_stock(self, cantidad):
        """Resta del inventario las unidades que se acaban de vender."""
        self.stock -= cantidad

    def devolver_stock(self, cantidad):
        """Suma al inventario las unidades de una venta anulada."""
        self.stock += cantidad

    def a_diccionario(self):
        """Convierte nombre, precio y existencias para poder guardarlos."""
        datos = super().a_diccionario()
        datos["nombre"] = self.nombre
        datos["precio"] = self.precio
        datos["stock"] = self.stock
        return datos

    def etiqueta(self):
        """Muestra nombre, precio y existencias, con aviso si queda poco stock."""
        alerta = " ⚠ stock bajo" if self.stock_bajo() else ""
        return f"{self.nombre} · ${self.precio:.2f} · stock {self.stock}{alerta}"


# =====================================================================
class Venta(ModeloBase):
    """Venta simple: un cliente, un producto, una cantidad."""

    def __init__(self, id_registro, cliente_id, producto_id, cantidad,
                 precio_unitario, fecha=""):
        """Crea una venta y conserva el precio que tenía el producto ese día."""
        super().__init__(id_registro)
        self.cliente_id = int(cliente_id)
        self.producto_id = int(producto_id)
        self.cantidad = int(cantidad)
        self.precio_unitario = float(precio_unitario)
        self.fecha = fecha or date.today().isoformat()

    def calcular_total(self):
        """Multiplica cantidad por precio unitario y redondea a dos decimales."""
        # Se calcula cada vez; NO se guarda como atributo para que nunca
        # quede desactualizado si cambia la cantidad
        return round(self.cantidad * self.precio_unitario, 2)

    def a_diccionario(self):
        """Convierte los datos de la venta a un formato almacenable en JSON."""
        datos = super().a_diccionario()
        datos["cliente_id"] = self.cliente_id
        datos["producto_id"] = self.producto_id
        datos["cantidad"] = self.cantidad
        datos["precio_unitario"] = self.precio_unitario
        datos["fecha"] = self.fecha
        return datos

    def etiqueta(self):
        """Resume fecha, cliente, cantidad, producto y total de la venta."""
        return (f"{self.fecha} · cliente {self.cliente_id} · "
                f"{self.cantidad} x producto {self.producto_id} "
                f"= ${self.calcular_total():.2f}")

# =====================================================================
# NUEVO MODELO: PROVEEDOR
# =====================================================================
class Proveedor(Persona):
    """Proveedor ES UNA Persona, con RUC y empresa."""

    def __init__(self, id_registro, nombre, apellido, email, ruc, empresa=""):
        super().__init__(id_registro, nombre, apellido, email)
        self.ruc = str(ruc)
        self.empresa = empresa

    def a_diccionario(self):
        datos = super().a_diccionario()
        datos["ruc"] = self.ruc
        datos["empresa"] = self.empresa
        return datos

    def etiqueta(self):
        return f"{super().etiqueta()} - {self.empresa or 'sin empresa'} - RUC {self.ruc}"


# =====================================================================
# NUEVO MODELO: COMPRA
# =====================================================================
class Compra(ModeloBase):
    """Compra simple: un proveedor, un producto y una cantidad."""

    def __init__(self, id_registro, proveedor_id, producto_id, cantidad,
                 costo_unitario, fecha=""):
        super().__init__(id_registro)
        self.proveedor_id = int(proveedor_id)
        self.producto_id = int(producto_id)
        self.cantidad = int(cantidad)
        self.costo_unitario = float(costo_unitario)
        self.fecha = fecha or date.today().isoformat()

    def calcular_total(self):
        return round(self.cantidad * self.costo_unitario, 2)

    def a_diccionario(self):
        datos = super().a_diccionario()
        datos["proveedor_id"] = self.proveedor_id
        datos["producto_id"] = self.producto_id
        datos["cantidad"] = self.cantidad
        datos["costo_unitario"] = self.costo_unitario
        datos["fecha"] = self.fecha
        return datos

    def etiqueta(self):
        return (f"{self.fecha} · proveedor {self.proveedor_id} · "
                f"{self.cantidad} x producto {self.producto_id} "
                f"= ${self.calcular_total():.2f}")
