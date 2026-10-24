"""Controladors: conectan las acciones del menú con modelos y archivos JSON.

Aquí se validan los datos y se coordinan las operaciones de clientes,
productos y ventas antes de guardarlas.
"""

from abc import ABC, abstractmethod

from models import Cliente, Producto, Venta, Proveedor, Compra
from shared.json_manager import GestorJSON
from shared.herramientas import es_email_valido


# =====================================================================
# CLASE BASE (ABSTRACTA)
# =====================================================================
# Solo dice QUÉ métodos debe tener todo controlador.
# CÓMO se hace cada uno lo escribe cada controlador, de la forma más simple.
class CrudBase(ABC):
    """Define las operaciones que debe ofrecer cada controlador."""

    @abstractmethod
    def leer(self):
        """Devuelve todos los registros que maneja el controlador."""
        pass

    @abstractmethod
    def obtener(self, id_registro):
        """Busca y devuelve un registro por su identificador."""
        pass

    @abstractmethod
    def buscar(self, texto):
        """Devuelve los registros que coinciden con un texto de búsqueda."""
        pass

    @abstractmethod
    def siguiente(self):
        """Calcula el identificador que se asignará al próximo registro."""
        pass

    @abstractmethod
    def crear(self, datos):
        """Valida los datos y agrega un registro nuevo."""
        pass

    @abstractmethod
    def actualizar(self, id_registro, datos):
        """Cambia algunos campos de un registro existente."""
        pass

    @abstractmethod
    def eliminar(self, id_registro):
        """Quita un registro existente."""
        pass


# =====================================================================
# CONTROLADOR DE CLIENTES
# =====================================================================
class ClienteController(CrudBase):
    """Administra clientes en memoria y mantiene sus datos en clientes.json."""

    def __init__(self, archivo="data/clientes.json"):
        """Carga los clientes del archivo y los convierte en objetos Cliente."""
        self.gestor = GestorJSON(archivo)

        # Leemos el JSON y convertimos cada diccionario en un objeto Cliente
        self.lista = []
        for datos in self.gestor.leer():
            self.lista.append(Cliente.desde_diccionario(datos))

    def guardar(self):
        """Convierte los clientes a diccionarios y los escribe en el archivo."""
        datos = []
        for cliente in self.lista:
            datos.append(cliente.a_diccionario())
        self.gestor.guardar(datos)

    def validar(self, datos, id_actual=None):
        """Revisa campos obligatorios, formato y duplicados; None significa válido."""
        # Al crear hay que traer los tres obligatorios; al actualizar, solo lo que cambia
        if id_actual is None:
            for campo in ("nombre", "apellido", "email"):
                if str(datos.get(campo, "")).strip() == "":
                    return f"El campo {campo} es obligatorio"

        if "email" in datos:
            email = str(datos["email"]).strip().lower()
            if not es_email_valido(email):
                return f"Email inválido: '{email}'"
            # CONJUNTO con los emails de los OTROS clientes
            usados = {c.email for c in self.lista if c.id != id_actual}
            if email in usados:
                return "Ese email ya está registrado"

        telefono = str(datos.get("telefono", "")).strip()
        if telefono != "" and not telefono.isdigit():
            return "El teléfono solo puede tener números"
        return None

    def leer(self):
        """Entrega la lista de clientes actualmente cargada."""
        return self.lista

    def obtener(self, id_cliente):
        """Encuentra un cliente por id o devuelve None si no existe."""
        for cliente in self.lista:
            if cliente.id == id_cliente:
                return cliente
        return None

    def buscar(self, texto):
        """Busca el texto en nombre, apellido, email, teléfono y ciudad."""
        texto = texto.strip().lower()
        encontrados = []
        if texto == "":
            return encontrados

        for cliente in self.lista:
            if (texto in cliente.nombre.lower()
                    or texto in cliente.apellido.lower()
                    or texto in cliente.email
                    or texto in cliente.telefono
                    or texto in cliente.ciudad.lower()):
                encontrados.append(cliente)
        return encontrados

    def siguiente(self):
        """Devuelve un id mayor que los que ya tienen los clientes."""
        mayor = 0
        for cliente in self.lista:
            if cliente.id > mayor:
                mayor = cliente.id
        return mayor + 1

    def crear(self, datos):
        """Valida los datos, crea el cliente y guarda la lista actualizada."""
        error = self.validar(datos)
        if error:
            return False, error

        cliente = Cliente(self.siguiente(),
                          str(datos["nombre"]).strip().title(),
                          str(datos["apellido"]).strip().title(),
                          str(datos["email"]).strip().lower(),
                          str(datos.get("telefono", "")).strip(),
                          str(datos.get("ciudad", "")).strip().title())
        self.lista.append(cliente)
        self.guardar()
        return True, f"Cliente creado: {cliente.etiqueta()}"

    def actualizar(self, id_cliente, datos):
        """Valida y aplica solo los cambios permitidos al cliente indicado."""
        cliente = self.obtener(id_cliente)
        if cliente is None:
            return False, f"No existe un cliente con id {id_cliente}"
        if not datos:
            return False, "No se indicó ningún cambio"

        # DIFERENCIA de conjuntos: campos que no existen en un cliente
        permitidos = {"nombre", "apellido", "email", "telefono", "ciudad"}
        desconocidos = set(datos) - permitidos
        if desconocidos:
            return False, f"Campos no válidos: {', '.join(sorted(desconocidos))}"

        # Se valida ANTES de tocar el objeto: si algo falla, no cambia nada
        error = self.validar(datos, id_cliente)
        if error:
            return False, error

        for campo, valor in datos.items():
            valor = str(valor).strip()
            if campo in ("nombre", "apellido", "ciudad"):
                valor = valor.title()
            elif campo == "email":
                valor = valor.lower()
            setattr(cliente, campo, valor)

        self.guardar()
        return True, f"Cliente {id_cliente} actualizado"

    def eliminar(self, id_cliente):
        """Elimina un cliente por id y guarda el resultado."""
        cliente = self.obtener(id_cliente)
        if cliente is None:
            return False, f"No existe un cliente con id {id_cliente}"

        self.lista.remove(cliente)
        self.guardar()
        return True, f"Cliente {id_cliente} eliminado"

    # --- propio de clientes ---
    def ciudades(self):
        """Devuelve las ciudades distintas de los clientes en orden alfabético."""
        return sorted({c.ciudad for c in self.lista if c.ciudad != ""})


