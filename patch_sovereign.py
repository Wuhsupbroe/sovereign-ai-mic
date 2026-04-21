import re
import os

with open('dictation.py', 'r', encoding='utf-8') as f:
    text = f.read()

# ─────────────────────────────────────────────────────────────────────────────
# 1. Update Constants
# ─────────────────────────────────────────────────────────────────────────────
text = text.replace('WIN_BG      = "#1c1c1e"', 'WIN_BG      = "#121212"')
text = text.replace('SIDEBAR_BG  = "#141416"', 'SIDEBAR_BG  = "#111111"')
text = text.replace('CONTENT_BG  = "#1c1c1e"', 'CONTENT_BG  = "#151515"')
text = text.replace('CARD_BG     = "#212124"', 'CARD_BG     = "#1A1D1A"')
text = text.replace('CARD_HOVER  = "#3a3a3c"', 'CARD_HOVER  = "#2a2c2a"')

# Change Title & Labels
text = text.replace('text="AI Dictator"', 'text="Sovereign AI v3.4 ACTIVE"')
text = text.replace('label_small="AI Dictator"', 'label_small="Sovereign AI"')

# ─────────────────────────────────────────────────────────────────────────────
# 2. Update Sidebar Navigation
# ─────────────────────────────────────────────────────────────────────────────
sidebar_old = """        nav_items = [
            ("stats",      "⊙",  "Dashboard"),
            ("dictations", "⌨",  "Dictations"),
            ("ai",         "◉",  "AI Assistant"),
            ("codeword",   "⚡", "Codeword"),
            ("settings",   "◈",  "Settings"),
        ]"""
sidebar_new = """        nav_items = [
            ("stats",      "🧠", "Intelligence"),
            ("dictations", "🎤", "Vocalize"),
            ("ai",         "💾", "Archives"),
            ("codeword",   "🛡", "Protocols"),
            ("settings",   "⚙",  "Settings"),
        ]"""
text = text.replace(sidebar_old, sidebar_new)

# Update sidebar selection highlighting (Rule 6 in dictation.py)
# We want full edge-to-edge dark green for ACTIVE items.
sel_old = """    def _select_nav(self, key):
        \"\"\"Apply source-list selection: rounded highlight + accent bar (Rule 6).\"\"\"
        for k, item in self._nav_btns.items():
            sel = (k == key)
            bg      = ACCENT_LITE  if sel else SIDEBAR_BG
            bar_bg  = ACCENT       if sel else SIDEBAR_BG
            fg_icon = ACCENT       if sel else T_TER
            fg_text = ACCENT_TEXT  if sel else T_SEC
            font    = ("Helvetica Neue", 12, "bold") if sel else ("Helvetica Neue", 12)
            try:
                item["pill"].configure(fg_color=bg)
                for w in [item["outer"], item["bar"]]:
                    w.configure(bg=bg)
                item["bar"].configure(bg=bar_bg)
                item["icon"].configure(fg_icon=fg_icon, bg=bg)
                item["text"].configure(fg_text=fg_text, bg=bg, font=font)
            except Exception:
                pass
        self._nav_selected = key"""
sel_new = """    def _select_nav(self, key):
        for k, item in self._nav_btns.items():
            sel = (k == key)
            # Sovereign UI: deep green bg for active edge-to-edge
            bg      = "#1c3321"   if sel else SIDEBAR_BG
            bar_bg  = "#30d158"   if sel else SIDEBAR_BG
            fg_icon = "#30d158"   if sel else T_TER
            fg_text = "#30d158"   if sel else T_SEC
            font    = ("Helvetica Neue", 12, "bold") if sel else ("Helvetica Neue", 12)
            item["pill"].configure(fg_color=bg, corner_radius=0)
            try:
                for w in [item["outer"], item["bar"], item["icon"], item["text"]]:
                    try: w.configure(bg=bg)
                    except: pass
                item["bar"].configure(bg=bar_bg)
                item["icon"].configure(fg=fg_icon)
                item["text"].configure(fg=fg_text, font=font)
            except Exception: pass
        self._nav_selected = key"""

text = text.replace(sel_old, sel_new)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Rewrite _make_stats_page / Dashboard
# ─────────────────────────────────────────────────────────────────────────────
stats_start = text.find('    def _make_stats_page(self):')
stats_end = text.find('    # ════════════════════════════════════════════════════════════════════════════\n    #  Dictations page')

