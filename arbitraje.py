import os
import sys
import time
import threading
import requests
import json
from datetime import datetime
from itertools import permutations
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

import customtkinter as ctk
from PIL import Image

# --- Configuración de Rutas para PyInstaller ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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
        self.proxima_actualizacion = 0

        self.after(0, lambda: self.wm_state('zoomed'))
        self.title("Arbitrage Monitor Pro v13.6 - USDT to MEP")
        
        try:
            self.iconbitmap(resource_path("app_icon.ico"))
        except: pass

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

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0); self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="CONFIGURACIÓN", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)
        
        self.threshold_entry = self.create_input_with_presets("Umbral de Alerta (%)", "1.0", [("1%", 1.0), ("2%", 2.0), ("3%", 3.0), ("5%", 5.0)])
        self.interval_entry = self.create_input_with_presets("Intervalo Consulta (seg)", "30", [("30s", 30), ("1m", 60), ("3m", 180), ("5m", 300)])
        self.cooldown_entry = self.create_input_with_presets("Cooldown Alertas (seg)", "300", [("5m", 300), ("10m", 600), ("15m", 900), ("30m", 1800)])
        
        self.only_best_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self.sidebar, text="Telegram: Solo la más alta", variable=self.only_best_var).pack(pady=10, padx=20, anchor="w")

        self.ex_scroll = ctk.CTkScrollableFrame(self.sidebar, height=250, fg_color="transparent"); self.ex_scroll.pack(fill="both", expand=True, padx=10, pady=5)
        self.exchange_vars = {}; self.bridge_vars = {} 

        ctk.CTkLabel(self.ex_scroll, text="--- CRIPTO ---", font=ctk.CTkFont(size=10, slant="italic")).pack()
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
        target = self.bridge_vars if group == "bridge" else self.exchange_vars
        for k, v in target.items():
            if group == "bridge" or (group == "oficial" and k.startswith("oficial_")) or (group == "cripto" and not k.startswith("oficial_")): v.set(state)

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
            img = ctk.CTkImage(Image.open(resource_path(f"logos/{name}.png")), size=(20, 20))
            ctk.CTkLabel(f, image=img, text="").pack(side="left", padx=5)
        except: pass
        ctk.CTkCheckBox(f, text=name, variable=var, font=ctk.CTkFont(size=11)).pack(side="left")

    def setup_main_area(self):
        self.status_bar = ctk.CTkFrame(self, height=40, fg_color="#1a1a1a")
        self.status_bar.grid(row=0, column=1, sticky="new", padx=10, pady=(10, 0))
        self.status_label = ctk.CTkLabel(self.status_bar, text="Bot detenido. Presione 'INICIAR BOT'", font=ctk.CTkFont(weight="bold"))
        self.status_label.pack(side="left", padx=20)

        self.tabview = ctk.CTkTabview(self, fg_color="#0a0a0a")
        self.tabview.grid(row=0, column=1, padx=10, pady=(55, 10), sticky="nsew")
        
        self.tabs_map = {
            "USDT": self.tabview.add("USDT (CriptoYa)"),
            "OFICIAL": self.tabview.add("OFICIAL (ComparaDolar)"),
            "MIX": self.tabview.add("OFICIAL vs USDT"),
            "MEP_USDT": self.tabview.add("MEP vs USDT"),
            "OFICIAL_MEP": self.tabview.add("OFICIAL vs MEP"),
            "USDT_MEP": self.tabview.add("USDT vs MEP") # NUEVA PESTAÑA
        }
        self.containers = {k: ctk.CTkScrollableFrame(v, fg_color="transparent") for k, v in self.tabs_map.items()}
        for c in self.containers.values(): c.pack(fill="both", expand=True)

    # --- MOTORES DE DATOS ---
    def fetch_mep_full(self):
        try:
            r = requests.get("https://criptoya.com/api/dolar", timeout=10).json()
            return {"ci": float(r["mep"]["al30"]["ci"]["price"]), "24hs": float(r["mep"]["al30"]["24hs"]["price"])}
        except: return None

    def fetch_parity(self, ex):
        try:
            r = requests.get(f"https://criptoya.com/api/{ex}/usdt/usd/0.1", timeout=10).json()
            # Devolvemos Ask para entrar a USDT y Bid para salir de USDT a Dólar
            return ex, float(r.get("totalAsk", 0)), float(r.get("totalBid", 0))
        except: return ex, None, None

    def fetch_oficial_api(self, active_keys):
        try:
            r = requests.get("https://api.comparadolar.ar/usd", timeout=15)
            if r.status_code != 200: return {}
            p = {}
            for item in r.json():
                slug = item.get("name", "").lower().replace(" ", "").replace("á", "a")
                if f"oficial_{slug}" in active_keys:
                    pretty = self.oficial_entities.get(slug, item["prettyName"].replace("á", "a"))
                    p[pretty] = {"ask": float(item.get("ask", 0)), "bid": float(item.get("bid", 0))}
            return p
        except: return {}

    def fetch_usdt_criptoya(self, active_ids):
        p = {}
        def get_one(eid):
            try:
                r = requests.get(f"https://criptoya.com/api/{eid}/usdt/ars/0.1", timeout=10).json()
                return self.cripto_exchanges.get(eid, eid.replace("p2p"," P2P").capitalize()), float(r["totalAsk"]), float(r["totalBid"])
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
            self.update_countdown_ui()
        else:
            self.is_running = False
            self.btn_toggle.configure(text="INICIAR BOT", fg_color="#28a745", hover_color="#218838")
            self.status_label.configure(text="Bot detenido.")

    def update_countdown_ui(self):
        if not self.is_running: return
        restante = int(max(0, self.proxima_actualizacion - time.time()))
        self.status_label.configure(text=f"Próxima actualización en: {restante}s")
        self.after(1000, self.update_countdown_ui)

    def main_loop(self):
        while self.is_running:
            try:
                interval = int(self.interval_entry.get())
                self.proxima_actualizacion = time.time() + interval
                keys = [k for k, v in self.exchange_vars.items() if v.get()]
                bridges_keys = [k for k, v in self.bridge_vars.items() if v.get()]
                threshold = float(self.threshold_entry.get())

                for cat in self.containers: self.after(0, lambda c=cat: self.clear_container(c))

                with ThreadPoolExecutor(max_workers=5) as executor:
                    f_usdt = executor.submit(self.fetch_usdt_criptoya, [k for k in keys if not k.startswith("oficial_")])
                    f_oficial = executor.submit(self.fetch_oficial_api, [k for k in keys if k.startswith("oficial_")])
                    f_mep = executor.submit(self.fetch_mep_full)
                    p_usdt, p_oficial, p_mep = f_usdt.result(), f_oficial.result(), f_mep.result()

                self.analyze_standard(p_usdt, threshold, "USDT")
                self.analyze_standard(p_oficial, threshold, "OFICIAL")
                self.analyze_oficial_mep(p_oficial, p_mep, threshold)
                
                if bridges_keys:
                    parities = {}
                    with ThreadPoolExecutor(max_workers=6) as exe:
                        f_par = [exe.submit(self.fetch_parity, b) for b in bridges_keys]
                        for f in as_completed(f_par):
                            ex, a, b = f.result()
                            if a: parities[ex] = {"ask": a, "bid": b, "name": self.bridge_list.get(ex, ex.capitalize())}
                    
                    if parities:
                        # Para Oficial -> USDT usamos el mejor Ask (menor costo)
                        best_b_ask = min(parities.values(), key=lambda x: x["ask"])
                        self.analyze_cross(p_oficial, p_usdt, best_b_ask, threshold, "MIX")
                        self.analyze_cross_mep(p_mep, p_usdt, best_b_ask, threshold, "MEP_USDT")
                        
                        # Para USDT -> MEP usamos el mejor Bid (que nos den más dólares por USDT)
                        best_b_bid = max(parities.values(), key=lambda x: x["bid"])
                        self.analyze_usdt_mep(p_usdt, p_mep, best_b_bid, threshold)

                while time.time() < self.proxima_actualizacion and self.is_running: time.sleep(0.5)
            except: time.sleep(2)

    def clear_container(self, cat):
        container = self.containers[cat]
        for widget in container.winfo_children(): widget.destroy()

    # --- ANÁLISIS ---
    def analyze_standard(self, precios, threshold, cat):
        if not precios: return
        ex_min, ex_max = min(precios, key=lambda x: precios[x]["ask"]), max(precios, key=lambda x: precios[x]["bid"])
        spread = (precios[ex_max]["bid"] - precios[ex_min]["ask"]) / precios[ex_min]["ask"] * 100
        self.render_card(self.containers[cat], ex_min, ex_max, precios[ex_min], precios[ex_max], spread, cat, True)
        for ex1, ex2 in permutations(precios.keys(), 2):
            ask, bid = precios[ex1]["ask"], precios[ex2]["bid"]
            gain = (bid - ask) / ask * 100
            if gain >= threshold:
                self.render_card(self.containers[cat], ex1, ex2, precios[ex1], precios[ex2], gain, cat)
                self.process_telegram(cat, ex1, ex2, ask, bid, gain)

    def analyze_oficial_mep(self, p_oficial, p_mep, threshold):
        if not p_oficial or not p_mep: return
        dest_data = {"bid": p_mep["ci"], "mep_24": p_mep["24hs"]}
        best_source = min(p_oficial, key=lambda x: p_oficial[x]["ask"])
        sp_ci, sp_24 = (dest_data["bid"] - p_oficial[best_source]["ask"]) / p_oficial[best_source]["ask"] * 100, (dest_data["mep_24"] - p_oficial[best_source]["ask"]) / p_oficial[best_source]["ask"] * 100
        self.render_card(self.containers["OFICIAL_MEP"], best_source, "Dolar MEP (M)", p_oficial[best_source], dest_data, {"ci": sp_ci, "24h": sp_24}, "OFICIAL_MEP", True)
        for name, p in p_oficial.items():
            g_ci = (dest_data["bid"] - p["ask"]) / p["ask"] * 100
            if g_ci >= threshold:
                self.render_card(self.containers["OFICIAL_MEP"], name, "Dolar MEP (M)", p, dest_data, {"ci": g_ci, "24h": sp_24}, "OFICIAL_MEP")
                self.process_telegram("OFICIAL_MEP", name, "MEP", p["ask"], dest_data["bid"], g_ci)

    def analyze_cross(self, p_oficial, p_usdt, bridge, threshold, cat):
        if not p_oficial or not p_usdt: return
        src = {f"{n} (O)": {"ask": p["ask"] * bridge["ask"], "raw_price": p["ask"], "bridge_name": bridge["name"], "parity": bridge["ask"]} for n, p in p_oficial.items()}
        b_s, b_d = min(src, key=lambda x: src[x]["ask"]), max(p_usdt, key=lambda x: p_usdt[x]["bid"])
        spread_g = (p_usdt[b_d]["bid"] - src[b_s]["ask"]) / src[b_s]["ask"] * 100
        self.render_card(self.containers[cat], b_s, b_d, src[b_s], p_usdt[b_d], spread_g, cat, True)
        for s_n, s_d in src.items():
            for c_n, c_d in p_usdt.items():
                gain = (c_d["bid"] - s_d["ask"]) / s_d["ask"] * 100
                if gain >= threshold:
                    self.render_card(self.containers[cat], s_n, c_n, s_d, c_d, gain, cat)
                    self.process_telegram(cat, s_n, c_n, s_d["ask"], c_d["bid"], gain)

    def analyze_cross_mep(self, p_mep, p_usdt, bridge, threshold, cat):
        if not p_mep or not p_usdt: return
        s_d = {"ask": p_mep["ci"] * bridge["ask"], "raw_price": p_mep["ci"], "bridge_name": bridge["name"], "parity": bridge["ask"]}
        b_d = max(p_usdt, key=lambda x: p_usdt[x]["bid"])
        self.render_card(self.containers[cat], "Dolar MEP (M)", b_d, s_d, p_usdt[b_d], (p_usdt[b_d]["bid"] - s_d["ask"]) / s_d["ask"] * 100, cat, True)

    def analyze_usdt_mep(self, p_usdt, p_mep, bridge, threshold):
        """Lógica para la nueva funcionalidad USDT -> Dólar -> MEP"""
        if not p_usdt or not p_mep: return
        # El origen es el USDT/ARS más barato. El destino es el MEP CI/24h.
        # Costo por dólar final = Precio USDT ARS / Cantidad de USD que recibo por USDT
        best_usdt_name = min(p_usdt, key=lambda x: p_usdt[x]["ask"])
        costo_ars = p_usdt[best_usdt_name]["ask"]
        
        source_data = {
            "ask": costo_ars / bridge["bid"], # ARS necesarios por cada Dólar MEP final
            "raw_price": costo_ars,
            "bridge_name": bridge["name"],
            "parity": bridge["bid"]
        }
        dest_data = {"bid": p_mep["ci"], "mep_24": p_mep["24hs"]}
        
        sp_ci = (dest_data["bid"] - source_data["ask"]) / source_data["ask"] * 100
        sp_24 = (dest_data["mep_24"] - source_data["ask"]) / source_data["ask"] * 100
        
        self.render_card(self.containers["USDT_MEP"], f"{best_usdt_name} (U)", "Dolar MEP (M)", source_data, dest_data, {"ci": sp_ci, "24h": sp_24}, "USDT_MEP", True)
        
        for name, p in p_usdt.items():
            costo_usd = p["ask"] / bridge["bid"]
            gain_ci = (dest_data["bid"] - costo_usd) / costo_usd * 100
            if gain_ci >= threshold:
                item_source = {"ask": costo_usd, "raw_price": p["ask"], "bridge_name": bridge["name"], "parity": bridge["bid"]}
                self.render_card(self.containers["USDT_MEP"], f"{name} (U)", "Dolar MEP (M)", item_source, dest_data, {"ci": gain_ci, "24h": sp_24}, "USDT_MEP")
                self.process_telegram("USDT_MEP", name, "MEP", costo_usd, dest_data["bid"], gain_ci)

    # --- RENDERER ---
    def render_card(self, container, ex1, ex2, d1, d2, spread, cat, is_m=False):
        self.after(0, lambda: self._ui_render_card(container, ex1, ex2, d1, d2, spread, cat, is_m))

    def _ui_render_card(self, container, ex1, ex2, d1, d2, spread, cat, is_m):
        try:
            card = ctk.CTkFrame(container, fg_color="#161616", corner_radius=12, border_width=1, border_color="#555" if is_m else "#333")
            card.pack(fill="x", pady=8, padx=10, side="top")

            h = ctk.CTkFrame(card, fg_color="transparent"); h.pack(fill="x", padx=15, pady=8)
            bh = ctk.CTkFrame(h, fg_color="#2b2b2b" if is_m else "#1e8449", corner_radius=6); bh.pack(side="left")
            ctk.CTkLabel(bh, text="MERCADO" if is_m else "OPORTUNIDAD", font=ctk.CTkFont(weight="bold", size=13)).pack(padx=10, pady=2)
            ctk.CTkLabel(h, text=datetime.now().strftime("%H:%M:%S"), font=ctk.CTkFont(size=11), text_color="#666").pack(side="right")
            
            body = ctk.CTkFrame(card, fg_color="transparent"); body.pack(fill="x", padx=10, pady=10)
            body.grid_columnconfigure((0,1,2), weight=1, uniform="group")
            
            def box_ui(parent, name, p_data, txt, color, is_sell, col):
                b = ctk.CTkFrame(parent, fg_color="#222", corner_radius=10, border_width=1, border_color="#444")
                b.grid(row=0, column=col, sticky="nsew", padx=5)
                try:
                    clean_name = name.split(' (')[0].replace('á', 'a')
                    img = ctk.CTkImage(Image.open(resource_path(f"logos/{clean_name}.png")), size=(34, 34))
                    ctk.CTkLabel(b, image=img, text="").pack(pady=(10,0))
                except: pass
                ctk.CTkLabel(b, text=name, font=ctk.CTkFont(size=11, weight="bold")).pack()
                price = p_data['bid'] if is_sell else p_data['ask']
                ctk.CTkLabel(b, text=f"${price:,.2f}", font=ctk.CTkFont(size=16, weight="bold"), text_color=color).pack()
                if is_sell and "mep_24" in p_data: ctk.CTkLabel(b, text=f"CI: ${p_data['bid']:,.2f}\n24h: ${p_data['mep_24']:,.2f}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#aaa").pack(pady=(5, 10))
                elif not is_sell and "bridge_name" in p_data: 
                    lbl = f"{'USDT' if '(U)' in name else 'Entidad'}: ${p_data['raw_price']:,.2f}\nvia {p_data['bridge_name']} (x{p_data['parity']})"
                    ctk.CTkLabel(b, text=lbl, font=ctk.CTkFont(size=11), text_color="#aaa").pack(pady=(5, 10))
                else: ctk.CTkLabel(b, text=txt, font=ctk.CTkFont(size=10), text_color="#555").pack(pady=(2, 8))

            box_ui(body, ex1, d1, "COMPRA", "#28a745", False, 0)
            box_ui(body, ex2, d2, "VENTA", "#e74c3c", True, 2)
            s_box = ctk.CTkFrame(body, fg_color="transparent"); s_box.grid(row=0, column=1, padx=10, sticky="nsew")
            
            # --- PROFIT DUAL PARA MEP ---
            if isinstance(spread, dict) and cat in ["OFICIAL_MEP", "USDT_MEP"]:
                top = ctk.CTkFrame(s_box, fg_color="#3b8ed0", corner_radius=15); top.pack(fill="both", expand=True, pady=(0, 2))
                ctk.CTkLabel(top, text="PROFIT CI", font=ctk.CTkFont(size=10, weight="bold"), text_color="black").pack(pady=(8,0))
                ctk.CTkLabel(top, text=f"{spread['ci']:.2f}%", font=ctk.CTkFont(size=20, weight="bold"), text_color="black").pack()
                bot = ctk.CTkFrame(s_box, fg_color="#3BD0C9", corner_radius=15); bot.pack(fill="both", expand=True)
                ctk.CTkLabel(bot, text="PROFIT 24H", font=ctk.CTkFont(size=10, weight="bold"), text_color="black").pack(pady=(5,0))
                ctk.CTkLabel(bot, text=f"{spread['24h']:.2f}%", font=ctk.CTkFont(size=20, weight="bold"), text_color="black").pack(pady=(0,8))
            else:
                one_box = ctk.CTkFrame(s_box, fg_color="#3b8ed0", corner_radius=15); one_box.pack(fill="both", expand=True)
                val = spread["ci"] if isinstance(spread, dict) else spread
                ctk.CTkLabel(one_box, text="PROFIT TOTAL", font=ctk.CTkFont(size=11, weight="bold"), text_color="black").pack(expand=True, pady=(15,0))
                ctk.CTkLabel(one_box, text=f"{val:.2f}%", font=ctk.CTkFont(size=28, weight="bold"), text_color="black").pack(expand=True, pady=(0,20))
        except: pass

    def process_telegram(self, cat, ex1, ex2, ask, bid, gain):
        if not self.TELEGRAM_TOKEN: return
        key = (ex1, ex2, cat)
        if time.time() - self._alertas_enviadas.get(key, 0) > float(self.cooldown_entry.get()):
            msg = f"🔥 [{cat}] {gain:.2f}%\n🛒 {ex1.upper()}: {ask:,.2f}\n💰 {ex2.upper()}: {bid:,.2f}"
            threading.Thread(target=lambda m=msg: requests.post(f"https://api.telegram.org/bot{self.TELEGRAM_TOKEN}/sendMessage", data={"chat_id": self.CHAT_ID, "text": m})).start()
            self._alertas_enviadas[key] = time.time()

