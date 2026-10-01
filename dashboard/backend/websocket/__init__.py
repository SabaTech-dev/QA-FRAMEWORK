"""WebSocket connection manager package (F-3, card cbfac469).

Paquete regular (con __init__.py) para que ``import websocket`` resuelva
SIEMPRE al paquete local y no al websocket-client transitivo de site-packages
(colision de nombres verificada en la imagen qa-framework-backend).
"""
