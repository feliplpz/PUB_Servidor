from flask import request
from src.utils.logging import Logger


def register_socket_events(socketio):
    """Registra eventos WebSocket"""

    @socketio.on("connect", namespace="/sensor")
    def socket_connect():
        """Manipula conexão WebSocket"""
        Logger.log_message(f"Cliente WebSocket conectado: {request.sid}")

    @socketio.on("disconnect", namespace="/sensor")
    def socket_disconnect():
        """Manipula desconexão WebSocket"""
        Logger.log_message(f"Cliente WebSocket desconectado: {request.sid}")
