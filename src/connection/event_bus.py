from src.utils.logging import Logger


class EventBus:
    """Centralized event system for component communication."""
    _subscribers = {}

    @classmethod
    def subscribe(cls, event_type, callback):
        """
        Register a callback for a specific event type.

        Args:
            event_type (str): Event type to subscribe to
            callback (callable): Function to call when event occurs
        """
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(callback)
        Logger.log_message(f"New subscriber registered for event: {event_type}")

    @classmethod
    def publish(cls, event_type, data):
        """
        Publish an event to all subscribers.

        Args:
            event_type (str): Event type to publish
            data (dict): Event data
        """
        if event_type in cls._subscribers:
            for callback in cls._subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    Logger.log_error(f"Error processing event {event_type}: {e}")