"""Abstract port module"""

from abc import ABC, abstractmethod

class AbstractPort(ABC):
    """Abstract port class."""

    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint

    @abstractmethod
    def fetch_item_price(self, item_name: str) -> dict:
        """Fetch item price based on name."""
        pass
    
    @abstractmethod
    def post_offer(self) -> None:
        """Post offer to that marketplace."""
        pass

    @abstractmethod
    def buy_offer(self) -> None:
        """Buy offer from that marketplace."""
        pass
    
    def get_7_day_price(self) -> dict:
        """Calculate 7 day price of given skin for that marketplace."""
        pass
