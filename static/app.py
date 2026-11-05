import os, sqlite3, secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash

APP_DIR=os.path.dirname(os.path.abspath(__file__))
DB_PATH=os.environ.get("DATABASE_PATH",os.path.join(APP_DIR,"club_data.db"))
app=Flask(__name__,template_folder=os.path.join(APP_DIR,"templates"),static_folder=os.path.join(APP_DIR,"static"))
app.secret_key=os.environ.get("SECRET_KEY") or secrets.token_hex(32)

def db():
    c=sqlite3.connect(DB_PATH,timeout=30); c.row_factory=sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON"); return c

def init_db():
    c=db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,password_hash TEXT,google_id TEXT UNIQUE,created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS settings(user_id INTEGER NOT NULL,key TEXT NOT NULL,value TEXT NOT NULL DEFAULT '',PRIMARY KEY(user_id,key));
    CREATE TABLE IF NOT EXISTS tables(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,kind TEXT NOT NULL,number INTEGER NOT NULL,price REAL NOT NULL DEFAULT 30000,active INTEGER NOT NULL DEFAULT 0,started TEXT,paused INTEGER NOT NULL DEFAULT 0,paused_at TEXT,paused_seconds INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,name TEXT NOT NULL,category TEXT NOT NULL,size TEXT NOT NULL DEFAULT '',price REAL NOT NULL DEFAULT 0,cost REAL NOT NULL DEFAULT 0,image TEXT NOT NULL DEFAULT '',active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,kind TEXT NOT NULL,table_number INTEGER NOT NULL,started TEXT NOT NULL,ended TEXT NOT NULL,seconds INTEGER NOT NULL,total REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,kind TEXT NOT NULL,table_number INTEGER NOT NULL,product_id INTEGER NOT NULL,name TEXT NOT NULL,category TEXT NOT NULL,size TEXT NOT NULL DEFAULT '',qty INTEGER NOT NULL DEFAULT 1,total REAL NOT NULL DEFAULT 0,cost_total REAL NOT NULL DEFAULT 0,created TEXT NOT NULL);
    """)
    # Import old single-account tables as unowned records; first registering user adopts them.
    for table in ("tables","products","sessions","sales"):
        cols=[r["name"] for r in c.execute(f"PRAGMA table_info({table})")]
        if "user_id" not in cols: c.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")
    cols=[r["name"] for r in c.execute("PRAGMA table_info(settings)")]
    if cols and "user_id" not in cols:
        c.execute("ALTER TABLE settings RENAME TO settings_legacy")
        c.execute("CREATE TABLE settings(user_id INTEGER NOT NULL,key TEXT NOT NULL,value TEXT NOT NULL DEFAULT '',PRIMARY KEY(user_id,key))")
        if c.execute("SELECT 1 FROM sqlite_master WHERE name='settings_legacy'").fetchone():
            for r in c.execute("SELECT key,value FROM settings_legacy").fetchall():
                c.execute("INSERT OR IGNORE INTO settings(user_id,key,value) VALUES(0,?,?)",(r["key"],r["value"]))
            c.execute("DROP TABLE settings_legacy")
    c.commit(); c.close()

def who(): return session.get("user_id")
def need_login(fn):
    @wraps(fn)
    def inner(*a,**kw):
        if not who(): return redirect(url_for("login"))
        return fn(*a,**kw)
    return inner
def seed(uid):
    c=db()
    # The very first account takes over existing single-user data.
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0]==1:
        for t in ("tables","products","sessions","sales"): c.execute(f"UPDATE {t} SET user_id=? WHERE user_id=0",(uid,))
        c.execute("UPDATE settings SET user_id=? WHERE user_id=0",(uid,))
    c.execute("INSERT OR IGNORE INTO settings(user_id,key,value) VALUES(?,?,?)",(uid,"club_name","BILYARD CLUB"))
    if c.execute("SELECT COUNT(*) FROM tables WHERE user_id=?",(uid,)).fetchone()[0]==0:
        for n in range(1,6): c.execute("INSERT INTO tables(user_id,kind,number,price) VALUES(?,?,?,?)",(uid,"BILLIARD",n,30000))
        for n in range(1,4): c.execute("INSERT INTO tables(user_id,kind,number,price) VALUES(?,?,?,?)",(uid,"TENNIS",n,20000))
    if c.execute("SELECT COUNT(*) FROM products WHERE user_id=?",(uid,)).fetchone()[0]==0:
        items=[]
        for brand in ("Suv","Coca-Cola","Fanta","Sprite","Pepsi"):
            for size,price in (("0.5L",7000),("1L",11000),("1.5L",15000),("2L",19000)):
                items.append((brand,"Ichimlik",size,3000 if brand=="Suv" else price,0))
        items += [("Chips","Gazak","",10000,4000),("Suxarik","Gazak","",8000,3000),("Shokolad","Gazak","",10000,5000),("Yong'oq","Gazak","",15000,8000),("Pullik tayoqcha","Tayoqcha","",5000,0)]
        c.executemany("INSERT INTO products(user_id,name,category,size,price,cost) VALUES(?,?,?,?,?,?)",[(uid,*x) for x in items])
    c.commit(); c.close()
def money(x): return f"{float(x or 0):,.0f}".replace(","," ")+" so'm"
def elapsed(t):
    if not t["active"] or not t["started"]: return 0
    start=datetime.fromisoformat(t["started"])
    end=datetime.fromisoformat(t["paused_at"]) if t["paused"] and t["paused_at"] else datetime.now()
    return max(0,int((end-start).total_seconds())-int(t["paused_seconds"] or 0))
def fmt(s): return f"{s//3600:02d}:{s%3600//60:02d}:{s%60:02d}"
@app.context_processor
def inject():
    if not who(): return {"club_name":"BILYARD CLUB","money":money}
    c=db(); r=c.execute("SELECT value FROM settings WHERE user_id=? AND key='club_name'",(who(),)).fetchone(); c.close()
    return {"club_name":r["value"] if r else "BILYARD CLUB","money":money,"user_email":session.get("email")}
@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        email=request.form.get("email","").strip().lower(); pw=request.form.get("password","")
        if "@" not in email or len(pw)<6:
            flash("Email to'g'ri bo'lsin, parol kamida 6 ta belgidan iborat bo'lsin.")
        else:
            c=db()
            try:
                cur=c.execute("INSERT INTO users(email,password_hash,created) VALUES(?,?,?)",(email,generate_password_hash(pw),datetime.now().isoformat()))
                uid=cur.lastrowid; c.commit(); c.close(); seed(uid)
                session.clear(); session["user_id"]=uid; session["email"]=email
                return redirect(url_for("home"))
            except sqlite3.IntegrityError:
                c.close(); flash("Bu email bilan akkaunt mavjud.")
    return render_template("auth.html",mode="register",google_enabled=bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")))
@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","").strip().lower(); pw=request.form.get("password","")
        c=db(); u=c.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone(); c.close()
        if u and u["password_hash"] and check_password_hash(u["password_hash"],pw):
            session.clear(); session["user_id"]=u["id"]; session["email"]=u["email"]; seed(u["id"])
            return redirect(url_for("home"))
        flash("Email yoki parol noto'g'ri.")
    return render_template("auth.html",mode="login",google_enabled=bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")))
@app.get("/logout")
def logout(): session.clear(); return redirect(url_for("login"))
@app.get("/auth/google")
def google_login():
    if not (os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")):
        flash("Google kirishi hali sozlanmagan. Hozircha email va parol orqali kiring."); return redirect(url_for("login"))
    try:
        from authlib.integrations.flask_client import OAuth
        oauth=OAuth(app)
        google=oauth.register(name="google",client_id=os.environ["GOOGLE_CLIENT_ID"],client_secret=os.environ["GOOGLE_CLIENT_SECRET"],server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",client_kwargs={"scope":"openid email profile"})
        return google.authorize_redirect(url_for("google_callback",_external=True))
    except Exception:
        flash("Google sozlamasini tekshiring."); return redirect(url_for("login"))
@app.get("/auth/google/callback")
def google_callback():
    try:
        from authlib.integrations.flask_client import OAuth
        oauth=OAuth(app); google=oauth.register(name="google",client_id=os.environ["GOOGLE_CLIENT_ID"],client_secret=os.environ["GOOGLE_CLIENT_SECRET"],server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",client_kwargs={"scope":"openid email profile"})
        info=google.authorize_access_token(); userinfo=info.get("userinfo") or google.userinfo()
        gid=userinfo["sub"]; email=userinfo["email"].lower()
        c=db(); u=c.execute("SELECT * FROM users WHERE google_id=? OR email=?",(gid,email)).fetchone()
        if not u:
            cur=c.execute("INSERT INTO users(email,google_id,created) VALUES(?,?,?)",(email,gid,datetime.now().isoformat())); uid=cur.lastrowid
        else:
            uid=u["id"]; c.execute("UPDATE users SET google_id=COALESCE(google_id,?) WHERE id=?",(gid,uid))
        c.commit(); c.close(); seed(uid); session.clear(); session["user_id"]=uid; session["email"]=email
        return redirect(url_for("home"))
    except Exception:
        flash("Google orqali kirishda xato yuz berdi."); return redirect(url_for("login"))
@app.get("/")
@need_login
def home():
    c=db(); uid=who()
    rows=c.execute("SELECT * FROM tables WHERE user_id=? ORDER BY CASE kind WHEN 'TENNIS' THEN 0 ELSE 1 END,number",(uid,)).fetchall()
    products=c.execute("SELECT * FROM products WHERE user_id=? AND active=1 ORDER BY category,name,size",(uid,)).fetchall(); c.close()
    data=[]
    for t in rows:
        d=dict(t); d["elapsed"]=fmt(elapsed(t)); d["charge"]=money(elapsed(t)/3600*t["price"]); data.append(d)
    return render_template("index.html",tables=data,products=products)
@app.post("/table/add")
@need_login
def add_table():
    kind=request.form.get("kind","BILLIARD")
    if kind not in ("BILLIARD","TENNIS"): flash("Stol turi noto'g'ri."); return redirect(url_for("settings"))
    c=db(); uid=who(); n=c.execute("SELECT COALESCE(MAX(number),0)+1 FROM tables WHERE user_id=? AND kind=?",(uid,kind)).fetchone()[0]
    default=30000 if kind=="BILLIARD" else 20000
    try: price=float(request.form.get("price") or default)
    except: price=default
    c.execute("INSERT INTO tables(user_id,kind,number,price) VALUES(?,?,?,?)",(uid,kind,n,price)); c.commit(); c.close()
    flash("Yangi stol qo'shildi."); return redirect(url_for("settings"))
@app.post("/table/<int:tid>/delete")
@need_login
def delete_table(tid):
    c=db(); t=c.execute("SELECT * FROM tables WHERE id=? AND user_id=?",(tid,who())).fetchone()
    if t and not t["active"]:
        c.execute("DELETE FROM tables WHERE id=? AND user_id=?",(tid,who())); c.commit(); flash("Stol o'chirildi.")
    else: flash("Band stolni o'chirib bo'lmaydi.")
    c.close(); return redirect(url_for("settings"))
@app.post("/table/<int:tid>/start")
@need_login
def start(tid):
    c=db(); t=c.execute("SELECT * FROM tables WHERE id=? AND user_id=?",(tid,who())).fetchone()
    if t and not t["active"]: c.execute("UPDATE tables SET active=1,started=?,paused=0,paused_at=NULL,paused_seconds=0 WHERE id=? AND user_id=?",(datetime.now().isoformat(),tid,who())); c.commit()
    c.close(); return redirect(url_for("home"))
@app.post("/table/<int:tid>/pause")
@need_login
def pause(tid):
    c=db(); t=c.execute("SELECT * FROM tables WHERE id=? AND user_id=?",(tid,who())).fetchone()
    if t and t["active"]:
        now=datetime.now()
        if not t["paused"]: c.execute("UPDATE tables SET paused=1,paused_at=? WHERE id=? AND user_id=?",(now.isoformat(),tid,who()))
        else:
            extra=max(0,int((now-datetime.fromisoformat(t["paused_at"])).total_seconds())) if t["paused_at"] else 0
            c.execute("UPDATE tables SET paused=0,paused_at=NULL,paused_seconds=COALESCE(paused_seconds,0)+? WHERE id=? AND user_id=?",(extra,tid,who()))
        c.commit()
    c.close(); return redirect(url_for("home"))
@app.post("/table/<int:tid>/finish")
@need_login
def finish(tid):
    c=db(); t=c.execute("SELECT * FROM tables WHERE id=? AND user_id=?",(tid,who())).fetchone()
    if t and t["active"]:
        sec=elapsed(t); ended=datetime.now().isoformat(); total=sec/3600*t["price"]
        c.execute("INSERT INTO sessions(user_id,kind,table_number,started,ended,seconds,total) VALUES(?,?,?,?,?,?,?)",(who(),t["kind"],t["number"],t["started"],ended,sec,total))
        c.execute("UPDATE tables SET active=0,started=NULL,paused=0,paused_at=NULL,paused_seconds=0 WHERE id=? AND user_id=?",(tid,who())); c.commit()
        flash(f"Stol yakunlandi. Vaqt: {fmt(sec)}. Stol haqi: {money(total)}")
    c.close(); return redirect(url_for("home"))
@app.post("/sale")
@need_login
def sale():
    try: tid=int(request.form["table_id"]); pid=int(request.form["product_id"]); qty=max(1,int(request.form.get("qty",1)))
    except: flash("Mahsulot yoki stol tanlashda xato."); return redirect(url_for("home"))
    c=db(); t=c.execute("SELECT * FROM tables WHERE id=? AND user_id=?",(tid,who())).fetchone()
    p=c.execute("SELECT * FROM products WHERE id=? AND user_id=? AND active=1",(pid,who())).fetchone()
    if t and t["active"] and p:
        c.execute("INSERT INTO sales(user_id,kind,table_number,product_id,name,category,size,qty,total,cost_total,created) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(who(),t["kind"],t["number"],p["id"],p["name"],p["category"],p["size"],qty,p["price"]*qty,p["cost"]*qty,datetime.now().isoformat()))
        c.commit(); flash(f"{p['name']} × {qty} qo'shildi.")
    else: flash("Mahsulot qo'shish uchun avval o'z stolingizni band qiling.")
    c.close(); return redirect(url_for("home"))
@app.route("/reports")
@need_login
def reports():
    period=request.args.get("period","day"); now=datetime.now()
    if period=="week": start=(now-timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
    elif period=="month": start=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    else: period="day"; start=now.replace(hour=0,minute=0,second=0,microsecond=0)
    s,e=start.isoformat(),now.isoformat(); c=db(); uid=who()
    table_total=c.execute("SELECT COALESCE(SUM(total),0) FROM sessions WHERE user_id=? AND ended BETWEEN ? AND ?",(uid,s,e)).fetchone()[0]
    sales=c.execute("SELECT COALESCE(SUM(total),0),COALESCE(SUM(cost_total),0) FROM sales WHERE user_id=? AND created BETWEEN ? AND ?",(uid,s,e)).fetchone()
    billiard=c.execute("SELECT COUNT(*) FROM sessions WHERE user_id=? AND kind='BILLIARD' AND ended BETWEEN ? AND ?",(uid,s,e)).fetchone()[0]
    tennis=c.execute("SELECT COUNT(*) FROM sessions WHERE user_id=? AND kind='TENNIS' AND ended BETWEEN ? AND ?",(uid,s,e)).fetchone()[0]
    water=c.execute("SELECT COALESCE(SUM(qty),0) FROM sales WHERE user_id=? AND name='Suv' AND created BETWEEN ? AND ?",(uid,s,e)).fetchone()[0]
    snacks=c.execute("SELECT COALESCE(SUM(qty),0) FROM sales WHERE user_id=? AND category='Gazak' AND created BETWEEN ? AND ?",(uid,s,e)).fetchone()[0]
    c.close(); total=table_total+sales[0]
    return render_template("reports.html",period=period,total=money(total),profit=money(total-sales[1]),billiard=billiard,tennis=tennis,water=water,snacks=snacks)
@app.route("/settings",methods=["GET","POST"])
@need_login
def settings():
    c=db(); uid=who()
    if request.method=="POST":
        action=request.form.get("action")
        if action=="club": c.execute("INSERT OR REPLACE INTO settings(user_id,key,value) VALUES(?,?,?)",(uid,"club_name",request.form.get("club_name","BILYARD CLUB")))
        elif action=="price":
            try: c.execute("UPDATE tables SET price=? WHERE id=? AND user_id=?",(float(request.form["price"]),int(request.form["table_id"]),uid))
            except: flash("Narx noto'g'ri.")
        elif action=="product":
            try: c.execute("INSERT INTO products(user_id,name,category,size,price,cost) VALUES(?,?,?,?,?,?)",(uid,request.form["name"],request.form["category"],request.form.get("size",""),float(request.form["price"]),float(request.form.get("cost",0))))
            except: flash("Mahsulot ma'lumotlari xato.")
        elif action=="product_price":
            try: c.execute("UPDATE products SET price=?,cost=? WHERE id=? AND user_id=?",(float(request.form["price"]),float(request.form.get("cost",0)),int(request.form["product_id"]),uid))
            except: flash("Mahsulot narxi xato.")
        c.commit(); c.close(); flash("Saqlandi."); return redirect(url_for("settings"))
    tables=c.execute("SELECT * FROM tables WHERE user_id=? ORDER BY kind,number",(uid,)).fetchall()
    products=c.execute("SELECT * FROM products WHERE user_id=? AND active=1 ORDER BY name,size",(uid,)).fetchall(); c.close()
    return render_template("settings.html",tables=tables,products=products)
@app.get("/api/status")
@need_login
def status():
    c=db(); rows=c.execute("SELECT * FROM tables WHERE user_id=?",(who(),)).fetchall(); c.close()
    return jsonify({str(t["id"]):{"elapsed":fmt(elapsed(t)),"active":t["active"],"paused":t["paused"],"charge":money(elapsed(t)/3600*t["price"])} for t in rows})
@app.get("/manifest.webmanifest")
def manifest(): return send_from_directory(APP_DIR,"manifest.webmanifest",mimetype="application/manifest+json")
@app.get("/sw.js")
def sw():
    r=send_from_directory(os.path.join(APP_DIR,"static"),"sw.js",mimetype="application/javascript"); r.headers["Service-Worker-Allowed"]="/"; r.headers["Cache-Control"]="no-cache"; return r
init_db()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
