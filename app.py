# ============================================================
# BILLIARD GLOBAL PRO 4
# ============================================================
# Bitta faylli Flask dastur.
#
# FUNKSIYALAR:
#   - Login / parol
#   - 5 ta bilyard stoli
#   - 3 ta tennis stoli
#   - Stolni band qilish / bo'shatish
#   - Stol vaqtini hisoblash
#   - Mahsulotlarni stolga qo'shish
#   - Stol + mahsulot = bitta shchot
#   - Yakuniy hisob
#   - Tushum
#   - Xarajat
#   - Sof foyda
#   - Mahsulot qo'shish
#   - Narxlarni sozlash
#   - Telefon / planshet / kompyuter ekraniga mos
#
# MUHIM:
# Internetdagi turli davlatlardagi qurilmalarni birlashtirish
# uchun keyinchalik markaziy PostgreSQL/server qo'shiladi.
# ============================================================

from flask import Flask, request, redirect, session
from flask import jsonify, render_template_string
import sqlite3
import time
import os


# ============================================================
# 1. FLASK SOZLAMASI
# ============================================================

app = Flask(__name__)

# Login sessiyasini himoyalash uchun maxfiy kalit.
app.secret_key = "BILLIARD_GLOBAL_PRO_4_SECRET_2026"


# ============================================================
# 2. DATABASE MANZILI
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_FILE = os.path.join(
    BASE_DIR,
    "billiard_global_pro4.db"
)


# ============================================================
# 3. DATABASE BILAN ULANISH
# ============================================================

def db():
    """
    SQLite bazasiga ulanish.
    Har bir so'rov uchun alohida ulanish ishlatiladi.
    """

    connection = sqlite3.connect(
        DB_FILE,
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# 4. DATABASE YARATISH
# ============================================================

def init_database():

    connection = db()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # Klub sozlamalari
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            club_name TEXT NOT NULL,
            password TEXT NOT NULL,
            billiard_price INTEGER NOT NULL,
            tennis_price INTEGER NOT NULL
        )
    """)

    # --------------------------------------------------------
    # Stol jadvali
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY,
            table_type TEXT NOT NULL,
            number INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 0,
            started REAL NOT NULL DEFAULT 0,
            saved_seconds INTEGER NOT NULL DEFAULT 0
        )
    """)

    # --------------------------------------------------------
    # Mahsulotlar
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Ichimlik',
            price INTEGER NOT NULL DEFAULT 0
        )
    """)

    # --------------------------------------------------------
    # Stolga qo'shilgan mahsulotlar
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS table_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1
        )
    """)

    # --------------------------------------------------------
    # Yakunlangan shchotlar
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER NOT NULL,
            table_type TEXT NOT NULL,
            table_money INTEGER NOT NULL,
            product_money INTEGER NOT NULL,
            total INTEGER NOT NULL,
            created REAL NOT NULL
        )
    """)

    # --------------------------------------------------------
    # Xarajatlar
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            created REAL NOT NULL
        )
    """)

    # --------------------------------------------------------
    # Boshlang'ich klub sozlamasi
    # --------------------------------------------------------

    existing_settings = cursor.execute("""
        SELECT id
        FROM settings
        WHERE id=1
    """).fetchone()

    if not existing_settings:

        cursor.execute("""
            INSERT INTO settings
            (
                id,
                club_name,
                password,
                billiard_price,
                tennis_price
            )
            VALUES
            (
                1,
                'BILLIARD GLOBAL',
                '1234',
                30000,
                30000
            )
        """)

    # --------------------------------------------------------
    # 5 ta bilyard stoli
    # --------------------------------------------------------

    for number in range(1, 6):

        cursor.execute("""
            INSERT OR IGNORE INTO tables
            (
                id,
                table_type,
                number
            )
            VALUES
            (
                ?,
                'billiard',
                ?
            )
        """, (
            number,
            number
        ))

    # --------------------------------------------------------
    # 3 ta tennis stoli
    # --------------------------------------------------------

    for number in range(1, 4):

        table_id = 100 + number

        cursor.execute("""
            INSERT OR IGNORE INTO tables
            (
                id,
                table_type,
                number
            )
            VALUES
            (
                ?,
                'tennis',
                ?
            )
        """, (
            table_id,
            number
        ))

    # --------------------------------------------------------
    # Boshlang'ich mahsulotlar
    # --------------------------------------------------------

    products = [

        ("Suv 1 litr", "Ichimlik", 3000),

        ("Suv 0.5 litr", "Ichimlik", 2000),

        ("Coca Cola", "Ichimlik", 8000),

        ("Pepsi", "Ichimlik", 8000),

        ("Fanta", "Ichimlik", 8000),

        ("Choy", "Ichimlik", 5000),

        ("Kofe", "Ichimlik", 10000),

        ("Chips", "Snek", 8000),

        ("Shokolad", "Snek", 7000),

        ("Yong'oq", "Snek", 9000),

    ]

    for name, category, price in products:

        exists = cursor.execute("""
            SELECT id
            FROM products
            WHERE name=?
        """, (name,)).fetchone()

        if not exists:

            cursor.execute("""
                INSERT INTO products
                (
                    name,
                    category,
                    price
                )
                VALUES
                (
                    ?,
                    ?,
                    ?
                )
            """, (
                name,
                category,
                price
            ))

    connection.commit()
    connection.close()


# Dasturni ishga tushirishdan oldin baza tayyorlanadi.
init_database()


