from flask_mail import Message
import requests
import os

class NotificationService:
    @staticmethod
    def send_order_confirmation(pedido):
        """Envía notificaciones de pedido recibido/pendiente"""
        api_key = os.environ.get('BREVO_API_KEY')
        if not api_key:
            print("DEBUG NOTIFICACION: BREVO_API_KEY no configurada. No se puede enviar confirmación de pedido.")
            return

        # Construir instrucciones dinámicas según pago
        instrucciones_pago = ""
        metodo_nombre = pedido.metodo_pago.nombre.lower() if pedido.metodo_pago else ""

        if 'efectivo' in metodo_nombre and 'local' in metodo_nombre:
            instrucciones_pago = """
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>💵 Paso final: Confirmar pago en efectivo</h3>
                <p>Para preparar tu pedido, necesitamos que nos confirmes por WhatsApp que pasarás a retirar y abonar.</p>
                <p><a href="https://wa.me/3584171716?text=Hola! Hice el pedido %23{numero} y paso a retirar." style="background-color: #25d366; color: white; padding: 10px 20px; text-decoration: none; border-radius: 20px;">Confirmar pedido por WhatsApp</a></p>
            </div>
            """.format(numero=pedido.numero_pedido)
        elif 'transferencia' in metodo_nombre:
            instrucciones_pago = """
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>🏦 Datos para la Transferencia</h3>
                <p><strong>Banco:</strong> Mercado Pago<br>
                <strong>Titular:</strong> Tomas Cruseno<br>
                <strong>CVU:</strong> 0000003100068933152485<br>
                <strong>Alias:</strong> el.vestuario.r4</p>
                <p><strong>Monto a transferir:</strong> ${total}</p>
                <br>
                <p style="color: #d32f2f;"><strong>⚠️ IMPORTANTE:</strong> Enviá el comprobante por WhatsApp para confirmar tu pedido.</p>
                <p><a href="https://wa.me/3584171716" style="background-color: #25d366; color: white; padding: 10px 20px; text-decoration: none; border-radius: 20px;">Enviar Comprobante</a></p>
            </div>
            """.format(total=pedido.total)
        elif 'efectivo' in metodo_nombre: # Pago Facil / Rapipago
            instrucciones_pago = """
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>📄 Instrucciones de Pago (Rapipago / Pago Fácil)</h3>
                <p>Acercate a la sucursal e indicá este código CVU para ingresar dinero:</p>
                <div style="font-size: 20px; font-weight: bold; background: #e3f2fd; padding: 10px; text-align: center;">0000003100068933152485</div>
                <p><strong>Monto a pagar:</strong> ${total}</p>
                <br>
                <p style="color: #d32f2f;"><strong>⚠️ IMPORTANTE:</strong> Una vez pagado, envianos el ticket por WhatsApp.</p>
                <p><a href="https://wa.me/3584171716" style="background-color: #25d366; color: white; padding: 10px 20px; text-decoration: none; border-radius: 20px;">Enviar Comprobante</a></p>
            </div>
            """.format(total=pedido.total)

        # Construir lista de items
        items_html = ""
        for item in pedido.items:
            items_html += f"<li>{item.producto.nombre} (x{item.cantidad}) - Talle: {item.talle.nombre}</li>"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                    <h2 style="text-align: center; color: #000;">¡Gracias por tu compra, {pedido.cliente_nombre}!</h2>
                    <p style="text-align: center; font-size: 18px;">Tu pedido <strong>#{pedido.numero_pedido}</strong> ha sido registrado.</p>
                    
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <h3>📋 Detalles del Pedido</h3>
                    <ul>
                        {items_html}
                    </ul>
                    <p><strong>Total: ${pedido.total}</strong></p>
                    <p>Forma de Pago: {pedido.metodo_pago.nombre if pedido.metodo_pago else 'A convenir'}</p>
                    <p>Forma de Envío/Retiro: {pedido.metodo_envio}</p>
                    
                    {instrucciones_pago}
                    
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <p style="font-size: 12px; color: #999; text-align: center;">
                        Si tienes alguna duda, responde a este correo o contáctanos por WhatsApp.
                    </p>
                </div>
            </body>
        </html>
        """

        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": api_key
        }
        
        payload = {
            "sender": {"name": "El Vestuario", "email": os.environ.get('MAIL_DEFAULT_SENDER', 'elvestuario.r4@gmail.com')},
            "to": [{"email": pedido.cliente_email}],
            "subject": f"Confirmación de Pedido #{pedido.numero_pedido} - El Vestuario",
            "htmlContent": html_content
        }
        
        try:
            print(f"DEBUG NOTIFICACION: Enviando confirmación de pedido a {pedido.cliente_email}...", flush=True)
            requests.post(url, headers=headers, json=payload, timeout=15)
        except Exception as e:
            print(f"DEBUG NOTIFICACION: Error enviando mail de pedido: {e}")

    @staticmethod
    def send_order_approved_email(pedido):
        """Envía email cuando el admin aprueba/envía el pedido"""
        api_key = os.environ.get('BREVO_API_KEY')
        if not api_key: return

        # Construir lista de items
        items_html = ""
        for item in pedido.items:
            # Check for attributes safely in case eager loading isn't on
            p_nombre = item.producto.nombre if item.producto else "Producto"
            t_nombre = item.talle.nombre if item.talle else "-"
            items_html += f"<li>{p_nombre} (x{item.cantidad}) - Talle: {t_nombre}</li>"

        tracking_info = ""
        if pedido.metodo_envio and 'propio' not in pedido.metodo_envio.lower() and 'local' not in pedido.metodo_envio.lower():
             tracking_info = f"""
             <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>🚚 Información de Envío</h3>
                <p>Tu pedido ha sido despachado por <strong>{pedido.metodo_envio}</strong>.</p>
                <p>Pronto recibirás un código de seguimiento o novedades adicionales.</p>
             </div>
             """
        elif 'local' in (pedido.metodo_envio or '').lower():
             tracking_info = f"""
             <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>🏬 ¡Listo para retirar!</h3>
                <p>Tu pedido ya está listo en nuestro local.</p>
                <p>Te esperamos en los horarios de atención.</p>
             </div>
             """

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <h2 style="color: #2e7d32;">¡Tu pedido está en camino! 🚀</h2>
                        <p style="font-size: 16px;">Hola {pedido.cliente_nombre}, tenemos buenas noticias.</p>
                    </div>
                    
                    <p>El pedido <strong>#{pedido.numero_pedido}</strong> ha sido aprobado y procesado exitosamente.</p>
                    
                    {tracking_info}
                    
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <h3>📦 Resumen de la compra</h3>
                    <ul>
                        {items_html}
                    </ul>
                    
                    <p><strong>Total: ${pedido.total}</strong></p>
                    
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <p style="font-size: 12px; color: #999; text-align: center;">
                        Gracias por confiar en El Vestuario.
                    </p>
                </div>
            </body>
        </html>
        """

        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": api_key
        }
        
        payload = {
            "sender": {"name": "El Vestuario", "email": os.environ.get('MAIL_DEFAULT_SENDER', 'elvestuario.r4@gmail.com')},
            "to": [{"email": pedido.cliente_email}],
            "subject": f"¡Pedido Enviado! #{pedido.numero_pedido} - El Vestuario",
            "htmlContent": html_content
        }
        
        try:
            print(f"DEBUG NOTIFICACION: Enviando aviso de aprobación a {pedido.cliente_email}...", flush=True)
            requests.post(url, headers=headers, json=payload, timeout=15)
        except Exception as e:
            print(f"DEBUG NOTIFICACION: Error enviando mail de aprobación: {e}")

    @staticmethod
    def send_payment_confirmation(pedido):
        """Envía notificaciones cuando el pago se acredita"""
        from app import mail # Importación diferida para evitar ciclos
        
        # 1. Notificación por Email
        msg = Message(
            f"Pago Confirmado - Pedido #{pedido.numero_pedido}",
            recipients=[pedido.cliente_email]
        )
        msg.body = f"""
        Hola {pedido.cliente_nombre}, tu pago del pedido #{pedido.numero_pedido} se acreditó correctamente.
        
        Detalles del pedido:
        Total: ${pedido.total}
        Estado: PAGADO
        
        ¡Gracias por tu compra!
        """
        try:
            mail.send(msg)
        except Exception as e:
            print(f"Error enviando email: {e}")

        # 2. Notificación por WhatsApp (Meta Cloud API)
        # Se asume que existen variables de entorno configuradas
        wa_token = os.environ.get('WA_TOKEN')
        wa_phone_id = os.environ.get('WA_PHONE_ID')
        
        if wa_token and wa_phone_id:
            url = f"https://graph.facebook.com/v17.0/{wa_phone_id}/messages"
            headers = {
                "Authorization": f"Bearer {wa_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": pedido.cliente_telefono,
                "type": "template",
                "template": {
                    "name": "confirmacion_pago", # Nombre del template aprobado en Meta
                    "language": { "code": "es" },
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                { "type": "text", "text": pedido.cliente_nombre },
                                { "type": "text", "text": pedido.numero_pedido },
                                { "type": "text", "text": str(pedido.total) }
                            ]
                        }
                    ]
                }
            }
            try:
                requests.post(url, json=payload, headers=headers)
            except Exception as e:
                print(f"Error enviando WhatsApp: {e}")
        else:
            print("WhatsApp no configurado. Simulando envío para pedido #" + pedido.numero_pedido)
            print(f"WHATSAPP A {pedido.cliente_telefono}: Hola {pedido.cliente_nombre}, pago confirmado por ${pedido.total}")

    @staticmethod
    def send_password_reset_email(email, token, nombre):
        """Envía email para restablecer contraseña"""
        from app import mail
        
        # Link al frontend (asumiendo que corre en el mismo host o configurado)
        # En producción debería ser una variable de entorno FRONTEND_URL
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:4200')
        reset_link = f"{frontend_url}/reset-password?token={token}"
        
        msg = Message(
            "Restablecer Contraseña - El Vestuario",
            recipients=[email]
        )
        msg.body = f"""
        Hola {nombre},
        
        Recibimos una solicitud para restablecer tu contraseña.
        Haz clic en el siguiente enlace para crear una nueva contraseña:
        
        {reset_link}
        
        Si no solicitaste esto, puedes ignorar este correo.
        El enlace expirará en 1 hora.
        
        Saludos,
        El equipo de El Vestuario
        """
        try:
            print(f"DEBUG EMAIL: Enviando reset link a {email}: {reset_link}")
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Error enviando email de reset: {e}")
            return False

    @staticmethod
    def send_verification_code(cliente, codigo, metodo):
        """Envía el código de verificación por email o WhatsApp/SMS"""
        if metodo == 'email':
            api_key = os.environ.get('BREVO_API_KEY')
            if not api_key:
                print("DEBUG NOTIFICACION: BREVO_API_KEY no configurada. No se puede enviar email de verificación.")
                return False
                
            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": api_key
            }
            
            payload = {
                "sender": {"name": "El Vestuario", "email": os.environ.get('MAIL_DEFAULT_SENDER', 'elvestuario.r4@gmail.com')},
                "to": [{"email": cliente.email}],
                "subject": "Código de Verificación - El Vestuario",
                "textContent": f"Hola {cliente.nombre}, tu código de verificación es: {codigo}\n\nEste código es necesario para activar tu cuenta."
            }
            
            try:
                print(f"DEBUG NOTIFICACION: Enviando código de verificación a {cliente.email} vía Brevo...", flush=True)
                response = requests.post(url, headers=headers, json=payload, timeout=15)
                return response.status_code in [201, 202, 200]
            except Exception as e:
                print(f"DEBUG NOTIFICACION: Error enviando mail de verificación: {e}")
                return False
        else:
            # 1. Intentar WhatsApp (Meta Cloud API) si están las credenciales
            wa_token = os.environ.get('WA_TOKEN')
            wa_phone_id = os.environ.get('WA_PHONE_ID')
            
            if wa_token and wa_phone_id:
                url = f"https://graph.facebook.com/v17.0/{wa_phone_id}/messages"
                headers = {
                    "Authorization": f"Bearer {wa_token}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "messaging_product": "whatsapp",
                    "to": cliente.telefono,
                    "type": "template",
                    "template": {
                        "name": "verificacion_cuenta", # Nombre del template que debe estar aprobado en Meta
                        "language": { "code": "es" },
                        "components": [
                            {
                                "type": "body",
                                "parameters": [
                                    { "type": "text", "text": cliente.nombre },
                                    { "type": "text", "text": codigo }
                                ]
                            }
                        ]
                    }
                }
                try:
                    print(f"DEBUG NOTIFICACION: Intentando enviar WhatsApp a {cliente.telefono}...", flush=True)
                    response = requests.post(url, json=payload, headers=headers, timeout=10)
                    if response.status_code in [200, 201]:
                        print("DEBUG NOTIFICACION: WhatsApp enviado con éxito vía Meta.", flush=True)
                        return True
                    else:
                        print(f"DEBUG NOTIFICACION: WhatsApp falló (Status: {response.status_code}). Intentando fallback a SMS...", flush=True)
                except Exception as e:
                    print(f"DEBUG NOTIFICACION: Error en WhatsApp Meta: {e}. Intentando fallback a SMS...", flush=True)

            # 2. Fallback a SMS (Brevo) si no hay WhatsApp o falló
            api_key = os.environ.get('BREVO_API_KEY')
            if not api_key:
                print("DEBUG NOTIFICACION: BREVO_API_KEY no configurada. No se puede enviar SMS de fallback.")
                return False

            telefono_limpio = "".join(filter(str.isdigit, cliente.telefono))
            url_sms = "https://api.brevo.com/v3/transactionalSMS/sms"
            headers_sms = {
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": api_key
            }
            
            payload_sms = {
                "type": "transactional",
                "sender": "ElVestuario",
                "recipient": telefono_limpio,
                "content": f"Hola {cliente.nombre}, tu codigo de verificacion El Vestuario es: {codigo}"
            }
            
            try:
                print(f"DEBUG NOTIFICACION: Enviando SMS de fallback a {telefono_limpio} vía Brevo...", flush=True)
                requests.post(url_sms, headers=headers_sms, json=payload_sms, timeout=15)
                return True
            except Exception as e:
                print(f"DEBUG NOTIFICACION: Error en SMS de fallback: {e}")
                return False

    @staticmethod
    def send_newsletter(subject, html_content, recipients, test_email=None):
        """
        Envía un newsletter usando la API de Brevo (HTTP) para evitar bloqueos de puertos SMTP.
        """
        api_key = os.environ.get('BREVO_API_KEY')
        if not api_key:
            print("DEBUG NEWSLETTER: BREVO_API_KEY no configurada.")
            return 0
            
        # Si es test, sobrescribir lista
        if test_email:
            recipients = [{'email': test_email, 'nombre': 'Test Admin'}]
            
        count = 0
        total = len(recipients)
        
        print(f"DEBUG NEWSLETTER: Iniciando envío a {total} destinatarios vía Brevo API.")
        
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": api_key
        }
        
        sender_email = os.environ.get('MAIL_DEFAULT_SENDER', 'elvestuario.r4@gmail.com')
        
        for recipient in recipients:
            try:
                email = recipient['email']
                nombre = recipient.get('nombre') or 'Cliente'
                
                payload = {
                    "sender": {"name": "El Vestuario", "email": sender_email},
                    "to": [{"email": email, "name": nombre}],
                    "subject": subject,
                    "htmlContent": html_content
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                
                if response.status_code in [200, 201, 202]:
                    count += 1
                else:
                    print(f"Error Brevo enviando a {email}: {response.text}")
                
                # Rate limiting suave (no bombardear la API)
                if not test_email and count % 5 == 0:
                    import time
                    time.sleep(0.2)
                    
            except Exception as e:
                print(f"Error enviando newsletter a {email}: {e}")
                continue

        print(f"DEBUG NEWSLETTER: Finalizado. Enviados: {count}/{total}")
        return count

