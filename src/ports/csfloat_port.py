from .abstract_port import AbstractPort
import requests
from typing import Any
import os
from dotenv import load_dotenv
from dataclasses import dataclass

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

@dataclass
class CSFloatListing:
    listing_id: str
    price_cents: int
    market_hash_name: str
    url: None | str
    raw: dict | None = None


class CSFloatPort(AbstractPort):
    """
    CSFloat implementation.

    endpoint example: "https://csfloat.com/api/v1"
    """

    def __init__(self, api_key: str, endpoint: str = "https://csfloat.com/api/v1", timeout_s: int = 20):
        super().__init__(api_key=api_key, endpoint=endpoint.rstrip("/"))
        self.timeout_s = timeout_s
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": self.api_key,
                "Accept": "application/json",
                "User-Agent": "cs2-skin-trader/1.0",
            }
        )

    def _url(self, path: str) -> str:
        return f"{self.endpoint}{path}"

    def _raise_for_api_error(self, response: requests.Response) -> None:
        try:
            payload = response.json()
        except Exception:
            payload = None

        if not response.ok:
            msg = f"CSFloat API error: {response.status_code}"
            if isinstance(payload, dict):
                # common patterns: {"error": "..."} or {"message": "..."}
                msg_detail = payload.get("error") or payload.get("message") or payload
                msg = f"{msg} - {msg_detail}"
            raise RuntimeError(msg)

    def _parse_listings(self, payload: dict) -> list[CSFloatListing]:
        listings: list[CSFloatListing] = []
        for obj in payload.get("data", []) or []:
            listing_id = str(obj.get("id") or obj.get("listing_id") or "")
            price_cents = int(obj.get("price") or 0)
            item = obj.get("item") or {}
            mhn = str(item.get("market_hash_name") or "")
            url = obj.get("url")
            listings.append(
                CSFloatListing(
                    listing_id=listing_id,
                    price_cents=price_cents,
                    market_hash_name=mhn,
                    url=url,
                    raw=obj,
                )
            )
        return listings

    def fetch_item_price(self, item_name: str) -> dict:
        """
        Fetch current listing prices for an item and return the cheapest listing.

        CSFloat uses exact Steam market_hash_name naming, including wear:
        e.g. "AK-47 | Redline (Field-Tested)"

        Returns:
        {
          "market": "csfloat",
          "market_hash_name": "...",
          "best_ask_cents": 12345,
          "best_listing_id": "...",
          "listings_count": 10,
          "best_listing": {...raw listing...}
        }
        """
        params = {
            "market_hash_name": item_name,
            "limit": 1,
            "sort_by": "lowest_price",
            "type": "buy_now"
        }
        response = self._session.get(self._url("/listings"), params=params, timeout=self.timeout_s)
        self._raise_for_api_error(response)
        float_data = response.json().get("data", [])
        final = float_data[0].get("price", 0) / 100
        return final

    def post_offer(self, asset_id: int | None = None, price_cents: int | None = None, sale_type: str = "buy_now") -> None:
        """
        Create a CSFloat listing.

        Public docs show:
        POST /listings
        Body: {"asset_id": <int>, "type": "buy_now", "price": <int cents>}

        Args:
          asset_id: Steam asset id of the item in your inventory.
          price_cents: Listing price in cents.
          sale_type: Usually "buy_now".
        """
        if asset_id is None or price_cents is None:
            raise ValueError("post_offer requires asset_id and price_cents")

        body = {"asset_id": int(asset_id), "type": str(sale_type), "price": int(price_cents)}
        response = self._session.post(self._url("/listings"), json=body, timeout=self.timeout_s)
        self._raise_for_api_error(response)
        # If you want to return listing ID, change return type to dict and return response.json()

    def buy_offer(self, listing_id: str | None, **kwargs: Any) -> None:
        """
        Buying via CSFloat is not clearly documented as a public REST endpoint.

        Some marketplaces handle purchases via web checkout / trade flows that
        may not be exposed publicly in API docs.

        This method raises by default. If you obtain official documentation
        or partner endpoints, implement them here.

        Args:
          listing_id: The listing you intend to buy (if supported).
        """
        raise NotImplementedError(
            "CSFloat 'buy listing' is not exposed in the public API docs. "
            "Implement this only if you have official/partner endpoint access."
        )

    def _history_sales(
        self,
        item_name: str,
        paint_index: int | None = None,
        **extra_params: Any,
    ) -> list[dict]:
        """
        Fetch sales history objects from:
        /history/<market_hash_name>/graph
        """
        if not item_name:
            raise ValueError("_history_sales requires item_name")

        encoded_name = quote(item_name, safe="")
        params: dict[str, Any] = {**extra_params}
        if paint_index is not None:
            params["paint_index"] = int(paint_index)

        response = self._session.get(
            self._url(f"/history/{encoded_name}/graph"),
            params=params,
            timeout=self.timeout_s,
        )
        self._raise_for_api_error(response)
        print("HISTORY RESPONSE")
        return response.json()

    def get_7_day_price(self, item_name: str | None = None, paint_index: int | None = None) -> dict:
        """
        Compute 7-day average sale price (in cents) using CSFloat sales history:
        GET /history/<market_hash_name>/sales?paint_index=...

        Returns:
        {
          "market": "csfloat",
          "market_hash_name": "...",
          "paint_index": 415,
          "avg_7d_cents": 204500,
          "median_7d_cents": 203900,
          "min_7d_cents": ...,
          "max_7d_cents": ...,
          "sales_count_7d": 37,
          "source": "csfloat_history_sales",
        }
        """
        if not item_name:
            raise ValueError("get_7_day_price requires item_name for CSFloat")

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=7)

        sales_data = self._history_sales(item_name=item_name, paint_index=paint_index, limit=500)

        for sales in sales_data:
            print(sales)
            break
    
if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("CSFLOAT_API_KEY")
    port = CSFloatPort(api_key=api_key)
    print(port.fetch_item_price(item_name="AK-47 | Slate (Field-Tested)"))
    print(port.get_7_day_price(item_name="AK-47 | Slate (Field-Tested)"))