# ============================================================
# 5. SOZLAMALARNI OLISH
# ============================================================

def settings():

    connection = db()

    row = connection.execute("""
        SELECT *
        FROM settings
        WHERE id=1
    """).fetchone()

    connection.close()

    return row


# ============================================================
# 6. LOGIN TEKSHIRISH
# ============================================================

def is_logged():

    return session.get(
        "logged_in",
        False
    )


# ============================================================
# 7. PULNI FORMATLASH
# ============================================================

def format_money(value):

    return (
        f"{int(value):,}"
        .replace(",", " ")
        + " so'm"
    )


# ============================================================
# 8. STOL VAQTINI HISOBLASH
# ============================================================

def elapsed_seconds(row):

    saved = int(
        row["saved_seconds"]
    )

    if not row["active"]:

        return saved

    started = float(
        row["started"]
    )

    return saved + int(
        time.time() - started
    )


# ============================================================
# 9. STOL MA'LUMOTINI HISOBLASH
# ============================================================

def table_data(row):

    current_settings = settings()

    if row["table_type"] == "billiard":

        hourly_price = current_settings[
            "billiard_price"
        ]

    else:

        hourly_price = current_settings[
            "tennis_price"
        ]

    seconds = elapsed_seconds(row)

    table_money = int(
        seconds * hourly_price / 3600
    )

    connection = db()

    product_money = connection.execute("""
        SELECT
            COALESCE(
                SUM(price * quantity),
                0
            )
        FROM table_items
        WHERE table_id=?
    """, (
        row["id"],
    )).fetchone()[0]

    connection.close()

    total = (
        table_money +
        product_money
    )

    hours = seconds // 3600

    minutes = (
        seconds % 3600
    ) // 60

    secs = seconds % 60

    return {

        "id": row["id"],

        "type": row["table_type"],

        "number": row["number"],

        "active": bool(
            row["active"]
        ),

        "time":
            f"{hours:02}:{minutes:02}:{secs:02}",

        "table_money":
            table_money,

        "product_money":
            product_money,

        "total":
            total
    }


# ============================================================
# 10. LOGIN SAHIFASI
# ============================================================

LOGIN_PAGE = """

<!DOCTYPE html>

<html lang="uz">

<head>

<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>Billiard Global</title>

<style>

* {
    box-sizing:border-box;
}

body {

    margin:0;

    min-height:100vh;

    display:flex;

    justify-content:center;

    align-items:center;

    font-family:Arial;

    color:white;

    background:
    radial-gradient(
        circle at top,
        #176b39,
        #020603 70%
    );
}

.login {

    width:min(420px,92%);

    padding:35px;

    border-radius:30px;

    background:#06160c;

    border:1px solid #31824a;

    box-shadow:
    0 25px 80px #000;

    text-align:center;
}

.logo {

    font-size:75px;

}

h1 {

    margin-bottom:25px;

}

input {

    width:100%;

    padding:16px;

    margin:7px 0;

    border:0;

    border-radius:14px;

    font-size:17px;
}

button {

    width:100%;

    padding:15px;

    border:0;

    border-radius:14px;

    background:#16a34a;

    color:white;

    font-size:17px;

    font-weight:bold;

    cursor:pointer;
}

.error {

    color:#ff7373;

}

</style>

</head>

<body>

<div class="login">

<div class="logo">
🎱
</div>

<h1>
BILLIARD GLOBAL
</h1>

<form method="POST">

<input
type="password"
name="password"
placeholder="Parol"
autofocus
>

<button>
🔐 KIRISH
</button>

</form>

{% if error %}

<p class="error">
Parol noto'g'ri!
</p>

{% endif %}

</div>

</body>

</html>

"""


# ============================================================
# 11. LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        password = request.form.get(
            "password",
            ""
        )

        if password == settings()["password"]:

            session[
                "logged_in"
            ] = True

            return redirect("/dashboard")

        return render_template_string(
            LOGIN_PAGE,
            error=True
        )

    return render_template_string(
        LOGIN_PAGE,
        error=False
    )


# ============================================================
# 12. LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ============================================================
# 13. ASOSIY SAHIFA
# ============================================================

