# 📧 Guía: Configurar hola@vuelodigno.com para RECIBIR emails

## 🎯 Objetivo
Crear `hola@vuelodigno.com` que reenvíe automáticamente todos los emails a tu Gmail personal (`zelmagarza1099@gmail.com`).

**Costo: $0 / mes** (100% gratis, ilimitado)

---

## ✅ Paso 1: Crear cuenta en Cloudflare

1. Ve a https://www.cloudflare.com/
2. Click en **"Sign Up"** (arriba derecha)
3. Ingresa:
   - Email: `zelmagarza1099@gmail.com` (o el que prefieras)
   - Contraseña: (elige una segura)
4. Verifica tu email (revisa inbox)
5. Login en Cloudflare

---

## ✅ Paso 2: Agregar tu dominio a Cloudflare

1. En el dashboard, click en **"Add a Site"** (botón azul)
2. Ingresa tu dominio: `vuelodigno.com`
3. Click en **"Add site"**
4. Selecciona plan **FREE** (gratis)
5. Click en **"Continue"**

---

## ✅ Paso 3: Cambiar los Nameservers

Cloudflare te mostrará 2 nameservers personalizados, ejemplo:

```
alex.ns.cloudflare.com
lucy.ns.cloudflare.com
```

**IMPORTANTE:** Los tuyos serán diferentes. Cópialos exactamente como aparecen.

### **3.1 Si compraste el dominio en GoDaddy:**

1. Ve a https://account.godaddy.com/products
2. Busca `vuelodigno.com` y click en **"DNS"** o **"Manage"**
3. Busca la sección **"Nameservers"**
4. Click en **"Change"** o **"Edit"**
5. Selecciona **"Custom nameservers"**
6. Borra los nameservers actuales de GoDaddy
7. Agrega los 2 nameservers de Cloudflare (uno por uno)
8. Click en **"Save"**

### **3.2 Si compraste en NIC México / Akky:**

1. Busca la sección de "Gestión DNS" o "DNS Management" en tu panel
2. Encuentra "Nameservers" o "Servidores DNS"
3. Cambia a los nameservers de Cloudflare
4. Guarda cambios

---

## ✅ Paso 4: Esperar propagación DNS

⏰ **Tiempo: 5 minutos a 2 horas** (normalmente 15-30 mins)

1. Regresa a Cloudflare
2. Click en **"Done, check nameservers"**
3. Cloudflare verificará automáticamente
4. Recibirás un email cuando esté listo: "vuelodigno.com is now active on Cloudflare"

💡 **Tip:** Mientras esperas, puedes continuar con los siguientes pasos (pero no funcionarán hasta que el dominio esté activo).

---

## ✅ Paso 5: Activar Email Routing

1. En el dashboard de Cloudflare, selecciona `vuelodigno.com`
2. En el menú izquierdo, busca **"Email"** (ícono de sobre)
3. Click en **"Email Routing"**
4. Click en **"Get Started"** (botón azul)

Cloudflare te mostrará un resumen:
- ✅ Forwarding ilimitado gratis
- ✅ Sin límites de emails

5. Click en **"Continue"** o **"Enable Email Routing"**

---

## ✅ Paso 6: Cloudflare agregará registros DNS automáticamente

Cloudflare agregará automáticamente 3 registros MX a tu dominio:

```
MX  @  route1.mx.cloudflare.net  (priority 79)
MX  @  route2.mx.cloudflare.net  (priority 57)
MX  @  route3.mx.cloudflare.net  (priority 7)
```

✅ **No tienes que hacer nada**, Cloudflare lo hace automático.

6. Click en **"Automatic"** o **"Add records and enable"**

---

## ✅ Paso 7: Agregar tu Gmail como destino

1. En **"Destination addresses"**, click en **"Add destination address"**
2. Ingresa: `zelmagarza1099@gmail.com`
3. Click en **"Save and Continue"** o **"Add"**

**IMPORTANTE:** Cloudflare enviará un email de verificación a `zelmagarza1099@gmail.com`

4. Ve a tu Gmail
5. Busca email de: `no-reply@cloudflaremail.com`
   - Asunto: "Verify your destination email address"
6. Click en el link de verificación **"Verify email address"**
7. Verás: "✅ Email address verified"

---

## ✅ Paso 8: Crear el email hola@vuelodigno.com

1. Regresa a Cloudflare → Email Routing
2. Busca la sección **"Routing rules"** o **"Custom addresses"**
3. Click en **"Create address"** o **"Add rule"**