if __name__ == "__main__":
    ArbitrageBotGUI().mainloop()



# import os
# import sys
# import time
# import threading
# import requests
# import json
# from datetime import datetime
# from itertools import permutations
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from dotenv import load_dotenv

# import customtkinter as ctk
# from PIL import Image

# # --- Configuración de Rutas para PyInstaller ---
# def resource_path(relative_path):
#     try:
#         base_path = sys._MEIPASS
#     except Exception:
#         base_path = os.path.abspath(".")
#     return os.path.join(base_path, relative_path)

# ctk.set_appearance_mode("Dark")
# ctk.set_default_color_theme("blue")

# class ArbitrageBotGUI(ctk.CTk):
#     def __init__(self):
#         super().__init__()
#         load_dotenv()
#         self.TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
#         self.CHAT_ID = os.getenv("CHAT_ID")
#         self.is_running = False
#         self._alertas_enviadas = {}
#         self.proxima_actualizacion = 0

#         self.after(0, lambda: self.wm_state('zoomed'))
#         self.title("Arbitrage Monitor Pro v13.5")
        
#         try:
#             self.iconbitmap(resource_path("app_icon.ico"))
#         except: pass

#         self.oficial_entities = {
#             "uala": "Uala", "reba": "Reba", "plus": "Plus", 
#             "cocos": "Cocos", "fiwind": "Fiwind", "buenbit": "Buenbit"
#         }
#         self.cripto_exchanges = {
#             "fiwind": "Fiwind", "buenbit": "Buenbit", "lemoncashp2p": "Lemon Cash P2P",
#             "pluscrypto": "Plus Crypto", "satoshitango": "SatoshiTango", "lemoncash": "Lemon Cash",
#             "belo": "belo", "bybit": "Bybit", "tiendacrypto": "TiendaCrypto",
#             "binancep2p": "Binance P2P", "cocoscrypto": "Cocos Crypto", "bingxp2p": "BingX P2P",
#             "decrypto": "Decrypto", "bybitp2p": "Bybit P2P", "eldoradop2p": "El Dorado P2P"
#         }
#         self.bridge_list = {
#             "belo": "belo", "binancep2p": "Binance P2P", "fiwind": "Fiwind", 
#             "satoshitango": "SatoshiTango", "tiendacrypto": "TiendaCrypto", "decrypto": "Decrypto"
#         }

