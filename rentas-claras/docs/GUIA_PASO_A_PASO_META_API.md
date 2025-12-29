# 🚀 Guía Paso a Paso: Crear Cuenta Meta Developer para WhatsApp API

## ⚠️ IMPORTANTE: Lee Esto Primero

**Zelma, como eres empleada de Meta**, el portal de desarrolladores detectará tu cuenta de trabajo y bloqueará la creación de apps personales.

### Opciones:

| Opción | Recomendación |
|--------|---------------|
| **A) Tu papá crea la cuenta** | ✅ **MEJOR OPCIÓN** - Él es el dueño del negocio |
| **B) Tu cuenta personal** | ⚠️ Usa navegador incógnito, desconectada de Meta |

---

## 📋 Paso 1: Preparación (2 minutos)

### Si tu papá va a hacerlo:
1. Necesita una cuenta de Facebook (puede ser su cuenta personal)
2. Tener su teléfono a la mano para verificación
3. Un email que revise regularmente

### Si tú lo haces:
1. **Cierra TODOS los navegadores**
2. **Abre una ventana de incógnito/privada**:
   - Chrome: `Cmd + Shift + N`
   - Safari: `Cmd + Shift + N`
   - Firefox: `Cmd + Shift + P`
3. **NO inicies sesión en Facebook/Meta/Workplace**

---

## 📋 Paso 2: Crear Cuenta de Desarrollador (5 minutos)

### 2.1 Ir al Portal de Desarrolladores

