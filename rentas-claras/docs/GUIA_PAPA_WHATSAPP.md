# 📱 Guía Rápida: Configurar WhatsApp para RentasClaras

## Para: Papá (el dueño del negocio)
## Tiempo estimado: 30 minutos

---

## ¿Qué vamos a hacer?

Configurar WhatsApp para que el sistema envíe recordatorios de renta **automáticamente** a todos los inquilinos que no han pagado. Un clic = 32 mensajes personalizados.

---

## Paso 1: Crear Cuenta de Desarrollador (10 min)

1. Abre **https://developers.facebook.com** en tu navegador
2. Inicia sesión con tu cuenta de Facebook
3. Haz clic en **"Empezar"** o **"Get Started"**
4. Acepta los términos
5. Verifica tu teléfono o email si te lo pide

---

## Paso 2: Crear una App (5 min)

1. Ve a **https://developers.facebook.com/apps**
2. Haz clic en **"Crear App"** (botón verde)
3. Selecciona **"Otro"** → **"Business"**
4. Nombre de la app: `RentasClaras`
5. Tu email de contacto
6. Clic en **"Crear App"**

---

## Paso 3: Agregar WhatsApp (5 min)

1. En tu app, busca **"Agregar productos"**
2. Encuentra **"WhatsApp"** y haz clic en **"Configurar"**
3. Te llevará a la página de configuración de WhatsApp

---

## Paso 4: Copiar las Credenciales (2 min)

En la página de WhatsApp, verás:

1. **Phone number ID**: Un número largo (ej: `123456789012345`)
2. **Access Token**: Un texto largo que empieza con `EAA...`

**⚠️ IMPORTANTE:** Copia estos dos valores y mándamelos por WhatsApp. Los necesito para conectar el sistema.

---

## Paso 5: Agregar Número de Prueba (3 min)

1. En la configuración de WhatsApp, busca **"API Setup"**
2. Encuentra **"To"** (Destinatario)
3. Haz clic en **"Manage phone number list"**
4. Agrega tu número de teléfono (el tuyo, para pruebas)
5. Te llegará un código por WhatsApp
6. Ingresa el código para verificar

---

## Paso 6: Crear Plantilla de Mensaje (5 min)

1. Ve a **WhatsApp Manager** → **Message Templates**
2. Clic en **"Create Template"**
3. Llena así:

| Campo | Valor |
|-------|-------|
| Name | `rent_reminder` |
| Category | `UTILITY` |
| Language | `Spanish (Mexico)` |

4. En el cuerpo del mensaje, escribe exactamente:

```
Buenos días {{1}}. Espero esté bien. Para recordarle por favor del pago de la renta de {{2}}. Total: ${{3}} MXN. Gracias.
```

5. Haz clic en **"Submit"**

(La aprobación tarda 1-2 días)

---

## ¿Qué sigue?

Una vez que tengas:
- ✅ Phone Number ID
- ✅ Access Token
- ✅ Plantilla aprobada

Mándame esa info y yo conecto todo. Después, solo tienes que:

1. Abrir la app de RentasClaras
2. Marcar quién ya pagó
3. Hacer clic en **"Enviar a Todos"**

¡Y listo! Todos los pendientes reciben su mensaje automáticamente.

---

## ¿Preguntas?

Llámame o mándame WhatsApp. 📞