#         self.grid_columnconfigure(1, weight=1)
#         self.grid_rowconfigure(0, weight=1)
#         self.setup_sidebar()
#         self.setup_main_area()

#     def setup_sidebar(self):
#         self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0); self.sidebar.grid(row=0, column=0, sticky="nsew")
#         ctk.CTkLabel(self.sidebar, text="CONFIGURACIÓN", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)
        
#         self.threshold_entry = self.create_input_with_presets("Umbral de Alerta (%)", "1.0", [("1%", 1.0), ("2%", 2.0), ("3%", 3.0), ("5%", 5.0)])
#         self.interval_entry = self.create_input_with_presets("Intervalo Consulta (seg)", "30", [("30s", 30), ("1m", 60), ("3m", 180), ("5m", 300)])
#         self.cooldown_entry = self.create_input_with_presets("Cooldown Alertas (seg)", "300", [("5m", 300), ("10m", 600), ("15m", 900), ("30m", 1800)])
        
#         self.only_best_var = ctk.BooleanVar(value=True)
#         ctk.CTkCheckBox(self.sidebar, text="Telegram: Solo la más alta", variable=self.only_best_var).pack(pady=10, padx=20, anchor="w")

#         self.ex_scroll = ctk.CTkScrollableFrame(self.sidebar, height=250, fg_color="transparent"); self.ex_scroll.pack(fill="both", expand=True, padx=10, pady=5)
#         self.exchange_vars = {}; self.bridge_vars = {} 