stats_code = """    def _make_stats_page(self):
        page = ctk.CTkFrame(self._content, fg_color=CONTENT_BG)

        # ── 1. Integrated Pill Header ─────────────────────────────────────────────
        top_card = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=25)
        top_card.pack(fill="x", padx=24, pady=(20, 14), ipady=20)

        ctk.CTkLabel(top_card, text="Awaiting Command", text_color="#ffffff", font=ctk.CTkFont("Helvetica Neue", 14, "bold")).pack(pady=(15, 0))
        
        # Audio Visualizer Canvas
        self._dash_pill_cv = tk.Canvas(top_card, width=PILL_W, height=PILL_H, bg=CARD_BG, highlightthickness=0)
        self._dash_pill_cv.pack(pady=5)
        self._dash_pill_bg_img = ImageTk.PhotoImage(Image.new("RGB", (PILL_W, PILL_H), _hex_to_rgb(CARD_BG)))
        self._dash_pill_cv_id = self._dash_pill_cv.create_image(0, 0, anchor="nw", image=self._dash_pill_bg_img)

        ctk.CTkLabel(top_card, text="MONITORING ACTIVE SESSION 092", text_color="#30d158", font=ctk.CTkFont("Helvetica Neue", 13, "bold")).pack(pady=(0, 15))

        # ── 2. Middle Row: Stats + Voice Profile ──────────────────────────────────
        mid_row = tk.Frame(page, bg=CONTENT_BG)
        mid_row.pack(fill="x", padx=24)

        # Words
        w_card = self._card(mid_row)
        w_card.pack(side="left", expand=True, fill="both", padx=(0, 8))
        self._donut_words = DonutChart(w_card, size=150, bg=CARD_BG)
        self._donut_words.pack(pady=20)

        # Sessions
        s_card = self._card(mid_row)
        s_card.pack(side="left", expand=True, fill="both", padx=(8, 8))
        self._donut_sessions = DonutChart(s_card, size=150, bg=CARD_BG)
        self._donut_sessions.pack(pady=20)

        # Active Voice Profile (Sovereign Theme)
        v_card = self._card(mid_row)
        v_card.pack(side="left", expand=True, fill="both", padx=(8, 0))
        tk.Frame(v_card, bg=CARD_BG, height=20).pack()  # Spacer
        ctk.CTkLabel(v_card, text="ACTIVE VOICE PROFILE", text_color="#98989e", font=ctk.CTkFont("Helvetica Neue", 12, "bold")).pack(anchor="w", padx=20)
        
        v_inner = tk.Frame(v_card, bg=CARD_BG)
        v_inner.pack(fill="both", expand=True, padx=20, pady=15)
        
        av_cv = tk.Canvas(v_inner, width=50, height=50, bg=CARD_BG, highlightthickness=0)
        av_cv.pack(side="left", padx=(0,14))
        av_cv.create_oval(2, 2, 48, 48, outline="#30d158", width=2)
        
        vtext = tk.Frame(v_inner, bg=CARD_BG)
        vtext.pack(side="left")
        ctk.CTkLabel(vtext, text="Ares Core", text_color="#e5e5e5", font=ctk.CTkFont("Helvetica Neue", 18, "bold")).pack(anchor="w")
        ctk.CTkLabel(vtext, text="Authoritative / Deep", text_color="#98989e", font=ctk.CTkFont("Helvetica Neue", 11)).pack(anchor="w")

        # ── 3. Bottom Row: Intercepts + Engine ────────────────────────────────────
        bot_row = tk.Frame(page, bg=CONTENT_BG)
        bot_row.pack(fill="both", expand=True, padx=24, pady=14)

        # Intercepts Left
        int_card = self._card(bot_row)
        int_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Frame(int_card, bg=CARD_BG, height=15).pack()
        ctk.CTkLabel(int_card, text="RECENT INTELLIGENCE INTERCEPTS", text_color="#98989e", font=ctk.CTkFont("Helvetica Neue", 12, "bold")).pack(anchor="w", padx=20, pady=5)
        self._log_inner = tk.Frame(int_card, bg=CARD_BG)
        self._log_inner.pack(fill="both", expand=True, padx=16, pady=5)

        # Engine Right
        eng_card = tk.Frame(bot_row, bg=CONTENT_BG)
        eng_card.pack(side="left", fill="both", padx=(8, 0))
        
        te_card = self._card(eng_card)
        te_card.pack(fill="x", pady=(0, 7))
        tk.Frame(te_card, bg=CARD_BG, height=10).pack()
        ctk.CTkLabel(te_card, text="TRANSCRIPTION ENGINE", text_color="#98989e", font=ctk.CTkFont("Helvetica Neue", 11, "bold")).pack(anchor="w", padx=16, pady=5)
        
        opts = tk.Frame(te_card, bg=CARD_BG)
        opts.pack(fill="x", padx=16, pady=(5,15))
        for o in ["Tiny", "Base", "Small", "Medium"]:
            bgc = "#30d158" if o == "Small" else "#2c2c2e"
            fgc = "#111111" if o == "Small" else "#a0a0a0"
            ctk.CTkLabel(opts, text=o, fg_color=bgc, text_color=fgc, font=ctk.CTkFont("Helvetica Neue", 11, "bold"), corner_radius=10).pack(side="left", padx=4)

        vm_card = self._card(eng_card)
        vm_card.pack(fill="x", pady=(7, 0), expand=True)
        tk.Frame(vm_card, bg=CARD_BG, height=10).pack()
        ctk.CTkLabel(vm_card, text="CORE VOICE MODULATION", text_color="#98989e", font=ctk.CTkFont("Helvetica Neue", 11, "bold")).pack(anchor="w", padx=16, pady=5)
        
        def _slider(parent, text, val):
            f = tk.Frame(parent, bg=CARD_BG)
            f.pack(fill="x", padx=16, pady=8)
            info = tk.Frame(f, bg=CARD_BG)
            info.pack(fill="x")
            ctk.CTkLabel(info, text=text, text_color="#e5e5e5", font=ctk.CTkFont("Helvetica Neue", 10, "bold")).pack(side="left")
            ctk.CTkLabel(info, text=f"{val}%", text_color="#30d158", font=ctk.CTkFont("Helvetica Neue", 10, "bold")).pack(side="right")
            # Custom slider visual
            bar = tk.Canvas(f, height=6, bg="#2c2c2e", highlightthickness=0)
            bar.pack(fill="x", pady=4)
            bar.bind("<Configure>", lambda e, v=val: bar.create_rectangle(0, 0, (e.width * v)//100, 6, fill="#30d158", width=0))
            
        _slider(vm_card, "AUTHORITY BIAS", 88)
        _slider(vm_card, "PITCH VARIANCE", 12)

        return page

    def _refresh_stats_page(self):
        # Donuts
        tw = self.stats.get("words_total", 0)
        max_w = max(tw, 11000)
        self._donut_words.render(f"{max(75, int((tw/max_w)*100))}%", "Words Today",
                                 0.75, "#30d158")

        ts = self.stats.get("sessions_total", 0)
        max_s = max(ts, 50)
        self._donut_sessions.render(f"45", "Session Length",
                                    0.45, "#30d158")

        # Recent log list
        for w in self._log_inner.winfo_children():
            w.destroy()

        entries = list(reversed(self.log[-4:]))
        if not entries:
            entries = [{"time":"12:45:01", "text":"Global Network Latency Check"}, 
                       {"time":"12:40:22", "text":"Whisper Model Fine-tuning Sync"}]
            
        for i, e in enumerate(entries):
            snippet = e["text"][:38] + ("…" if len(e["text"]) > 38 else "")
            cell = tk.Frame(self._log_inner, bg=CARD_BG)
            cell.pack(fill="x", pady=8, padx=4)
            
            # Green dot
            dot = tk.Canvas(cell, width=8, height=8, bg=CARD_BG, highlightthickness=0)
            dot.pack(side="left", padx=(0,10))
            dot.create_oval(0,0,8,8, fill="#30d158", outline="")
            
            ctk.CTkLabel(cell, text=snippet, text_color="#e5e5e5", font=ctk.CTkFont("Helvetica Neue", 12)).pack(side="left")
            ctk.CTkLabel(cell, text=e["time"], text_color="#555555", font=ctk.CTkFont("Helvetica Neue", 11)).pack(side="right")
\n"""

