import os
import csv
from .ports.csfloat_port import CSFloatPort
import json
from dotenv import load_dotenv
from pathlib import Path

def load_config() -> dict:
    with open("src/config/knife_list.json", "r", encoding="utf-8") as f:
        skins = json.load(f)
    return skins

def create_name(weapon, skin, wear):
    return f"★ {weapon} | {skin} ({wear})"

if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("CSFLOAT_API_KEY")
    port = CSFloatPort(api_key=api_key)
    data = load_config()
    print(data) 
    market_names = []
    for weapon_cfg in data["weapons"]:
        weapon = weapon_cfg["weapon"]

        for skin in weapon_cfg["skins"]:
            skin_name = skin["name"]

            for wear in skin["wears"]:
                # Vanilla doesn't use "(Wear)" in market name
                if wear == "Vanilla":
                    market_name = f"★ {weapon} | {skin_name}"
                else:
                    market_name = f"★ {weapon} | {skin_name} ({wear})"

                market_names.append(market_name)

    result_list = []
    for name in market_names:
        try:
            current_price = port.fetch_item_price(item_name=name)
            metrics = port.calculate_sales_metrics(item_name=name)
        except Exception:
            current_price = 0
            metrics = {"7d_avg_price": 0, "7d_volume": 0}
        final_dict = {
            "name": name,
            "current_price": current_price,
            **metrics
        }
        result_list.append(final_dict)
    fieldnames = result_list[0].keys()
    BASE_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = BASE_DIR.parent
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    file_path = data_dir / "output.csv"
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result_list)

