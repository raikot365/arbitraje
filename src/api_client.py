import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.config import OFICIAL_ENTITIES, CRIPTO_EXCHANGES

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self):
        self.session = requests.Session()
    
    def get_initial_tasas(self):
        tasas = {"Ninguna (0%)": 0.0}
        try:
            r1 = self.session.get("https://rendimientos.co/api/config", timeout=10)
            r1.raise_for_status()
            for item in r1.json().get("garantizados", []):
                name = item.get("nombre", "")
                clean = name.lower().replace("á", "a")
                tna = float(item.get("tna", 0))
                if any(x in clean for x in ["uala", "naranja", "fiwind"]):
                    tasas[f"{name} ({tna}%)"] = tna
                    
            r2 = self.session.get("https://rendimientos.co/api/fci", timeout=10)
            r2.raise_for_status()
            for item in r2.json().get("data", []):
                name = item.get("nombre", "")
                tna = float(item.get("tna", 0))
                if "cocos" in name.lower(): tasas[f"Cocos FCI ({tna}%)"] = tna
                elif "mercado fondo" in name.lower(): tasas[f"Mercado Pago ({tna}%)"] = tna
        except requests.RequestException as e:
            logger.error(f"Error fetching tasas: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing tasas: {e}")
        return tasas

    def fetch_fees(self):
        try:
            r = self.session.get("https://criptoya.com/api/fees", timeout=10)
            r.raise_for_status()
            data = r.json()
            fees = {}
            for ex, assets in data.items():
                fees[ex] = {}
                for coin, networks in assets.items():
                    try:
                        min_fee = min(net.get("withdraw", 0) for net in networks.values())
                        fees[ex][coin] = min_fee
                    except:
                        pass
            return fees
        except ValueError as e:
            logger.error(f"Invalid JSON fetching fees: {e}")
        except requests.RequestException as e:
            logger.error(f"Error fetching fees: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing fees: {e}")
        return {}

    def fetch_mep_full(self):
        try:
            r = self.session.get("https://criptoya.com/api/dolar", timeout=10)
            r.raise_for_status()
            data = r.json()
            return {"ci": float(data["mep"]["al30"]["ci"]["price"]), "24hs": float(data["mep"]["al30"]["24hs"]["price"])}
        except ValueError as e:
            logger.error(f"Invalid JSON fetching mep: {e}")
        except requests.RequestException as e:
            logger.error(f"Error fetching mep: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing mep: {e}")
        return None

    def fetch_parities(self, active_bridges):
        p = {}
        try:
            r = self.session.get("https://criptoya.com/api/usdt/usd/0.1", timeout=10)
            r.raise_for_status()
            data = r.json()
            for ex in active_bridges:
                if ex in data:
                    p[ex] = (ex, float(data[ex].get("totalAsk", 0)), float(data[ex].get("totalBid", 0)))
                else:
                    p[ex] = (ex, None, None)
        except ValueError as e:
            logger.error(f"Invalid JSON fetching parities: {e}")
        except requests.RequestException as e:
            logger.error(f"Error fetching parities: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing parities: {e}")
        return p

    def fetch_oficial_api(self, active_keys):
        try:
            r = self.session.get("https://api.comparadolar.ar/usd", timeout=15)
            r.raise_for_status()
            p = {}
            for item in r.json():
                slug = item.get("name", "").lower().replace(" ", "").replace("á", "a")
                if f"oficial_{slug}" in active_keys:
                    pretty = OFICIAL_ENTITIES.get(slug, item.get("prettyName", slug).replace("á", "a"))
                    p[pretty] = {"ask": float(item.get("ask", 0)), "bid": float(item.get("bid", 0))}
            return p
        except ValueError as e:
            logger.error(f"Invalid JSON fetching oficial: {e}")
        except requests.RequestException as e:
            logger.error(f"Error fetching oficial: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing oficial: {e}")
        return {}

    def fetch_coin_criptoya(self, active_ids, coin="usdt"):
        p = {}
        try:
            r = self.session.get(f"https://criptoya.com/api/{coin}/ars/0.1", timeout=10)
            r.raise_for_status()
            data = r.json()
            for eid, details in data.items():
                if eid in active_ids:
                    name = CRIPTO_EXCHANGES.get(eid, eid.capitalize())
                    p[name] = {"ask": float(details["totalAsk"]), "bid": float(details["totalBid"])}
        except ValueError as e:
            logger.error(f"Invalid JSON fetching {coin}: {e}")
        except requests.RequestException as e:
            logger.error(f"Error fetching {coin}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing {coin}: {e}")
        return p

    def fetch_usdt_criptoya(self, active_ids):
        return self.fetch_coin_criptoya(active_ids, "usdt")

    def fetch_binance_tickers(self):
        try:
            r = self.session.get('https://api.binance.com/api/v3/ticker/bookTicker', timeout=10)
            r.raise_for_status()
            data = r.json()
            tickers = {}
            for t in data:
                tickers[t["symbol"]] = {"ask": float(t["askPrice"]), "bid": float(t["bidPrice"])}
            return tickers
        except Exception as e:
            logger.error(f"Error fetching Binance tickers: {e}")
        return {}
