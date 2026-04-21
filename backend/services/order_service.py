from models import db, Pedido, ItemPedido, Producto, Talle, StockTalle, PromocionProducto, MetodoPago
from datetime import datetime, timedelta
import uuid

class OrderService:
    @staticmethod
    def create_order(data: dict):
        """
        Lógica de creación de pedido con validación de stock, promociones automáticas y cupones.
        """
        metodo_pago_val = data.get('metodo_pago') or data.get('metodo_pago_id')
        metodo_pago_id = None
        
        # Mapeo de nombres del frontend a backend
        mapeo_frontend = {
            'mercadopago_card': 'mercadopago',
            'efectivo_local': 'efectivo_local',
            'transferencia': 'transferencia',
            'efectivo': 'efectivo',
        }
        
        if isinstance(metodo_pago_val, str) and not metodo_pago_val.isdigit():
            search_name = mapeo_frontend.get(metodo_pago_val, metodo_pago_val)
            # Buscar ID por nombre
            metodo = MetodoPago.query.filter(MetodoPago.nombre.ilike(f"%{search_name}%")).first()
            if metodo:
                metodo_pago_id = metodo.id
            else:
                # Fallback dinámico: busca el primero activo si no hay match
                metodo_fallback = MetodoPago.query.filter_by(activo=True).first()
                metodo_pago_id = metodo_fallback.id if metodo_fallback else 1
        else:
            # Si es ID numérico, verificar que exista
            try:
                provided_id = int(metodo_pago_val) if metodo_pago_val else None
                if provided_id and MetodoPago.query.get(provided_id):
                    metodo_pago_id = provided_id
                else:
                    metodo_fallback = MetodoPago.query.filter_by(nombre='transferencia').first() or MetodoPago.query.first()
                    metodo_pago_id = metodo_fallback.id if metodo_fallback else 1
            except:
                metodo_pago_id = 1

        # 1. Validar Stock y Preparar Items
        items_procesados = []
        
        for item_data in data.get('items', []):
            producto = Producto.query.get(item_data['producto_id'])
            talle = Talle.query.get(item_data['talle_id'])
            cantidad = int(item_data['cantidad'])
            
            if not producto or not talle:
                continue

            stock_talle = StockTalle.query.filter_by(producto_id=producto.id, talle_id=talle.id).first()
            if not stock_talle or stock_talle.cantidad < cantidad:
                raise Exception(f"Stock insuficiente: {producto.nombre} ({talle.nombre})")
            
            # Usar precio actual
            precio_unitario = producto.get_precio_actual()
            
            items_procesados.append({
                'producto': producto,
                'talle': talle,
                'cantidad': cantidad,
                'precio_unitario': precio_unitario,
                'descuento_aplicado': 0, # Se calculará globalmente
            })

        # 1.5 Calcular Promoción por CANTIDAD (NUEVO)
        # "Llevando 2 unidades, se aplica un 10%. Llevando 3 unidades, se aplica un 15%."
        total_qty = sum(item['cantidad'] for item in items_procesados)
        qty_discount_percent = 0
        
        if total_qty >= 3:
            qty_discount_percent = 15
        elif total_qty == 2:
            qty_discount_percent = 10
            
        if qty_discount_percent > 0:
            for item in items_procesados:
                # Aplica sobre el precio unitario * cantidad
                # Se suma a 'descuento_aplicado'
                amount = (item['precio_unitario'] * item['cantidad'] * qty_discount_percent) / 100
                item['descuento_aplicado'] += amount

        # 2. Calcular Promociones AUTOMÁTICAS (Globalmente)
        promos_auto = PromocionProducto.query.filter_by(activa=True, es_cupon=False).all()
        
        # Agrupar items por promoción aplicable para casos 2x1, 3x2, etc.
        # Nota: Un item podría tener múltiples promociones. 
        # Simplificación: Iteramos promociones y buscamos items que apliquen.
        
        for promo in promos_auto:
            if not promo.esta_activa():
                continue
                
            items_aplicables = [item for item in items_procesados if OrderService._is_promo_applicable(promo, item['producto'])]
            
            if not items_aplicables:
                continue
                
            tipo = promo.tipo_promocion.nombre.lower()
            valor = promo.valor or 0
            
            if 'porcentaje' in tipo:
                for item in items_aplicables:
                    descuento = (item['precio_unitario'] * item['cantidad'] * valor) / 100
                    item['descuento_aplicado'] += descuento
                    
            elif 'fijo' in tipo:
                for item in items_aplicables:
                    # Descuento fijo por unidad? O total? Asumimos por unidad si es 'descuento_fijo'
                    descuento = valor * item['cantidad']
                    # No descontar más que el precio
                    max_desc = item['precio_unitario'] * item['cantidad']
                    item['descuento_aplicado'] += min(descuento, max_desc)
                    
            elif '2x1' in tipo or '3x2' in tipo:
                # Expandir a unidades individuales para "Mix & Match"
                unidades = []
                for item in items_aplicables:
                    for _ in range(item['cantidad']):
                        unidades.append({'precio': item['precio_unitario'], 'ref_item': item})
                
                # Ordenar por precio descendente (pagas los caros, gratis los baratos)
                unidades.sort(key=lambda x: x['precio'], reverse=True)
                
                n = 2 if '2x1' in tipo else 3
                
                for i, unidad in enumerate(unidades):
                    # Si es slot gratuito (cada n-ésimo item, indices 0-based: 2x1 -> paga 0, gratis 1. 3x2 -> paga 0,1, gratis 2)
                    # wait, logic: 2x1 -> Buy 2, items index 0, 1. Pay 0. Free 1.
                    # if (i + 1) % n == 0: -> Free
                    if (i + 1) % n == 0:
                        unidad['ref_item']['descuento_aplicado'] += unidad['precio']

        # Calcular Subtotal y Descuento Total acumulado
        subtotal_calculado = 0
        descuento_total = 0
        
        for item in items_procesados:
            line_total = item['precio_unitario'] * item['cantidad']
            subtotal_calculado += line_total
            descuento_total += item['descuento_aplicado']

        # 3. Crear Pedido Base
        numero_pedido = OrderService._generate_next_order_id()
        pedido = Pedido(
            numero_pedido=numero_pedido,
            cliente_nombre=data.get('cliente_nombre'),
            cliente_email=data.get('cliente_email', '').lower().strip(), # Normalize email
            cliente_telefono=data.get('cliente_telefono', ''),
            cliente_direccion=data.get('calle', '') + ' ' + str(data.get('altura', '')),
            cliente_codigo_postal=data.get('codigo_postal'),
            cliente_localidad=data.get('ciudad'),
            cliente_provincia=data.get('provincia'),
            cliente_dni=data.get('dni'),
            metodo_pago_id=metodo_pago_id,
            metodo_envio=data.get('metodo_envio', 'correo_argentino'),
            costo_envio=float(data.get('costo_envio', 0)),
            estado='pendiente_aprobacion',
            aprobado=False,
            subtotal=subtotal_calculado, 
            descuento=descuento_total,
            total=0, # Se calcula al final
            fecha_expiracion=datetime.now() + timedelta(days=5)
        )
        
        db.session.add(pedido)
        db.session.flush() # ID
        
        # 4. Guardar Items
        for item in items_procesados:
            item_pedido = ItemPedido(
                pedido_id=pedido.id,
                producto_id=item['producto'].id,
                talle_id=item['talle'].id,
                cantidad=item['cantidad'],
                precio_unitario=item['precio_unitario'],
                descuento_aplicado=item['descuento_aplicado'],
                subtotal=(item['precio_unitario'] * item['cantidad']) - item['descuento_aplicado']
            )
            db.session.add(item_pedido)
            
        # 5. Procesar Cupón (si existe) -> Puede ser adicional
        codigo_cupon = data.get('codigo_cupon')
        descuento_cupon = 0
        if codigo_cupon:
            cupon = PromocionProducto.query.filter_by(codigo=codigo_cupon, activa=True, es_cupon=True).first()
            if cupon and cupon.esta_activa():
                # Validaciones simples de cupón
                if cupon.max_usos and cupon.usos_actuales >= cupon.max_usos:
                    raise Exception("Cupón agotado")
                if subtotal_calculado < cupon.compra_minima:
                    raise Exception(f"Monto mínimo: ${cupon.compra_minima}")
                
                 # Aplicar cupón
                # Simplificación: Aplicar sobre el total restante o recalcular?
                # Aplicamos directo al descuento total del pedido
                if cupon.tipo_promocion.nombre == 'descuento_porcentaje':
                     # Sobre el total descontado o sobre el subtotal? Usualmente sobre el total previo
                     base = subtotal_calculado - descuento_total
                     desc = base * (cupon.valor / 100)
                     descuento_cupon += desc
                elif cupon.tipo_promocion.nombre == 'descuento_fijo':
                    descuento_cupon += cupon.valor
                
                if cupon.envio_gratis:
                    pedido.costo_envio = 0
                    
                cupon.usos_actuales += 1
                
        pedido.descuento += descuento_cupon

        # 6. Descuento Método de Pago (15%)
        # CRITICAL FIX: Apply ONLY on products, NOT on shipping
        # The 15% discount should apply on (subtotal - product_discounts), NOT including shipping cost
        
        base_pago = pedido.subtotal - pedido.descuento  # Product total after discounts
        base_pago = max(0, base_pago)
        
        descuento_pago = 0
        metodo = MetodoPago.query.get(metodo_pago_id)
        if metodo:
            nombre = metodo.nombre.lower()
            if 'transferencia' in nombre or 'efectivo' in nombre:
                # Nuevo Logic: 10% para Shorts (Cat 8), 15% para el resto
                # Se calcula sobre el neto (Total item - descuentos previos)
                
                for item in items_procesados:
                    item_total = item['precio_unitario'] * item['cantidad']
                    item_net = item_total - item['descuento_aplicado']
                    if item_net < 0: item_net = 0
                    
                    percentage = 0.15 # Default (Remeras, etc)
                    
                    # Verificar si es Short (ID 8) o descendiente
                    es_short = False
                    cat_cursor = item['producto'].categoria
                    # Recorrer hacia arriba hasta encontrar root o id 8
                    # Limite de seguridad para evitar loops infinitos (aunque no deberia haber)
                    for _ in range(5): 
                        if not cat_cursor: break
                        if cat_cursor.id == 8:
                            es_short = True
                            break
                        cat_cursor = cat_cursor.categoria_padre
                    
                    if es_short: # Shorts y derivados
                        percentage = 0.10
                        
                    descuento_pago += item_net * percentage
        
        pedido.descuento += descuento_pago
        
        # 7. Total Final = Products (with discounts) + Shipping
        total_final = (pedido.subtotal + pedido.costo_envio) - pedido.descuento
        pedido.total = max(0, total_final)
        
        # Enviar notificación de confirmación
        try:
            from services.notification_service import NotificationService
            NotificationService.send_order_confirmation(pedido)
        except Exception as e:
            print(f"Error enviando notificación de pedido: {e}")

        # Asegurar que el método de pago esté cargado para la respuesta
        if not pedido.metodo_pago:
            pedido.metodo_pago = MetodoPago.query.get(pedido.metodo_pago_id)

        return pedido

    @staticmethod
    def _is_promo_applicable(promo, producto):
        if promo.alcance == 'tienda': return True
        if promo.alcance == 'producto' and any(p.id == producto.id for p in promo.productos): return True
        if promo.alcance == 'categoria' and any(c.id == producto.categoria_id for c in promo.categorias): return True
        return False

    @staticmethod
    def _generate_next_order_id():
        # Obtener el último pedido para calcular la secuencia
        try:
            # Buscar el último pedido creado por ID para tener referencia base
            last_order = Pedido.query.order_by(Pedido.id.desc()).first()
            
            start_code = 'AA0000'
            if last_order and last_order.numero_pedido:
                start_code = last_order.numero_pedido

            # Lógica de incremento y validación de colisiones
            current_code = start_code
            
            for _ in range(10): # Intentar 10 veces encontrar un hueco libre
                # Parsear
                if len(current_code) != 6 or not current_code[:2].isalpha() or not current_code[2:].isdigit():
                    current_code = 'AA0000'

                letters = current_code[:2]
                number = int(current_code[2:])
                
                number += 1
                if number > 9999:
                    number = 0
                    first_char = letters[0]
                    second_char = letters[1]
                    if second_char == 'Z':
                        second_char = 'A'
                        if first_char == 'Z':
                             return 'AAA001' 
                        else:
                            first_char = chr(ord(first_char) + 1)
                    else:
                        second_char = chr(ord(second_char) + 1)
                    letters = f"{first_char}{second_char}"
                
                candidate = f"{letters}{number:04d}"
                
                # Verificar si existe
                exists = Pedido.query.filter_by(numero_pedido=candidate).first()
                if not exists:
                    return candidate
                
                # Si existe, usamos este candidato como base para el siguiente loop
                current_code = candidate
            
            # Fallback random si falla loop
            return f"ER{datetime.now().strftime('%M%S')}"
            
        except Exception as e:
            print(f"Error generando ID pedido: {e}")
            return f"ER{datetime.now().strftime('%M%S')}"
