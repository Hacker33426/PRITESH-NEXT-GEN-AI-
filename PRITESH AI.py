#!/usr/bin/env python3
# PRITESH AI NEXT GEN V3 | WinGo 30s | BIG/SMALL only
# Pydroid 3 compatible. Uses actual API history; no demo/random outcomes.

import json, math, os, sqlite3, time, urllib.request
from datetime import datetime, timezone, timedelta

APP_NAME = "PRITESH AI NEXT GEN V3"
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
POLL_SECONDS = 2
HISTORY_LIMIT = 10
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pritesh_next_gen_v3.db")
WHITE, RESET, CLEAR = "\033[97m", "\033[0m", "\033[2J\033[H"

def out(s=""):
    print(WHITE + str(s) + RESET, flush=True)

def valid_num(v):
    try:
        n = int(str(v).strip())
        return n if 0 <= n <= 9 else None
    except (TypeError, ValueError):
        return None

def side(n):
    return "BIG" if n >= 5 else "SMALL"

def normalize(a, alpha=0.0):
    vals = [max(0.0, float(x)) + alpha for x in a]
    total = sum(vals)
    return [x / total for x in vals] if total else [1.0 / len(vals)] * len(vals)

def sigmoid(x):
    x = max(-30.0, min(30.0, x))
    return 1.0 / (1.0 + math.exp(-x))

def entropy(p):
    return -sum(x * math.log(x) for x in p if x > 0)

def period_at(moment):
    # Project's specified UTC 30-second period convention:
    # YYYYMMDD + 1000 + (seconds_since_midnight // 30 + 1)
    t = moment.astimezone(timezone.utc)
    seconds = t.hour * 3600 + t.minute * 60 + t.second
    interval = seconds // 30 + 1
    return t.strftime("%Y%m%d") + "1000" + str(interval).zfill(4)

def next_period(period):
    # Use the date-aware UTC clock formula, not a blind suffix increment.
    # The caller supplies the current UTC time for rollover safety.
    return period_at(datetime.now(timezone.utc) + timedelta(seconds=30))

def period_key(p):
    s = str(p)
    return (len(s), s)