#         ctk.CTkLabel(self.ex_scroll, text="--- CRIPTO ---", font=ctk.CTkFont(size=10, slant="italic")).pack()
#         self.create_bulk_buttons(self.ex_scroll, "cripto")
#         for eid, name in self.cripto_exchanges.items(): self.create_check(eid, name, self.exchange_vars)
        
#         ctk.CTkLabel(self.ex_scroll, text="--- OFICIAL ---", font=ctk.CTkFont(size=10, slant="italic")).pack(pady=(15,0))
#         self.create_bulk_buttons(self.ex_scroll, "oficial")
#         for eid, name in self.oficial_entities.items(): self.create_check(f"oficial_{eid}", name, self.exchange_vars)

#         ctk.CTkLabel(self.ex_scroll, text="--- PUENTE (USD) ---", font=ctk.CTkFont(size=10, slant="italic"), text_color="#3b8ed0").pack(pady=(15,0))
#         self.create_bulk_buttons(self.ex_scroll, "bridge")
#         for eid, name in self.bridge_list.items(): self.create_check(eid, name, self.bridge_vars)

#         self.btn_toggle = ctk.CTkButton(self.sidebar, text="INICIAR BOT", fg_color="#28a745", height=45, command=self.toggle_bot, font=ctk.CTkFont(weight="bold"))
#         self.btn_toggle.pack(pady=20, padx=20, fill="x")

