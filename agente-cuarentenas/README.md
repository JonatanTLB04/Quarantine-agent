# Agente de cuarentenas (The Launch Box)

Cada 15 minutos busca en Autotask los tickets "Gmail Admin Quarantine Alert" de cada cliente,
revisa la cuarentena de Google Admin, decide Allow / Deny / Dudoso con Claude, aplica la acción
y cierra los tickets con una nota. El dashboard muestra todo lo que hizo.

## Variables en Railway
- AUTOTASK_USERNAME, AUTOTASK_SECRET, AUTOTASK_INTEGRATION_CODE
- GOOGLE_HS_EMAIL, GOOGLE_HS_PASSWORD
- GOOGLE_HS_TOTP_SECRET (opcional, solo si la cuenta tiene verificación en dos pasos)
- ANTHROPIC_API_KEY
- DATABASE_URL = ${{Postgres.DATABASE_URL}}
- DASHBOARD_USER, DASHBOARD_PASSWORD
- MODO = observacion   (cambiar a "real" cuando ya confíes en sus decisiones)

Opcionales: INTERVAL_MIN (15), CLAUDE_MODEL, GOOGLE_ALLOW_LABEL (Allow), GOOGLE_DENY_LABEL (Deny),
AUTOTASK_NOTE_TYPE (1), HEADLESS (true).

## Volumen
Monta un volumen en /data para guardar la sesión de Google y las capturas de depuración.

## Depuración
- /debug/hs-lista.png: lo que ve el agente en la cuarentena
- /debug/hs-login-fallo.png: si no pudo iniciar sesión
- /debug/hs-accion-fallo.png: si no pudo dar Allow o Deny
