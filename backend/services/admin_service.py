from models import db, Producto, Pedido, Admin, Categoria, StockTalle, VentaExterna
from sqlalchemy import func
from datetime import datetime, timedelta

class AdminService:
    @staticmethod
    def get_dashboard_stats():
        """
        Calcula las estadísticas principales para el dashboard con desglose de ventas.
        """
        ahora = datetime.utcnow() - timedelta(hours=3)  # Argentina Time
        hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Inicio de semana (domingo anterior o hoy si es domingo)
        dia_semana = (ahora.weekday() + 1) % 7
        semana_inicio = hoy_inicio - timedelta(days=dia_semana)
        
        # Inicio de mes
        mes_inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_productos = Producto.query.count()
        productos_activos = Producto.query.filter_by(activo=True).count()
        
        # Productos sin stock comercializable (<= 5 según lógica de negocio)
        productos_sin_stock = Producto.query.filter(
            ~Producto.stock_talles.any(StockTalle.cantidad > 5)
        ).count()
        
        total_pedidos = Pedido.query.filter(Pedido.estado != 'cancelado').count()
        pedidos_pendientes_aprobacion = Pedido.query.filter_by(aprobado=False, estado='pendiente_aprobacion').count()
        pedidos_pendientes = Pedido.query.filter(Pedido.estado.notin_(['entregado', 'cancelado'])).count()
        
        # --- Cálculo de Ventas por Períodos ---
        def get_ventas_periodo(inicio, fin=None):
            # Web
            q_web = db.session.query(func.sum(Pedido.total)).filter(
                Pedido.aprobado == True,
                Pedido.estado.in_(['pendiente', 'confirmado', 'en_preparacion', 'enviado', 'entregado']),
                Pedido.created_at >= inicio
            )
            if fin: q_web = q_web.filter(Pedido.created_at <= fin)
            v_web = q_web.scalar() or 0
            
            # Externas
            q_ext = db.session.query(func.sum(VentaExterna.ganancia_total)).filter(
                VentaExterna.fecha >= inicio
            )
            if fin: q_ext = q_ext.filter(VentaExterna.fecha <= fin)
            v_ext = q_ext.scalar() or 0
            
            return float(v_web) + float(v_ext)

        ventas_hoy = get_ventas_periodo(hoy_inicio)
        ventas_semana = get_ventas_periodo(semana_inicio)
        ventas_mes = get_ventas_periodo(mes_inicio)
        
        # Ventas totales (histórico completo)
        total_ventas_web = db.session.query(func.sum(Pedido.total)).filter(
            Pedido.aprobado == True,
            Pedido.estado.in_(['pendiente', 'confirmado', 'en_preparacion', 'enviado', 'entregado'])
        ).scalar() or 0
        total_ventas_externas = db.session.query(func.sum(VentaExterna.ganancia_total)).scalar() or 0
        total_ventas = float(total_ventas_web) + float(total_ventas_externas)
        
        total_ventas_externas_count = VentaExterna.query.count()
        
        return {
            'productos': {
                'total': total_productos,
                'activos': productos_activos,
                'bajo_stock': productos_sin_stock
            },
            'pedidos': {
                'total': total_pedidos,
                'total_web': total_pedidos,
                'total_externas': total_ventas_externas_count,
                'pendientes': pedidos_pendientes,
                'pendientes_aprobacion': pedidos_pendientes_aprobacion
            },
            'ventas': {
                'total': total_ventas,
                'hoy': ventas_hoy,
                'semana': ventas_semana,
                'mes': ventas_mes
            }
        }

    @staticmethod
    def get_sales_stats(periodo: str, ahora: datetime = None, semana_offset: int = 0, anio: int = None):
        """
        Genera datos para los gráficos de ventas con las nuevas reglas:
        - Semana: 8 semanas desde el 1 de enero del año, navegable por bloques de 8
        - Mes: 12 meses del año especificado, navegable por año
        - Año: Solo el año actual
        """
        if not ahora: 
            # Ajustar a horario local Argentina (GMT-3) para que las estadísticas coincidan con el día real del usuario
            ahora = datetime.utcnow() - timedelta(hours=3)
        datos = []
        intervalos = []
        
        if periodo == 'dia':
            # Día a día: Semana actual (Dom a Sáb) - mantener como estaba
            dia_semana_custom = (ahora.weekday() + 1) % 7
            fecha_domingo = ahora - timedelta(days=dia_semana_custom)
            dias_labels = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
            for i in range(7):
                fecha = fecha_domingo + timedelta(days=i)
                inicio = datetime(fecha.year, fecha.month, fecha.day, 0, 0, 0)
                fin = datetime(fecha.year, fecha.month, fecha.day, 23, 59, 59)
                intervalos.append((f"{dias_labels[i]} {fecha.strftime('%d/%m')}", inicio, fin))
        
        elif periodo == 'semana':
            # Semana a semana: Mostrar última 8 semanas terminando en la fecha de referencia
            # 1. Encontrar el lunes de la semana de referencia
            dia_semana = (ahora.weekday()) # 0=Lunes, 6=Domingo
            lunes_ref = ahora - timedelta(days=dia_semana)
            lunes_ref = lunes_ref.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 2. Queremos ver 8 semanas. Para que 'ahora' sea el final, restamos 7 semanas al inicio
            # Así el rango es [Semana-7 ... Semana-0]
            fecha_inicio_bloque = lunes_ref - timedelta(weeks=7)
            
            # Generar 8 semanas consecutivas
            for i in range(8):
                inicio_semana = fecha_inicio_bloque + timedelta(weeks=i)
                inicio = inicio_semana
                fin = inicio + timedelta(days=6, hours=23, minutes=59, seconds=59)
                
                # Opcional: No mostrar semanas futuras si estamos navegando cerca de la fecha real
                # Pero si navegamos al pasado, queremos verlas.
                # Solo break si inicio es mayor que NOW (tiempo real, no fecha_ref)
                if inicio > ahora:
                     break
                
                label = f"S {inicio.strftime('%d/%m')}"
                intervalos.append((label, inicio, fin))
                
        elif periodo == 'mes':
            # Mes a mes: 12 meses del año especificado
            year = anio if anio else ahora.year
            meses_es = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
            
            for mes_num in range(1, 13):
                inicio = datetime(year, mes_num, 1, 0, 0, 0)
                
                # Calcular último día del mes
                if mes_num == 12:
                    fin = datetime(year + 1, 1, 1) - timedelta(seconds=1)
                else:
                    fin = datetime(year, mes_num + 1, 1) - timedelta(seconds=1)
                
                # No mostrar meses futuros
                if inicio > ahora:
                    break
                    
                intervalos.append((meses_es[mes_num], inicio, fin))
                
        elif periodo == 'anio':
            # Año a año: Arrancar desde el primer registro histórico
            anio_actual = ahora.year
            
            # Obtener el año más antiguo de pedidos o ventas
            min_pedido = db.session.query(func.min(Pedido.created_at)).scalar()
            min_venta = db.session.query(func.min(VentaExterna.fecha)).scalar()
            
            y1 = min_pedido.year if min_pedido else anio_actual
            y2 = min_venta.year if min_venta else anio_actual
            
            anio_inicio = min(y1, y2)
            
            # Asegurar que al menos mostramos desde el año pasado si no hay data (o el actual)
            # anio_inicio = min(anio_inicio, anio_actual) 
            
            for year in range(anio_inicio, anio_actual + 1):
                inicio = datetime(year, 1, 1, 0, 0, 0)
                fin = datetime(year, 12, 31, 23, 59, 59)
                
                # Si es el año actual y aún no terminó, cortar hasta hoy (opcional, o dejar fin de año)
                if year == anio_actual and fin > ahora:
                    fin = ahora
                    
                intervalos.append((str(year), inicio, fin))
        
        # Calcular ventas para cada intervalo
        max_venta = 0
        total_periodo = 0
        for label, inicio, fin in intervalos:
            # Ventas del sitio web (Aprobados o Entregados)
            ventas_web = db.session.query(func.sum(Pedido.total)).filter(
                Pedido.aprobado == True,
                Pedido.estado.in_(['pendiente', 'confirmado', 'en_preparacion', 'enviado', 'entregado']),
                Pedido.created_at.between(inicio, fin)
            ).scalar() or 0
            
            # Ventas externas
            ventas_externas = db.session.query(func.sum(VentaExterna.ganancia_total)).filter(
                VentaExterna.fecha.between(inicio, fin)
            ).scalar() or 0
            
            # Total combinado
            ventas = float(ventas_web) + float(ventas_externas)
            datos.append({'label': label, 'ventas': ventas, 'fecha': inicio.isoformat()})
            max_venta = max(max_venta, ventas)
            total_periodo += ventas
            
        return {
            'periodo': periodo,
            'datos': datos,
            'total_periodo': float(total_periodo),
            'max_venta': float(max_venta) if max_venta > 0 else 1
        }
