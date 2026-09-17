from itertools import permutations

class ArbitrageAnalyzer:
    def analyze_standard(self, precios, threshold, cat, fees=None, capital_usd=1000.0):
        cards = []
        alerts = []
        fees = fees or {}
        if not precios: return cards, alerts
        
        ex_min, ex_max = min(precios, key=lambda x: precios[x]["ask"]), max(precios, key=lambda x: precios[x]["bid"])
        
        # Calculate real spread with fees if applicable
        fee_usdt = fees.get(ex_min.lower(), {}).get("USDT", 0) if cat == "USDT" else 0
        capital_ars = capital_usd * precios[ex_min]["ask"]
        usdt_bought = capital_usd
        usdt_received = usdt_bought - fee_usdt
        ars_received = usdt_received * precios[ex_max]["bid"]
        spread = (ars_received - capital_ars) / capital_ars * 100
        
        d1_mod = precios[ex_min].copy()
        if fee_usdt: d1_mod["fee"] = fee_usdt
        
        cards.append({"ex1": ex_min, "ex2": ex_max, "d1": d1_mod, "d2": precios[ex_max], "spread": spread, "cat": cat, "is_m": True})
        
        for ex1, ex2 in permutations(precios.keys(), 2):
            ask, bid = precios[ex1]["ask"], precios[ex2]["bid"]
            
            f_usdt = fees.get(ex1.lower(), {}).get("USDT", 0) if cat == "USDT" else 0
            u_bought = capital_usd
            u_received = u_bought - f_usdt
            c_ars = u_bought * ask
            a_received = u_received * bid
            gain = (a_received - c_ars) / c_ars * 100
            
            if gain >= threshold:
                d1 = precios[ex1].copy()
                if f_usdt: d1["fee"] = f_usdt
                cards.append({"ex1": ex1, "ex2": ex2, "d1": d1, "d2": precios[ex2], "spread": gain, "cat": cat, "is_m": False})
                alerts.append({"cat": cat, "ex1": ex1, "ex2": ex2, "ask": ask, "bid": bid, "gain": gain})
                
        return cards, alerts

    def analyze_triangular(self, coin_precios, binance_tickers, fees, threshold, capital_usd=1000.0):
        cards = []
        usdt_precios = coin_precios.get("usdt", {})
        if not usdt_precios or not binance_tickers: return cards
        
        ex_min_usdt = min(usdt_precios, key=lambda x: usdt_precios[x]["ask"])
        capital_ars = capital_usd * usdt_precios[ex_min_usdt]["ask"]

        from itertools import permutations
        coins = ["BTC", "ETH", "USDC", "DAI"]
        
        def get_binance_rate(c_from, c_to):
            pair1 = c_from + c_to
            if pair1 in binance_tickers:
                return binance_tickers[pair1]["bid"], "Bid", pair1
            pair2 = c_to + c_from
            if pair2 in binance_tickers and binance_tickers[pair2]["ask"] > 0:
                return 1.0 / binance_tickers[pair2]["ask"], "Ask", pair2
            return None, None, None

        all_combinations = []
        
        for length in [1, 2, 3]:
            for seq in permutations(coins, length):
                valid_path = True
                binance_steps = []
                current_coin = seq[0]
                multiplier = 1.0
                
                for next_coin in list(seq[1:]) + ["USDT"]:
                    rate, action, pair = get_binance_rate(current_coin, next_coin)
                    if rate is None or rate <= 0:
                        valid_path = False
                        break
                    
                    rate_after_fee = rate * 0.999 # 0.1% binance spot fee
                    multiplier *= rate_after_fee
                    
                    # Store original rate for display
                    disp_rate = binance_tickers[pair]["bid"] if action == "Bid" else binance_tickers[pair]["ask"]
                    binance_steps.append({
                        "from": current_coin, "to": next_coin, 
                        "pair": pair, "action": action, "rate": float(disp_rate)
                    })
                    current_coin = next_coin
                    
                if not valid_path: continue
                
                c_start = seq[0].lower()
                start_precios = coin_precios.get(c_start, {})
                for ex1, p_start in start_precios.items():
                    start_ask = p_start["ask"]
                    if start_ask <= 0: continue
                    start_fee = fees.get(ex1.lower(), {}).get(seq[0], 0.0)
                    if start_fee == 0.0 and seq[0] in ["BTC", "ETH"]: start_fee = 0.0005
                    
                    c_bought = capital_ars / start_ask
                    c_received = c_bought - start_fee
                    if c_received <= 0: continue
                    
                    usdt_received = c_received * multiplier
                    usdt_transferred = usdt_received - 0.5
                    if usdt_transferred <= 0: continue
                    
                    for ex2, p_usdt in usdt_precios.items():
                        ars_bid = p_usdt["bid"]
                        ars_final = usdt_transferred * ars_bid
                        profit = (ars_final - capital_ars) / capital_ars * 100
                        
                        card = {
                            "ex1": ex1, "ex2": ex2, 
                            "d1": {"ask": start_ask, "fee": start_fee, "coin": seq[0]}, 
                            "d2": {"bid": ars_bid}, 
                            "spread": profit, 
                            "cat": f"TRIANGULAR ({len(seq)+1} SALTOS)", 
                            "is_m": False,
                            "extra": {"steps": binance_steps, "start_coin": seq[0]}
                        }
                        all_combinations.append(card)
                        if profit >= threshold:
                            cards.append(card)
                            
        if all_combinations:
            best = max(all_combinations, key=lambda x: x["spread"])
            best_market = best.copy()
            best_market["is_m"] = True
            cards.append(best_market)
            
        cards.sort(key=lambda x: (x["is_m"], x["spread"]), reverse=True)
        return cards[:15]

    def analyze_oficial_mep(self, p_oficial, p_mep, threshold, y_diario):
        cards = []; alerts = []
        if not p_oficial or not p_mep: return cards, alerts
        
        dest = {"bid": p_mep["ci"], "mep_24": p_mep["24hs"]}
        best = min(p_oficial, key=lambda x: p_oficial[x]["ask"])
        price_best = p_oficial[best]["ask"]
        s_ci = (dest["bid"] - price_best) / price_best * 100
        s_24 = (((dest["mep_24"] - price_best) / price_best) - y_diario) * 100
        cards.append({"ex1": best, "ex2": "Dolar MEP (M)", "d1": p_oficial[best], "d2": dest, "spread": {"ci": s_ci, "24h": s_24}, "cat": "OFICIAL_MEP", "is_m": True})
        
        for name, p in p_oficial.items():
            g_ci = (dest["bid"] - p["ask"]) / p["ask"] * 100
            g_24 = (((dest["mep_24"] - p["ask"]) / p["ask"]) - y_diario) * 100
            if g_ci >= threshold or g_24 >= threshold:
                cards.append({"ex1": name, "ex2": "Dolar MEP (M)", "d1": p, "d2": dest, "spread": {"ci": g_ci, "24h": g_24}, "cat": "OFICIAL_MEP", "is_m": False})
                alerts.append({"cat": "OFICIAL_MEP", "ex1": name, "ex2": "MEP", "ask": p["ask"], "bid": dest["bid"], "gain": max(g_ci, g_24)})
                
        return cards, alerts

    def analyze_cross(self, p_oficial, p_usdt, bridge, threshold, cat):
        cards = []; alerts = []
        if not p_oficial or not p_usdt: return cards, alerts
        
        src = {f"{n} (O)": {"ask": p["ask"] * bridge["ask"], "raw_price": p["ask"], "bridge_name": bridge["name"], "parity": bridge["ask"]} for n, p in p_oficial.items()}
        b_s = min(src, key=lambda x: src[x]["ask"])
        b_d = max(p_usdt, key=lambda x: p_usdt[x]["bid"])
        spread = (p_usdt[b_d]["bid"] - src[b_s]["ask"]) / src[b_s]["ask"] * 100
        cards.append({"ex1": b_s, "ex2": b_d, "d1": src[b_s], "d2": p_usdt[b_d], "spread": spread, "cat": cat, "is_m": True})
        
        for s_n, s_d in src.items():
            for c_n, c_d in p_usdt.items():
                gain = (c_d["bid"] - s_d["ask"]) / s_d["ask"] * 100
                if gain >= threshold:
                    cards.append({"ex1": s_n, "ex2": c_n, "d1": s_d, "d2": c_d, "spread": gain, "cat": cat, "is_m": False})
                    alerts.append({"cat": cat, "ex1": s_n, "ex2": c_n, "ask": s_d["ask"], "bid": c_d["bid"], "gain": gain})
                    
        return cards, alerts

    def analyze_cross_mep(self, p_mep, p_usdt, bridge, threshold, cat):
        cards = []; alerts = []
        if not p_mep or not p_usdt: return cards, alerts
        
        s_d = {"ask": p_mep["ci"] * bridge["ask"], "raw_price": p_mep["ci"], "bridge_name": bridge["name"], "parity": bridge["ask"]}
        b_d = max(p_usdt, key=lambda x: p_usdt[x]["bid"])
        spread = (p_usdt[b_d]["bid"] - s_d["ask"]) / s_d["ask"] * 100
        cards.append({"ex1": "Dolar MEP (M)", "ex2": b_d, "d1": s_d, "d2": p_usdt[b_d], "spread": spread, "cat": cat, "is_m": True})
        return cards, alerts

    def analyze_usdt_mep(self, p_usdt, p_mep, bridge, threshold, y_diario):
        cards = []; alerts = []
        if not p_usdt or not p_mep: return cards, alerts
        
        dest = {"bid": p_mep["ci"], "mep_24": p_mep["24hs"]}
        best = min(p_usdt, key=lambda x: p_usdt[x]["ask"])
        costo_b = p_usdt[best]["ask"] / bridge["bid"]
        s_ci = (dest["bid"] - costo_b) / costo_b * 100
        s_24 = (((dest["mep_24"] - costo_b) / costo_b) - y_diario) * 100
        item_b = {"ask": costo_b, "raw_price": p_usdt[best]["ask"], "bridge_name": bridge["name"], "parity": bridge["bid"]}
        cards.append({"ex1": f"{best} (U)", "ex2": "Dolar MEP (M)", "d1": item_b, "d2": dest, "spread": {"ci": s_ci, "24h": s_24}, "cat": "USDT_MEP", "is_m": True})
        
        for name, p in p_usdt.items():
            costo = p["ask"] / bridge["bid"]
            g_ci = (dest["bid"] - costo) / costo * 100
            g_24 = (((dest["mep_24"] - costo) / costo) - y_diario) * 100
            if g_ci >= threshold or g_24 >= threshold:
                item_s = {"ask": costo, "raw_price": p["ask"], "bridge_name": bridge["name"], "parity": bridge["bid"]}
                cards.append({"ex1": f"{name} (U)", "ex2": "Dolar MEP (M)", "d1": item_s, "d2": dest, "spread": {"ci": g_ci, "24h": g_24}, "cat": "USDT_MEP", "is_m": False})
                alerts.append({"cat": "USDT_MEP", "ex1": name, "ex2": "MEP", "ask": costo, "bid": dest["bid"], "gain": max(g_ci, g_24)})
                
        return cards, alerts