# =====================================================================
# CONTROLADOR DE PRODUCTOS
# =====================================================================
class ProductoController(CrudBase):
    """Administra el catálogo de productos y su cantidad disponible."""

    def __init__(self, archivo="data/productos.json"):
        """Carga los productos guardados y los convierte en objetos Producto."""
        self.gestor = GestorJSON(archivo)

        self.lista = []
        for datos in self.gestor.leer():
            self.lista.append(Producto.desde_diccionario(datos))

    def guardar(self):
        """Guarda en JSON una representación de cada producto."""
        datos = []
        for producto in self.lista:
            datos.append(producto.a_diccionario())
        self.gestor.guardar(datos)

    def validar(self, datos, id_actual=None):
        """Comprueba campos obligatorios, precio, stock y nombre duplicado."""
        if id_actual is None:
            for campo in ("nombre", "precio"):
                if str(datos.get(campo, "")).strip() == "":
                    return f"El campo {campo} es obligatorio"

        # es_precio_valido es el método ESTÁTICO de Producto
        if "precio" in datos and not Producto.es_precio_valido(datos["precio"]):
            return f"Precio inválido: '{datos['precio']}' (debe ser un número mayor a 0)"

        stock = str(datos.get("stock", "")).strip()
        if stock != "" and not stock.isdigit():
            return "El stock debe ser un número entero positivo"

        if "nombre" in datos:
            nombre = str(datos["nombre"]).strip().title()
            for otro in self.lista:
                if otro.nombre == nombre and otro.id != id_actual:
                    return f"Ya existe un producto llamado {nombre}"
        return None

    def leer(self):
        """Entrega la lista de productos actualmente cargada."""
        return self.lista

    def obtener(self, id_producto):
        """Encuentra un producto por id o devuelve None si no existe."""
        for producto in self.lista:
            if producto.id == id_producto:
                return producto
        return None

    def buscar(self, texto):
        """Busca productos cuyo nombre contenga el texto indicado."""
        texto = texto.strip().lower()
        encontrados = []
        if texto == "":
            return encontrados

        for producto in self.lista:
            if texto in producto.nombre.lower():
                encontrados.append(producto)
        return encontrados

    def siguiente(self):
        """Devuelve un id mayor que los que ya tienen los productos."""
        mayor = 0
        for producto in self.lista:
            if producto.id > mayor:
                mayor = producto.id
        return mayor + 1

    def crear(self, datos):
        """Valida y guarda un producto nuevo; el stock comienza en cero si falta."""
        error = self.validar(datos)
        if error:
            return False, error

        # Si no escribieron el stock, empieza en 0
        stock = str(datos.get("stock", "")).strip()
        producto = Producto(self.siguiente(),
                            str(datos["nombre"]).strip().title(),
                            float(datos["precio"]),
                            int(stock) if stock != "" else 0)
        self.lista.append(producto)
        self.guardar()
        return True, f"Producto creado: {producto.etiqueta()}"

    def actualizar(self, id_producto, datos):
        """Aplica al producto existente solo los campos permitidos y válidos."""
        producto = self.obtener(id_producto)
        if producto is None:
            return False, f"No existe un producto con id {id_producto}"
        if not datos:
            return False, "No se indicó ningún cambio"

        desconocidos = set(datos) - {"nombre", "precio", "stock"}
        if desconocidos:
            return False, f"Campos no válidos: {', '.join(sorted(desconocidos))}"

        error = self.validar(datos, id_producto)
        if error:
            return False, error

        if "nombre" in datos:
            producto.nombre = str(datos["nombre"]).strip().title()
        if "precio" in datos:
            producto.precio = float(datos["precio"])
        if "stock" in datos:
            producto.stock = int(datos["stock"])

        self.guardar()
        return True, f"Producto {id_producto} actualizado"

    def eliminar(self, id_producto):
        """Elimina un producto por id y guarda el catálogo actualizado."""
        producto = self.obtener(id_producto)
        if producto is None:
            return False, f"No existe un producto con id {id_producto}"

        self.lista.remove(producto)
        self.guardar()
        return True, f"Producto {id_producto} eliminado"

    # --- propio de productos ---
    def con_stock_bajo(self):
        """Devuelve los productos cuyo inventario llegó al mínimo establecido."""
        bajos = []
        for producto in self.lista:
            if producto.stock_bajo():
                bajos.append(producto)
        return bajos