MAIN_PAGE = """

<!DOCTYPE html>

<html lang="uz">

<head>

<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>{{club_name}}</title>

<style>

* {
    box-sizing:border-box;
}

body {

    margin:0;

    background:
    radial-gradient(
        circle at top,
        #125d31,
        #020803 70%
    );

    color:white;

    font-family:
    Arial,
    sans-serif;
}

header {

    position:sticky;

    top:0;

    z-index:20;

    background:#041008ee;

    backdrop-filter:
    blur(15px);

    border-bottom:
    1px solid #2c6d40;
}

.header {

    max-width:1500px;

    margin:auto;

    padding:14px 20px;

    display:flex;

    align-items:center;

    justify-content:
    space-between;

    gap:12px;

    flex-wrap:wrap;
}

.logo {

    font-size:24px;

    font-weight:bold;
}

.nav {

    display:flex;

    gap:7px;

    flex-wrap:wrap;
}

.nav button {

    width:auto;

    padding:
    10px 14px;

    font-size:14px;
}

.container {

    max-width:1500px;

    margin:auto;

    padding:20px;
}

.title {

    margin-top:20px;

}

.grid {

    display:grid;

    grid-template-columns:
    repeat(
        auto-fit,
        minmax(245px,1fr)
    );

    gap:18px;
}

.card {

    padding:20px;

    border-radius:25px;

    background:
    linear-gradient(
        145deg,
        #124d29,
        #06150a
    );

    border:
    1px solid #37814c;

    box-shadow:
    0 15px 45px #0009;
}

.icon {

    font-size:65px;

    text-align:center;
}

.card h2 {

    text-align:center;
}

.status {

    padding:10px;

    border-radius:12px;

    text-align:center;

    font-weight:bold;

    margin:10px 0;
}

.free {

    background:#166534;
}

.busy {

    background:#991b1b;
}

.timer {

    font-family:monospace;

    font-size:30px;

    text-align:center;

    margin:13px;
}

.info {

    display:flex;

    justify-content:
    space-between;

    background:#0004;

    padding:9px;

    margin:5px 0;

    border-radius:10px;
}

.total {

    background:#166534;

    padding:13px;

    margin-top:10px;

    border-radius:13px;

    text-align:center;

    font-size:21px;

    font-weight:bold;
}

.actions {

    display:flex;

    gap:8px;

    margin-top:12px;
}

.actions button {

    flex:1;
}

button {

    padding:13px;

    border:0;

    border-radius:13px;

    background:#16a34a;

    color:white;

    font-weight:bold;

    cursor:pointer;
}

button:hover {

    filter:
    brightness(1.15);
}

.blue {

    background:#2563eb;
}

.red {

    background:#dc2626;
}

.orange {

    background:#d97706;
}

.gray {

    background:#374151;
}

.modal {

    display:none;

    position:fixed;

    inset:0;

    z-index:100;

    padding:15px;

    overflow:auto;

    background:#000d;
}

.modal-box {

    max-width:900px;

    margin:20px auto;

    padding:22px;

    border-radius:25px;

    background:#082013;

    border:1px solid #3b8c52;

    box-shadow:
    0 25px 80px #000;
}

.modal-header {

    display:flex;

    justify-content:
    space-between;

    align-items:center;
}

.modal-header button {

    width:auto;
}

.products {

    display:grid;

    grid-template-columns:
    repeat(
        auto-fit,
        minmax(150px,1fr)
    );

    gap:10px;
}

.product {

    padding:15px;

    background:#12391f;

    border-radius:16px;

    text-align:center;
}

.product-name {

    font-weight:bold;

    font-size:17px;
}

.product-price {

    margin:8px;
}

.item {

    display:flex;

    justify-content:
    space-between;

    padding:12px;

    margin:6px 0;

    border-radius:12px;

    background:#12391f;
}

input {

    width:100%;

    padding:14px;

    border:0;

    border-radius:12px;

    margin:6px 0;
}

.stat {

    display:flex;

    justify-content:
    space-between;

    padding:15px;

    margin:7px 0;

    border-radius:13px;

    background:#12391f;
}

.big-total {

    padding:22px;

    border-radius:18px;

    background:#166534;

    text-align:center;

    font-size:27px;

    font-weight:bold;
}

@media(max-width:600px) {

    .container {

        padding:10px;
    }

    .logo {

        font-size:19px;
    }

    .nav button {

        font-size:12px;

        padding:
        9px 10px;
    }

}

</style>

</head>

<body>


<header>

<div class="header">

<div class="logo">

🎱 {{club_name}}

</div>

<div class="nav">

<button onclick="openStats()">
📊 Hisobot
</button>

<button onclick="openProducts()">
🥤 Mahsulot
</button>

<button onclick="openSettings()">
⚙️ Sozlama
</button>

<a href="/logout">

<button class="red">
🚪 Chiqish
</button>

</a>

</div>

</div>

</header>


<div class="container">

<h1 class="title">
🎱 BILYARD STOLLARI
</h1>

<div
id="billiardList"
class="grid">
</div>


<h1 class="title">
🏓 TENNIS STOLLARI
</h1>

<div
id="tennisList"
class="grid">
</div>

</div>


<!-- ======================================================
     STOL SHCHOT MODALI
====================================================== -->

<div
id="tableModal"
class="modal">

<div class="modal-box">

<div class="modal-header">

<h2 id="tableTitle">
Stol
</h2>

<button
class="gray"
onclick="closeModal('tableModal')">
✕
</button>

</div>

<div id="tableInfo">
</div>

<h3>
🥤 Mahsulot qo'shish
</h3>

<div
id="productButtons"
class="products">
</div>

<h3>
🧾 Stol shchoti
</h3>

<div id="items">
</div>

<div
id="tableTotal"
class="big-total">
0 so'm
</div>

<br>

<button
onclick="finishTable()">

✅ YAKUNIY SHCHOT

</button>

</div>

</div>


<!-- ======================================================
     HISOBOT
====================================================== -->

<div
id="statsModal"
class="modal">

<div class="modal-box">

<div class="modal-header">

<h2>
📊 HISOBOT
</h2>

<button
class="gray"
onclick="closeModal('statsModal')">
✕
</button>

</div>

<div id="stats">
</div>

<hr>

<h3>
💸 Xarajat qo'shish
</h3>

<input
id="expenseName"
placeholder="Xarajat nomi">

<input
id="expenseAmount"
type="number"
placeholder="Summa">

<button
onclick="addExpense()">

💾 XARAJATNI SAQLASH

</button>

</div>

</div>


<!-- ======================================================
     SOZLAMALAR
====================================================== -->

<div
id="settingsModal"
class="modal">

<div class="modal-box">

<div class="modal-header">

<h2>
⚙️ SOZLAMALAR
</h2>

<button
class="gray"
onclick="closeModal('settingsModal')">
✕
</button>

</div>

<input
id="clubName"
placeholder="Klub nomi">

<input
id="password"
type="password"
placeholder="Yangi parol">

<input
id="billiardPrice"
type="number"
placeholder="Bilyard 1 soat">

<input
id="tennisPrice"
type="number"
placeholder="Tennis 1 soat">

<button
onclick="saveSettings()">

💾 SAQLASH

</button>

</div>

</div>


<!-- ======================================================
     MAHSULOTLAR
====================================================== -->

<div
id="productsModal"
class="modal">

<div class="modal-box">

<div class="modal-header">

<h2>
🥤 MAHSULOTLAR
</h2>

<button
class="gray"
onclick="closeModal('productsModal')">
✕
</button>

</div>

<div
id="productList"
class="products">
</div>

<hr>

<h3>
➕ Yangi mahsulot
</h3>

<input
id="newProductName"
placeholder="Mahsulot nomi">

<input
id="newProductCategory"
placeholder="Ichimlik yoki Snek">

<input
id="newProductPrice"
type="number"
placeholder="Narxi">

<button
onclick="addProduct()">

➕ MAHSULOT QO'SHISH

</button>

</div>

</div>


<script>


// ========================================================
// JAVASCRIPT
// ========================================================

let selectedTable = null;


// --------------------------------------------------------
// Pulni chiroyli ko'rsatish
// --------------------------------------------------------

function money(value) {

    return Number(
        value || 0
    ).toLocaleString(
        "uz-UZ"
    ) + " so'm";

}


// --------------------------------------------------------
// Modal yopish
// --------------------------------------------------------

function closeModal(id) {

    document.getElementById(
        id
    ).style.display = "none";

}


// --------------------------------------------------------
// Stollarni olish
// --------------------------------------------------------

async function loadTables() {

    const response =
        await fetch(
            "/api/tables"
        );

    if (!response.ok) {
        return;
    }

    const tables =
        await response.json();

    drawTables(
        tables.filter(
            t => t.type === "billiard"
        ),
        "billiardList"
    );

    drawTables(
        tables.filter(
            t => t.type === "tennis"
        ),
        "tennisList"
    );

}


// --------------------------------------------------------
// Stollarni chizish
// --------------------------------------------------------

function drawTables(
    tables,
    elementId
) {

    const box =
        document.getElementById(
            elementId
        );

    box.innerHTML = "";

    tables.forEach(
        table => {

        const card =
            document.createElement(
                "div"
            );

        card.className =
            "card";

        card.innerHTML = `

            <div class="icon">

                ${
                    table.type === "billiard"
                    ? "🎱"
                    : "🏓"
                }

            </div>

            <h2>

                ${
                    table.type === "billiard"
                    ? "Bilyard"
                    : "Tennis"
                }

                ${table.number}

            </h2>

            <div class="status
                ${
                    table.active
                    ? "busy"
                    : "free"
                }">

                ${
                    table.active
                    ? "🔴 BAND"
                    : "🟢 BO'SH"
                }

            </div>

            <div class="timer">

                ${table.time}

            </div>

            <div class="info">

                <span>Stol:</span>

                <b>
                    ${money(
                        table.table_money
                    )}
                </b>

            </div>

            <div class="info">

                <span>Mahsulot:</span>

                <b>
                    ${money(
                        table.product_money
                    )}
                </b>

            </div>

            <div class="total">

                JAMI

                <br>

                ${money(
                    table.total
                )}

            </div>

            <div class="actions">

                <button
                    class="blue"
                    onclick="
                        openTable(
                            ${table.id}
                        )
                    ">

                    🧾 SHCHOT

                </button>

                <button
                    class="${
                        table.active
                        ? "red"
                        : ""
                    }"
                    onclick="
                        toggleTable(
                            ${table.id}
                        )
                    ">

                    ${
                        table.active
                        ? "⏸ TO'XTATISH"
                        : "▶️ BAND QILISH"
                    }

                </button>

            </div>
        `;

        box.appendChild(card);

    });

}


// --------------------------------------------------------
// Stolni band qilish / to'xtatish
// --------------------------------------------------------

async function toggleTable(id) {

    await fetch(
        "/api/table/"
        + id
        + "/toggle",
        {
            method:"POST"
        }
    );

    await loadTables();

    if (
        selectedTable === id
    ) {

        await loadTable();

    }

}


// --------------------------------------------------------
// Stolni ochish
// --------------------------------------------------------

async function openTable(id) {

    selectedTable = id;

    await loadTable();

    document.getElementById(
        "tableModal"
    ).style.display =
        "block";

}


// --------------------------------------------------------
// Tanlangan stol ma'lumotlari
// --------------------------------------------------------

async function loadTable() {

    if (!selectedTable) {
        return;
    }

    const response =
        await fetch(
            "/api/table/"
            + selectedTable
        );

    const table =
        await response.json();


    document.getElementById(
        "tableTitle"
    ).innerText =

        (
            table.type === "billiard"
            ? "🎱 Bilyard "
            : "🏓 Tennis "
        )
        + table.number;


    document.getElementById(
        "tableInfo"
    ).innerHTML = `

        <div class="stat">

            <span>Holat</span>

            <b>

                ${
                    table.active
                    ? "🔴 BAND"
                    : "🟢 BO'SH"
                }

            </b>

        </div>

        <div class="stat">

            <span>Vaqt</span>

            <b>
                ${table.time}
            </b>

        </div>

        <button
            onclick="
                toggleTable(
                    ${table.id}
                )
            ">

            ${
                table.active
                ? "⏸ TO'XTATISH"
                : "▶️ BAND QILISH"
            }

        </button>

    `;


    // Mahsulotlarni yuklash

    const productsResponse =
        await fetch(
            "/api/products"
        );

    const products =
        await productsResponse.json();

    const productBox =
        document.getElementById(
            "productButtons"
        );

    productBox.innerHTML = "";


    products.forEach(
        product => {

        productBox.innerHTML += `

            <div class="product">

                <div class="product-name">

                    ${product.name}

                </div>

                <div class="product-price">

                    ${money(
                        product.price
                    )}

                </div>

                <small>

                    ${product.category}

                </small>

                <br><br>

                <button
                    class="blue"
                    onclick="
                        addProductToTable(
                            ${product.id}
                        )
                    ">

                    ➕ QO'SHISH

                </button>

            </div>

        `;

    });


    // Stol mahsulotlari

    const itemResponse =
        await fetch(
            "/api/table/"
            + selectedTable
            + "/items"
        );

    const items =
        await itemResponse.json();

    const itemsBox =
        document.getElementById(
            "items"
        );

    itemsBox.innerHTML = "";


    if (items.length === 0) {

        itemsBox.innerHTML =
            "<p>Mahsulot qo'shilmagan.</p>";

    }


    items.forEach(
        item => {

        itemsBox.innerHTML += `

            <div class="item">

                <span>

                    ${item.name}

                    ×

                    ${item.quantity}

                </span>

                <b>

                    ${money(
                        item.price *
                        item.quantity
                    )}

                </b>

            </div>

        `;

    });


    document.getElementById(
        "tableTotal"
    ).innerText =
        money(table.total);

}


// --------------------------------------------------------
// Mahsulotni stolga qo'shish
// --------------------------------------------------------

async function addProductToTable(
    productId
) {

    if (!selectedTable) {
        return;
    }

    await fetch(
        "/api/table/"
        + selectedTable
        + "/add",
        {

            method:"POST",

            headers:{
                "Content-Type":
                "application/json"
            },

            body:JSON.stringify({

                product_id:
                    productId

            })

        }
    );

    await loadTable();

    await loadTables();

}


// --------------------------------------------------------
// Stolni yakunlash
// --------------------------------------------------------

async function finishTable() {

    if (!selectedTable) {
        return;
    }

    const yes =
        confirm(
            "Stolni yakunlaysizmi?"
        );

    if (!yes) {
        return;
    }


    const response =
        await fetch(
            "/api/table/"
            + selectedTable
            + "/finish",
            {
                method:"POST"
            }
        );

    const result =
        await response.json();


    alert(

        "YAKUNIY SHCHOT\n\n"

        + "Stol: "
        + money(
            result.table_money
        )

        + "\nMahsulot: "
        + money(
            result.product_money
        )

        + "\n\nJAMI: "
        + money(
            result.total
        )

    );


    closeModal(
        "tableModal"
    );

    selectedTable = null;

    await loadTables();

}


// --------------------------------------------------------
// Hisobotni ochish
// --------------------------------------------------------

async function openStats() {

    const response =
        await fetch(
            "/api/stats"
        );

    const data =
        await response.json();


    document.getElementById(
        "stats"
    ).innerHTML = `

        <div class="stat">

            <span>🎱 Bilyard</span>

            <b>
                ${money(
                    data.billiard
                )}
            </b>

        </div>

        <div class="stat">

            <span>🏓 Tennis</span>

            <b>
                ${money(
                    data.tennis
                )}
            </b>

        </div>

        <div class="stat">

            <span>🥤 Mahsulot</span>

            <b>
                ${money(
                    data.products
                )}
            </b>

        </div>

        <div class="stat">

            <span>💰 Tushum</span>

            <b>
                ${money(
                    data.revenue
                )}
            </b>

        </div>

        <div class="stat">

            <span>💸 Xarajat</span>

            <b>
                ${money(
                    data.expenses
                )}
            </b>

        </div>

        <div class="big-total">

            SOF FOYDA

            <br><br>

            ${money(
                data.profit
            )}

        </div>

    `;


    document.getElementById(
        "statsModal"
    ).style.display =
        "block";

}


// --------------------------------------------------------
// Xarajat qo'shish
// --------------------------------------------------------

async function addExpense() {

    const name =
        document.getElementById(
            "expenseName"
        ).value.trim();

    const amount =
        Number(
            document.getElementById(
                "expenseAmount"
            ).value
        );


    if (
        !name ||
        amount <= 0
    ) {

        alert(
            "Xarajat ma'lumotini kiriting!"
        );

        return;

    }


    await fetch(
        "/api/expenses",
        {

            method:"POST",

            headers:{
                "Content-Type":
                "application/json"
            },

            body:JSON.stringify({

                name:name,

                amount:amount

            })

        }
    );


    document.getElementById(
        "expenseName"
    ).value = "";

    document.getElementById(
        "expenseAmount"
    ).value = "";


    await openStats();

}


// --------------------------------------------------------
// Sozlamalarni ochish
// --------------------------------------------------------

async function openSettings() {

    const response =
        await fetch(
            "/api/settings"
        );

    const data =
        await response.json();


    document.getElementById(
        "clubName"
    ).value =
        data.club_name;


    document.getElementById(
        "billiardPrice"
    ).value =
        data.billiard_price;


    document.getElementById(
        "tennisPrice"
    ).value =
        data.tennis_price;


    document.getElementById(
        "password"
    ).value = "";


    document.getElementById(
        "settingsModal"
    ).style.display =
        "block";

}


// --------------------------------------------------------
// Sozlamalarni saqlash
// --------------------------------------------------------

async function saveSettings() {

    const data = {

        club_name:
            document.getElementById(
                "clubName"
            ).value,

        password:
            document.getElementById(
                "password"
            ).value,

        billiard_price:
            Number(
                document.getElementById(
                    "billiardPrice"
                ).value
            ),

        tennis_price:
            Number(
                document.getElementById(
                    "tennisPrice"
                ).value
            )

    };


    const response =
        await fetch(
            "/api/settings",
            {

                method:"POST",

                headers:{
                    "Content-Type":
                    "application/json"
                },

                body:JSON.stringify(data)

            }
        );


    const result =
        await response.json();


    if (result.ok) {

        alert(
            "Sozlamalar saqlandi!"
        );

        location.reload();

    }

}


// --------------------------------------------------------
// Mahsulotlar oynasi
// --------------------------------------------------------

async function openProducts() {

    const response =
        await fetch(
            "/api/products"
        );

    const products =
        await response.json();

    const box =
        document.getElementById(
            "productList"
        );

    box.innerHTML = "";


    products.forEach(
        product => {

        box.innerHTML += `

            <div class="product">

                <div class="product-name">

                    ${product.name}

                </div>

                <div>

                    ${product.category}

                </div>

                <div>

                    ${money(
                        product.price
                    )}

                </div>

            </div>

        `;

    });


    document.getElementById(
        "productsModal"
    ).style.display =
        "block";

}


// --------------------------------------------------------
// Yangi mahsulot
// --------------------------------------------------------

async function addProduct() {

    const name =
        document.getElementById(
            "newProductName"
        ).value.trim();

    const category =
        document.getElementById(
            "newProductCategory"
        ).value.trim();

    const price =
        Number(
            document.getElementById(
                "newProductPrice"
            ).value
        );


    if (
        !name ||
        price <= 0
    ) {

        alert(
            "Mahsulot nomi va narxini kiriting!"
        );

        return;

    }


    await fetch(
        "/api/products/add",
        {

            method:"POST",

            headers:{
                "Content-Type":
                "application/json"
            },

            body:JSON.stringify({

                name:name,

                category:
                    category ||
                    "Ichimlik",

                price:price

            })

        }
    );


    document.getElementById(
        "newProductName"
    ).value = "";

    document.getElementById(
        "newProductCategory"
    ).value = "";

    document.getElementById(
        "newProductPrice"
    ).value = "";


    alert(
        "Mahsulot qo'shildi!"
    );


    await openProducts();

}


// --------------------------------------------------------
// Har soniyada stol holatini yangilash
// --------------------------------------------------------

setInterval(
    loadTables,
    1000
);


// --------------------------------------------------------
// Dastur ochilganda stollarni chiqarish
// --------------------------------------------------------

loadTables();

</script>

</body>

</html>

"""