#     def create_bulk_buttons(self, parent, group):
#         f = ctk.CTkFrame(parent, fg_color="transparent"); f.pack(fill="x", pady=2)
#         ctk.CTkButton(f, text="Todos", width=60, height=18, font=ctk.CTkFont(size=9), fg_color="#333", command=lambda: self.toggle_group_vars(group, True)).pack(side="left", padx=(10, 5))
#         ctk.CTkButton(f, text="Ninguno", width=60, height=18, font=ctk.CTkFont(size=9), fg_color="#333", command=lambda: self.toggle_group_vars(group, False)).pack(side="left")

#     def toggle_group_vars(self, group, state):
#         target = self.bridge_vars if group == "bridge" else self.exchange_vars
#         for k, v in target.items():
#             if group == "bridge" or (group == "oficial" and k.startswith("oficial_")) or (group == "cripto" and not k.startswith("oficial_")): v.set(state)

#     def create_input_with_presets(self, label, default, presets):
#         c = ctk.CTkFrame(self.sidebar, fg_color="transparent"); c.pack(fill="x", pady=5)
#         ctk.CTkLabel(c, text=label).pack()
#         e = ctk.CTkEntry(c, justify="center", width=120); e.insert(0, default); e.pack(pady=2)
#         p = ctk.CTkFrame(c, fg_color="transparent"); p.pack()
#         for t, v in presets: ctk.CTkButton(p, text=t, width=42, height=22, font=ctk.CTkFont(size=10), fg_color="#333", command=lambda val=v, ent=e: (ent.delete(0, "end"), ent.insert(0, str(val)))).pack(side="left", padx=2)
#         return e

#     def create_check(self, internal_id, name, target_dict):
#         f = ctk.CTkFrame(self.ex_scroll, fg_color="transparent"); f.pack(fill="x", pady=1)
#         var = ctk.BooleanVar(value=True); target_dict[internal_id] = var
#         try:
#             img = ctk.CTkImage(Image.open(resource_path(f"logos/{name}.png")), size=(20, 20))
#             ctk.CTkLabel(f, image=img, text="").pack(side="left", padx=5)
#         except: pass
#         ctk.CTkCheckBox(f, text=name, variable=var, font=ctk.CTkFont(size=11)).pack(side="left")

