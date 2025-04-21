from src.utils.logging import Logger


class EventBus:
    """Sistema de eventos centralizado para comunicação entre componentes"""
    _subscribers = {}
    
    @classmethod
    def subscribe(cls, event_type, callback):
        """
        Registra um callback para um tipo específico de evento
        
        Args:
            event_type (str): Tipo de evento para se inscrever
            callback (callable): Função a ser chamada quando o evento ocorrer
        """
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(callback)
        Logger.log_message(f"Novo assinante registrado para evento: {event_type}")
    
    @classmethod
    def publish(cls, event_type, data):
        """
        Publica um evento para todos os assinantes
        
        Args:
            event_type (str): Tipo de evento a ser publicado
            data (dict): Dados do evento
        """
        if event_type in cls._subscribers:
            for callback in cls._subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    Logger.log_message(f"Erro ao processar evento {event_type}: {e}")