# ============================================================
# 14. ASOSIY ROUTE
# ============================================================

@app.route("/")
def home():
    club = settings()["club_name"]
    page = """<!doctype html>
<html lang="uz"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__CLUB__ — Billiard Club</title>
<meta name="description" content="__CLUB__ — bilyard va tennis klubini boshqarish tizimi. Stol, vaqt, mahsulot, tushum va foyda hisobotlari.">
<meta name="robots" content="index,follow">
<style>body{margin:0;font-family:Arial,sans-serif;background:#07130b;color:#fff;display:grid;place-items:center;min-height:100vh}.box{max-width:700px;padding:40px;text-align:center;background:#0d2415;border-radius:24px;box-shadow:0 20px 60px #000}h1{font-size:42px;margin:0 0 15px}p{font-size:19px;line-height:1.6;color:#cfe8d4}.btn{display:inline-block;margin-top:20px;padding:15px 28px;background:#16a34a;color:#fff;text-decoration:none;border-radius:12px;font-weight:bold}</style>
</head><body><div class="box"><div style="font-size:55px">🎱</div><h1>__CLUB__</h1><p>Professional bilyard va tennis klubini boshqarish tizimi.</p><p>Stollar, vaqt hisobi, mahsulotlar, tushum, xarajat va foyda hisobotlari — barchasi bitta tizimda.</p><a class="btn" href="/login">🔐 Boshqaruv paneliga kirish</a></div></body></html>"""
    return page.replace("__CLUB__", club)

