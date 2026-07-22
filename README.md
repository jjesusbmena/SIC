# Publicador de ofertas de Mercado Libre a Telegram (con links de afiliado)

Busca las ofertas con mayor descuento/ventas en categorías de Mercado Libre
México, genera tu link de afiliado y publica en tu canal/grupo de Telegram.

## Cómo funciona

1. **Ofertas** (`src/ml_offers.py`): consulta el buscador público de Mercado
   Libre (`GET /sites/MLM/search`) por categoría y se queda con los items que
   tienen `original_price > price` (descuento real, no inventado) por encima
   del umbral configurado. El "ranking de tendencia" combina el % de
   descuento con `sold_quantity`, ambos datos reales que devuelve la API.
   *(No se usa el endpoint oficial `/trends` porque requiere OAuth con
   autorización de tu cuenta de desarrollador; si más adelante quieres
   sumarlo, lo podemos agregar.)*
2. **Link de afiliado** (`src/affiliate.py`): usa Playwright para pegar la
   URL del producto en el generador de links del portal de Afiliados,
   reutilizando una sesión ya iniciada (ver setup abajo).
3. **Telegram** (`src/telegram_bot.py`): publica foto + caption con precio,
   descuento y el link de afiliado usando la Bot API oficial.

## Setup

### 1. Instalar dependencias

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Crear el bot de Telegram

1. Abre Telegram y busca **@BotFather**.
2. Envía `/newbot`, sigue las instrucciones y copia el **token** que te da.
3. Crea tu canal/grupo (o usa uno existente) y agrega el bot como
   administrador (necesita permiso para publicar).
4. Para obtener el `chat_id`:
   - Si el canal es público, puedes usar directamente `@nombre_del_canal`.
   - Si es privado, envía un mensaje cualquiera al canal y visita
     `https://api.telegram.org/bot<TU_TOKEN>/getUpdates` en el navegador;
     busca el campo `"chat":{"id": ...}` en la respuesta.

### 3. Configurar variables de entorno

```bash
cp .env.example .env
```

Llena `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`. Las variables
`ML_AFFILIATE_EMAIL` / `ML_AFFILIATE_PASSWORD` son opcionales — el login se
hace manualmente en el paso siguiente, no se usan credenciales guardadas en
texto plano para el login automático.

### 4. Iniciar sesión una vez en el portal de Afiliados

```bash
python scripts/login_afiliados.py
```

Se abre un navegador real. Inicia sesión con tu cuenta de Mercado Libre
(incluyendo cualquier verificación en dos pasos) y presiona ENTER en la
terminal cuando ya estés dentro de la Central de Afiliados. Esto guarda
`storage_state.json` con tu sesión para que el resto de la automatización no
te vuelva a pedir login. Repite este paso si la sesión expira.

### 5. Ajustar categorías/umbral (opcional)

Edita `config/settings.yaml`: categorías a rastrear, % mínimo de descuento,
cuántas ofertas por categoría y el total a publicar por corrida.

## Ejecutar

```bash
# Ver qué publicaría, sin tocar Telegram ni el portal de afiliados
python -m src.main --dry-run

# Correrlo de verdad
python -m src.main
```

Cada item publicado se registra en `posted_items.json` para no repetirse
dentro de la ventana configurada (`dedupe_window_days`, por defecto 7 días).

## Aviso sobre el generador de links de afiliado

El portal de Afiliados de Mercado Libre es una interfaz web, no una API
pública documentada, así que `src/affiliate.py` usa localizadores basados en
texto/rol (más resistentes a cambios de diseño que clases CSS), pero
Mercado Libre puede cambiar la UI en cualquier momento. Si falla:

```bash
python -m src.affiliate --debug "https://articulo.mercadolibre.com.mx/..."
```

corre con el navegador visible para que puedas inspeccionar la página real y
ajustar los localizadores en `src/affiliate.py`.

## Automatizar la ejecución periódica con GitHub Actions

El workflow `.github/workflows/publish-ofertas.yml` corre cada 6 horas
(`cron: "0 */6 * * *"`, hora UTC) y también se puede lanzar manualmente desde
la pestaña **Actions** del repo (botón "Run workflow").

### Secrets que debes configurar

En el repo de GitHub: **Settings → Secrets and variables → Actions → New
repository secret**.

| Secret | Valor |
|---|---|
| `TELEGRAM_BOT_TOKEN` | El token que te dio @BotFather |
| `TELEGRAM_CHAT_ID` | El chat_id o `@nombre_del_canal` |
| `ML_STORAGE_STATE_B64` | Tu `storage_state.json` codificado en base64 (ver abajo) |

Para generar `ML_STORAGE_STATE_B64`, después de correr
`python scripts/login_afiliados.py` localmente:

```bash
base64 -w0 storage_state.json   # Linux
base64 -i storage_state.json    # macOS
```

Copia el resultado completo como valor del secret.

### Por qué esto necesita mantenimiento manual periódico

La sesión guardada en `storage_state.json` **expira** (Mercado Libre la
invalida por tiempo, cambio de contraseña, o actividad sospechosa). Cuando
eso pase, el workflow empezará a fallar en el paso "Publicar ofertas" con un
error de `AffiliateLinkError`. Para solucionarlo:

1. Corre `python scripts/login_afiliados.py` de nuevo en tu máquina.
2. Regenera el base64 y actualiza el secret `ML_STORAGE_STATE_B64` en GitHub.

No hay forma de evitar este paso manual sin automatizar el login completo
(usuario/contraseña/2FA), lo cual no es recomendable ni estable porque
Mercado Libre puede bloquear logins automatizados detectados como bot.

### Control de duplicados en CI

Cada corrida commitea de vuelta `posted_items.json` al branch (con el
`GITHUB_TOKEN` por defecto, sin secrets extra) para que la siguiente corrida
sepa qué ofertas ya se publicaron.