# =====================================================================
# CONTROLADOR DE VENTAS
# =====================================================================
class VentaController(CrudBase):
    """Registra ventas, descuenta existencias y puede anular operaciones."""

    def __init__(self, clientes, productos, archivo="data/ventas.json"):
        """Recibe los controladores compartidos y carga las ventas guardadas."""
        # La venta USA a los otros dos controladores.
        # Hay que pasarle los MISMOS que usa main.py.
        self.clientes = clientes
        self.productos = productos
        self.gestor = GestorJSON(archivo)

        self.lista = []
        for datos in self.gestor.leer():
            self.lista.append(Venta.desde_diccionario(datos))

    def guardar(self):
        """Escribe la lista de ventas en el archivo JSON correspondiente."""
        datos = []
        for venta in self.lista:
            datos.append(venta.a_diccionario())
        self.gestor.guardar(datos)

    def validar(self, datos):
        """Comprueba que cliente, producto y cantidad permitan realizar la venta."""
        try:
            cliente_id = int(datos.get("cliente_id", 0))
            producto_id = int(datos.get("producto_id", 0))
            cantidad = int(datos.get("cantidad", 0))
        except (TypeError, ValueError):
            return "cliente_id, producto_id y cantidad deben ser números enteros"

        if cantidad <= 0:
            return "La cantidad debe ser mayor a 0"
        if self.clientes.obtener(cliente_id) is None:
            return f"No existe un cliente con id {cliente_id}"

        producto = self.productos.obtener(producto_id)
        if producto is None:
            return f"No existe un producto con id {producto_id}"
        if not producto.hay_stock(cantidad):
            return (f"Stock insuficiente de {producto.nombre}: "
                    f"hay {producto.stock}, piden {cantidad}")
        return None

    def leer(self):
        """Entrega la lista de ventas actualmente cargada."""
        return self.lista

    def obtener(self, id_venta):
        """Encuentra una venta por id o devuelve None si no existe."""
        for venta in self.lista:
            if venta.id == id_venta:
                return venta
        return None

    def buscar(self, texto):
        """Busca ventas por una parte de su fecha, por ejemplo año y mes."""
        # Las ventas se buscan por fecha, ej: "2026-09"
        texto = texto.strip()
        encontradas = []
        if texto == "":
            return encontradas

        for venta in self.lista:
            if texto in venta.fecha:
                encontradas.append(venta)
        return encontradas

    def siguiente(self):
        """Devuelve un id mayor que los que ya tienen las ventas."""
        mayor = 0
        for venta in self.lista:
            if venta.id > mayor:
                mayor = venta.id
        return mayor + 1

    def crear(self, datos):
        """Registra la venta, descuenta stock y guarda ambos cambios."""
        # datos = {"cliente_id": 1, "producto_id": 2, "cantidad": 3}
        error = self.validar(datos)
        if error:
            return False, error

        producto = self.productos.obtener(int(datos["producto_id"]))
        venta = Venta(self.siguiente(),
                      int(datos["cliente_id"]),
                      producto.id,
                      int(datos["cantidad"]),
                      producto.precio)          # foto del precio del momento

        producto.descontar_stock(venta.cantidad)
        self.productos.guardar()                # guarda el stock nuevo en productos.json
        self.lista.append(venta)
        self.guardar()                          # guarda la venta en ventas.json
        return True, f"Venta {venta.id} registrada por ${venta.calcular_total():.2f}"

    def actualizar(self, id_venta, datos):
        """No permite editar ventas; para corregir una se debe anular y rehacer."""
        # Una venta registrada no se modifica: se anula y se registra otra
        return False, "Las ventas no se pueden modificar: anúlela y registre otra"

    def eliminar(self, id_venta):
        """Anula la venta, devuelve las existencias y guarda los cambios."""
        venta = self.obtener(id_venta)
        if venta is None:
            return False, f"No existe la venta {id_venta}"

        producto = self.productos.obtener(venta.producto_id)
        if producto is not None:
            producto.devolver_stock(venta.cantidad)
            self.productos.guardar()

        self.lista.remove(venta)
        self.guardar()
        return True, f"Venta {id_venta} anulada y stock devuelto"

    # --- propio de ventas ---
    def comprobante(self, id_venta):
        """Prepara el texto del comprobante o devuelve None si no hay esa venta."""
        venta = self.obtener(id_venta)
        if venta is None:
            return None

        cliente = self.clientes.obtener(venta.cliente_id)
        producto = self.productos.obtener(venta.producto_id)
        total = venta.calcular_total()

        texto = f"COMPROBANTE #{venta.id}   fecha: {venta.fecha}\n"
        texto += f"Cliente : {cliente.nombre_completo() if cliente else 'eliminado'}\n"
        texto += f"Producto: {producto.nombre if producto else 'eliminado'}\n"
        texto += f"Cantidad: {venta.cantidad} x ${venta.precio_unitario:.2f}\n"
        texto += "-" * 42 + "\n"
        texto += f"SUBTOTAL: ${total:.2f}\n"
        texto += f"TOTAL con IVA: ${Producto.con_iva(total):.2f}"
        return texto

    def ventas_por_cliente(self):
        """Agrupa las ventas en un diccionario cuya clave es el id del cliente."""
        agrupadas = {}
        for venta in self.lista:
            if venta.cliente_id not in agrupadas:
                agrupadas[venta.cliente_id] = []
            agrupadas[venta.cliente_id].append(venta)
        return agrupadas

    def total_vendido(self):
        """Suma el total de todas las ventas registradas."""
        total = 0
        for venta in self.lista:
            total += venta.calcular_total()
        return round(total, 2)