@app.route("/dashboard")
def dashboard():
    if not is_logged():
        return redirect("/login")
    return render_template_string(MAIN_PAGE, club_name=settings()["club_name"])

@app.route("/robots.txt")
def robots():
    text = "User-agent: *\nAllow: /\nDisallow: /dashboard\nDisallow: /login\nSitemap: " + request.host_url.rstrip("/") + "/sitemap.xml\n"
    return text, 200, {"Content-Type":"text/plain; charset=utf-8"}

@app.route("/sitemap.xml")
def sitemap():
    base = request.host_url.rstrip("/")
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>' + base + '/</loc></url></urlset>'
    return xml, 200, {"Content-Type":"application/xml; charset=utf-8"}


# ============================================================
# 15. STOLLAR API
# ============================================================

@app.route("/api/tables")
def api_tables():

    if not is_logged():

        return jsonify(
            {"error":"login"}
        ), 401

    connection = db()

    rows = connection.execute("""
        SELECT *
        FROM tables
        ORDER BY id
    """).fetchall()

    connection.close()

    return jsonify([
        table_data(row)
        for row in rows
    ])


# ============================================================
# 16. BIRTA STOL API
# ============================================================

@app.route(
    "/api/table/<int:table_id>"
)
def api_table(table_id):

    if not is_logged():

        return jsonify(
            {"error":"login"}
        ), 401

    connection = db()

    row = connection.execute("""
        SELECT *
        FROM tables
        WHERE id=?
    """, (
        table_id,
    )).fetchone()

    connection.close()

    if not row:

        return jsonify(
            {"error":"table"}
        ), 404

    return jsonify(
        table_data(row)
    )


