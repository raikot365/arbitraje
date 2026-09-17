import sys
import os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

OFICIAL_ENTITIES = {
    "uala": "Uala", "reba": "Reba", "plus": "Plus", 
    "cocos": "Cocos", "fiwind": "Fiwind", "buenbit": "Buenbit"
}

CRIPTO_EXCHANGES = {
    "fiwind": "Fiwind", "buenbit": "Buenbit", "lemoncashp2p": "Lemon Cash P2P", 
    "pluscrypto": "Plus Crypto", "satoshitango": "SatoshiTango", "lemoncash": "Lemon Cash", 
    "belo": "belo", "bybit": "Bybit", "tiendacrypto": "TiendaCrypto", "binancep2p": "Binance P2P", 
    "cocoscrypto": "Cocos Crypto", "bingxp2p": "BingX P2P", "decrypto": "Decrypto", 
    "bybitp2p": "Bybit P2P", "eldoradop2p": "El Dorado P2P", "nexo": "Nexo"
}

BRIDGE_LIST = {
    "belo": "belo", "binancep2p": "Binance P2P", "fiwind": "Fiwind", 
    "satoshitango": "SatoshiTango", "tiendacrypto": "TiendaCrypto", "decrypto": "Decrypto", "nexo": "Nexo"
}