#     def setup_main_area(self):
#         self.status_bar = ctk.CTkFrame(self, height=40, fg_color="#1a1a1a")
#         self.status_bar.grid(row=0, column=1, sticky="new", padx=10, pady=(10, 0))
#         self.status_label = ctk.CTkLabel(self.status_bar, text="Bot detenido. Presione 'INICIAR BOT'", font=ctk.CTkFont(weight="bold"))
#         self.status_label.pack(side="left", padx=20)

#         self.tabview = ctk.CTkTabview(self, fg_color="#0a0a0a")
#         self.tabview.grid(row=0, column=1, padx=10, pady=(55, 10), sticky="nsew")
        
#         self.tabs_map = {
#             "USDT": self.tabview.add("USDT (CriptoYa)"),
#             "OFICIAL": self.tabview.add("OFICIAL (ComparaDolar)"),
#             "MIX": self.tabview.add("OFICIAL vs USDT"),
#             "MEP_USDT": self.tabview.add("MEP vs USDT"),
#             "OFICIAL_MEP": self.tabview.add("OFICIAL vs MEP")
#         }
#         self.containers = {k: ctk.CTkScrollableFrame(v, fg_color="transparent") for k, v in self.tabs_map.items()}
#         for c in self.containers.values(): c.pack(fill="both", expand=True)

#     # --- MOTORES ---
#     def fetch_mep_full(self):
#         try:
#             r = requests.get("https://criptoya.com/api/dolar", timeout=10).json()
#             return {"ci": float(r["mep"]["al30"]["ci"]["price"]), "24hs": float(r["mep"]["al30"]["24hs"]["price"])}
#         except: return None

#     def fetch_parity(self, ex):
#         try:
#             r = requests.get(f"https://criptoya.com/api/{ex}/usdt/usd/0.1", timeout=10).json()
#             return ex, float(r.get("totalAsk", 0)), float(r.get("totalBid", 0))
#         except: return ex, None, None

#     def fetch_oficial_api(self, active_keys):
#         try:
#             r = requests.get("https://api.comparadolar.ar/usd", timeout=15)
#             if r.status_code != 200: return {}
#             p = {}
#             for item in r.json():
#                 slug = item.get("name", "").lower().replace(" ", "").replace("á", "a")
#                 if f"oficial_{slug}" in active_keys:
#                     pretty = self.oficial_entities.get(slug, item["prettyName"].replace("á", "a"))
#                     p[pretty] = {"ask": float(item.get("ask", 0)), "bid": float(item.get("bid", 0))}
#             return p
#         except: return {}

#     def fetch_usdt_criptoya(self, active_ids):
#         p = {}
#         def get_one(eid):
#             try:
#                 r = requests.get(f"https://criptoya.com/api/{eid}/usdt/ars/0.1", timeout=10).json()
#                 return self.cripto_exchanges.get(eid, eid.replace("p2p"," P2P").capitalize()), float(r["totalAsk"]), float(r["totalBid"])
#             except: return None, None, None
#         with ThreadPoolExecutor(max_workers=8) as exe:
#             futures = [exe.submit(get_one, i) for i in active_ids]
#             for f in as_completed(futures):
#                 n, a, b = f.result()
#                 if n: p[n] = {"ask": a, "bid": b}
#         return p

#     # --- CONTROL ---
#     def toggle_bot(self):
#         """Maneja el inicio y detención visual y lógica del bot"""
#         if not self.is_running:
#             # INICIAR
#             self.is_running = True
#             self.btn_toggle.configure(text="DETENER BOT", fg_color="#dc3545", hover_color="#c82333")
#             threading.Thread(target=self.main_loop, daemon=True).start()
#             self.update_countdown_ui()
#         else:
#             # DETENER
#             self.is_running = False
#             self.btn_toggle.configure(text="INICIAR BOT", fg_color="#28a745", hover_color="#218838")
#             self.status_label.configure(text="Bot detenido.")

#     def update_countdown_ui(self):
#         if not self.is_running: return
#         restante = int(max(0, self.proxima_actualizacion - time.time()))
#         self.status_label.configure(text=f"Próxima actualización en: {restante}s")
#         self.after(1000, self.update_countdown_ui)

#     def main_loop(self):
#         while self.is_running:
#             try:
#                 interval = int(self.interval_entry.get())
#                 self.proxima_actualizacion = time.time() + interval
#                 keys = [k for k, v in self.exchange_vars.items() if v.get()]
#                 bridges = [k for k, v in self.bridge_vars.items() if v.get()]
#                 threshold = float(self.threshold_entry.get())

#                 # Limpiar UI antes de nuevo ciclo
#                 for cat in self.containers:
#                     self.after(0, lambda c=cat: self.clear_container(c))

#                 with ThreadPoolExecutor(max_workers=5) as executor:
#                     f_usdt = executor.submit(self.fetch_usdt_criptoya, [k for k in keys if not k.startswith("oficial_")])
#                     f_oficial = executor.submit(self.fetch_oficial_api, [k for k in keys if k.startswith("oficial_")])
#                     f_mep = executor.submit(self.fetch_mep_full)
#                     p_usdt, p_oficial, p_mep = f_usdt.result(), f_oficial.result(), f_mep.result()

#                 # Análisis de datos
#                 self.analyze_standard(p_usdt, threshold, "USDT")
#                 self.analyze_standard(p_oficial, threshold, "OFICIAL")
#                 self.analyze_oficial_mep(p_oficial, p_mep, threshold)
                