class Store:
    def __init__(self):
        self.db = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS results(
          period TEXT PRIMARY KEY, side TEXT NOT NULL, fetched_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS predictions(
          period TEXT PRIMARY KEY, prediction TEXT NOT NULL,
          confidence REAL NOT NULL, probabilities TEXT NOT NULL,
          model TEXT NOT NULL, outcome TEXT, actual_side TEXT,
          created_at TEXT NOT NULL, settled_at TEXT
        );
        CREATE TABLE IF NOT EXISTS model_scores(
          name TEXT PRIMARY KEY, brier_sum REAL NOT NULL DEFAULT 0,
          samples INTEGER NOT NULL DEFAULT 0
        );
        """)
        self.db.commit()

    def add_results(self, rows):
        with self.db:
            for r in rows:
                self.db.execute(
                    "INSERT OR IGNORE INTO results(period,side,fetched_at) VALUES(?,?,?)",
                    (r["period"], r["side"], datetime.now(timezone.utc).isoformat())
                )

    def history(self, limit=800):
        rows = self.db.execute(
            "SELECT period,side FROM results ORDER BY length(period),period LIMIT -1"
        ).fetchall()
        data = [dict(x) for x in rows]
        return data[-limit:]

    def exists(self, p):
        return self.db.execute("SELECT 1 FROM predictions WHERE period=?", (p,)).fetchone() is not None

    def save(self, p, pred, conf, probs, model, model_probs):
        with self.db:
            self.db.execute("""
              INSERT OR IGNORE INTO predictions
              (period,prediction,confidence,probabilities,model,created_at)
              VALUES(?,?,?,?,?,?)
            """, (p, pred, conf, json.dumps(probs), model, datetime.now(timezone.utc).isoformat()))
        self._save_model_probs(p, model_probs)

    def _save_model_probs(self, p, model_probs):
        # Stored alongside prediction in a private table for later online scoring.
        with self.db:
            self.db.execute("""
              CREATE TABLE IF NOT EXISTS prediction_models(
                period TEXT NOT NULL, name TEXT NOT NULL, p_big REAL NOT NULL,
                PRIMARY KEY(period,name)
              )
            """)
            for name, p_big in model_probs.items():
                self.db.execute("INSERT OR IGNORE INTO prediction_models VALUES(?,?,?)",
                                (p, name, float(p_big)))

    def settle(self, p, actual_side):
        row = self.db.execute(
            "SELECT * FROM predictions WHERE period=? AND outcome IS NULL", (p,)
        ).fetchone()
        if row is None:
            return
        result = "WIN" if row["prediction"] == actual_side else "LOSS"
        models = self.db.execute(
            "SELECT name,p_big FROM prediction_models WHERE period=?", (p,)
        ).fetchall()
        y = 1.0 if actual_side == "BIG" else 0.0
        with self.db:
            self.db.execute("""
              UPDATE predictions SET outcome=?,actual_side=?,settled_at=?
              WHERE period=? AND outcome IS NULL
            """, (result, actual_side, datetime.now(timezone.utc).isoformat(), p))
            for m in models:
                brier = (float(m["p_big"]) - y) ** 2
                self.db.execute("""
                  INSERT INTO model_scores(name,brier_sum,samples) VALUES(?,?,1)
                  ON CONFLICT(name) DO UPDATE SET
                  brier_sum=brier_sum+excluded.brier_sum,
                  samples=samples+1
                """, (m["name"], brier))

    def weights(self, names):
        rows = self.db.execute("SELECT name,brier_sum,samples FROM model_scores").fetchall()
        score = {r["name"]: (r["brier_sum"], r["samples"]) for r in rows}
        result = {}
        for name in names:
            if name not in score or score[name][1] < 5:
                result[name] = 1.0
            else:
                avg = score[name][0] / score[name][1]
                result[name] = max(0.35, min(2.0, math.exp(1.8 * (0.25 - avg))))
        return result

    def current_prediction(self, p):
        r = self.db.execute("SELECT * FROM predictions WHERE period=?", (p,)).fetchone()
        return dict(r) if r else None

    def stats(self):
        r = self.db.execute("""
          SELECT SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) wins,
                 SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END) losses,
                 SUM(CASE WHEN outcome IS NULL THEN 1 ELSE 0 END) pending
          FROM predictions
        """).fetchone()
        w, l, pend = int(r["wins"] or 0), int(r["losses"] or 0), int(r["pending"] or 0)
        total = w + l
        return w, l, pend, (100.0 * w / total if total else 0.0)

    def recent(self):
        rows = self.db.execute("""
          SELECT period,prediction,confidence,outcome,actual_side
          FROM predictions ORDER BY length(period) DESC,period DESC LIMIT ?
        """, (HISTORY_LIMIT,)).fetchall()
        return [dict(r) for r in rows]

class LiveAPI:
    def fetch(self):
        url = API_URL + "?ts=" + str(int(time.time() * 1000))
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0", "Accept": "application/json",
            "Cache-Control": "no-cache"
        })
        with urllib.request.urlopen(req, timeout=12) as res:
            payload = json.loads(res.read().decode("utf-8"))
        items = payload.get("data", {}).get("list", []) if isinstance(payload, dict) else []
        rows = []
        for item in items:
            if not isinstance(item, dict):
                continue
            p = item.get("issueNumber") or item.get("issue") or item.get("period")
            n = valid_num(item.get("number", item.get("result")))
            if p is not None and n is not None:
                rows.append({"period": str(p), "side": side(n)})
        rows.sort(key=lambda x: period_key(x["period"]))
        if not rows:
            raise ValueError("No valid period/result records in API response")
        return rows

def binary_frequency(bits, alpha=1.0):
    big = sum(1 for x in bits if x == "BIG")
    small = len(bits) - big
    return (big + alpha) / (len(bits) + 2 * alpha)

def markov_probability(bits, order):
    if len(bits) <= order:
        return None, 0
    key = tuple(bits[-order:])
    followers = [bits[i + order] for i in range(len(bits) - order)
                 if tuple(bits[i:i + order]) == key]
    if not followers:
        return None, 0
    return binary_frequency(followers, 1.5), len(followers)

def make_models(history):
    bits = [x["side"] for x in history]
    if not bits:
        bits = ["BIG", "SMALL"]
    models = {}

    # LEVEL 1: Bayesian multi-window base rates, Laplace smoothing.
    windows = [(12, .22), (30, .30), (80, .28), (250, .20)]
    p = sum(binary_frequency(bits[-n:]) * w for n, w in windows)
    models["L1-BAYES-MULTIWINDOW"] = p

    # LEVEL 1: Exponentially weighted trend.
    ew_big, ew_small = 0.0, 0.0
    for b in bits:
        ew_big *= .94
        ew_small *= .94
        if b == "BIG": ew_big += 1
        else: ew_small += 1
    models["L1-EWMA-TREND"] = (ew_big + 1.0) / (ew_big + ew_small + 2.0)

    # LEVEL 2: Multi-order Markov, reliability shrinks sparse contexts to base rate.
    base = binary_frequency(bits[-100:])
    for order in (1, 2, 3):
        mp, count = markov_probability(bits, order)
        reliability = count / (count + 6.0) if mp is not None else 0.0
        models[f"L2-MARKOV-{order}"] = base * (1 - reliability) + (mp or base) * reliability

    # LEVEL 2: Run-length / transition-conditioned probability with smoothing.
    last = bits[-1]
    followers = [bits[i + 1] for i in range(len(bits) - 1) if bits[i] == last]
    trans = binary_frequency(followers, 2.0) if followers else base
    reliability = len(followers) / (len(followers) + 8.0)
    models["L2-TRANSITION"] = base * (1 - reliability) + trans * reliability

    # LEVEL 3: Recency-vs-long baseline and volatility-aware shrinkage.
    short_p = binary_frequency(bits[-15:])
    long_p = binary_frequency(bits[-120:])
    deviation = short_p - long_p
    volatility = abs(deviation)
    models["L3-RECENCY-DRIFT"] = max(.05, min(.95, long_p + deviation * (0.35 if volatility < .25 else .18)))

    # LEVEL 3: Pattern context (last 2-4 outcomes), discounted by sample age.
    ctx_num, ctx_den = 0.0, 0.0
    for order in (2, 3, 4):
        if len(bits) <= order: continue
        key = tuple(bits[-order:])
        for i in range(len(bits) - order):
            if tuple(bits[i:i + order]) == key:
                age = len(bits) - i - order
                wt = math.exp(-age / 90.0) / order
                ctx_den += wt
                if bits[i + order] == "BIG": ctx_num += wt
    ctx_p = (ctx_num + 1.5) / (ctx_den + 3.0) if ctx_den else base
    models["L3-CONTEXT-MATCH"] = ctx_p

    # Clamp all model outputs to avoid extreme, unjustified confidence.
    return {k: max(.03, min(.97, float(v))) for k, v in models.items()}

def predict(history, store):
    models = make_models(history)
    weights = store.weights(list(models))
    total = sum(weights.values())
    p_big = sum(models[k] * weights[k] for k in models) / total
    p_big = max(.02, min(.98, p_big))
    pred = "BIG" if p_big >= .5 else "SMALL"
    # Confidence is the ensemble's estimated side probability, tempered by data sufficiency
    # and model disagreement. It is an estimate, not a calibrated guarantee.
    disagreement = sum(weights[k] * (models[k] - p_big) ** 2 for k in models) / total
    n = len(history)
    sample_factor = min(1.0, n / 80.0)
    agreement_factor = max(.55, 1.0 - math.sqrt(disagreement) * 1.8)
    raw = max(p_big, 1.0 - p_big)
    confidence = min(0.85, (0.5 + (raw - .5) * agreement_factor) * (.72 + .28 * sample_factor))
    return pred, round(confidence * 100, 1), p_big, models

def choose_target(rows):
    now = datetime.now(timezone.utc)
    clock_period = period_at(now)
    latest = rows[-1]["period"]
    # If API already contains the clock's issue, that issue is completed; target next slot.
    if period_key(latest) >= period_key(clock_period):
        target = period_at(now + timedelta(seconds=30))
    else:
        target = clock_period
    return target, clock_period

class Engine:
    def __init__(self):
        self.api = LiveAPI()
        self.store = Store()
        self.last_prediction = None

    def sync(self):
        rows = self.api.fetch()
        self.store.add_results(rows)
        for r in rows:
            self.store.settle(r["period"], r["side"])
        return rows

    def run_once(self):
        rows = self.sync()
        target, clock_period = choose_target(rows)
        if not self.store.exists(target):
            hist = self.store.history()
            pred, conf, p_big, models = predict(hist, self.store)
            self.store.save(target, pred, conf, p_big, "3-LEVEL ADAPTIVE MATHEMATICAL ENSEMBLE", models)
        return rows[-1], target, clock_period, self.store.current_prediction(target)

    def render(self, latest, target, clock_period, p):
        wins, losses, pending, accuracy = self.store.stats()
        print(CLEAR, end="")
        out("╔" + "═" * 58 + "╗")
        out("║" + APP_NAME.center(58) + "║")
        out("║" + "WINGO 30 SECONDS | BIG / SMALL ONLY".center(58) + "║")
        out("╠" + "═" * 58 + "╣")
        out(f"║ ENGINE STATUS : 🟢 ACTIVE{' ' * 37}║")
        out(f"║ ACTIVE PERIOD : {target:<42}║")
        out(f"║ CLOCK PERIOD  : {clock_period:<42}║")
        out("╠" + "═" * 58 + "╣")
        if p:
            emoji = "🟢" if p["prediction"] == "BIG" else "🔵"
            out(f"║ PREDICTION    : {emoji} {p['prediction']:<39}║")
            out(f"║ CONFIDENCE    : {p['confidence']:>5.1f}%{' ' * 36}║")
            out(f"║ PRED STATUS   : 🟡 WAITING FOR RESULT{' ' * 20}║" if not p["outcome"] else
                f"║ PRED STATUS   : {'✅ WIN' if p['outcome']=='WIN' else '❌ LOSS':<42}║")
        else:
            out("║ PREDICTION    : WAITING FOR VALID HISTORY DATA          ║")
        out("╠" + "═" * 58 + "╣")
        out(f"║ WIN / LOSS    : ✅ {wins}  |  ❌ {losses}{' ' * 28}║")
        out(f"║ ACCURACY      : {accuracy:.1f}%{' ' * 43}║")
        out(f"║ PENDING       : {pending:<45}║")
        out("╠" + "═" * 58 + "╣")
        out("║ 3-LEVEL MODEL ENGINE                                      ║")
        out("║ L1: BAYES MULTI-WINDOW + EWMA                              ║")
        out("║ L2: MARKOV 1/2/3 + TRANSITION PROBABILITY                 ║")
        out("║ L3: CONTEXT MATCH + RECENCY DRIFT + ADAPTIVE BRIER         ║")
        out("╠" + "═" * 58 + "╣")
        out("║ LAST 10 PREDICTION HISTORY                                 ║")
        out("║ PERIOD             PREDICTION  CONF.   RESULT              ║")
        out("║" + "─" * 58 + "║")
        for r in self.store.recent():
            mark = "⏳ PENDING" if not r["outcome"] else ("✅ WIN" if r["outcome"] == "WIN" else "❌ LOSS")
            out(f"║ {r['period'][-16:]:<18} {r['prediction']:<10} {r['confidence']:>5.1f}%  {mark:<15}║")
        out("╚" + "═" * 58 + "╝")
        out("Refresh: 2 seconds | Ctrl+C to stop")
        out("Note: statistical estimate only; random outcomes cannot be guaranteed.")

    def run(self):
        out("Starting PRITESH AI NEXT GEN V3...")
        while True:
            try:
                latest, target, clock_period, p = self.run_once()
                self.render(latest, target, clock_period, p)
            except KeyboardInterrupt:
                out("Engine stopped.")
                break
            except Exception as e:
                print(CLEAR, end="")
                out(APP_NAME + " | ENGINE WAITING")
                out("DATA SYNC ERROR: " + str(e)[:180])
                out("No fake prediction or result has been generated.")
            time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    Engine().run()
