import sys
import os

def get_base_path():
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def resource_path(relative_path):
    base_path = get_base_path()
    full_path = os.path.normpath(os.path.join(base_path, relative_path))
    if not os.path.exists(full_path):
        cwd_path = os.path.normpath(os.path.join(os.path.abspath("."), relative_path))
        if os.path.exists(cwd_path):
            return cwd_path
    return full_path

def get_logo_path(name):
    """
    Busca la imagen de logo correspondiente a una entidad o exchange, manejando:
    - Nombres limpios ("Fiwind", "Lemon Cash")
    - Sufijos de categoría o mercado ("Fiwind (O)", "belo (U)", "Dolar MEP (M)")
    - Caracteres con tilde ("á" -> "a")
    - Diferencias de mayúsculas/minúsculas ("Uala" -> "uala.png", "Nexo" -> "nexo.png")
    - Variaciones de nombre ("Binance Spot" -> "Binance P2P.png")
    """
    if not name:
        return None
    
    clean = name.split(" (")[0].strip().replace("á", "a")
    
    # 1. Búsqueda directa
    direct_path = resource_path(os.path.join("logos", f"{clean}.png"))
    if os.path.exists(direct_path):
        return direct_path
        
    # 2. Búsqueda insensible a mayúsculas/minúsculas en el directorio de logos
    logos_dir = resource_path("logos")
    if os.path.isdir(logos_dir):
        target = f"{clean.lower()}.png"
        try:
            for fname in os.listdir(logos_dir):
                if fname.lower() == target:
                    return os.path.join(logos_dir, fname)
        except Exception:
            pass
            
    # 3. Variaciones conocidas (Binance Spot utiliza el logo de Binance)
    if "binance" in clean.lower():
        fallback_binance = resource_path(os.path.join("logos", "Binance P2P.png"))
        if os.path.exists(fallback_binance):
            return fallback_binance

    return None

OFICIAL_ENTITIES = {
    "uala": "Uala", "reba": "Reba", "plus": "Plus", 
    "cocos": "Cocos", "fiwind": "Fiwind", "buenbit": "Buenbit"
}

CRIPTO_EXCHANGES = {
    "fiwind": "Fiwind", "buenbit": "Buenbit", "lemoncashp2p": "Lemon Cash P2P", 
    "pluscrypto": "Plus Crypto", "satoshitango": "SatoshiTango", "lemoncash": "Lemon Cash", 
    "belo": "belo", "bybit": "Bybit", "tiendacrypto": "TiendaCrypto", "binancep2p": "Binance P2P", 
    "cocoscrypto": "Cocos Crypto", "bingxp2p": "BingX P2P", "decrypto": "Decrypto", 
    "bybitp2p": "Bybit P2P", "eldoradop2p": "El Dorado P2P", "nexo": "Nexo",
    "letsbit": "LB Finanzas", "okexp2p": "OKX P2P", "ripio": "Ripio"
}

BRIDGE_LIST = {
    "belo": "belo", "binancep2p": "Binance P2P", "fiwind": "Fiwind", 
    "satoshitango": "SatoshiTango", "tiendacrypto": "TiendaCrypto", "decrypto": "Decrypto", "nexo": "Nexo",
    "letsbit": "LB Finanzas", "okexp2p": "OKX P2P", "ripio": "Ripio"
}