# ============================================================
# 17. STOLNI BAND / TO'XTATISH
# ============================================================

@app.route(
    "/api/table/<int:table_id>/toggle",
    methods=["POST"]
)
def toggle_table(table_id):

    if not is_logged():

        return jsonify(
            {"error":"login"}
        ), 401

    connection = db()

    row = connection.execute("""
        SELECT *
        FROM tables
        WHERE id=?
    """, (
        table_id,
    )).fetchone()

    if not row:

        connection.close()

        return jsonify(
            {"error":"table"}
        ), 404


    if row["active"]:

        seconds = elapsed_seconds(
            row
        )

        connection.execute("""
            UPDATE tables
            SET
                active=0,
                started=0,
                saved_seconds=?
            WHERE id=?
        """, (
            seconds,
            table_id
        ))

    else:

        connection.execute("""
            UPDATE tables
            SET
                active=1,
                started=?
            WHERE id=?
        """, (
            time.time(),
            table_id
        ))


    connection.commit()

    connection.close()

    return jsonify(
        {"ok":True}
    )


# ============================================================
# 18. MAHSULOTLAR API
# ============================================================

@app.route("/api/products")
def api_products():

    if not is_logged():

        return jsonify(
            {"error":"login"}
        ), 401

    connection = db()

    rows = connection.execute("""
        SELECT *
        FROM products
        ORDER BY id
    """).fetchall()

    connection.close()

    return jsonify([
        dict(row)
        for row in rows
    ])