# =====================================================================
# NUEVO CONTROLADOR DE PROVEEDORES
# =====================================================================
class ProveedorController(CrudBase):
    """Administra proveedores y guarda sus datos en proveedores.json."""

    def __init__(self, archivo="data/proveedores.json"):
        self.gestor = GestorJSON(archivo)
        self.lista = []
        for datos in self.gestor.leer():
            self.lista.append(Proveedor.desde_diccionario(datos))

    def guardar(self):
        self.gestor.guardar([proveedor.a_diccionario() for proveedor in self.lista])

    def validar(self, datos, id_actual=None):
        # Tupla: define los campos que deben llegar al crear un proveedor.
        if id_actual is None:
            obligatorios = ("nombre", "apellido", "email", "ruc")
            for campo in obligatorios:
                if str(datos.get(campo, "")).strip() == "":
                    return f"El campo {campo} es obligatorio"

        if "email" in datos:
            email = str(datos["email"]).strip().lower()
            if not es_email_valido(email):
                return f"Email inválido: '{email}'"
            # Conjunto: permite comprobar rápidamente si el email ya existe.
            usados = {p.email for p in self.lista if p.id != id_actual}
            if email in usados:
                return "Ese email ya está registrado"

        if "ruc" in datos:
            ruc = str(datos["ruc"]).strip()
            if not ruc.isdigit() or len(ruc) != 13:
                return "El RUC debe tener exactamente 13 dígitos numéricos"
            # Otro conjunto evita que dos proveedores compartan el mismo RUC.
            usados_ruc = {p.ruc for p in self.lista if p.id != id_actual}
            if ruc in usados_ruc:
                return "Ese RUC ya está registrado"
        return None

    def leer(self):
        return self.lista

    def obtener(self, id_registro):
        for proveedor in self.lista:
            if proveedor.id == id_registro:
                return proveedor
        return None

    def buscar(self, texto):
        texto = str(texto).strip().lower()
        if not texto:
            return []
        encontrados = []
        for proveedor in self.lista:
            if (texto in proveedor.nombre.lower()
                    or texto in proveedor.apellido.lower()
                    or texto in proveedor.email.lower()
                    or texto in proveedor.ruc
                    or texto in proveedor.empresa.lower()):
                encontrados.append(proveedor)
        return encontrados

    def siguiente(self):
        mayor = 0
        for proveedor in self.lista:
            if proveedor.id > mayor:
                mayor = proveedor.id
        return mayor + 1

    def crear(self, datos):
        error = self.validar(datos)
        if error:
            return False, error
        proveedor = Proveedor(
            self.siguiente(),
            str(datos["nombre"]).strip().title(),
            str(datos["apellido"]).strip().title(),
            str(datos["email"]).strip().lower(),
            str(datos["ruc"]).strip(),
            str(datos.get("empresa", "")).strip().title()
        )
        self.lista.append(proveedor)
        self.guardar()
        return True, f"Proveedor creado: {proveedor.etiqueta()}"

    def actualizar(self, id_registro, datos):
        proveedor = self.obtener(id_registro)
        if proveedor is None:
            return False, f"No existe un proveedor con id {id_registro}"
        if not datos:
            return False, "No se indicó ningún cambio"
        permitidos = {"nombre", "apellido", "email", "ruc", "empresa"}
        desconocidos = set(datos) - permitidos
        if desconocidos:
            return False, f"Campos no válidos: {', '.join(sorted(desconocidos))}"
        error = self.validar(datos, id_registro)
        if error:
            return False, error
        for campo, valor in datos.items():
            valor = str(valor).strip()
            if campo in ("nombre", "apellido", "empresa"):
                valor = valor.title()
            elif campo == "email":
                valor = valor.lower()
            setattr(proveedor, campo, valor)
        self.guardar()
        return True, f"Proveedor {id_registro} actualizado"

    def eliminar(self, id_registro):
        proveedor = self.obtener(id_registro)
        if proveedor is None:
            return False, f"No existe un proveedor con id {id_registro}"
        self.lista.remove(proveedor)
        self.guardar()
        return True, f"Proveedor {id_registro} eliminado"

    def empresas(self):
        # Conjunto para quitar repetidas; sorted devuelve la lista ordenada.
        return sorted({p.empresa for p in self.lista if p.empresa})


