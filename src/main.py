import requests
import os
import time
import logging
from dotenv import load_dotenv, find_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CSMarketAnalyzer:
    def __init__(self):
        load_dotenv(find_dotenv())
        self.csfloat_api_key = os.getenv("CSFLOAT_API_KEY")
        
        self.steam_api_url = "https://steamcommunity.com/market/listings/730/{}/render/"
        self.csfloat_base_url = "https://csfloat.com/api/v1/listings"
        
        self.STEAM_FEE = 0.15
        self.FLOAT_FEE = 0.02

    def get_steam_current_price(self, item_name):
        """Fetches current lowest Steam market price without authentication."""
        try:
            url = self.steam_api_url.format(item_name)
            params = {
                "start": 0,
                "count": 10,
                "currency": 1,  # USD
                "language": "english"
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            
            if resp.status_code == 429:
                logger.warning("Steam Rate Limit hit. Waiting 5 seconds...")
                time.sleep(5)
                return 0.0
            
            if resp.status_code != 200:
                logger.error(f"Steam API returned status {resp.status_code}")
                return 0.0

            data = resp.json()
            
            if not data.get("success"):
                logger.warning(f"Steam API unsuccessful for {item_name}")
                return 0.0
            
            # Try multiple methods to get the price
            
            # Method 1: Check lowest_price field
            lowest_price = data.get("lowest_price")
            if lowest_price:
                price_str = lowest_price.replace("$", "").replace(",", "")
                price = float(price_str)
                logger.info(f"{item_name}: Steam lowest price: ${price:.2f}")
                return price
            
            # Method 2: Parse from listinginfo (actual sell orders)
            listinginfo = data.get("listinginfo", {})
            if listinginfo:
                prices = []
                for listing_id, listing in listinginfo.items():
                    # Converted price is in cents
                    converted_price = listing.get("converted_price", 0)
                    if converted_price > 0:
                        prices.append(converted_price / 100)
                
                if prices:
                    min_price = min(prices)
                    logger.info(f"{item_name}: Steam lowest price (from listings): ${min_price:.2f}")
                    return min_price
            
            # Method 3: Check median sale price as fallback
            median_price = data.get("median_sale_price")
            if median_price:
                price_str = median_price.replace("$", "").replace(",", "")
                price = float(price_str)
                logger.info(f"{item_name}: Steam median price (fallback): ${price:.2f}")
                return price
            
            logger.warning(f"No price data found for {item_name}")
            return 0.0
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching Steam data: {e}")
            return 0.0
        except Exception as e:
            logger.error(f"Unexpected error fetching Steam price for {item_name}: {e}")
            return 0.0

    def get_market_data(self, item_name):
        """Fetches market data from both Steam and CSFloat."""
        data = {"name": item_name, "steam_price": 0.0, "float": 0.0}

        # 1. Fetch Steam Current Lowest Price
        logger.info(f"Fetching Steam price for {item_name}...")
        data["steam_price"] = self.get_steam_current_price(item_name)
        time.sleep(2)  # Avoid rate limiting

        # 2. Fetch CSFloat Lowest Price
        logger.info(f"Fetching CSFloat price for {item_name}...")
        headers = {"Authorization": self.csfloat_api_key} if self.csfloat_api_key else {}
        params = {
            "market_hash_name": item_name,
            "limit": 1,
            "sort_by": "lowest_price",
            "type": "buy_now"
        }
        
        try:
            resp = requests.get(self.csfloat_base_url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                float_data = resp.json().get("data", [])
                if float_data:
                    # CSFloat prices are in cents
                    data["float"] = float_data[0].get("price", 0) / 100
                    logger.info(f"CSFloat price: ${data['float']:.2f}")
                else:
                    logger.warning(f"No listings found on CSFloat for {item_name}")
            else:
                logger.error(f"CSFloat API returned status {resp.status_code}")
        except Exception as e:
            logger.error(f"Error fetching CSFloat data: {e}")

        return data

    def calculate_margins(self, data):
        """Calculate profit margins for both arbitrage directions."""
        s_price = data["steam_price"]
        f_price = data["float"]

        if s_price <= 0 or f_price <= 0:
            return "N/A", "N/A"

        # Steam to Float: Buy on Steam (after 15% fee), sell on Float
        s_to_f = ((s_price * (1 - self.STEAM_FEE)) - f_price) / f_price * 100
        
        # Float to Steam: Buy on Float (after 2% fee), sell on Steam
        f_to_s = ((f_price * (1 - self.FLOAT_FEE)) - s_price) / s_price * 100
        
        return f"{s_to_f:+.2f}%", f"{f_to_s:+.2f}%"

    def run_analysis(self, items):
        """Run analysis on a list of items."""
        print("\n" + "="*80)
        print("CS:GO Market Analysis - Steam vs CSFloat")
        print("="*80)
        
        header = f"{'Item Name':<40} | {'Steam':<10} | {'Float':<10} | {'S->F Margin':<12}"
        print(header)
        print("-" * 80)

        for item in items:
            market_data = self.get_market_data(item)
            s_to_f, f_to_s = self.calculate_margins(market_data)
            
            item_display = item[:40]
            print(f"{item_display:<40} | ${market_data['steam_price']:<9.2f} | ${market_data['float']:<9.2f} | {s_to_f:<12}")
            
            time.sleep(1)  # Rate limiting
        
        print("="*80 + "\n")

if __name__ == "__main__":
    items_to_analyze = [
        "AK-47 | Slate (Field-Tested)",
        "Kilowatt Case"
    ]
    
    analyzer = CSMarketAnalyzer()
    analyzer.run_analysis(items_to_analyze)