🔗 **Abre este link**: [https://developers.facebook.com](https://developers.facebook.com)

![Step 1](https://i.imgur.com/placeholder1.png)

### 2.2 Iniciar Sesión

1. Haz clic en **"Log In"** (esquina superior derecha)
2. Usa la cuenta de Facebook de tu papá (o tu cuenta personal NO de trabajo)
3. Si no tiene cuenta, clic en "Create Account"

### 2.3 Registrarse como Desarrollador

1. Aparecerá un mensaje: **"Get Started as a Developer"**
2. Haz clic en **"Get Started"**
3. Acepta los términos y condiciones ✅
4. Verifica el teléfono si te lo pide (te mandan SMS)
5. Verifica el email si te lo pide

**✅ CHECKPOINT**: Deberías ver el "Meta for Developers Dashboard"

---

## 📋 Paso 3: Crear una App de Negocios (5 minutos)

### 3.1 Ir a Mis Apps

🔗 **Abre**: [https://developers.facebook.com/apps](https://developers.facebook.com/apps)

### 3.2 Crear Nueva App

1. Haz clic en el botón verde **"Create App"**

2. **Selecciona el tipo de app**:
   - Aparecerán opciones como "Consumer", "Business", etc.
   - Selecciona: **"Other"** → Luego **"Business"**
   - Clic en **"Next"**

3. **Información de la App**:
   ```
   App name: RentasClaras
   App contact email: [tu email o el de tu papá]
   Business Account: (déjalo vacío por ahora o selecciona si ya tienes uno)
   ```

4. Clic en **"Create App"**

5. **Verificación de seguridad**: Te puede pedir tu contraseña de nuevo

**✅ CHECKPOINT**: Deberías ver el "App Dashboard" de tu nueva app

---

## 📋 Paso 4: Agregar el Producto WhatsApp (3 minutos)

### 4.1 Buscar WhatsApp en Productos

1. En tu App Dashboard, busca la sección **"Add products to your app"**
2. Busca el cuadro que dice **"WhatsApp"**
3. Haz clic en **"Set Up"**

### 4.2 Configurar WhatsApp

1. Te llevará a la página de configuración de WhatsApp
2. Sigue los pasos que te indica (puede pedir crear un Meta Business Account)

**Si te pide crear Meta Business Account**:
- Nombre del negocio: `Administración Garza` (o como quiera llamarlo tu papá)
- Dirección: La dirección real del negocio
- Esto es gratis y necesario para WhatsApp Business API

---

## 📋 Paso 5: Obtener Credenciales de Prueba (2 minutos)

### 5.1 Ir a API Setup

1. En el menú izquierdo de WhatsApp, haz clic en **"API Setup"**
2. Verás dos valores importantes:

```
📞 Phone number ID: 123456789012345
🔑 Temporary access token: EAAGm0PX4ZCps...
```

### 5.2 Copiar y Guardar

**¡COPIA ESTOS VALORES AHORA!**

```bash
# Guarda esto en un lugar seguro (notepad, etc.)
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_ACCESS_TOKEN=EAAGm0PX4ZCps...
```

⚠️ **El token temporal expira en 24 horas** - está bien para probar

**✅ CHECKPOINT**: Tienes los dos valores copiados

---

## 📋 Paso 6: Agregar Número de Prueba (3 minutos)

Antes de la verificación del negocio, solo puedes enviar mensajes a números verificados.

### 6.1 Agregar tu Número

1. En "API Setup", busca la sección **"Send and receive messages"**
2. Donde dice **"To"**, haz clic en **"Manage phone number list"**
3. Clic en **"Add phone number"**
4. Ingresa TU número de celular (el de pruebas): `+52 81 1234 5678`
5. Recibirás un código por WhatsApp
6. Ingresa el código

**✅ CHECKPOINT**: Tu número aparece como "Verified"

---

## 📋 Paso 7: Probar que Funciona (2 minutos)

### 7.1 Enviar Mensaje de Prueba

1. En "API Setup", busca **"Step 2: Send messages"**
2. Ya debería tener un template de prueba llamado `hello_world`
3. Selecciona tu número verificado
4. Haz clic en **"Send Message"**

### 7.2 Verificar

📱 **Revisa tu WhatsApp** - Deberías recibir un mensaje de prueba

**✅ CHECKPOINT FINAL**: Recibiste el mensaje de prueba

---

## 🎉 ¡Listo para el Siguiente Paso!

### Lo que tienes ahora:
- ✅ Cuenta de desarrollador Meta
- ✅ App "RentasClaras" creada
- ✅ WhatsApp API configurado
- ✅ Credenciales de prueba (Phone Number ID + Token)
- ✅ Tu número verificado para pruebas

### Siguiente: Crear Templates de Mensajes

Una vez que me confirmes que completaste estos pasos, te guiaré para:
1. Crear los templates `rent_reminder_formal` y `late_fee_notice`
2. Configurar las credenciales en el archivo `.env`
3. Escribir el código del `WhatsAppClient`

---

## 🆘 Problemas Comunes

### "Error: You need a Business Account"
- Haz clic en "Create Business Account"
- Llena los datos básicos del negocio de tu papá
- Es gratis

### "This account cannot create apps"
- Estás usando tu cuenta de Meta employee
- Cierra todo y usa incógnito con otra cuenta

### "Verification required"
- Sigue los pasos de verificación (SMS o email)
- Es normal para nuevas cuentas

### "Token expired"
- Los tokens temporales duran 24 horas
- Puedes generar uno nuevo en "API Setup"

---

## 📸 Capturas de Referencia

*(Las capturas de pantalla reales del proceso estarían aquí)*

### Pantalla 1: Meta for Developers Dashboard
```
┌─────────────────────────────────────────────┐
│  Meta for Developers                        │
│  ┌─────────────────────────────────────┐   │
│  │  Welcome, [Nombre]!                 │   │
│  │  [Create App]  [My Apps]            │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### Pantalla 2: WhatsApp API Setup
```
┌─────────────────────────────────────────────┐
│  WhatsApp > API Setup                       │
│  ─────────────────────────────────────────  │
│  Step 1: Select phone numbers               │
│  From: Test Number (15550000000)            │
│  Phone number ID: 123456789012345           │
│  ─────────────────────────────────────────  │
│  Temporary access token:                    │
│  [EAAGm0PX4ZCps...] [Copy]                 │
└─────────────────────────────────────────────┘
```

---

## 📞 ¿Necesitas Ayuda?

Si te atoras en algún paso, dime:
1. En qué paso estás
2. Qué error o mensaje ves
3. Una captura de pantalla si puedes

¡Estoy aquí para ayudarte! 🚀
