# 📧 Guía: Configurar Emails para VueloDigno

Esta guía te ayudará a configurar los emails profesionales para VueloDigno usando **Resend** (envío) y **Cloudflare Email Routing** (recepción).

---

## 🎯 **Objetivo Final:**

- ✅ `reclamos@vuelodigno.com` → Para ENVIAR reclamos a aerolíneas (vía Resend)
- ✅ `hola@vuelodigno.com` → Para RECIBIR emails de usuarios (forwarding a tu Gmail vía Cloudflare)

**Costo total: $0/mes** (gratis hasta 3,000 emails/mes en Resend)

---

## 📝 **Pre-requisitos:**

1. ✅ Dominio `vuelodigno.com` (o el que hayas comprado)
2. ✅ Cuenta en Resend (ya la tienes)
3. ✅ Cuenta en Cloudflare (gratis)

---

## 🚀 **PASO 1: Configurar Resend para ENVIAR emails**

### 1.1 Agregar tu dominio a Resend

1. Ve a https://resend.com/domains
2. Click en **"Add Domain"**
3. Ingresa: `vuelodigno.com`
4. Click en **"Add"**

### 1.2 Verificar tu dominio (Registros DNS)

Resend te mostrará 3 registros DNS que necesitas agregar:

**Ejemplo de registros (los tuyos serán diferentes):**

| Type | Name | Value |
|------|------|-------|
| TXT | `@` o `vuelodigno.com` | `resend-verification=abc123xyz...` |
| MX | `@` o `vuelodigno.com` | `feedback-smtp.resend.com` (priority 10) |
| TXT | `resend._domainkey` | `p=MIGfMA0GCSqGS...` (DKIM key) |

**¿Dónde agregar estos registros?**

Depende de dónde compraste el dominio:

#### **Si compraste en GoDaddy:**
1. Ve a https://dcc.godaddy.com/control/portfolio/dns
2. Busca tu dominio `vuelodigno.com`
3. Click en **"DNS"** → **"Manage Zones"**
4. Click en **"Add Record"** para cada uno
5. Copia exactamente los valores de Resend

#### **Si compraste en NIC México / Akky:**
1. Busca la sección de "Gestión DNS" o "DNS Management"
2. Agrega los 3 registros uno por uno
3. Guarda cambios

### 1.3 Esperar propagación DNS (5-30 minutos)

1. Regresa a Resend después de 10 minutos
2. Click en **"Verify Domain"**
3. Si aparece ✅ "Verified", ¡listo!
4. Si no, espera 10-20 minutos más

### 1.4 Crear API Key en Resend

1. Ve a https://resend.com/api-keys
2. Click en **"Create API Key"**
3. Nombre: `VueloDigno Production`
4. Permission: **Full Access** (o "Sending access")
5. Click en **"Create"**
6. **COPIA LA KEY** (solo se muestra una vez)
   - Ejemplo: `re_123abc456def...`

### 1.5 Actualizar tu código

**Archivo `.env`:**

```bash
RESEND_API_KEY=re_TU_KEY_AQUI
FROM_EMAIL=reclamos@vuelodigno.com
```

**NO compartas esta key con nadie. Agrégala a `.gitignore`**

---

## 📨 **PASO 2: Configurar Cloudflare para RECIBIR emails**

### 2.1 Agregar dominio a Cloudflare

1. Ve a https://www.cloudflare.com/
2. Crea cuenta gratis (si no tienes)
3. Click en **"Add a Site"**
4. Ingresa: `vuelodigno.com`
5. Selecciona plan **FREE** (gratis)
6. Click en **"Continue"**

### 2.2 Cambiar nameservers

Cloudflare te dará 2 nameservers, ejemplo:

```
alex.ns.cloudflare.com
lucy.ns.cloudflare.com
```

**Ve a donde compraste el dominio (GoDaddy/NIC México):**

1. Busca sección **"Nameservers"** o **"DNS Management"**
2. Cambia de los nameservers actuales a los de Cloudflare
3. Guarda cambios

⏳ **Espera 15-30 minutos** para que Cloudflare detecte el cambio.

### 2.3 Configurar Email Routing

1. En Cloudflare, ve a **"Email"** → **"Email Routing"**
2. Click en **"Get Started"** (si es primera vez)
3. Cloudflare agregará automáticamente registros MX

### 2.4 Crear Email Forward