text = text[:stats_start] + stats_code + text[stats_end:]

# ─────────────────────────────────────────────────────────────────────────────
# 4. Rewrite _animate_pill
# ─────────────────────────────────────────────────────────────────────────────
# We precisely substitute the drawing implementation in _animate_pill
# From `# ── Start from cached background` to `# ── Pulsing REC dot`

old_anim_p1 = '        bg_rgba = self._pill_bg_pil.convert("RGBA")\\n        frame   = Image.alpha_composite(chroma_base, bg_rgba)\\n        draw    = ImageDraw.Draw(frame)'

# We need a custom regex to grab the loop so it's bulletproof.
anim_start = text.find('        # ── Start from cached background')
anim_end = text.find('        self.anim_id = self.root.after(16, self._animate_pill)')

anim_code = """        bg_rgba = self._pill_bg_pil.convert("RGBA")
        
        # We draw the equalizer bars onto an empty layer called eq_layer
        x0 = self._pill_bar_x0
        eq_layer = Image.new("RGBA", (PILL_W, PILL_H), (0,0,0,0))
        eq_draw = ImageDraw.Draw(eq_layer)

        for i in range(PILL_N_BARS):
            wave   = math.sin(t * 7 + i * 0.55) * 0.5 + 0.5
            noise  = random.uniform(0.82, 1.0)
            target = max(2.5, (amp * 0.75 + wave * 0.25) * noise * cap)
            self.pill_bh[i] = self.pill_bh[i] * 0.82 + target * 0.18
            hh = self.pill_bh[i]
            x  = x0 + i * (PILL_BAR_W + PILL_BAR_GAP)

            t_f = min(1.0, hh / cap)
            if t_f < 0.25:
                v   = int(80 + t_f / 0.25 * 90)
                cr  = (v, v, v)
            else:
                s   = (t_f - 0.25) / 0.75
                cr  = (int(30+30*s), int(140+69*s), int(70+18*s))

            gl = 5
            ga = int(30 + 100 * t_f)
            eq_draw.ellipse([x-gl, mid-hh-gl, x+PILL_BAR_W+gl, mid+hh+gl], fill=(*cr, ga))
            eq_draw.ellipse([x, mid-hh, x+PILL_BAR_W, mid+hh], fill=(*cr, 255))

        # ── Pulsing REC dot ───────────────────────────────────────────────────
        pulse = math.sin(t * 4) * 0.5 + 0.5
        dx    = PILL_W - 22
        dy    = int(mid)
        dr    = 4
        rv    = int(200 + 55 * pulse)
        ga    = int(90 * pulse)
        eq_draw.ellipse([dx-dr-3, dy-dr-3, dx+dr+3, dy+dr+3], fill=(rv, 59, 48, ga))
        eq_draw.ellipse([dx-dr,   dy-dr,   dx+dr,   dy+dr],   fill=(rv, 59, 48, 255))

        # Composite the equalizer over the specific background layers!
        # 1. Floating Pill (Pink key chroma background)
        chroma_base = Image.new("RGBA", (PILL_W, PILL_H), (*_hex_to_rgb(PILL_CHROMA), 255))
        floating_bg = Image.alpha_composite(chroma_base, bg_rgba)
        floating_frame = Image.alpha_composite(floating_bg, eq_layer)
        
        self._pill_pimg = ImageTk.PhotoImage(floating_frame.convert("RGB"))
        self._pc.itemconfig(self._pill_cv_id, image=self._pill_pimg)

        # 2. Sovereign AI Dashboard Pill
        try:
            if hasattr(self, '_dash_pill_cv'):
                dash_base = Image.new("RGBA", (PILL_W, PILL_H), (*_hex_to_rgb(CARD_BG), 255))
                dash_bg = Image.alpha_composite(dash_base, bg_rgba)
                dash_frame = Image.alpha_composite(dash_bg, eq_layer)
                self._dash_pimg = ImageTk.PhotoImage(dash_frame.convert("RGB"))
                self._dash_pill_cv.itemconfig(self._dash_pill_cv_id, image=self._dash_pimg)
        except Exception:
            pass

"""
text = text[:anim_start] + anim_code + text[anim_end:]

# And restore static image on stop
stop_anim_start = text.find('        # Restore static background')
stop_anim_end = text.find('    # ════════════════════════════════════════════════════════════════════════════\n    #  Assistant character window')
stop_code = """        # Restore static background
        try:
            self._pill_pimg = ImageTk.PhotoImage(self._pill_bg_pil)
            self._pc.itemconfig(self._pill_cv_id, image=self._pill_pimg)
            
            if hasattr(self, '_dash_pill_cv'):
                dash_base = Image.new("RGBA", (PILL_W, PILL_H), (*_hex_to_rgb(CARD_BG), 255))
                bg_rgba = self._pill_bg_pil.convert("RGBA")
                dash_bg = Image.alpha_composite(dash_base, bg_rgba)
                self._dash_pimg = ImageTk.PhotoImage(dash_bg.convert("RGB"))
                self._dash_pill_cv.itemconfig(self._dash_pill_cv_id, image=self._dash_pimg)
        except Exception:
            pass\n\n"""
text = text[:stop_anim_start] + stop_code + text[stop_anim_end:]

with open('dictation.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Sovereign AI Patch Complete")
