# Publicador de ofertas de Mercado Libre a Telegram (con links de afiliado)

Busca las ofertas con mayor descuento/ventas en categorías de Mercado Libre
México, genera tu link de afiliado y publica en tu canal/grupo de Telegram.

## Cómo funciona

1. **Ofertas** (`src/ml_offers.py`): consulta el buscador de Mercado Libre
   (`GET /sites/MLM/search`) por categoría y se queda con los items que
   tienen `original_price > price` (descuento real, no inventado) por encima
   del umbral configurado. El "ranking de tendencia" combina el % de
   descuento con `sold_quantity`, ambos datos reales que devuelve la API.
   Mercado Libre exige un `access_token` OAuth real para llamar a este
   endpoint (ya no acepta llamadas anónimas), por eso el paso de OAuth abajo.
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

Llena `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` (ver paso 2). El resto
(`ML_CLIENT_ID`, `ML_CLIENT_SECRET`, `ML_REFRESH_TOKEN`) se llenan en el
siguiente paso.

### 4. Crear tu aplicación de Mercado Libre y autorizarla (OAuth)

Mercado Libre exige un token real (`Authorization: Bearer`) para consultar
ofertas — ya no acepta llamadas anónimas a su buscador.

1. Ve a **https://developers.mercadolibre.com.mx/apps** (logueado con tu
   cuenta de Mercado Libre) y crea una aplicación nueva.
2. Nombre y descripción: lo que quieras. En **Redirect URI** pon
   `https://www.google.com.mx` (no necesita ser un servidor tuyo real, solo
   sirve para leer el `code` de la URL a la que te redirige).
3. Al crearla, copia el **Client ID** y el **Client Secret**.
4. Corre el script de autorización (con el entorno virtual activo):
   ```bash
   python scripts/ml_oauth_setup.py
   ```
5. Te pide el Client ID/Secret, te da una URL para abrir en el navegador,
   inicias sesión y aceptas los permisos. Mercado Libre te redirige a algo
   como `https://www.google.com.mx/?code=TG-XXXXXXXX...` — copia solo el
   valor de `code` (lo que sigue a `code=`) y pégalo cuando el script lo pida.
6. El script imprime `ML_CLIENT_ID`, `ML_CLIENT_SECRET` y `ML_REFRESH_TOKEN` —
   pégalos en tu archivo `.env`.

**Importante**: el `refresh_token` de Mercado Libre es de un solo uso. Cada
vez que `src/main.py` lo usa para pedir un `access_token` nuevo, Mercado
Libre le entrega un `refresh_token` distinto y el anterior queda inválido.
Corriendo localmente, si ves un aviso de "el refresh_token cambió", copia el
valor nuevo a tu `.env`. En GitHub Actions esto se resuelve solo (ver abajo).

### 5. Iniciar sesión una vez en el portal de Afiliados

```bash
python scripts/login_afiliados.py
```

Se abre un navegador real. Inicia sesión con tu cuenta de Mercado Libre
(incluyendo cualquier verificación en dos pasos) y presiona ENTER en la
terminal cuando ya estés dentro de la Central de Afiliados. Esto guarda
`storage_state.json` con tu sesión para que el resto de la automatización no
te vuelva a pedir login. Repite este paso si la sesión expira.

### 6. Ajustar categorías/umbral (opcional)

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
| `ML_CLIENT_ID` | El Client ID de tu app de Mercado Libre |
| `ML_CLIENT_SECRET` | El Client Secret de tu app de Mercado Libre |
| `ML_REFRESH_TOKEN` | El refresh_token que te dio `scripts/ml_oauth_setup.py` |
| `GH_PAT_SECRETS` | Personal Access Token de GitHub (ver abajo) |

Para generar `ML_STORAGE_STATE_B64`, después de correr
`python scripts/login_afiliados.py` localmente:

```bash
base64 -w0 storage_state.json   # Linux
base64 -i storage_state.json    # macOS
```

Copia el resultado completo como valor del secret.

#### Crear el `GH_PAT_SECRETS`

El `refresh_token` de Mercado Libre es de un solo uso (ver paso 4 del setup):
cada corrida del workflow necesita guardar el `refresh_token` nuevo que le
entrega ML. Como este repo es **público**, ese valor no puede vivir en el
código — el workflow lo actualiza directamente como GitHub Secret usando la
API de GitHub, y para eso necesita un token con permiso de escritura sobre
secrets:

1. Ve a **github.com/settings/personal-access-tokens/new** (fine-grained
   token, en tu cuenta, no en el repo).
2. **Repository access**: selecciona solo `jjesusbmena/SIC`.
3. **Permissions → Repository permissions → Secrets**: ponlo en **Read and
   write**.
4. Genera el token y cópialo — solo se muestra una vez.
5. Guárdalo como el secret `GH_PAT_SECRETS` (paso anterior).

Este PAT no puede leer código ni hacer nada fuera de gestionar secrets de ese
repo específico, según el alcance que configuraste.

### Qué se rota solo y qué necesita mantenimiento manual

- **`ML_REFRESH_TOKEN`**: se rota solo en cada corrida (vía `GH_PAT_SECRETS`),
  no necesitas hacer nada mientras el workflow corra al menos una vez cada
  pocos días. Si el workflow está desactivado mucho tiempo, revisa el aviso
  de vigencia del refresh_token en el paso 4 del setup.
- **`storage_state.json` / `ML_STORAGE_STATE_B64`**: la sesión del portal de
  Afiliados **sí expira** (Mercado Libre la invalida por tiempo, cambio de
  contraseña, o actividad sospechosa). Cuando eso pase, el workflow empezará
  a fallar en el paso "Publicar ofertas" con un error de `AffiliateLinkError`.
  Para solucionarlo:
  1. Corre `python scripts/login_afiliados.py` de nuevo en tu máquina.
  2. Regenera el base64 y actualiza el secret `ML_STORAGE_STATE_B64` en GitHub.

No hay forma de evitar este paso manual sin automatizar el login completo
(usuario/contraseña/2FA), lo cual no es recomendable ni estable porque
Mercado Libre puede bloquear logins automatizados detectados como bot.

### Control de duplicados en CI

Cada corrida commitea de vuelta `posted_items.json` al branch (con el
`GITHUB_TOKEN` por defecto, sin secrets extra) para que la siguiente corrida
sepa qué ofertas ya se publicaron.