# =====================================================================
# NUEVO CONTROLADOR DE COMPRAS
# =====================================================================
class CompraController(CrudBase):
    """Registra compras: incrementa el stock y permite anularlas con control."""

    def __init__(self, proveedores, productos, archivo="data/compras.json"):
        # Recibe las mismas instancias que main.py para modificar el stock real.
        self.proveedores = proveedores
        self.productos = productos
        self.gestor = GestorJSON(archivo)
        self.lista = []
        for datos in self.gestor.leer():
            self.lista.append(Compra.desde_diccionario(datos))

    def guardar(self):
        self.gestor.guardar([compra.a_diccionario() for compra in self.lista])

    def validar(self, datos):
        try:
            proveedor_id = int(datos.get("proveedor_id", 0))
            producto_id = int(datos.get("producto_id", 0))
            cantidad = int(datos.get("cantidad", 0))
        except (TypeError, ValueError):
            return "proveedor_id, producto_id y cantidad deben ser números enteros"
        if self.proveedores.obtener(proveedor_id) is None:
            return f"No existe un proveedor con id {proveedor_id}"
        producto = self.productos.obtener(producto_id)
        if producto is None:
            return f"No existe un producto con id {producto_id}"
        if cantidad <= 0:
            return "La cantidad debe ser mayor a 0"
        costo = datos.get("costo_unitario", "")
        if not Producto.es_precio_valido(costo):
            return "El costo unitario debe ser un número mayor que cero"
        return None

    def leer(self):
        return self.lista

    def obtener(self, id_registro):
        for compra in self.lista:
            if compra.id == id_registro:
                return compra
        return None

    def buscar(self, texto):
        texto = str(texto).strip()
        if not texto:
            return []
        return [compra for compra in self.lista if texto in compra.fecha]

    def siguiente(self):
        mayor = 0
        for compra in self.lista:
            if compra.id > mayor:
                mayor = compra.id
        return mayor + 1

    def crear(self, datos):
        error = self.validar(datos)
        if error:
            return False, error
        producto = self.productos.obtener(int(datos["producto_id"]))
        compra = Compra(
            self.siguiente(), int(datos["proveedor_id"]), producto.id,
            int(datos["cantidad"]), float(datos["costo_unitario"])
        )
        producto.devolver_stock(compra.cantidad)
        self.productos.guardar()
        self.lista.append(compra)
        self.guardar()
        return True, f"Compra {compra.id} registrada por ${compra.calcular_total():.2f}"

    def actualizar(self, id_registro, datos):
        return False, "Las compras no se pueden modificar: anúlela y registre otra"

    def eliminar(self, id_registro):
        compra = self.obtener(id_registro)
        if compra is None:
            return False, f"No existe la compra {id_registro}"
        producto = self.productos.obtener(compra.producto_id)
        if producto is None:
            return False, "No se puede anular: el producto ya no existe"
        if not producto.hay_stock(compra.cantidad):
            return (False, f"No se puede anular la compra: hay {producto.stock} unidades "
                           f"y se necesitan {compra.cantidad} para descontarlas")
        producto.descontar_stock(compra.cantidad)
        self.productos.guardar()
        self.lista.remove(compra)
        self.guardar()
        return True, f"Compra {id_registro} anulada y stock descontado"

    def comprobante(self, id_compra):
        compra = self.obtener(id_compra)
        if compra is None:
            return None
        proveedor = self.proveedores.obtener(compra.proveedor_id)
        producto = self.productos.obtener(compra.producto_id)
        total = compra.calcular_total()
        texto = f"ORDEN DE COMPRA #{compra.id}   fecha: {compra.fecha}\\n"
        texto += f"Proveedor: {proveedor.nombre_completo() if proveedor else 'eliminado'}\\n"
        texto += f"Empresa  : {proveedor.empresa if proveedor else 'eliminada'}\\n"
        texto += f"Producto : {producto.nombre if producto else 'eliminado'}\\n"
        texto += f"Cantidad : {compra.cantidad} x ${compra.costo_unitario:.2f}\\n"
        texto += "-" * 42 + "\\n"
        texto += f"SUBTOTAL: ${total:.2f}\\n"
        texto += f"TOTAL con IVA: ${Producto.con_iva(total):.2f}"
        return texto

    def orden_compra(self, id_compra):
        return self.comprobante(id_compra)

    def compras_por_proveedor(self):
        # Diccionario de listas: cada clave es un proveedor y contiene sus compras.
        agrupadas = {}
        for compra in self.lista:
            if compra.proveedor_id not in agrupadas:
                agrupadas[compra.proveedor_id] = []
            agrupadas[compra.proveedor_id].append(compra)
        return agrupadas

    def total_comprado(self):
        return round(sum(compra.calcular_total() for compra in self.lista), 2)