#                 if bridges:
#                     parities = {}
#                     with ThreadPoolExecutor(max_workers=6) as exe:
#                         f_par = [exe.submit(self.fetch_parity, b) for b in bridges]
#                         for f in as_completed(f_par):
#                             ex, a, b = f.result()
#                             if a: parities[ex] = {"ask": a, "name": self.bridge_list.get(ex, ex.capitalize())}
#                     if parities:
#                         best_b = min(parities, key=lambda x: parities[x]["ask"])
#                         self.analyze_cross(p_oficial, p_usdt, parities[best_b], threshold, "MIX")
#                         self.analyze_cross_mep(p_mep, p_usdt, parities[best_b], threshold, "MEP_USDT")

#                 while time.time() < self.proxima_actualizacion and self.is_running: 
#                     time.sleep(0.5)
#             except: time.sleep(2)

#     def clear_container(self, cat):
#         container = self.containers[cat]
#         for widget in container.winfo_children():
#             widget.destroy()

#     # --- ANÁLISIS ---
#     def analyze_standard(self, precios, threshold, cat):
#         if not precios: return
#         ex_min, ex_max = min(precios, key=lambda x: precios[x]["ask"]), max(precios, key=lambda x: precios[x]["bid"])
#         spread = (precios[ex_max]["bid"] - precios[ex_min]["ask"]) / precios[ex_min]["ask"] * 100
#         self.render_card(self.containers[cat], ex_min, ex_max, precios[ex_min], precios[ex_max], spread, cat, True)
#         for ex1, ex2 in permutations(precios.keys(), 2):
#             ask, bid = precios[ex1]["ask"], precios[ex2]["bid"]
#             gain = (bid - ask) / ask * 100
#             if gain >= threshold:
#                 self.render_card(self.containers[cat], ex1, ex2, precios[ex1], precios[ex2], gain, cat)
#                 self.process_telegram(cat, ex1, ex2, ask, bid, gain)

#     def analyze_oficial_mep(self, p_oficial, p_mep, threshold):
#         if not p_oficial or not p_mep: return
#         dest_data = {"bid": p_mep["ci"], "mep_24": p_mep["24hs"]}
#         best_source = min(p_oficial, key=lambda x: p_oficial[x]["ask"])
#         sp_ci, sp_24 = (dest_data["bid"] - p_oficial[best_source]["ask"]) / p_oficial[best_source]["ask"] * 100, (dest_data["mep_24"] - p_oficial[best_source]["ask"]) / p_oficial[best_source]["ask"] * 100
#         self.render_card(self.containers["OFICIAL_MEP"], best_source, "Dolar MEP (M)", p_oficial[best_source], dest_data, {"ci": sp_ci, "24h": sp_24}, "OFICIAL_MEP", True)
#         for name, p in p_oficial.items():
#             g_ci = (dest_data["bid"] - p["ask"]) / p["ask"] * 100
#             if g_ci >= threshold:
#                 self.render_card(self.containers["OFICIAL_MEP"], name, "Dolar MEP (M)", p, dest_data, {"ci": g_ci, "24h": sp_24}, "OFICIAL_MEP")
#                 self.process_telegram("OFICIAL_MEP", name, "MEP", p["ask"], dest_data["bid"], g_ci)

#     def analyze_cross(self, p_oficial, p_usdt, bridge, threshold, cat):
#         if not p_oficial or not p_usdt: return
#         src = {f"{n} (O)": {"ask": p["ask"] * bridge["ask"], "raw_price": p["ask"], "bridge_name": bridge["name"], "parity": bridge["ask"]} for n, p in p_oficial.items()}
#         b_s, b_d = min(src, key=lambda x: src[x]["ask"]), max(p_usdt, key=lambda x: p_usdt[x]["bid"])
#         spread_g = (p_usdt[b_d]["bid"] - src[b_s]["ask"]) / src[b_s]["ask"] * 100
#         self.render_card(self.containers[cat], b_s, b_d, src[b_s], p_usdt[b_d], spread_g, cat, True)
#         for s_n, s_d in src.items():
#             for c_n, c_d in p_usdt.items():
#                 gain = (c_d["bid"] - s_d["ask"]) / s_d["ask"] * 100
#                 if gain >= threshold:
#                     self.render_card(self.containers[cat], s_n, c_n, s_d, c_d, gain, cat)
#                     self.process_telegram(cat, s_n, c_n, s_d["ask"], c_d["bid"], gain)

#     def analyze_cross_mep(self, p_mep, p_usdt, bridge, threshold, cat):
#         if not p_mep or not p_usdt: return
#         s_d = {"ask": p_mep["ci"] * bridge["ask"], "raw_price": p_mep["ci"], "bridge_name": bridge["name"], "parity": bridge["ask"]}
#         b_d = max(p_usdt, key=lambda x: p_usdt[x]["bid"])
#         self.render_card(self.containers[cat], "Dolar MEP (M)", b_d, s_d, p_usdt[b_d], (p_usdt[b_d]["bid"] - s_d["ask"]) / s_d["ask"] * 100, cat, True)

#     # --- RENDERER ---
#     def render_card(self, container, ex1, ex2, d1, d2, spread, cat, is_m=False):
#         self.after(0, lambda: self._ui_render_card(container, ex1, ex2, d1, d2, spread, cat, is_m))

#     def _ui_render_card(self, container, ex1, ex2, d1, d2, spread, cat, is_m):
#         try:
#             card = ctk.CTkFrame(container, fg_color="#161616", corner_radius=12, border_width=1, border_color="#555" if is_m else "#333")
#             card.pack(fill="x", pady=8, padx=10, side="top")