4. Completa:
   - **Custom address:** `hola`
   - **Action:** Forward to
   - **Destination:** `zelmagarza1099@gmail.com` (selecciona de la lista)

5. Click en **"Save"** o **"Create"**

✅ **¡Listo!** Ya tienes `hola@vuelodigno.com` funcionando.

---

## ✅ Paso 9: Probar que funciona

### Opción 1: Email Test desde Cloudflare

1. En Email Routing, busca **"Send test email"** o similar
2. Cloudflare enviará un email de prueba a `hola@vuelodigno.com`
3. Deberías recibirlo en `zelmagarza1099@gmail.com` en ~10 segundos

### Opción 2: Enviar email manual

1. Desde otro email (Outlook, otro Gmail, etc.)
2. Manda un email a: `hola@vuelodigno.com`
3. Asunto: "Test"
4. Mensaje: "Probando email forwarding"
5. Envía

6. **Revisa tu Gmail:** `zelmagarza1099@gmail.com`
   - Deberías ver el email en ~10-30 segundos
   - **FROM:** mostrará el email original del remitente
   - **TO:** `hola@vuelodigno.com` (forwarded to you)

---

## 📊 Paso 10: Verificar que todo funciona

En Cloudflare Email Routing verás:

✅ **Status:** Active
✅ **Addresses:** hola@vuelodigno.com → zelmagarza1099@gmail.com
✅ **Activity log:** Muestra emails recibidos y reenviados

---

## ⚠️ Troubleshooting

### ❌ "Domain not active" en Cloudflare

**Causa:** Los nameservers no han sido cambiados o DNS aún no propagó.

**Solución:**
1. Verifica que cambiaste los nameservers correctamente
2. Espera 30 minutos más
3. Usa https://www.whatsmydns.net/ para verificar propagación DNS

### ❌ No llegan emails a `hola@vuelodigno.com`

**Causas posibles:**

1. **Email destino no verificado:**
   - Ve a Cloudflare → Email Routing → Destination addresses
   - Verifica que `zelmagarza1099@gmail.com` tenga ✅ verde
   - Si no, reenvía el email de verificación

2. **DNS no propagado:**
   - Espera 1-2 horas
   - Verifica registros MX: https://mxtoolbox.com/SuperTool.aspx
   - Ingresa: `vuelodigno.com`
   - Deberías ver 3 registros MX de Cloudflare

3. **Email va a SPAM:**
   - Revisa carpeta SPAM en Gmail
   - Marca como "No es spam" si lo encuentras ahí

4. **Routing rule mal configurada:**
   - Ve a Email Routing → Routing rules
   - Verifica que `hola@vuelodigno.com` esté activa
   - Edita y guarda de nuevo si es necesario

---

## 🎉 Resultado Final

Ahora cuando alguien te escriba a `hola@vuelodigno.com`:

1. ✅ Email llega a servidores de Cloudflare
2. ✅ Cloudflare lo reenvía automáticamente a `zelmagarza1099@gmail.com`
3. ✅ Recibes el email en tu Gmail personal
4. ✅ Puedes responder desde Gmail (el destinatario verá tu Gmail, no hola@)

---

## 📝 Opcional: Responder DESDE hola@vuelodigno.com

Si quieres que tus respuestas salgan desde `hola@vuelodigno.com` (no desde tu Gmail), necesitas configurar **Gmail SMTP Relay** o **Google Workspace**.

**Opciones:**

1. **Google Workspace** ($108 MXN/mes)
   - Buzón completo con envío y recepción
   - Más profesional

2. **Solo recibir** (GRATIS - lo que acabas de configurar)
   - Recibes en Gmail
   - Respondes desde Gmail (el destinatario ve tu Gmail)

**Para MVP, la opción gratis es suficiente.** Los usuarios ven que les responde Zelma desde Gmail, no es problema.

---

## ✅ Checklist Final

- [ ] Dominio `vuelodigno.com` agregado a Cloudflare
- [ ] Nameservers cambiados
- [ ] Email Routing activado
- [ ] `zelmagarza1099@gmail.com` verificado como destino
- [ ] `hola@vuelodigno.com` creado y activo
- [ ] Email de prueba enviado y recibido

---

**¿Necesitas ayuda?** Mándame un mensaje por LinkedIn o... espera, mándame un email a `hola@vuelodigno.com` cuando esté funcionando 😄

**Zelma Garza Salinas**
https://www.linkedin.com/in/zelmag/
