import os
import sys
import time
import threading
import requests
import json
from datetime import datetime
from itertools import product, permutations
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

import customtkinter as ctk
from PIL import Image

# --- Configuración de Rutas para PyInstaller ---
def resource_path(relative_path):
    """ Obtiene la ruta absoluta para recursos, compatible con PyInstaller """
    try:
        # PyInstaller crea una carpeta temporal y guarda la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Configuración Visual ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ArbitrageBotGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        load_dotenv()
        self.TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
        self.CHAT_ID = os.getenv("CHAT_ID")
        self.is_running = False
        self._alertas_enviadas = {}

        # 1. Iniciar maximizada
        self.after(0, lambda: self.wm_state('zoomed'))
        self.title("Arbitrage Monitor Pro v1.0.1")
        
        # --- AGREGÁ ESTA LÍNEA PARA EL ICONO DE VENTANA ---
        try:
            # Usamos resource_path para que funcione dentro del .exe
            self.iconbitmap(resource_path("app_icon.ico"))
        except:
            pass

        # Mapeos para nombres y logos
        self.oficial_entities = {
            "uala": "Uala", "reba": "Reba", "plus": "Plus", 
            "cocos": "Cocos", "fiwind": "Fiwind", "buenbit": "Buenbit"
        }
        self.cripto_exchanges = {
            "fiwind": "Fiwind", "buenbit": "Buenbit", "lemoncashp2p": "Lemon Cash P2P",
            "pluscrypto": "Plus Crypto", "satoshitango": "SatoshiTango", "lemoncash": "Lemon Cash",
            "belo": "belo", "bybit": "Bybit", "tiendacrypto": "TiendaCrypto",
            "binancep2p": "Binance P2P", "cocoscrypto": "Cocos Crypto", "bingxp2p": "BingX P2P",
            "decrypto": "Decrypto", "bybitp2p": "Bybit P2P", "eldoradop2p": "El Dorado P2P"
        }
        self.bridge_list = {
            "belo": "belo", "binancep2p": "Binance P2P", "fiwind": "Fiwind", 
            "satoshitango": "SatoshiTango", "tiendacrypto": "TiendaCrypto", "decrypto": "Decrypto"
        }

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.setup_sidebar()
        self.setup_main_area()

    # --- SIDEBAR ---
    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0); self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="CONFIGURACIÓN", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)
        
        self.threshold_entry = self.create_input_with_presets("Umbral de Alerta (%)", "1.0", [("1%", 1.0), ("2%", 2.0), ("3%", 3.0), ("5%", 5.0)])
        self.interval_entry = self.create_input_with_presets("Intervalo Consulta (seg)", "30", [("30s", 30), ("1m", 60), ("3m", 180), ("5m", 300)])
        self.cooldown_entry = self.create_input_with_presets("Cooldown Alertas (seg)", "300", [("5m", 300), ("10m", 600), ("15m", 900), ("30m", 1800)])
        
        self.only_best_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self.sidebar, text="Telegram: Solo la más alta", variable=self.only_best_var, font=ctk.CTkFont(size=12)).pack(pady=10, padx=20, anchor="w")

        ctk.CTkLabel(self.sidebar, text="Exchanges / Entidades", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        self.ex_scroll = ctk.CTkScrollableFrame(self.sidebar, height=250, fg_color="transparent"); self.ex_scroll.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.exchange_vars = {}
        self.bridge_vars = {} 

        ctk.CTkLabel(self.ex_scroll, text="--- CRIPTO ---", font=ctk.CTkFont(size=10, slant="italic")).pack(pady=(5,0))
        self.create_bulk_buttons(self.ex_scroll, "cripto")
        for eid, name in self.cripto_exchanges.items(): self.create_check(eid, name, self.exchange_vars)
        
        ctk.CTkLabel(self.ex_scroll, text="--- OFICIAL ---", font=ctk.CTkFont(size=10, slant="italic")).pack(pady=(15,0))
        self.create_bulk_buttons(self.ex_scroll, "oficial")
        for eid, name in self.oficial_entities.items(): self.create_check(f"oficial_{eid}", name, self.exchange_vars)

        ctk.CTkLabel(self.ex_scroll, text="--- PUENTE (USD) ---", font=ctk.CTkFont(size=10, slant="italic"), text_color="#3b8ed0").pack(pady=(15,0))
        self.create_bulk_buttons(self.ex_scroll, "bridge")
        for eid, name in self.bridge_list.items(): self.create_check(eid, name, self.bridge_vars)

        self.btn_toggle = ctk.CTkButton(self.sidebar, text="INICIAR BOT", fg_color="#28a745", height=45, command=self.toggle_bot, font=ctk.CTkFont(weight="bold"))
        self.btn_toggle.pack(pady=20, padx=20, fill="x")

    def create_bulk_buttons(self, parent, group):
        f = ctk.CTkFrame(parent, fg_color="transparent"); f.pack(fill="x", pady=2)
        ctk.CTkButton(f, text="Todos", width=60, height=18, font=ctk.CTkFont(size=9), fg_color="#333", command=lambda: self.toggle_group_vars(group, True)).pack(side="left", padx=(10, 5))
        ctk.CTkButton(f, text="Ninguno", width=60, height=18, font=ctk.CTkFont(size=9), fg_color="#333", command=lambda: self.toggle_group_vars(group, False)).pack(side="left")

    def toggle_group_vars(self, group, state):
        if group == "bridge":
            for v in self.bridge_vars.values(): v.set(state)
        else:
            for k, v in self.exchange_vars.items():
                if (group == "oficial" and k.startswith("oficial_")) or (group == "cripto" and not k.startswith("oficial_")): v.set(state)

    def create_input_with_presets(self, label, default, presets):
        c = ctk.CTkFrame(self.sidebar, fg_color="transparent"); c.pack(fill="x", pady=5)
        ctk.CTkLabel(c, text=label).pack()
        e = ctk.CTkEntry(c, justify="center", width=120); e.insert(0, default); e.pack(pady=2)
        p = ctk.CTkFrame(c, fg_color="transparent"); p.pack()
        for t, v in presets: ctk.CTkButton(p, text=t, width=42, height=22, font=ctk.CTkFont(size=10), fg_color="#333", command=lambda val=v, ent=e: (ent.delete(0, "end"), ent.insert(0, str(val)))).pack(side="left", padx=2)
        return e

    def create_check(self, internal_id, name, target_dict):
        f = ctk.CTkFrame(self.ex_scroll, fg_color="transparent"); f.pack(fill="x", pady=1)
        var = ctk.BooleanVar(value=True); target_dict[internal_id] = var
        try:
            img_path = resource_path(f"logos/{name}.png")
            img = ctk.CTkImage(Image.open(img_path), size=(20, 20))
            ctk.CTkLabel(f, image=img, text="").pack(side="left", padx=5)
        except: pass
        ctk.CTkCheckBox(f, text=name, variable=var, font=ctk.CTkFont(size=11)).pack(side="left")

    def setup_main_area(self):
        self.tabview = ctk.CTkTabview(self, fg_color="#0a0a0a")
        self.tabview.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.tab_usdt = self.tabview.add("USDT (CriptoYa)")
        self.tab_oficial = self.tabview.add("OFICIAL (ComparaDolar)")
        self.tab_mix = self.tabview.add("OFICIAL vs USDT")
        self.tab_mep_usdt = self.tabview.add("MEP vs USDT")
        self.tab_oficial_mep = self.tabview.add("OFICIAL vs MEP")
        
        self.cont_usdt = ctk.CTkScrollableFrame(self.tab_usdt, fg_color="transparent"); self.cont_usdt.pack(fill="both", expand=True)
        self.cont_oficial = ctk.CTkScrollableFrame(self.tab_oficial, fg_color="transparent"); self.cont_oficial.pack(fill="both", expand=True)
        self.cont_mix = ctk.CTkScrollableFrame(self.tab_mix, fg_color="transparent"); self.cont_mix.pack(fill="both", expand=True)
        self.cont_mep_usdt = ctk.CTkScrollableFrame(self.tab_mep_usdt, fg_color="transparent"); self.cont_mep_usdt.pack(fill="both", expand=True)
        self.cont_oficial_mep = ctk.CTkScrollableFrame(self.tab_oficial_mep, fg_color="transparent"); self.cont_oficial_mep.pack(fill="both", expand=True)

    # --- DATA ENGINES ---

    def fetch_mep_full(self):
        try:
            r = requests.get("https://criptoya.com/api/dolar", timeout=5).json()
            return {"ci": float(r["mep"]["al30"]["ci"]["price"]), "24hs": float(r["mep"]["al30"]["24hs"]["price"])}
        except: return None

    def fetch_parity(self, ex):
        try:
            r = requests.get(f"https://criptoya.com/api/{ex}/usdt/usd/0.1", timeout=5).json()
            return ex, float(r.get("totalAsk", 0)), float(r.get("totalBid", 0))
        except: return ex, None, None

    def fetch_oficial_api(self, active_keys):
        try:
            r = requests.get("https://api.comparadolar.ar/usd", timeout=10)
            if r.status_code != 200: return {}
            precios = {}
            for item in r.json():
                slug = item.get("name", "").lower().replace(" ", "").replace("á", "a")
                if f"oficial_{slug}" in active_keys:
                    pretty = self.oficial_entities.get(slug, item["prettyName"].replace("á", "a"))
                    precios[pretty] = {"ask": float(item.get("ask", 0)), "bid": float(item.get("bid", 0))}
            return precios
        except: return {}

    def fetch_usdt_criptoya(self, active_ids):
        p = {}
        def get_one(eid):
            try:
                r = requests.get(f"https://criptoya.com/api/{eid}/usdt/ars/0.1", timeout=5).json()
                name = self.cripto_exchanges.get(eid, eid.replace("p2p"," P2P").capitalize())
                return name, float(r["totalAsk"]), float(r["totalBid"])
            except: return None, None, None
        with ThreadPoolExecutor(max_workers=8) as exe:
            futures = [exe.submit(get_one, i) for i in active_ids]
            for f in as_completed(futures):
                n, a, b = f.result()
                if n: p[n] = {"ask": a, "bid": b}
        return p

    # --- CONTROL ---

    def toggle_bot(self):
        if not self.is_running:
            self.is_running = True
            self.btn_toggle.configure(text="DETENER BOT", fg_color="#dc3545", hover_color="#c82333")
            threading.Thread(target=self.main_loop, daemon=True).start()
        else:
            self.is_running = False
            self.btn_toggle.configure(text="INICIAR BOT", fg_color="#28a745", hover_color="#218838")

    def main_loop(self):
        while self.is_running:
            try:
                tab = self.tabview.get()
                threshold = float(self.threshold_entry.get())
                interval = int(self.interval_entry.get())
                keys = [k for k, v in self.exchange_vars.items() if v.get()]
                bridges = [k for k, v in self.bridge_vars.items() if v.get()]

                if tab == "USDT (CriptoYa)":
                    self.analyze_standard(self.fetch_usdt_criptoya([k for k in keys if not k.startswith("oficial_")]), threshold, self.cont_usdt)
                elif tab == "OFICIAL (ComparaDolar)":
                    self.analyze_standard(self.fetch_oficial_api([k for k in keys if k.startswith("oficial_")]), threshold, self.cont_oficial)
                elif tab == "OFICIAL vs USDT":
                    self.analyze_cross(keys, bridges, threshold, "OFICIAL")
                elif tab == "MEP vs USDT":
                    self.analyze_cross(keys, bridges, threshold, "MEP")
                elif tab == "OFICIAL vs MEP":
                    self.analyze_oficial_mep(keys, threshold)

                for _ in range(interval):
                    if not self.is_running: break
                    time.sleep(1)
            except: time.sleep(2)

    # --- LÓGICA DE ANÁLISIS ---

    def analyze_standard(self, precios, threshold, container):
        if not precios: return
        ex_min = min(precios, key=lambda x: precios[x]["ask"]); ex_max = max(precios, key=lambda x: precios[x]["bid"])
        spread = (precios[ex_max]["bid"] - precios[ex_min]["ask"]) / precios[ex_min]["ask"] * 100
        self.render_card(container, ex_min, ex_max, precios[ex_min], precios[ex_max], spread, True)
        for ex1, ex2 in permutations(precios.keys(), 2):
            ask, bid = precios[ex1]["ask"], precios[ex2]["bid"]
            gain = (bid - ask) / ask * 100
            if gain >= threshold:
                if time.time() - self._alertas_enviadas.get((ex1, ex2), 0) > float(self.cooldown_entry.get()):
                    self.render_card(container, ex1, ex2, precios[ex1], precios[ex2], gain)
                    self.process_telegram(ex1, ex2, ask, bid, gain)
                    self._alertas_enviadas[(ex1, ex2)] = time.time()

    def analyze_cross(self, keys, active_bridges, threshold, mode):
        if not active_bridges: return 
        p_cripto = self.fetch_usdt_criptoya([k for k in keys if not k.startswith("oficial_")])
        parities = {}
        with ThreadPoolExecutor(max_workers=6) as exe:
            futures = [exe.submit(self.fetch_parity, ex) for ex in active_bridges]
            for f in as_completed(futures):
                ex, ask_p, bid_p = f.result()
                if ask_p and ask_p > 0: parities[ex] = {"ask": ask_p, "name": self.bridge_list.get(ex, ex.capitalize())}

        if not p_cripto or not parities: return
        best_b_key = min(parities, key=lambda x: parities[x]["ask"]); best_ask_val = parities[best_b_key]["ask"]
        source_precios = {}
        if mode == "OFICIAL":
            p_oficial = self.fetch_oficial_api([k for k in keys if k.startswith("oficial_")])
            for name, p in p_oficial.items():
                source_precios[f"{name} (O)"] = {"ask": p["ask"] * best_ask_val, "raw_price": p["ask"], "bridge_name": parities[best_b_key]["name"], "parity": best_ask_val}
            container = self.cont_mix
        else:
            mep_p = self.fetch_mep_full()
            if mep_p: source_precios["Dolar MEP (M)"] = {"ask": mep_p["ci"] * best_ask_val, "raw_price": mep_p["ci"], "bridge_name": parities[best_b_key]["name"], "parity": best_ask_val}
            container = self.cont_mep_usdt

        if not source_precios: return
        best_source = min(source_precios, key=lambda x: source_precios[x]["ask"]); best_dest = max(p_cripto, key=lambda x: p_cripto[x]["bid"])
        spread_g = (p_cripto[best_dest]["bid"] - source_precios[best_source]["ask"]) / source_precios[best_source]["ask"] * 100
        self.render_card(container, best_source, best_dest, source_precios[best_source], p_cripto[best_dest], spread_g, True)
        
        for s_name, s_data in source_precios.items():
            for c_name, c_data in p_cripto.items():
                gain = (c_data["bid"] - s_data["ask"]) / s_data["ask"] * 100
                if gain >= threshold:
                    if time.time() - self._alertas_enviadas.get((s_name, c_name), 0) > float(self.cooldown_entry.get()):
                        self.render_card(container, s_name, c_name, s_data, c_data, gain)
                        self.process_telegram(s_name, c_name, s_data["ask"], c_data["bid"], gain)
                        self._alertas_enviadas[(s_name, c_name)] = time.time()

    def analyze_oficial_mep(self, keys, threshold):
        p_oficial = self.fetch_oficial_api([k for k in keys if k.startswith("oficial_")])
        mep_data = self.fetch_mep_full()
        if not p_oficial or not mep_data: return
        dest_data = {"bid": mep_data["ci"], "mep_24": mep_data["24hs"]}
        best_source = min(p_oficial, key=lambda x: p_oficial[x]["ask"])
        sp_ci = (dest_data["bid"] - p_oficial[best_source]["ask"]) / p_oficial[best_source]["ask"] * 100
        sp_24 = (dest_data["mep_24"] - p_oficial[best_source]["ask"]) / p_oficial[best_source]["ask"] * 100
        self.render_card(self.cont_oficial_mep, best_source, "Dolar MEP (M)", p_oficial[best_source], dest_data, {"ci": sp_ci, "24h": sp_24}, True)

        for name, p in p_oficial.items():
            g_ci = (dest_data["bid"] - p["ask"]) / p["ask"] * 100
            g_24 = (dest_data["mep_24"] - p["ask"]) / p["ask"] * 100
            if g_ci >= threshold:
                if time.time() - self._alertas_enviadas.get((name, "MEP"), 0) > float(self.cooldown_entry.get()):
                    self.render_card(self.cont_oficial_mep, name, "Dolar MEP (M)", p, dest_data, {"ci": g_ci, "24h": g_24})
                    self.process_telegram(name, "MEP", p["ask"], dest_data["bid"], g_ci)
                    self._alertas_enviadas[(name, "MEP")] = time.time()

    # --- RENDERER ---

    def render_card(self, container, ex1, ex2, d1, d2, spread, is_m=False):
        card = ctk.CTkFrame(container, fg_color="#161616", corner_radius=12, border_width=1, border_color="#333")
        h = ctk.CTkFrame(card, fg_color="transparent"); h.pack(fill="x", padx=15, pady=8)
        box = ctk.CTkFrame(h, fg_color="#2b2b2b" if is_m else "#1e8449", corner_radius=6); box.pack(side="left")
        ctk.CTkLabel(box, text="MERCADO" if is_m else "OPORTUNIDAD", font=ctk.CTkFont(weight="bold", size=13)).pack(padx=10, pady=2)
        ctk.CTkLabel(h, text=datetime.now().strftime("%H:%M:%S"), font=ctk.CTkFont(size=11), text_color="#666").pack(side="right")
        body = ctk.CTkFrame(card, fg_color="transparent"); body.pack(fill="x", padx=10, pady=10)
        body.grid_columnconfigure(0, weight=1, uniform="group")
        body.grid_columnconfigure(1, weight=1, uniform="group") 
        body.grid_columnconfigure(2, weight=1, uniform="group")

        def box_ui(parent, name, p_data, txt, color, is_sell, col):
            b = ctk.CTkFrame(parent, fg_color="#222", corner_radius=10, border_width=1, border_color="#444")
            b.grid(row=0, column=col, sticky="nsew", padx=5)
            clean = name.split(" (")[0].replace("á", "a")
            try:
                img_path = resource_path(f"logos/{clean}.png")
                img = ctk.CTkImage(Image.open(img_path), size=(34, 34))
                ctk.CTkLabel(b, image=img, text="").pack(pady=(10,0))
            except: pass
            ctk.CTkLabel(b, text=f"{name}", font=ctk.CTkFont(size=11, weight="bold")).pack()
            price = p_data["bid"] if is_sell else p_data["ask"]
            ctk.CTkLabel(b, text=f"${price:,.2f}", font=ctk.CTkFont(size=16, weight="bold"), text_color=color).pack()
            if is_sell and "mep_24" in p_data:
                ctk.CTkLabel(b, text=f"CI: ${p_data['bid']:,.2f}\n24h: ${p_data['mep_24']:,.2f}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#aaa").pack(pady=(5, 10))
            elif not is_sell and "bridge_name" in p_data:
                lbl = f"{'MEP' if '(M)' in name else 'Banco'}: ${p_data['raw_price']:,.2f}\nvia {p_data['bridge_name']} (x{p_data['parity']})"
                ctk.CTkLabel(b, text=lbl, font=ctk.CTkFont(size=12, weight="bold"), text_color="#aaa").pack(pady=(5, 10))
            else: ctk.CTkLabel(b, text=txt, font=ctk.CTkFont(size=10), text_color="#555").pack(pady=(2, 8))

        box_ui(body, ex1, d1, "COMPRA", "#28a745", False, 0)
        box_ui(body, ex2, d2, "VENTA", "#e74c3c", True, 2)
        s_box = ctk.CTkFrame(body, fg_color="transparent")
        s_box.grid(row=0, column=1, padx=10, sticky="nsew")

        if isinstance(spread, dict) and self.tabview.get() == "OFICIAL vs MEP":
            top = ctk.CTkFrame(s_box, fg_color="#3b8ed0", corner_radius=15)
            top.pack(fill="both", expand=True, pady=(0, 2))
            ctk.CTkLabel(top, text="PROFIT CI", font=ctk.CTkFont(size=10, weight="bold"), text_color="black").pack(pady=(8,0))
            ctk.CTkLabel(top, text=f"{spread['ci']:.2f}%", font=ctk.CTkFont(size=20, weight="bold"), text_color="black").pack()
            bot = ctk.CTkFrame(s_box, fg_color="#3BD0C9", corner_radius=15)
            bot.pack(fill="both", expand=True)
            ctk.CTkLabel(bot, text="PROFIT 24H", font=ctk.CTkFont(size=10, weight="bold"), text_color="black").pack(pady=(5,0))
            ctk.CTkLabel(bot, text=f"{spread['24h']:.2f}%", font=ctk.CTkFont(size=20, weight="bold"), text_color="black").pack(pady=(0,8))
        else:
            val = spread["ci"] if isinstance(spread, dict) else spread
            one_box = ctk.CTkFrame(s_box, fg_color="#3b8ed0", corner_radius=15)
            one_box.pack(fill="both", expand=True)
            ctk.CTkLabel(one_box, text="PROFIT TOTAL", font=ctk.CTkFont(size=11, weight="bold"), text_color="black").pack(expand=True, pady=(15,0))
            ctk.CTkLabel(one_box, text=f"{val:.2f}%", font=ctk.CTkFont(size=28, weight="bold"), text_color="black").pack(expand=True, pady=(0,20))

        card.pack(fill="x", pady=8, padx=10, side="top")
        if len(container.winfo_children()) > 30: container.winfo_children()[0].destroy()

    def process_telegram(self, ex1, ex2, ask, bid, gain):
        if not self.TELEGRAM_TOKEN: return
        msg = f"🔥 [{self.tabview.get()}] {gain:.2f}%\n🛒 {ex1.upper()}: {ask:,.2f}\n💰 {ex2.upper()}: {bid:,.2f}"
        threading.Thread(target=lambda m=msg: requests.post(f"https://api.telegram.org/bot{self.TELEGRAM_TOKEN}/sendMessage", data={"chat_id": self.CHAT_ID, "text": m})).start()

if __name__ == "__main__":
    ArbitrageBotGUI().mainloop()