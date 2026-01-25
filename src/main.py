import requests
import os
import time
import logging
import datetime
from dotenv import load_dotenv, find_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CSMarketAnalyzer:
    def __init__(self):
        load_dotenv(find_dotenv())
        self.csfloat_api_key = os.getenv("CSFLOAT_API_KEY")
        # REQUIRED: You must add STEAM_COOKIE to your .env file
        # Format: "steamLoginSecure=7656119xxxxxx%7C%7Cxxxxxx"
        self.steam_cookie = os.getenv("STEAM_COOKIE")
        
        self.history_url = "https://steamcommunity.com/market/pricehistory/"
        self.csfloat_base_url = "https://csfloat.com/api/v1/listings"
        
        self.STEAM_FEE = 0.15
        self.FLOAT_FEE = 0.02

    def get_steam_7d_avg(self, item_name):
        """Fetches price history and calculates 7-day average."""
        if not self.steam_cookie:
            logger.error("No Steam Cookie found in .env. Cannot fetch history.")
            return 0.0

        params = {"appid": 730, "market_hash_name": item_name}
        headers = {"Cookie": self.steam_cookie}
        
        try:
            resp = requests.get(self.history_url, params=params, headers=headers)
            if resp.status_code == 200:
                history = resp.json()
                if not history.get("success") or not history.get("prices"):
                    return 0.0

                # Steam returns prices in format: ["Jan 14 2026 01: +0", 1.55, "240"]
                # index 0: Date, index 1: Median Price, index 2: Volume
                raw_prices = history["prices"]
                seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
                
                recent_prices = []
                for entry in raw_prices:
                    # Clean the date string: "Jan 14 2026 01: +0" -> "Jan 14 2026"
                    date_str = " ".join(entry[0].split(" ")[:3])
                    entry_date = datetime.datetime.strptime(date_str, "%b %d %Y")
                    
                    if entry_date >= seven_days_ago:
                        recent_prices.append(entry[1])

                if recent_prices:
                    return sum(recent_prices) / len(recent_prices)
            
            elif resp.status_code == 429:
                logger.warning("Steam Rate Limit hit.")
        except Exception as e:
            logger.error(f"Error calculating 7d average: {e}")
        
        return 0.0

    def get_market_data(self, item_name):
        data = {"name": item_name, "steam_avg": 0.0, "float": 0.0}

        # 1. Fetch Steam 7-Day Avg
        data["steam_avg"] = self.get_steam_7d_avg(item_name)
        time.sleep(2) # Necessary to avoid 429

        # 2. Fetch CSFloat Lowest Price
        headers = {"Authorization": self.csfloat_api_key} if self.csfloat_api_key else {}
        f_params = {"market_hash_name": item_name, "limit": 1, "sort_by": "lowest_price", "type": "buy_now"}
        try:
            resp = requests.get(self.csfloat_base_url, params=f_params, headers=headers)
            if resp.status_code == 200:
                f_data = resp.json().get("data", [])
                if f_data:
                    data["float"] = f_data[0].get("price", 0) / 100
        except Exception as e:
            logger.error(f"Float Error: {e}")

        return data

    def calculate_margins(self, data):
        s_price = data["steam_avg"]
        f_price = data["float"]

        if s_price <= 0 or f_price <= 0:
            return "N/A", "N/A"

        s_to_f = ((s_price * (1 - self.STEAM_FEE)) - f_price) / f_price * 100
        f_to_s = ((f_price * (1 - self.FLOAT_FEE)) - s_price) / s_price * 100
        return f"{s_to_f:+.2f}%", f"{f_to_s:+.2f}%"

    def run_analysis(self, items):
        header = f"{'Item Name':<35} | {'Steam 7d':<8} | {'Float':<8} | {'S->F Margin':<12}"
        print(header)
        print("-" * len(header))

        for item in items:
            market_data = self.get_market_data(item)
            s_to_f, _ = self.calculate_margins(market_data)
            print(f"{item[:35]:<35} | ${market_data['steam_avg']:<7.2f} | ${market_data['float']:<7.2f} | {s_to_f:<12}")
            time.sleep(1)

if __name__ == "__main__":
    items_to_analyze = ["AK-47 | Slate (Field-Tested)", "Kilowatt Case"]
    analyzer = CSMarketAnalyzer()
    analyzer.run_analysis(items_to_analyze)