# ============================================================
# 19. YANGI MAHSULOT
# ============================================================

@app.route(
    "/api/products/add",
    methods=["POST"]
)
def api_add_product():

    if not is_logged():

        return jsonify(
            {"error":"login"}
        ), 401

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    category = str(
        data.get(
            "category",
            "Ichimlik"
        )
    ).strip()

    try:

        price = int(
            data.get(
                "price",
                0
            )
        )

    except:

        price = 0


    if (
        not name
        or price <= 0
    ):

        return jsonify(
            {"error":"invalid"}
        ), 400


    connection = db()

    connection.execute("""
        INSERT INTO products
        (
            name,
            category,
            price
        )
        VALUES
        (
            ?,
            ?,
            ?
        )
    """, (
        name,
        category or "Ichimlik",
        price
    ))

    connection.commit()

    connection.close()

    return jsonify(
        {"ok":True}
    )


# ============================================================
# 20. STOL MAHSULOTLARI
# ============================================================

@app.route(
    "/api/table/<int:table_id>/items"
)
def api_table_items(table_id):

    if not is_logged():

        return jsonify(
            {"error":"login"}
        ), 401

    connection = db()

    rows = connection.execute("""
        SELECT *
        FROM table_items
        WHERE table_id=?
        ORDER BY id
    """, (
        table_id,
    )).fetchall()

    connection.close()

    return jsonify([
        dict(row)
        for row in rows
    ])


# ============================================================
# 21. MAHSULOTNI STOLGA QO'SHISH
# ============================================================

@app.route(
    "/api/table/<int:table_id>/add",
    methods=["POST"]
)
def api_add_to_table(table_id):

    if not is_logged():

        return jsonify(
            {"error":"login"}
        ), 401

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    try:

        product_id = int(
            data.get(
                "product_id"
            )
        )

    except:

        return jsonify(
            {"error":"product"}
        ), 400


    connection = db()

    product = connection.execute("""
        SELECT *
        FROM products
        WHERE id=?
    """, (
        product_id,
    )).fetchone()

    if not product:

        connection.close()

        return jsonify(
            {"error":"product"}
        ), 404


    old = connection.execute("""
        SELECT *
        FROM table_items
        WHERE table_id=?
        AND product_id=?
    """, (
        table_id,
        product_id
    )).fetchone()


    if old:

        connection.execute("""
            UPDATE table_items
            SET quantity=quantity+1
            WHERE id=?
        """, (
            old["id"],
        ))

    else:

        connection.execute("""
            INSERT INTO table_items
            (
                table_id,
                product_id,
                name,
                price,
                quantity
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                1
            )
        """, (
            table_id,
            product_id,
            product["name"],
            product["price"]
        ))


    connection.commit()

    connection.close()

    return jsonify(
        {"ok":True}
    )


# ============================================================
# 22. YAKUNIY SHCHOT
# ============================================================