1. En **"Email Routing"** → **"Destination addresses"**
2. Click en **"Add destination email"**
3. Ingresa: **tu Gmail personal** (ej: `zelma.garza@gmail.com`)
4. Verifica el email (recibirás un email de confirmación en tu Gmail)

5. Ahora en **"Routing rules"** → **"Create address"**
6. **Custom address:** `hola@vuelodigno.com`
7. **Action:** Forward to → Selecciona tu Gmail
8. Click en **"Save"**

✅ **Listo!** Ahora todos los emails a `hola@vuelodigno.com` llegarán a tu Gmail.

---

## ⚠️ **IMPORTANTE: Conflicto de registros MX**

Si agregaste registros MX en Resend Y en Cloudflare, tendrás problemas.

**Solución:**

1. **SOLO Cloudflare** debe tener registros MX
2. En Resend, **NO agregues** el registro MX (solo TXT de verificación y DKIM)
3. Resend solo necesita **enviar**, no recibir

**Registros DNS finales (ejemplo):**

| Type | Name | Value | Servicio |
|------|------|-------|----------|
| TXT | `@` | `resend-verification=...` | Resend |
| TXT | `resend._domainkey` | `p=MIGfMA0...` | Resend (DKIM) |
| MX | `@` | `route1.mx.cloudflare.net` (priority 83) | Cloudflare |
| MX | `@` | `route2.mx.cloudflare.net` (priority 38) | Cloudflare |
| MX | `@` | `route3.mx.cloudflare.net` (priority 96) | Cloudflare |
| TXT | `@` | `v=spf1 include:_spf.mx.cloudflare.net include:_spf.resend.com ~all` | SPF (ambos) |

---

## ✅ **PASO 3: Probar que funciona**

### Probar ENVÍO (Resend):

```python
# test_resend.py
import resend
import os
from dotenv import load_dotenv

load_dotenv()
resend.api_key = os.getenv('RESEND_API_KEY')

params = {
    "from": "reclamos@vuelodigno.com",
    "to": ["tu-gmail@gmail.com"],  # Cambia por tu email
    "subject": "Test de envío",
    "html": "<strong>Funciona!</strong> Email enviado desde Resend."
}

email = resend.Emails.send(params)
print(email)
```

Ejecuta:
```bash
python test_resend.py
```

Deberías recibir el email en tu Gmail en ~10 segundos.

### Probar RECEPCIÓN (Cloudflare):

1. Desde otro email (Gmail personal, Outlook, etc.)
2. Manda un email a: `hola@vuelodigno.com`
3. Deberías recibirlo en tu Gmail en ~10 segundos

---

## 🔧 **Troubleshooting:**

### ❌ "Domain not verified" en Resend

- Espera 30 minutos más
- Verifica que copiaste los registros DNS exactamente
- Usa herramientas como https://mxtoolbox.com/SuperTool.aspx para verificar DNS

### ❌ No llegan emails a `hola@vuelodigno.com`

- Verifica en Cloudflare que el email destino esté verificado (check mark verde)
- Revisa tu carpeta de SPAM en Gmail
- En Cloudflare Email Routing → Activity, verás logs de emails recibidos

### ❌ Emails enviados desde Resend van a SPAM

- Espera 24-48 horas después de configurar DNS
- Verifica que DKIM y SPF estén configurados (Resend → Domains → "Verified")
- Evita palabras spam en asunto ("GRATIS!!!", "CLICK AQUÍ")

---

## 📊 **Límites Gratis:**

**Resend (envío):**
- 3,000 emails/mes gratis
- 100 emails/día
- Después: $20 USD/mes por 50,000 emails

**Cloudflare Email Routing (recepción):**
- ¡ILIMITADO gratis! 🎉

---

## 🚀 **Siguiente paso: Actualizar código para usar Reply-To**

Cuando envíes reclamos, asegúrate de incluir `reply_to` para que las respuestas vayan al usuario:

```python
params = {
    "from": "reclamos@vuelodigno.com",
    "to": [airline_email],
    "cc": [user_email],  # Copia al usuario
    "reply_to": [user_email],  # Respuestas van al usuario
    "subject": "Reclamo de compensación...",
    "html": letter_html
}
```

---

## 📞 **¿Problemas?**

Escríbeme a hola@vuelodigno.com (cuando ya esté funcionando 😄) o por LinkedIn.

**Zelma Garza Salinas**
https://www.linkedin.com/in/zelmag/