#             h = ctk.CTkFrame(card, fg_color="transparent"); h.pack(fill="x", padx=15, pady=8)
#             bh = ctk.CTkFrame(h, fg_color="#2b2b2b" if is_m else "#1e8449", corner_radius=6); bh.pack(side="left")
#             ctk.CTkLabel(bh, text="MERCADO 📊" if is_m else "OPORTUNIDAD 🚀", font=ctk.CTkFont(weight="bold", size=13)).pack(padx=10, pady=2)
#             ctk.CTkLabel(h, text=datetime.now().strftime("%H:%M:%S"), font=ctk.CTkFont(size=11), text_color="#666").pack(side="right")
            
#             body = ctk.CTkFrame(card, fg_color="transparent"); body.pack(fill="x", padx=10, pady=10)
#             body.grid_columnconfigure((0,1,2), weight=1, uniform="group")
            
#             def box_ui(parent, name, p_data, txt, color, is_sell, col):
#                 b = ctk.CTkFrame(parent, fg_color="#222", corner_radius=10, border_width=1, border_color="#444")
#                 b.grid(row=0, column=col, sticky="nsew", padx=5)
#                 try:
#                     clean_name = name.split(' (')[0].replace('á', 'a')
#                     img = ctk.CTkImage(Image.open(resource_path(f"logos/{clean_name}.png")), size=(34, 34))
#                     ctk.CTkLabel(b, image=img, text="").pack(pady=(10,0))
#                 except: pass
#                 ctk.CTkLabel(b, text=name, font=ctk.CTkFont(size=11, weight="bold")).pack()
#                 price = p_data['bid'] if is_sell else p_data['ask']
#                 ctk.CTkLabel(b, text=f"${price:,.2f}", font=ctk.CTkFont(size=16, weight="bold"), text_color=color).pack()
#                 if is_sell and "mep_24" in p_data: ctk.CTkLabel(b, text=f"CI: ${p_data['bid']:,.2f}\n24h: ${p_data['mep_24']:,.2f}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#aaa").pack(pady=(5, 10))
#                 elif not is_sell and "bridge_name" in p_data: ctk.CTkLabel(b, text=f"{'MEP' if '(M)' in name else 'Banco'}: ${p_data['raw_price']:,.2f}\nvia {p_data['bridge_name']} (x{p_data['parity']})", font=ctk.CTkFont(size=11), text_color="#aaa").pack(pady=(5, 10))
#                 else: ctk.CTkLabel(b, text=txt, font=ctk.CTkFont(size=10), text_color="#555").pack(pady=(2, 8))

#             box_ui(body, ex1, d1, "COMPRA", "#28a745", False, 0)
#             box_ui(body, ex2, d2, "VENTA", "#e74c3c", True, 2)
#             s_box = ctk.CTkFrame(body, fg_color="transparent"); s_box.grid(row=0, column=1, padx=10, sticky="nsew")
#             if isinstance(spread, dict) and cat == "OFICIAL_MEP":
#                 top = ctk.CTkFrame(s_box, fg_color="#3b8ed0", corner_radius=15); top.pack(fill="both", expand=True, pady=(0, 2))
#                 ctk.CTkLabel(top, text="PROFIT CI", font=ctk.CTkFont(size=10, weight="bold"), text_color="black").pack(pady=(8,0))
#                 ctk.CTkLabel(top, text=f"{spread['ci']:.2f}%", font=ctk.CTkFont(size=20, weight="bold"), text_color="black").pack()
#                 bot = ctk.CTkFrame(s_box, fg_color="#3BD0C9", corner_radius=15); bot.pack(fill="both", expand=True)
#                 ctk.CTkLabel(bot, text="PROFIT 24H", font=ctk.CTkFont(size=10, weight="bold"), text_color="black").pack(pady=(5,0))
#                 ctk.CTkLabel(bot, text=f"{spread['24h']:.2f}%", font=ctk.CTkFont(size=20, weight="bold"), text_color="black").pack(pady=(0,8))
#             else:
#                 one_box = ctk.CTkFrame(s_box, fg_color="#3b8ed0", corner_radius=15); one_box.pack(fill="both", expand=True)
#                 val = spread["ci"] if isinstance(spread, dict) else spread
#                 ctk.CTkLabel(one_box, text="PROFIT TOTAL", font=ctk.CTkFont(size=11, weight="bold"), text_color="black").pack(expand=True, pady=(15,0))
#                 ctk.CTkLabel(one_box, text=f"{val:.2f}%", font=ctk.CTkFont(size=28, weight="bold"), text_color="black").pack(expand=True, pady=(0,20))
#         except: pass

#     def process_telegram(self, cat, ex1, ex2, ask, bid, gain):
#         if not self.TELEGRAM_TOKEN: return
#         key = (ex1, ex2, cat)
#         cooldown = float(self.cooldown_entry.get())
#         if time.time() - self._alertas_enviadas.get(key, 0) > cooldown:
#             msg = f"🔥 [{cat}] {gain:.2f}%\n🛒 {ex1.upper()}: {ask:,.2f}\n💰 {ex2.upper()}: {bid:,.2f}"
#             threading.Thread(target=lambda m=msg: requests.post(f"https://api.telegram.org/bot{self.TELEGRAM_TOKEN}/sendMessage", data={"chat_id": self.CHAT_ID, "text": m})).start()
#             self._alertas_enviadas[key] = time.time()

# if __name__ == "__main__":
#     ArbitrageBotGUI().mainloop()