@app.route(
    "/api/table/<int:table_id>/finish",
    methods=["POST"]
)
def finish_table(table_id):

    if not is_logged():

        return jsonify(
            {"error":"login"}
        ), 401

    connection = db()

    table = connection.execute("""
        SELECT *
        FROM tables
        WHERE id=?
    """, (
        table_id,
    )).fetchone()

    if not table:

        connection.close()

        return jsonify(
            {"error":"table"}
        ), 404


    current_settings = settings()


    if table["table_type"] == "billiard":

        hourly_price = \
            current_settings[
                "billiard_price"
            ]

    else:

        hourly_price = \
            current_settings[
                "tennis_price"
            ]


    seconds = elapsed_seconds(
        table
    )


    table_money = int(
        seconds *
        hourly_price /
        3600
    )


    product_money = connection.execute("""
        SELECT
            COALESCE(
                SUM(
                    price * quantity
                ),
                0
            )
        FROM table_items
        WHERE table_id=?
    """, (
        table_id,
    )).fetchone()[0]


    total = (
        table_money +
        product_money
    )


    # Yakuniy shchotni saqlaymiz.

    connection.execute("""
        INSERT INTO sales
        (
            table_id,
            table_type,
            table_money,
            product_money,
            total,
            created
        )
        VALUES
        (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
    """, (
        table_id,
        table["table_type"],
        table_money,
        product_money,
        total,
        time.time()
    ))


    # Mahsulotlarni tozalaymiz.

    connection.execute("""
        DELETE FROM table_items
        WHERE table_id=?
    """, (
        table_id,
    ))


    # Stolni yana bo'sh qilamiz.

    connection.execute("""
        UPDATE tables
        SET
            active=0,
            started=0,
            saved_seconds=0
        WHERE id=?
    """, (
        table_id,
    ))


    connection.commit()

    connection.close()


    return jsonify({

        "table_money":
            table_money,

        "product_money":
            product_money,

        "total":
            total

    })


# ============================================================
# 23. HISOBOT
# ============================================================

@app.route("/api/stats")
def api_stats():

    if not is_logged():

        return jsonify(
            {"error":"login"}
        ), 401

    connection = db()


    billiard = connection.execute("""
        SELECT
            COALESCE(
                SUM(table_money),
                0
            )
        FROM sales
        WHERE table_type='billiard'
    """).fetchone()[0]


    tennis = connection.execute("""
        SELECT
            COALESCE(
                SUM(table_money),
                0
            )
        FROM sales
        WHERE table_type='tennis'
    """).fetchone()[0]


    products = connection.execute("""
        SELECT
            COALESCE(
                SUM(product_money),
                0
            )
        FROM sales
    """).fetchone()[0]


    expenses = connection.execute("""
        SELECT
            COALESCE(
                SUM(amount),
                0
            )
        FROM expenses
    """).fetchone()[0]


    connection.close()


    revenue = (
        billiard +
        tennis +
        products
    )


    profit = (
        revenue -
        expenses
    )


    return jsonify({

        "billiard":
            billiard,

        "tennis":
            tennis,

        "products":
            products,

        "expenses":
            expenses,

        "revenue":
            revenue,

        "profit":
            profit

    })


# ============================================================
# 24. XARAJAT
# ============================================================

@app.route(
    "/api/expenses",
    methods=["POST"]
)
def api_expense():

    if not is_logged():

        return jsonify(
            {"error":"login"}
        ), 401

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()


    try:

        amount = int(
            data.get(
                "amount",
                0
            )
        )

    except:

        amount = 0


    if (
        not name
        or amount <= 0
    ):

        return jsonify(
            {"error":"invalid"}
        ), 400


    connection = db()

    connection.execute("""
        INSERT INTO expenses
        (
            name,
            amount,
            created
        )
        VALUES
        (
            ?,
            ?,
            ?
        )
    """, (
        name,
        amount,
        time.time()
    ))

    connection.commit()

    connection.close()

    return jsonify(
        {"ok":True}
    )


# ============================================================
# 25. SOZLAMALAR API
# ============================================================

@app.route(
    "/api/settings",
    methods=["GET", "POST"]
)
def api_settings():

    if not is_logged():

        return jsonify(
            {"error":"login"}
        ), 401


    if request.method == "GET":

        return jsonify(
            dict(
                settings()
            )
        )


    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    old = settings()


    club_name = str(
        data.get(
            "club_name",
            old["club_name"]
        )
    ).strip()


    password = str(
        data.get(
            "password",
            ""
        )
    )


    if not password:

        password = old["password"]


    try:

        billiard_price = int(
            data.get(
                "billiard_price",
                old["billiard_price"]
            )
        )

    except:

        billiard_price = \
            old["billiard_price"]


    try:

        tennis_price = int(
            data.get(
                "tennis_price",
                old["tennis_price"]
            )
        )

    except:

        tennis_price = \
            old["tennis_price"]


    connection = db()

    connection.execute("""
        UPDATE settings

        SET
            club_name=?,
            password=?,
            billiard_price=?,
            tennis_price=?

        WHERE id=1
    """, (
        club_name or "BILLIARD GLOBAL",
        password,
        billiard_price,
        tennis_price
    ))

    connection.commit()

    connection.close()


    return jsonify(
        {"ok":True}
    )


# ============================================================
# 26. DASTURNI ISHGA TUSHIRISH
# ============================================================

if __name__ == "__main__":

    print("")
    print("=" * 60)
    print("       BILLIARD GLOBAL PRO 4")
    print("=" * 60)
    print("Dastur muvaffaqiyatli ishga tushmoqda...")
    print("Login parol: 1234")
    print("")
    print("Kompyuterda:")
    print("http://127.0.0.1:5000")
    print("")
    print("Telefon uchun bir xil Wi-Fi:")
    print("http://KOMPYUTER_IP:5000")
    print("=" * 60)
    print("")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True
    )