import os
import time
import threading
from datetime import datetime
import customtkinter as ctk
from PIL import Image

from src.config import resource_path, OFICIAL_ENTITIES, CRIPTO_EXCHANGES, BRIDGE_LIST
from src.api_client import APIClient
from src.analyzer import ArbitrageAnalyzer
from src.notifier import TelegramNotifier

class ArbitrageBotGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.api_client = APIClient()
        self.analyzer = ArbitrageAnalyzer()
        self.notifier = TelegramNotifier()
        
        self.is_running = False
        self.proxima_actualizacion = 0
        
        self.tasas_disponibles = self.api_client.get_initial_tasas()

        self.after(0, lambda: self.wm_state('zoomed'))
        self.title("Monitor de Arbitraje")
        
        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
                self.after(200, lambda: self.wm_iconbitmap(icon_path))
            except:
                pass

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.setup_sidebar()
        self.setup_main_area()

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0); self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="CONFIGURACIÓN", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)
        self.threshold_entry = self.create_input_with_presets("Umbral de Alerta (%)", "1.0", [("1%", 1.0), ("2%", 2.0), ("3%", 3.0), ("5%", 5.0)])
        self.interval_entry = self.create_input_with_presets("Intervalo Consulta (seg)", "30", [("30s", 30), ("1m", 60), ("5m", 300), ("10m", 600)])
        self.cooldown_entry = self.create_input_with_presets("Cooldown Alertas (seg)", "300", [("5m", 300), ("10m", 600), ("15m", 900), ("30m", 1800)])
        
        ctk.CTkLabel(self.sidebar, text="TASA COSTO OPORTUNIDAD", font=ctk.CTkFont(size=13, weight="bold"), text_color="#3BD0C9").pack(pady=(10, 5))
        self.tasa_selector = ctk.CTkOptionMenu(self.sidebar, values=list(self.tasas_disponibles.keys()), fg_color="#333", button_color="#444")
        self.tasa_selector.set("Ninguna (0%)")
        self.tasa_selector.pack(pady=5, padx=20, fill="x")

        self.only_best_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self.sidebar, text="Telegram: Solo la más alta", variable=self.only_best_var).pack(pady=10, padx=20, anchor="w")
        
        self.btn_config_tg = ctk.CTkButton(self.sidebar, text="⚙️ Configurar Telegram", fg_color="#444", command=self.open_telegram_config)
        self.btn_config_tg.pack(pady=5, padx=20, fill="x")

        self.ex_scroll = ctk.CTkScrollableFrame(self.sidebar, height=200, fg_color="transparent"); self.ex_scroll.pack(fill="both", expand=True, padx=10, pady=5)
        self.exchange_vars = {}; self.bridge_vars = {} 
        ctk.CTkLabel(self.ex_scroll, text="--- CRIPTO ---", font=ctk.CTkFont(size=10, slant="italic")).pack()
        self.create_bulk_buttons(self.ex_scroll, "cripto")
        for eid, name in CRIPTO_EXCHANGES.items(): self.create_check(eid, name, self.exchange_vars)
        ctk.CTkLabel(self.ex_scroll, text="--- OFICIAL ---", font=ctk.CTkFont(size=10, slant="italic")).pack(pady=(15,0))
        self.create_bulk_buttons(self.ex_scroll, "oficial")
        for eid, name in OFICIAL_ENTITIES.items(): self.create_check(f"oficial_{eid}", name, self.exchange_vars)
        ctk.CTkLabel(self.ex_scroll, text="--- PUENTE (USD) ---", font=ctk.CTkFont(size=10, slant="italic"), text_color="#3b8ed0").pack(pady=(15,0))
        self.create_bulk_buttons(self.ex_scroll, "bridge")
        for eid, name in BRIDGE_LIST.items(): self.create_check(eid, name, self.bridge_vars)
        
        self.btn_toggle = ctk.CTkButton(self.sidebar, text="INICIAR BOT", fg_color="#28a745", height=45, command=self.toggle_bot, font=ctk.CTkFont(weight="bold"))
        self.btn_toggle.pack(pady=20, padx=20, fill="x")

    def open_telegram_config(self):
        from src.settings import load_settings, save_settings
        config_win = ctk.CTkToplevel(self)
        config_win.title("Configuración de Telegram")
        config_win.geometry("400x320")
        config_win.grab_set()
        
        settings = load_settings()
        
        ctk.CTkLabel(config_win, text="Telegram Bot Token:").pack(pady=(20, 5))
        token_entry = ctk.CTkEntry(config_win, width=300)
        token_entry.pack()
        token_entry.insert(0, settings.get("telegram_token", ""))
        
        ctk.CTkLabel(config_win, text="Chat ID:").pack(pady=(10, 5))
        chat_entry = ctk.CTkEntry(config_win, width=300)
        chat_entry.pack()
        chat_entry.insert(0, settings.get("chat_id", ""))
        
        ctk.CTkLabel(config_win, text="Capital Inicial (USD):").pack(pady=(10, 5))
        capital_entry = ctk.CTkEntry(config_win, width=300)
        capital_entry.pack()
        capital_entry.insert(0, str(settings.get("capital_usd", 1000.0)))
        
        def save_and_close():
            new_settings = load_settings()
            new_settings["telegram_token"] = token_entry.get().strip()
            new_settings["chat_id"] = chat_entry.get().strip()
            try:
                new_settings["capital_usd"] = float(capital_entry.get().strip())
            except:
                pass
            save_settings(new_settings)
            self.notifier.reload_config()
            config_win.destroy()
            
        ctk.CTkButton(config_win, text="Guardar", command=save_and_close, fg_color="#28a745").pack(pady=20)

    def create_bulk_buttons(self, parent, group):
        f = ctk.CTkFrame(parent, fg_color="transparent"); f.pack(fill="x", pady=2)
        ctk.CTkButton(f, text="Todos", width=60, height=18, font=ctk.CTkFont(size=9), fg_color="#333", command=lambda: self.toggle_group_vars(group, True)).pack(side="left", padx=(10, 5))
        ctk.CTkButton(f, text="Ninguno", width=60, height=18, font=ctk.CTkFont(size=9), fg_color="#333", command=lambda: self.toggle_group_vars(group, False)).pack(side="left")

    def toggle_group_vars(self, group, state):
        target = self.bridge_vars if group == "bridge" else self.exchange_vars
        for k, v in target.items():
            if group == "bridge" or (group == "oficial" and k.startswith("oficial_")) or (group == "cripto" and not k.startswith("oficial_")): v.set(state)

    def create_input_with_presets(self, label, default, presets):
        c = ctk.CTkFrame(self.sidebar, fg_color="transparent"); c.pack(fill="x", pady=5); ctk.CTkLabel(c, text=label).pack()
        e = ctk.CTkEntry(c, justify="center", width=120); e.insert(0, default); e.pack(pady=2)
        p = ctk.CTkFrame(c, fg_color="transparent"); p.pack()
        for t, v in presets: ctk.CTkButton(p, text=t, width=42, height=22, font=ctk.CTkFont(size=10), fg_color="#333", command=lambda val=v, ent=e: (ent.delete(0, "end"), ent.insert(0, str(val)))).pack(side="left", padx=2)
        return e
    
    def create_check(self, internal_id, name, target_dict):
        f = ctk.CTkFrame(self.ex_scroll, fg_color="transparent"); f.pack(fill="x", pady=1); var = ctk.BooleanVar(value=True); target_dict[internal_id] = var
        try:
            img = ctk.CTkImage(Image.open(resource_path(f"logos/{name}.png")), size=(20, 20))
            ctk.CTkLabel(f, image=img, text="").pack(side="left", padx=5)
        except: pass
        ctk.CTkCheckBox(f, text=name, variable=var, font=ctk.CTkFont(size=11)).pack(side="left")

    def setup_main_area(self):
        self.status_bar = ctk.CTkFrame(self, height=40, fg_color="#1a1a1a"); self.status_bar.grid(row=0, column=1, sticky="new", padx=10, pady=(10, 0))
        self.status_label = ctk.CTkLabel(self.status_bar, text="Bot detenido.", font=ctk.CTkFont(weight="bold")); self.status_label.pack(side="left", padx=20)
        self.tabview = ctk.CTkTabview(self, fg_color="#0a0a0a"); self.tabview.grid(row=0, column=1, padx=10, pady=(55, 10), sticky="nsew")
        self.tabs_map = {"USDT": self.tabview.add("USDT (CriptoYa)"), "OFICIAL": self.tabview.add("OFICIAL (ComparaDolar)"), "MIX": self.tabview.add("OFICIAL vs USDT"), "MEP_USDT": self.tabview.add("MEP vs USDT"), "OFICIAL_MEP": self.tabview.add("OFICIAL vs MEP"), "USDT_MEP": self.tabview.add("USDT vs MEP"), "TRIANGULAR": self.tabview.add("TRIANGULAR")}
        self.containers = {k: ctk.CTkScrollableFrame(v, fg_color="transparent") for k, v in self.tabs_map.items()}
        for c in self.containers.values(): c.pack(fill="both", expand=True)

    def toggle_bot(self):
        if not self.is_running:
            self.is_running = True
            self.btn_toggle.configure(text="DETENER BOT", fg_color="#dc3545")
            threading.Thread(target=self.main_loop, daemon=True).start()
            self.update_countdown_ui()
        else:
            self.is_running = False
            self.btn_toggle.configure(text="INICIAR BOT", fg_color="#28a745")

    def update_countdown_ui(self):
        if not self.is_running: 
            self.status_label.configure(text="Bot detenido.")
            return
        restance = int(max(0, self.proxima_actualizacion - time.time()))
        self.status_label.configure(text=f"Próxima actualización en: {restance}s")
        self.after(1000, self.update_countdown_ui)

    def clear_container(self, cat):
        for w in self.containers[cat].winfo_children(): w.destroy()
        
    def main_loop(self):
        import concurrent.futures
        while self.is_running:
            try:
                interval = int(self.interval_entry.get())
                self.proxima_actualizacion = time.time() + interval
                keys = [k for k, v in self.exchange_vars.items() if v.get()]
                bridges_keys = [k for k, v in self.bridge_vars.items() if v.get()]
                threshold = float(self.threshold_entry.get())
                y_diario = (self.tasas_disponibles.get(self.tasa_selector.get(), 0.0) / 100) / 365 
                cooldown_secs = float(self.cooldown_entry.get())
                only_best = self.only_best_var.get()
                
                from src.settings import load_settings
                settings = load_settings()
                capital = float(settings.get("capital_usd", 1000.0))

                for cat in self.containers: self.after(0, lambda c=cat: self.clear_container(c))

                p_oficial = self.api_client.fetch_oficial_api([k for k in keys if k.startswith("oficial_")])
                p_mep = self.api_client.fetch_mep_full()
                fees = self.api_client.fetch_fees()
                
                # Fetch coins for standard and triangular (max 2 workers to avoid 429)
                cripto_keys = [k for k in keys if not k.startswith("oficial_")]
                coins_to_fetch = ["usdt", "btc", "eth", "usdc", "dai"]
                coin_precios = {}
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as exe:
                    futures = {exe.submit(self.api_client.fetch_coin_criptoya, cripto_keys, c): c for c in coins_to_fetch}
                    for f in concurrent.futures.as_completed(futures):
                        coin_precios[futures[f]] = f.result()
                        
                p_usdt = coin_precios.get("usdt", {})
                binance_tickers = self.api_client.fetch_binance_tickers()

                all_alerts = []

                cards, alerts = self.analyzer.analyze_standard(p_usdt, threshold, "USDT", fees=fees, capital_usd=capital)
                self.render_cards("USDT", cards)
                all_alerts.extend(alerts)
                
                # Triangular analyze
                cards_tri = self.analyzer.analyze_triangular(coin_precios, binance_tickers, fees, threshold, capital_usd=capital)
                self.render_cards("TRIANGULAR", cards_tri)

                cards, alerts = self.analyzer.analyze_standard(p_oficial, threshold, "OFICIAL")
                self.render_cards("OFICIAL", cards)
                all_alerts.extend(alerts)

                cards, alerts = self.analyzer.analyze_oficial_mep(p_oficial, p_mep, threshold, y_diario)
                self.render_cards("OFICIAL_MEP", cards)
                all_alerts.extend(alerts)
                
                if bridges_keys:
                    raw_parities = self.api_client.fetch_parities(bridges_keys)
                    parities = {}
                    for ex, (n, a, b) in raw_parities.items():
                        if a: parities[ex] = {"ask": a, "bid": b, "name": BRIDGE_LIST.get(ex, ex.capitalize())}
                            
                    if parities:
                        b_ask = min(parities.values(), key=lambda x: x["ask"])
                        cards, alerts = self.analyzer.analyze_cross(p_oficial, p_usdt, b_ask, threshold, "MIX")
                        self.render_cards("MIX", cards)
                        all_alerts.extend(alerts)
                        
                        cards, alerts = self.analyzer.analyze_cross_mep(p_mep, p_usdt, b_ask, threshold, "MEP_USDT")
                        self.render_cards("MEP_USDT", cards)
                        all_alerts.extend(alerts)
                        
                        b_bid = max(parities.values(), key=lambda x: x["bid"])
                        cards, alerts = self.analyzer.analyze_usdt_mep(p_usdt, p_mep, b_bid, threshold, y_diario)
                        self.render_cards("USDT_MEP", cards)
                        all_alerts.extend(alerts)

                self.notifier.process_alerts(all_alerts, cooldown_secs, only_best)

                while time.time() < self.proxima_actualizacion and self.is_running: time.sleep(0.5)
            except Exception as e:
                import traceback
                traceback.print_exc()
                time.sleep(2)
                
    def render_cards(self, cat, cards):
        for card_data in cards:
            self.after(0, lambda c=card_data: self._ui_render_card(self.containers[cat], c))

    def _ui_render_card(self, container, c_data):
        ex1 = c_data["ex1"]; ex2 = c_data["ex2"]
        d1 = c_data["d1"]; d2 = c_data["d2"]
        spread = c_data["spread"]; cat = c_data["cat"]
        is_m = c_data["is_m"]
        try:
            card = ctk.CTkFrame(container, fg_color="#161616", corner_radius=12, border_width=1, border_color="#555" if is_m else "#333")
            card.pack(fill="x", pady=8, padx=10, side="top")
            h = ctk.CTkFrame(card, fg_color="transparent"); h.pack(fill="x", padx=15, pady=8)
            bh = ctk.CTkFrame(h, fg_color="#2b2b2b" if is_m else "#1e8449", corner_radius=6); bh.pack(side="left")
            ctk.CTkLabel(bh, text="MERCADO" if is_m else "OPORTUNIDAD", font=ctk.CTkFont(weight="bold", size=13)).pack(padx=10, pady=2)
            ctk.CTkLabel(h, text=datetime.now().strftime("%H:%M:%S"), font=ctk.CTkFont(size=11), text_color="#666").pack(side="right")
            body = ctk.CTkFrame(card, fg_color="transparent"); body.pack(fill="x", padx=10, pady=10)
            if cat.startswith("TRIANGULAR"):
                body.grid_columnconfigure((0,1,2,3), weight=1, uniform="group")
            else:
                body.grid_columnconfigure((0,1,2), weight=1, uniform="group")
            
            def box_ui(parent, name, p_data, txt, color, is_sell, col):
                b = ctk.CTkFrame(parent, fg_color="#222", corner_radius=10, border_width=1, border_color="#444"); b.grid(row=0, column=col, sticky="nsew", padx=5)
                try:
                    clean = name.split(' (')[0].replace('á', 'a')
                    img = ctk.CTkImage(Image.open(resource_path(f"logos/{clean}.png")), size=(34, 34))
                    ctk.CTkLabel(b, image=img, text="").pack(pady=(10,0))
                except: pass
                ctk.CTkLabel(b, text=name, font=ctk.CTkFont(size=11, weight="bold")).pack()
                val_p = p_data['bid'] if is_sell else p_data['ask']
                ctk.CTkLabel(b, text=f"${val_p:,.2f}", font=ctk.CTkFont(size=16, weight="bold"), text_color=color).pack()
                if is_sell and "mep_24" in p_data: ctk.CTkLabel(b, text=f"CI: ${p_data['bid']:,.2f}\n24h: ${p_data['mep_24']:,.2f}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#aaa").pack(pady=(5, 10))
                elif not is_sell and "bridge_name" in p_data:
                    info = f"{'USDT' if '(U)' in name else 'Banco'}: ${p_data['raw_price']:,.2f}\nvia {p_data['bridge_name']} (x{p_data['parity']})"
                    ctk.CTkLabel(b, text=info, font=ctk.CTkFont(size=11), text_color="#aaa").pack(pady=(5, 10))
                else: 
                    fee_txt = f"\n(Fee: {p_data.get('fee', 0):.4f})" if "fee" in p_data else ""
                    ctk.CTkLabel(b, text=txt + fee_txt, font=ctk.CTkFont(size=10), text_color="#555").pack(pady=(2, 8))
                
            start_coin_txt = f"COMPRA {d1.get('coin', '')}".strip()
            box_ui(body, ex1, d1, start_coin_txt, "#28a745", False, 0)
            
            if cat.startswith("TRIANGULAR") and "extra" in c_data:
                extra = c_data["extra"]
                mid = ctk.CTkFrame(body, fg_color="transparent")
                mid.grid(row=0, column=1, padx=5, sticky="nsew")
                
                # We can have up to 3 Binance steps. Pack them in nice boxes.
                step_idx = 1
                for step in extra["steps"]:
                    operacion = "Vender" if step["action"] == "Bid" else "Comprar"
                    precio = step['rate']
                    
                    # Create a small frame for each step
                    f_step = ctk.CTkFrame(mid, fg_color="#2a2a2a", corner_radius=6)
                    f_step.pack(fill="x", pady=2, padx=5)
                    
                    title = f"Paso {step_idx}: {step['from']} ➔ {step['to']}"
                    
                    if precio < 10:
                        sub = f"{operacion} en Binance a {precio:,.6f}"
                    else:
                        sub = f"{operacion} en Binance a {precio:,.2f}"
                    
                    ctk.CTkLabel(f_step, text=title, font=ctk.CTkFont(size=12, weight="bold"), text_color="#ddd").pack(pady=(3, 0))
                    ctk.CTkLabel(f_step, text=sub, font=ctk.CTkFont(size=10), text_color="#aaa").pack(pady=(0, 3))
                    step_idx += 1
                    
                box_ui(body, ex2, d2, "VENTA USDT", "#e74c3c", True, 2)
                s_box = ctk.CTkFrame(body, fg_color="transparent"); s_box.grid(row=0, column=3, padx=10, sticky="nsew")
                one_box = ctk.CTkFrame(s_box, fg_color="#3b8ed0", corner_radius=15); one_box.pack(fill="both", expand=True)
                ctk.CTkLabel(one_box, text="PROFIT TOTAL", font=ctk.CTkFont(size=11, weight="bold"), text_color="black").pack(expand=True, pady=(15,0))
                ctk.CTkLabel(one_box, text=f"{spread:.2f}%", font=ctk.CTkFont(size=28, weight="bold"), text_color="black").pack(expand=True, pady=(0,20))
            else:
                box_ui(body, ex2, d2, "VENTA", "#e74c3c", True, 2)
                s_box = ctk.CTkFrame(body, fg_color="transparent"); s_box.grid(row=0, column=1, padx=10, sticky="nsew")
                if isinstance(spread, dict):
                    top = ctk.CTkFrame(s_box, fg_color="#3b8ed0", corner_radius=15); top.pack(fill="both", expand=True, pady=(0, 2))
                    ctk.CTkLabel(top, text="PROFIT CI", font=ctk.CTkFont(size=10, weight="bold"), text_color="black").pack(pady=(8,0))
                    ctk.CTkLabel(top, text=f"{spread['ci']:.2f}%", font=ctk.CTkFont(size=20, weight="bold"), text_color="black").pack()
                    bot = ctk.CTkFrame(s_box, fg_color="#3BD0C9", corner_radius=15); bot.pack(fill="both", expand=True)
                    ctk.CTkLabel(bot, text="PROFIT 24H", font=ctk.CTkFont(size=10, weight="bold"), text_color="black").pack(pady=(5,0))
                    ctk.CTkLabel(bot, text=f"{spread['24h']:.2f}%", font=ctk.CTkFont(size=20, weight="bold"), text_color="black").pack(pady=(0,8))
                else:
                    one_box = ctk.CTkFrame(s_box, fg_color="#3b8ed0", corner_radius=15); one_box.pack(fill="both", expand=True)
                    ctk.CTkLabel(one_box, text="PROFIT TOTAL", font=ctk.CTkFont(size=11, weight="bold"), text_color="black").pack(expand=True, pady=(15,0))
                    ctk.CTkLabel(one_box, text=f"{spread:.2f}%", font=ctk.CTkFont(size=28, weight="bold"), text_color="black").pack(expand=True, pady=(0,20))
        except: pass
