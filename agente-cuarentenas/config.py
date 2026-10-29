"""Clientes que revisa el agente.

Para agregar DX Foundation después, copia el bloque de Hyperscayle,
cambia los datos y agrega sus variables GOOGLE_DX_* en Railway.
"""
CLIENTS = [
    {
        "key": "hs",                      # identificador corto
        "name": "Hyperscayle",            # nombre que se ve en el dashboard
        "to": "admin@hyperscayle.com",    # el "To:" que aparece en los tickets de Autotask
        "env": "HS",                      # prefijo de sus variables: GOOGLE_HS_EMAIL, etc.
    },
]
