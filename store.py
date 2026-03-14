import sys, sqlite3, shutil, os
from datetime import datetime
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

# ═══════════════════════════════════════════════════════
#  BACKUP
# ═══════════════════════════════════════════════════════
def make_backup():
    os.makedirs("backup", exist_ok=True)
    if os.path.exists("shop.db"):
        dst = f"backup/backup_{datetime.now().strftime('%Y_%m_%d')}.db"
        if not os.path.exists(dst):
            shutil.copy2("shop.db", dst)
make_backup()

# ═══════════════════════════════════════════════════════
#  DATABASE
# ═══════════════════════════════════════════════════════
DB = sqlite3.connect("shop.db")
C  = DB.cursor()

# ── Migration: rename old sales table if it lacks invoice_no ──
try:
    C.execute("SELECT invoice_no FROM sales LIMIT 1")
except Exception:
    try:
        C.execute("ALTER TABLE sales RENAME TO sales_legacy")
        DB.commit()
    except Exception:
        pass

# ── Migration: fix customer_ledger / supplier_ledger column names ──
def _migrate_ledger(table, id_col):
    try:
        C.execute(f"SELECT type FROM {table} LIMIT 1")
        try:
            C.execute(f"SELECT date FROM {table} LIMIT 1")
        except Exception:
            try:
                C.execute(f"ALTER TABLE {table} ADD COLUMN date TEXT DEFAULT ''")
                DB.commit()
            except Exception:
                pass
    except Exception:
        try:
            tmp = f"{table}_old_bak"
            C.execute(f"ALTER TABLE {table} RENAME TO {tmp}")
            C.execute(f"""
                CREATE TABLE {table}(
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    {id_col}    INTEGER,
                    type        TEXT,
                    details     TEXT,
                    amount      REAL,
                    date        TEXT
                )
            """)
            try:
                C.execute(f"""
                    INSERT INTO {table}(id,{id_col},type,details,amount,date)
                    SELECT id,{id_col},transaction_type,details,amount,transaction_date
                    FROM {tmp}
                """)
            except Exception:
                pass
            C.execute(f"DROP TABLE IF EXISTS {tmp}")
            DB.commit()
        except Exception:
            pass

_migrate_ledger("customer_ledger", "customer_id")
_migrate_ledger("supplier_ledger", "supplier_id")

# ── Create all tables ──
C.executescript("""
CREATE TABLE IF NOT EXISTS products(
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    unit     TEXT DEFAULT 'قطعة',
    cost     REAL DEFAULT 0,
    price    REAL DEFAULT 0,
    quantity REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS customers(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    phone      TEXT DEFAULT '',
    total_debt REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS customer_ledger(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    type        TEXT,
    details     TEXT,
    amount      REAL,
    date        TEXT
);
CREATE TABLE IF NOT EXISTS suppliers(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    phone      TEXT DEFAULT '',
    total_debt REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS supplier_ledger(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER,
    type        TEXT,
    details     TEXT,
    amount      REAL,
    date        TEXT
);
CREATE TABLE IF NOT EXISTS sales(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no    TEXT,
    customer_id   INTEGER DEFAULT NULL,
    customer_name TEXT DEFAULT 'كاش',
    payment_type  TEXT DEFAULT 'كاش',
    total         REAL DEFAULT 0,
    paid_amount   REAL DEFAULT 0,
    remaining     REAL DEFAULT 0,
    profit        REAL DEFAULT 0,
    sale_date     TEXT
);
CREATE TABLE IF NOT EXISTS sale_items(
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id      INTEGER,
    product_id   INTEGER,
    product_name TEXT,
    unit         TEXT DEFAULT 'قطعة',
    cost         REAL,
    price        REAL,
    quantity     REAL,
    total        REAL,
    profit       REAL
);
CREATE TABLE IF NOT EXISTS purchases(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id   INTEGER DEFAULT NULL,
    supplier_name TEXT DEFAULT 'نقدي',
    payment_type  TEXT DEFAULT 'نقدي',
    total         REAL DEFAULT 0,
    paid_amount   REAL DEFAULT 0,
    remaining     REAL DEFAULT 0,
    purchase_date TEXT
);
CREATE TABLE IF NOT EXISTS purchase_items(
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id  INTEGER,
    product_id   INTEGER,
    product_name TEXT,
    unit         TEXT DEFAULT 'قطعة',
    cost         REAL,
    quantity     REAL,
    total        REAL
);
""")
DB.commit()

# ── Add missing columns to existing tables ──
for sql in [
    "ALTER TABLE products  ADD COLUMN cost REAL DEFAULT 0",
    "ALTER TABLE products  ADD COLUMN unit TEXT DEFAULT 'قطعة'",
    "ALTER TABLE customers ADD COLUMN phone TEXT DEFAULT ''",
    "ALTER TABLE sale_items     ADD COLUMN unit TEXT DEFAULT 'قطعة'",
    "ALTER TABLE purchase_items ADD COLUMN unit TEXT DEFAULT 'قطعة'",
    # ── NEW: partial payment columns ──
    "ALTER TABLE sales     ADD COLUMN paid_amount REAL DEFAULT 0",
    "ALTER TABLE sales     ADD COLUMN remaining   REAL DEFAULT 0",
    "ALTER TABLE purchases ADD COLUMN paid_amount REAL DEFAULT 0",
    "ALTER TABLE purchases ADD COLUMN remaining   REAL DEFAULT 0",
]:
    try:
        C.execute(sql); DB.commit()
    except Exception:
        pass

# ── Fix legacy rows: if paid_amount is NULL/0 and payment_type is 'كاش' set paid=total ──
try:
    C.execute("""
        UPDATE sales SET paid_amount=total, remaining=0
        WHERE (paid_amount IS NULL OR paid_amount=0) AND payment_type='كاش'
    """)
    C.execute("""
        UPDATE sales SET paid_amount=0, remaining=total
        WHERE (paid_amount IS NULL OR paid_amount=0) AND payment_type='آجل'
    """)
    C.execute("""
        UPDATE purchases SET paid_amount=total, remaining=0
        WHERE (paid_amount IS NULL OR paid_amount=0) AND payment_type='نقدي'
    """)
    C.execute("""
        UPDATE purchases SET paid_amount=0, remaining=total
        WHERE (paid_amount IS NULL OR paid_amount=0) AND payment_type='آجل'
    """)
    DB.commit()
except Exception:
    pass

# ═══════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════
UNITS = ["قطعة", "كيلو", "جرام", "لتر", "مللي", "متر", "سنتيمتر",
         "كرتون", "علبة", "كيس", "دزينة", "باكيت"]

def q(sql, p=()):
    C.execute(sql, p); DB.commit()

def rows(sql, p=()):
    C.execute(sql, p); return C.fetchall()

def one(sql, p=()):
    C.execute(sql, p); return C.fetchone()

def n(v):
    """Safe float."""
    try:
        return float(v) if v is not None else 0.0
    except Exception:
        return 0.0

def fmt_qty(v, unit=""):
    """Smart quantity display — removes trailing zeros."""
    f = n(v)
    if f == int(f):
        s = str(int(f))
    else:
        s = f"{f:.3f}".rstrip("0")
    return f"{s} {unit}".strip() if unit else s

def money(v):
    return f"{n(v):.2f}"

def inp(placeholder, max_w=None):
    w = QLineEdit()
    w.setPlaceholderText(placeholder)
    if max_w:
        w.setMaximumWidth(max_w)
    return w

def make_btn(text, color, cb=None, min_w=90):
    b = QPushButton(text)
    b.setStyleSheet(
        f"background:{color};color:white;font-weight:bold;"
        f"padding:6px 12px;border-radius:4px;font-size:12px;"
    )
    b.setMinimumWidth(min_w)
    if cb:
        b.clicked.connect(cb)
    return b

def make_table(headers, min_h=None):
    t = QTableWidget()
    t.setColumnCount(len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(True)
    if min_h:
        t.setMinimumHeight(min_h)
    return t

def fill_table(t, data, red_col=None, red_thresh=5,
               amber_col=None, amber_thresh=0.0):
    t.setRowCount(len(data))
    for i, row in enumerate(data):
        for j, val in enumerate(row):
            v = val if val is not None else 0
            if isinstance(v, float):
                text = fmt_qty(v)
            else:
                text = str(v)
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            if red_col is not None and j == red_col and n(v) < red_thresh:
                item.setBackground(QColor("#FFCDD2"))
                item.setForeground(QColor("#B71C1C"))
            if amber_col is not None and j == amber_col and n(v) > amber_thresh:
                item.setBackground(QColor("#FFF9C4"))
                item.setForeground(QColor("#E65100"))
            t.setItem(i, j, item)
    t.resizeColumnsToContents()


# ═══════════════════════════════════════════════════════
#  DIALOGS
# ═══════════════════════════════════════════════════════

# ── Improved Ledger Dialog with running balance ──
class LedgerDialog(QDialog):
    def __init__(self, entity_id, entity_name, ledger_table, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"كشف حساب: {entity_name}")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(820, 560)
        lay = QVBoxLayout(self)

        title = QLabel(f"📄  كشف حساب تفصيلي: {entity_name}")
        title.setFont(QFont("Arial", 13, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color:#1a237e;padding:8px;")
        lay.addWidget(title)

        # ── Table with running balance column ──
        tbl = QTableWidget()
        tbl.setColumnCount(5)
        tbl.setHorizontalHeaderLabels(["التاريخ", "النوع", "التفاصيل", "المبلغ", "الرصيد التراكمي"])
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setMinimumHeight(380)
        lay.addWidget(tbl)

        id_col = "customer_id" if "customer" in ledger_table else "supplier_id"
        data = rows(
            f"SELECT date, type, details, amount FROM {ledger_table} "
            f"WHERE {id_col}=? ORDER BY id ASC",
            (entity_id,)
        )

        # Calculate running balance
        balance   = 0.0
        total_debt   = 0.0
        total_paid   = 0.0
        tbl.setRowCount(len(data))
        for i, (date, typ, details, amount) in enumerate(data):
            amt = n(amount)
            is_payment = "سداد" in str(typ)
            if is_payment:
                balance    -= amt
                total_paid += amt
            else:
                balance    += amt
                total_debt += amt

            for j, val in enumerate([date, typ, details, f"{amt:.2f}", f"{balance:.2f}"]):
                item = QTableWidgetItem(val if val else "")
                item.setTextAlignment(Qt.AlignCenter)
                # Color payment rows green, debt rows red
                if is_payment:
                    item.setForeground(QColor("#2E7D32"))
                else:
                    item.setForeground(QColor("#C62828"))
                # Highlight balance column
                if j == 4:
                    item.setFont(QFont("Arial", 10, QFont.Bold))
                    if balance > 0:
                        item.setBackground(QColor("#FFF9C4"))
                    else:
                        item.setBackground(QColor("#E8F5E9"))
                tbl.setItem(i, j, item)
        tbl.resizeColumnsToContents()

        # Summary bar
        summary = QLabel(
            f"  📌 إجمالي المديونية: {total_debt:.2f}   |   "
            f"✅ إجمالي السدادات: {total_paid:.2f}   |   "
            f"💰 الرصيد المتبقي: {balance:.2f}"
        )
        summary.setStyleSheet(
            "font-weight:bold;padding:8px;color:#1a237e;"
            "background:#e8eaf6;border-radius:4px;"
        )
        lay.addWidget(summary)

        close_btn = make_btn("✖  إغلاق", "#757575", self.close, 100)
        close_btn.setFixedWidth(120)
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()
        btn_lay.addWidget(close_btn)
        lay.addLayout(btn_lay)


class InvoiceDialog(QDialog):
    """Sale invoice detail — shows items + payment breakdown."""
    def __init__(self, sale_id, invoice_no, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"تفاصيل الفاتورة: {invoice_no}")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(820, 480)
        lay = QVBoxLayout(self)

        # ── Header info ──
        sale = one(
            "SELECT customer_name, payment_type, total, paid_amount, remaining, profit, sale_date "
            "FROM sales WHERE id=?", (sale_id,)
        )
        if not sale:
            lay.addWidget(QLabel("لم يتم العثور على الفاتورة"))
            return

        cname, ptype, total, paid, remaining, profit, sdate = sale
        paid      = n(paid)
        remaining = n(remaining)

        hdr = QLabel(f"🧾  فاتورة رقم: {invoice_no}")
        hdr.setFont(QFont("Arial", 12, QFont.Bold))
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setStyleSheet("color:#1a237e;padding:4px;")
        lay.addWidget(hdr)

        # Info row
        info_lay = QHBoxLayout()
        for label, val, color in [
            ("العميل", cname, "#1a237e"),
            ("نوع الدفع", ptype, "#4527A0"),
            ("التاريخ", sdate, "#333"),
        ]:
            lbl = QLabel(f"<b>{label}:</b> {val}")
            lbl.setStyleSheet(f"color:{color};padding:4px 10px;")
            info_lay.addWidget(lbl)
        lay.addLayout(info_lay)

        # Items table
        tbl = make_table(
            ["المنتج", "الوحدة", "الكمية", "سعر الشراء", "سعر البيع", "الإجمالي", "الربح"]
        )
        data = rows(
            "SELECT product_name, unit, quantity, cost, price, total, profit "
            "FROM sale_items WHERE sale_id=?",
            (sale_id,)
        )
        fill_table(tbl, data)
        lay.addWidget(tbl)

        # Payment summary
        pay_frame = QFrame()
        pay_frame.setStyleSheet(
            "background:#f3f4f6;border-radius:6px;padding:4px;"
        )
        pay_lay = QGridLayout(pay_frame)

        def pay_lbl(text, color="#333", bold=False):
            l = QLabel(text)
            l.setStyleSheet(f"color:{color};{'font-weight:bold;' if bold else ''}padding:3px 8px;")
            return l

        pay_lay.addWidget(pay_lbl("إجمالي الفاتورة:", bold=True), 0, 0)
        pay_lay.addWidget(pay_lbl(f"{n(total):.2f}", "#1a237e", True), 0, 1)
        pay_lay.addWidget(pay_lbl("المدفوع كاش:", bold=True), 0, 2)
        pay_lay.addWidget(pay_lbl(f"{paid:.2f}", "#2E7D32", True), 0, 3)
        pay_lay.addWidget(pay_lbl("المتبقي (آجل):", bold=True), 0, 4)
        remaining_color = "#C62828" if remaining > 0 else "#2E7D32"
        pay_lay.addWidget(pay_lbl(f"{remaining:.2f}", remaining_color, True), 0, 5)
        pay_lay.addWidget(pay_lbl("الربح:", bold=True), 0, 6)
        pay_lay.addWidget(pay_lbl(f"{n(profit):.2f}", "#558B2F", True), 0, 7)
        lay.addWidget(pay_frame)


class PurchaseDetailDialog(QDialog):
    """Purchase invoice detail — shows items + payment breakdown."""
    def __init__(self, purchase_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"تفاصيل الشراء رقم: #{purchase_id}")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(720, 440)
        lay = QVBoxLayout(self)

        purch = one(
            "SELECT supplier_name, payment_type, total, paid_amount, remaining, purchase_date "
            "FROM purchases WHERE id=?", (purchase_id,)
        )
        if not purch:
            lay.addWidget(QLabel("لم يتم العثور على الفاتورة"))
            return

        sname, ptype, total, paid, remaining, pdate = purch
        paid      = n(paid)
        remaining = n(remaining)

        hdr = QLabel(f"📦  فاتورة شراء رقم: #{purchase_id}")
        hdr.setFont(QFont("Arial", 12, QFont.Bold))
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setStyleSheet("color:#C62828;padding:4px;")
        lay.addWidget(hdr)

        info_lay = QHBoxLayout()
        for label, val, color in [
            ("المورد", sname, "#4E342E"),
            ("نوع الدفع", ptype, "#4527A0"),
            ("التاريخ", pdate, "#333"),
        ]:
            lbl = QLabel(f"<b>{label}:</b> {val}")
            lbl.setStyleSheet(f"color:{color};padding:4px 10px;")
            info_lay.addWidget(lbl)
        lay.addLayout(info_lay)

        tbl = make_table(["المنتج", "الوحدة", "الكمية", "سعر الشراء", "الإجمالي"])
        data = rows(
            "SELECT product_name, unit, quantity, cost, total "
            "FROM purchase_items WHERE purchase_id=?",
            (purchase_id,)
        )
        fill_table(tbl, data)
        lay.addWidget(tbl)

        pay_frame = QFrame()
        pay_frame.setStyleSheet("background:#fce4ec;border-radius:6px;padding:4px;")
        pay_lay = QGridLayout(pay_frame)

        def pay_lbl(text, color="#333", bold=False):
            l = QLabel(text)
            l.setStyleSheet(f"color:{color};{'font-weight:bold;' if bold else ''}padding:3px 8px;")
            return l

        pay_lay.addWidget(pay_lbl("إجمالي الفاتورة:", bold=True), 0, 0)
        pay_lay.addWidget(pay_lbl(f"{n(total):.2f}", "#C62828", True), 0, 1)
        pay_lay.addWidget(pay_lbl("المدفوع:", bold=True), 0, 2)
        pay_lay.addWidget(pay_lbl(f"{paid:.2f}", "#2E7D32", True), 0, 3)
        pay_lay.addWidget(pay_lbl("المتبقي (آجل):", bold=True), 0, 4)
        remaining_color = "#C62828" if remaining > 0 else "#2E7D32"
        pay_lay.addWidget(pay_lbl(f"{remaining:.2f}", remaining_color, True), 0, 5)
        lay.addWidget(pay_frame)


# ═══════════════════════════════════════════════════════
#  PARTIAL PAYMENT DIALOG
# ═══════════════════════════════════════════════════════
class PartialPaymentDialog(QDialog):
    """
    Dialog to enter a partial upfront payment for a credit sale/purchase.
    Returns (paid_now, remaining) or (None, None) if cancelled.
    """
    def __init__(self, total, mode="sale", parent=None):
        super().__init__(parent)
        self.total = total
        self.result_paid = None
        self.result_remaining = None

        title = "دفع جزئي — فاتورة بيع" if mode == "sale" else "دفع جزئي — فاتورة شراء"
        self.setWindowTitle(title)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedSize(420, 220)
        lay = QVBoxLayout(self)

        lay.addWidget(QLabel(f"<b>إجمالي الفاتورة: {total:.2f}</b>"))

        form = QFormLayout()
        self.inp_paid = QLineEdit()
        self.inp_paid.setPlaceholderText("0.00  (اتركه فارغاً للآجل الكامل)")
        self.inp_paid.textChanged.connect(self._update_remaining)
        form.addRow("المدفوع الآن (كاش):", self.inp_paid)

        self.lbl_remaining = QLabel(f"{total:.2f}")
        self.lbl_remaining.setStyleSheet("font-weight:bold;color:#C62828;font-size:14px;")
        form.addRow("المتبقي (آجل):", self.lbl_remaining)
        lay.addLayout(form)

        note = QLabel("💡 المتبقي سيُضاف للدين تلقائياً")
        note.setStyleSheet("color:#757575;font-size:11px;")
        lay.addWidget(note)

        btns = QHBoxLayout()
        ok_btn = make_btn("✅  تأكيد", "#2E7D32", self._confirm)
        cancel_btn = make_btn("✖  إلغاء", "#C62828", self.reject)
        btns.addStretch()
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        lay.addLayout(btns)

    def _update_remaining(self, text):
        paid = n(text)
        remaining = max(0.0, self.total - paid)
        self.lbl_remaining.setText(f"{remaining:.2f}")
        self.lbl_remaining.setStyleSheet(
            f"font-weight:bold;font-size:14px;"
            f"color:{'#C62828' if remaining > 0 else '#2E7D32'};"
        )

    def _confirm(self):
        paid_text = self.inp_paid.text().strip()
        if paid_text == "":
            paid = 0.0
        else:
            paid = n(paid_text)
        if paid < 0 or paid > self.total + 1e-6:
            QMessageBox.warning(self, "خطأ", f"المبلغ المدفوع يجب أن يكون بين 0 و {self.total:.2f}")
            return
        self.result_paid      = min(paid, self.total)
        self.result_remaining = max(0.0, self.total - self.result_paid)
        self.accept()


# ═══════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════
class ShopApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("سرجة العلا")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(1280, 800)

        self.cart          = []
        self.purchase_cart = []

        root = QVBoxLayout(self)

        hdr = QLabel("🏪 سرجة العلا")
        hdr.setFont(QFont("Arial", 17, QFont.Bold))
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setStyleSheet(
            "color:white;background:#1a237e;padding:10px;"
            "border-radius:6px;margin-bottom:4px;"
        )
        root.addWidget(hdr)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabBar::tab{min-width:130px;padding:8px 10px;"
            "font-size:12px;font-weight:bold;}"
        )
        root.addWidget(self.tabs)

        for setup_fn, label in [
            (self.setup_pos_tab,       "🛒  نقطة البيع"),
            (self.setup_inventory_tab, "📦  المخزون"),
            (self.setup_purchases_tab, "🚚  المشتريات"),
            (self.setup_customers_tab, "👥  العملاء"),
            (self.setup_suppliers_tab, "🏭  الموردون"),
            (self.setup_reports_tab,   "📊  التقارير"),
        ]:
            w = QWidget()
            w.setLayoutDirection(Qt.RightToLeft)
            setup_fn(w)
            self.tabs.addTab(w, label)

        self.refresh_pos_products()
        self.refresh_inventory()
        self.refresh_purchases_products()
        self.refresh_customers()
        self.refresh_suppliers()
        self.refresh_customer_combos()
        self.refresh_supplier_combos()
        self.refresh_purchases_history()

    # ══════════════════════════════════════════════
    #  TAB 1 — نقطة البيع
    # ══════════════════════════════════════════════
    def setup_pos_tab(self, w):
        lay = QHBoxLayout(w)

        # ── Left ──
        left = QVBoxLayout()

        self.pos_search = inp("🔍  بحث سريع عن منتج...")
        self.pos_search.setStyleSheet("padding:7px;font-size:13px;")
        self.pos_search.textChanged.connect(self._search_pos)
        left.addWidget(self.pos_search)

        self.pos_products = make_table(
            ["ID", "المنتج", "الوحدة", "سعر البيع", "المخزون"], min_h=320
        )
        self.pos_products.doubleClicked.connect(lambda: self._add_to_cart(qty=1.0))
        left.addWidget(
            QLabel("  💡 انقر مرتين لإضافة 1 وحدة بسرعة  |  أو حدد الكمية واضغط 'إضافة'")
        )

        add_row = QHBoxLayout()
        self.pos_qty = inp("الكمية", 100)
        self.pos_qty.setText("1")
        self.pos_amt = inp("أو بمبلغ (جنيه)", 120)
        add_row.addWidget(QLabel("الكمية:"))
        add_row.addWidget(self.pos_qty)
        add_row.addWidget(QLabel("  أو مبلغ:"))
        add_row.addWidget(self.pos_amt)
        add_row.addWidget(make_btn("➕ إضافة للسلة", "#1565C0", self.add_to_cart))
        add_row.addStretch()
        left.addLayout(add_row)
        left.addWidget(self.pos_products)

        # ── Right ──
        right = QVBoxLayout()

        cart_hdr = QLabel("🛒  سلة البيع")
        cart_hdr.setFont(QFont("Arial", 12, QFont.Bold))
        cart_hdr.setAlignment(Qt.AlignCenter)
        cart_hdr.setStyleSheet("background:#e3f2fd;padding:6px;border-radius:4px;")
        right.addWidget(cart_hdr)

        self.cart_table = make_table(
            ["المنتج", "الوحدة", "الكمية", "السعر", "الإجمالي", "❌"]
        )
        self.cart_table.setMinimumWidth(460)
        self.cart_table.setMinimumHeight(300)
        self.cart_table.cellClicked.connect(self._cart_remove)
        right.addWidget(self.cart_table)

        tot_grp = QGroupBox("الإجماليات")
        tot_lay = QGridLayout(tot_grp)
        self.lbl_total  = QLabel("0.00")
        self.lbl_profit = QLabel("0.00")
        self.lbl_total.setStyleSheet("font-size:18px;font-weight:bold;color:#1a237e;")
        self.lbl_profit.setStyleSheet("font-size:16px;font-weight:bold;color:#2E7D32;")
        tot_lay.addWidget(QLabel("إجمالي الفاتورة:"), 0, 0)
        tot_lay.addWidget(self.lbl_total,  0, 1)
        tot_lay.addWidget(QLabel("إجمالي الربح:"),    1, 0)
        tot_lay.addWidget(self.lbl_profit, 1, 1)
        right.addWidget(tot_grp)

        pay_grp = QGroupBox("طريقة الدفع")
        pay_lay = QGridLayout(pay_grp)
        self.pos_cust_combo = QComboBox()
        self.pos_cust_combo.setMinimumWidth(200)
        pay_lay.addWidget(QLabel("العميل (للآجل):"), 0, 0)
        pay_lay.addWidget(self.pos_cust_combo, 0, 1, 1, 3)
        pay_lay.addWidget(make_btn("💵  بيع كاش",      "#2E7D32", self.sell_cash,          140), 1, 0)
        pay_lay.addWidget(make_btn("📋  بيع آجل",      "#C62828", self.sell_credit,        140), 1, 1)
        pay_lay.addWidget(make_btn("💳  بيع جزئي",     "#E65100", self.sell_partial,       140), 1, 2)
        pay_lay.addWidget(make_btn("🗑  إفراغ",        "#757575", self.clear_cart,         100), 1, 3)
        right.addWidget(pay_grp)

        lay.addLayout(left,  52)
        lay.addLayout(right, 48)
        self.pos_products.clicked.connect(self._pos_item_clicked)

    def _pos_item_clicked(self):
        row = self.pos_products.currentRow()
        if row != -1:
            unit = self.pos_products.item(row, 2).text()
            self.pos_qty.setPlaceholderText(f"الكمية ({unit})")

    def refresh_pos_products(self, text=""):
        res = rows(
            "SELECT id, name, unit, price, quantity FROM products "
            "WHERE name LIKE ? ORDER BY name",
            (f"%{text}%",)
        )
        data = [(r[0], f"{r[1]} ({r[2]})", r[2], r[3], r[4]) for r in res]
        fill_table(self.pos_products, data, red_col=4, red_thresh=0.001)

    def _search_pos(self, text):
        self.refresh_pos_products(text)

    def _add_to_cart(self, qty=None):
        row = self.pos_products.currentRow()
        if row == -1:
            QMessageBox.warning(self, "تنبيه", "اختر منتجاً من القائمة أولاً")
            return None

        pid   = int(self.pos_products.item(row, 0).text())
        name  = self.pos_products.item(row, 1).text()
        unit  = self.pos_products.item(row, 2).text()
        price = n(self.pos_products.item(row, 3).text())
        stock = n(self.pos_products.item(row, 4).text())

        if qty is None:
            amt_val = self.pos_amt.text().strip()
            if amt_val:
                try:
                    val = n(amt_val)
                    if val <= 0: raise ValueError()
                    qty = round(val / price, 4)
                except Exception:
                    QMessageBox.warning(self, "خطأ", "أدخل مبلغاً صحيحاً")
                    return None
            else:
                try:
                    qty = n(self.pos_qty.text())
                    if qty <= 0:
                        raise ValueError()
                except Exception:
                    QMessageBox.warning(self, "خطأ", "أدخل كمية صحيحة (مثال: 1 أو 0.5)")
                    return None

        # ── Already in cart → update ──
        for item in self.cart:
            if item["pid"] == pid:
                new_qty = round(item["qty"] + qty, 6)
                if new_qty > stock + 1e-6:
                    QMessageBox.warning(
                        self, "خطأ",
                        f"المخزون غير كافٍ!\n"
                        f"المتاح: {fmt_qty(stock, unit)}\n"
                        f"في السلة بالفعل: {fmt_qty(item['qty'], unit)}"
                    )
                    return None
                cost_r = one("SELECT cost FROM products WHERE id=?", (pid,))
                cost   = n(cost_r[0]) if cost_r else 0
                item.update({
                    "qty":    new_qty,
                    "cost":   cost,
                    "total":  round(new_qty * price, 4),
                    "profit": round((price - cost) * new_qty, 4),
                })
                self.refresh_cart()
                return item

        if qty > stock + 1e-6:
            QMessageBox.warning(
                self, "خطأ",
                f"المخزون غير كافٍ!\nالمتاح: {fmt_qty(stock, unit)}"
            )
            return None

        cost_r = one("SELECT cost FROM products WHERE id=?", (pid,))
        cost   = n(cost_r[0]) if cost_r else 0

        entry = {
            "pid": pid, "name": name, "unit": unit,
            "cost": cost, "price": price, "qty": qty,
            "total":  round(price * qty, 4),
            "profit": round((price - cost) * qty, 4),
        }
        self.cart.append(entry)
        self.pos_amt.clear()
        self.refresh_cart()
        return entry

    def add_to_cart(self):
        self._add_to_cart()

    def refresh_cart(self):
        self.cart_table.setRowCount(len(self.cart))
        for i, item in enumerate(self.cart):
            for j, v in enumerate([
                item["name"], item["unit"],
                fmt_qty(item["qty"]),
                money(item["price"]),
                money(item["total"]),
                "❌",
            ]):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignCenter)
                if j == 5:
                    cell.setForeground(QColor("#C62828"))
                self.cart_table.setItem(i, j, cell)

        total  = sum(i["total"]  for i in self.cart)
        profit = sum(i["profit"] for i in self.cart)
        self.lbl_total.setText(money(total))
        self.lbl_profit.setText(money(profit))
        self.cart_table.resizeColumnsToContents()

    def _cart_remove(self, row, col):
        if col == 5 and row < len(self.cart):
            del self.cart[row]
            self.refresh_cart()

    def clear_cart(self):
        self.cart.clear()
        self.refresh_cart()

    def sell_cash(self):
        self._process_sale(mode="cash")

    def sell_credit(self):
        self._process_sale(mode="credit")

    def sell_partial(self):
        self._process_sale(mode="partial")

    def _process_sale(self, mode):
        """mode: 'cash' | 'credit' | 'partial'"""
        if not self.cart:
            QMessageBox.warning(self, "تنبيه", "السلة فارغة!")
            return

        cust_id   = self.pos_cust_combo.currentData()
        cust_name = self.pos_cust_combo.currentText()

        if mode in ("credit", "partial") and not cust_id:
            QMessageBox.warning(self, "خطأ", "اختر عميلاً للبيع الآجل أو الجزئي")
            return

        total  = sum(i["total"]  for i in self.cart)
        profit = sum(i["profit"] for i in self.cart)

        # ── Determine paid / remaining ──
        if mode == "cash":
            paid_amount = total
            remaining   = 0.0
            ptype       = "كاش"
        elif mode == "credit":
            paid_amount = 0.0
            remaining   = total
            ptype       = "آجل"
        else:  # partial
            dlg = PartialPaymentDialog(total, mode="sale", parent=self)
            if dlg.exec() != QDialog.Accepted:
                return
            paid_amount = dlg.result_paid
            remaining   = dlg.result_remaining
            ptype       = "جزئي"

        # ── Validate stock ──
        for item in self.cart:
            res = one("SELECT quantity, unit FROM products WHERE id=?", (item["pid"],))
            if not res:
                QMessageBox.warning(self, "خطأ", f"المنتج [{item['name']}] غير موجود!")
                return
            db_stock = n(res[0])
            db_unit  = res[1] or item["unit"]
            if item["qty"] > db_stock + 1e-6:
                QMessageBox.warning(
                    self, "خطأ",
                    f"المخزون غير كافٍ للمنتج: {item['name']}\n"
                    f"المتاح: {fmt_qty(db_stock, db_unit)}\n"
                    f"المطلوب: {fmt_qty(item['qty'], db_unit)}"
                )
                return

        date = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

        q(
            "INSERT INTO sales(customer_id,customer_name,payment_type,total,paid_amount,remaining,profit,sale_date) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (cust_id if mode != "cash" else None,
             cust_name if mode != "cash" else "كاش",
             ptype, total, paid_amount, remaining, profit, date)
        )
        sale_id    = one("SELECT last_insert_rowid()")[0]
        invoice_no = f"INV-{sale_id:05d}"
        q("UPDATE sales SET invoice_no=? WHERE id=?", (invoice_no, sale_id))

        for item in self.cart:
            q(
                "INSERT INTO sale_items"
                "(sale_id,product_id,product_name,unit,cost,price,quantity,total,profit) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (sale_id, item["pid"], item["name"], item["unit"],
                 item["cost"], item["price"], item["qty"],
                 item["total"], item["profit"])
            )
            q("UPDATE products SET quantity = ROUND(quantity - ?, 6) WHERE id=?",
              (item["qty"], item["pid"]))

        # ── Update customer debt only for the remaining part ──
        if mode in ("credit", "partial") and remaining > 0:
            q("UPDATE customers SET total_debt = total_debt + ? WHERE id=?", (remaining, cust_id))
            details = (
                f"فاتورة {invoice_no} — إجمالي: {total:.2f}"
                + (f" — دفع كاش: {paid_amount:.2f}" if mode == "partial" else "")
            )
            q(
                "INSERT INTO customer_ledger(customer_id,type,details,amount,date) "
                "VALUES(?,?,?,?,?)",
                (cust_id,
                 "مشتريات آجل" if mode == "credit" else "مشتريات جزئية",
                 details, remaining, date)
            )

        # ── Summary message ──
        msg = (
            f"رقم الفاتورة : {invoice_no}\n"
            f"الإجمالي     : {total:.2f}\n"
            f"الربح        : {profit:.2f}"
        )
        if mode == "partial":
            msg += f"\n\nالمدفوع كاش  : {paid_amount:.2f}\nالمتبقي آجل  : {remaining:.2f}"
            msg += f"\nأُضيف للدين  : {cust_name}"
        elif mode == "credit":
            msg += f"\n\nأُضيف لحساب  : {cust_name}"

        QMessageBox.information(self, "✅ تم البيع", msg)

        self.cart.clear()
        self.refresh_cart()
        self.refresh_pos_products()
        self.refresh_inventory()
        self.refresh_customers()
        self.refresh_customer_combos()

    # ══════════════════════════════════════════════
    #  TAB 2 — المخزون
    # ══════════════════════════════════════════════
    def setup_inventory_tab(self, w):
        lay = QVBoxLayout(w)

        add_grp = QGroupBox("➕  إضافة / تعديل منتج")
        add_lay = QHBoxLayout(add_grp)

        self.inv_name  = inp("اسم المنتج")
        self.inv_unit  = QComboBox()
        self.inv_unit.addItems(UNITS)
        self.inv_unit.setMinimumWidth(90)
        self.inv_unit.setEditable(True)
        self.inv_cost  = inp("سعر الشراء",  110)
        self.inv_price = inp("سعر البيع",   110)
        self.inv_qty   = inp("الكمية",       90)

        add_lay.addWidget(self.inv_name)
        add_lay.addWidget(QLabel("الوحدة:"))
        add_lay.addWidget(self.inv_unit)
        add_lay.addWidget(QLabel("شراء:"))
        add_lay.addWidget(self.inv_cost)
        add_lay.addWidget(QLabel("بيع:"))
        add_lay.addWidget(self.inv_price)
        add_lay.addWidget(QLabel("كمية:"))
        add_lay.addWidget(self.inv_qty)
        add_lay.addWidget(make_btn("➕ إضافة",  "#388E3C", self.add_product))
        add_lay.addWidget(make_btn("✏️ تعديل", "#1565C0", self.edit_product))
        add_lay.addWidget(make_btn("🗑 حذف",   "#C62828", self.del_product))

        self.inv_search = inp("🔍  بحث...")
        self.inv_search.setStyleSheet("padding:6px;font-size:13px;")
        self.inv_search.textChanged.connect(lambda t: self.refresh_inventory(t))

        self.inv_table = make_table(
            ["ID", "المنتج", "الوحدة", "سعر الشراء", "سعر البيع", "المخزون", "هامش الربح %"],
            min_h=450
        )
        self.inv_table.clicked.connect(self._fill_inv_form)

        lay.addWidget(add_grp)
        lay.addWidget(self.inv_search)
        lay.addWidget(self.inv_table)

    def refresh_inventory(self, text=""):
        raw = rows(
            "SELECT id, name, unit, cost, price, quantity FROM products "
            "WHERE name LIKE ? ORDER BY name",
            (f"%{text}%",)
        )
        data = []
        for r in raw:
            cost, price = n(r[3]), n(r[4])
            margin = round((price - cost) / price * 100, 1) if price > 0 else 0.0
            data.append((r[0], r[1], r[2], cost, price, n(r[5]), margin))
        fill_table(self.inv_table, data, red_col=5, red_thresh=0.001)

    def _fill_inv_form(self):
        row = self.inv_table.currentRow()
        if row == -1: return
        self.inv_name.setText(self.inv_table.item(row, 1).text())
        unit_val = self.inv_table.item(row, 2).text()
        idx = self.inv_unit.findText(unit_val)
        self.inv_unit.setCurrentIndex(idx) if idx >= 0 else self.inv_unit.setCurrentText(unit_val)
        self.inv_cost.setText( self.inv_table.item(row, 3).text())
        self.inv_price.setText(self.inv_table.item(row, 4).text())
        self.inv_qty.setText(  self.inv_table.item(row, 5).text())

    def add_product(self):
        try:
            name  = self.inv_name.text().strip()
            unit  = self.inv_unit.currentText().strip() or "قطعة"
            cost  = n(self.inv_cost.text())
            price = n(self.inv_price.text())
            qty   = n(self.inv_qty.text())
            if not name: raise ValueError()
        except Exception:
            QMessageBox.warning(self, "خطأ", "أدخل بيانات صحيحة"); return
        q("INSERT INTO products(name,unit,cost,price,quantity) VALUES(?,?,?,?,?)",
          (name, unit, cost, price, qty))
        for f in (self.inv_name, self.inv_cost, self.inv_price, self.inv_qty):
            f.clear()
        self.refresh_inventory()
        self.refresh_pos_products()
        self.refresh_purchases_products()
        QMessageBox.information(self, "✅", f"تم إضافة المنتج: {name}")

    def edit_product(self):
        row = self.inv_table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "تنبيه", "اختر منتجاً للتعديل"); return
        pid = int(self.inv_table.item(row, 0).text())
        try:
            name  = self.inv_name.text().strip()
            unit  = self.inv_unit.currentText().strip() or "قطعة"
            cost  = n(self.inv_cost.text())
            price = n(self.inv_price.text())
            qty   = n(self.inv_qty.text())
            if not name: raise ValueError()
        except Exception:
            QMessageBox.warning(self, "خطأ", "أدخل بيانات صحيحة"); return
        q("UPDATE products SET name=?,unit=?,cost=?,price=?,quantity=? WHERE id=?",
          (name, unit, cost, price, qty, pid))
        self.refresh_inventory()
        self.refresh_pos_products()
        self.refresh_purchases_products()
        QMessageBox.information(self, "✅", "تم التعديل بنجاح")

    def del_product(self):
        row = self.inv_table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "تنبيه", "اختر منتجاً للحذف"); return
        pid  = int(self.inv_table.item(row, 0).text())
        name = self.inv_table.item(row, 1).text()
        reply = QMessageBox.question(
            self, "تأكيد الحذف", f"هل تريد حذف: {name}؟",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            q("DELETE FROM products WHERE id=?", (pid,))
            self.refresh_inventory()
            self.refresh_pos_products()

    # ══════════════════════════════════════════════
    #  TAB 3 — المشتريات
    # ══════════════════════════════════════════════
    def setup_purchases_tab(self, w):
        lay = QHBoxLayout(w)

        # ── Left ──
        left = QVBoxLayout()

        self.purch_search = inp("🔍  بحث عن منتج...")
        self.purch_search.setStyleSheet("padding:7px;font-size:13px;")
        self.purch_search.textChanged.connect(lambda t: self.refresh_purchases_products(t))
        left.addWidget(self.purch_search)

        self.purch_products = make_table(
            ["ID", "المنتج", "الوحدة", "سعر الشراء الحالي", "المخزون"], min_h=240
        )
        left.addWidget(self.purch_products)

        add_row = QHBoxLayout()
        self.purch_qty  = inp("الكمية (مثال: 0.5)", 160)
        self.purch_qty.setText("1")
        self.purch_cost = inp("سعر الشراء الجديد", 130)
        add_row.addWidget(QLabel("الكمية:"))
        add_row.addWidget(self.purch_qty)
        add_row.addWidget(QLabel("سعر الشراء:"))
        add_row.addWidget(self.purch_cost)
        add_row.addWidget(make_btn("➕ أضف للسلة", "#1565C0", self.add_to_purchase_cart))
        add_row.addStretch()
        left.addLayout(add_row)

        hist_grp = QGroupBox("📋  سجل المشتريات الأخيرة")
        hist_lay = QVBoxLayout(hist_grp)
        self.purch_history = make_table(
            ["#", "المورد", "الطريقة", "الإجمالي", "المدفوع", "المتبقي", "التاريخ", "تفاصيل"]
        )
        self.purch_history.setMaximumHeight(180)
        self.purch_history.cellDoubleClicked.connect(self._show_purchase_detail)
        hist_lay.addWidget(self.purch_history)
        left.addWidget(hist_grp)

        # ── Right ──
        right = QVBoxLayout()

        cart_hdr = QLabel("📦  سلة الشراء")
        cart_hdr.setFont(QFont("Arial", 12, QFont.Bold))
        cart_hdr.setAlignment(Qt.AlignCenter)
        cart_hdr.setStyleSheet("background:#fce4ec;padding:6px;border-radius:4px;")
        right.addWidget(cart_hdr)

        self.purch_cart_table = make_table(
            ["المنتج", "الوحدة", "الكمية", "سعر الشراء", "الإجمالي", "❌"], min_h=240
        )
        self.purch_cart_table.setMinimumWidth(430)
        self.purch_cart_table.cellClicked.connect(self._purch_cart_remove)
        right.addWidget(self.purch_cart_table)

        tot_grp = QGroupBox("الإجمالي")
        tot_lay = QHBoxLayout(tot_grp)
        self.lbl_purch_total = QLabel("0.00")
        self.lbl_purch_total.setStyleSheet("font-size:18px;font-weight:bold;color:#C62828;")
        tot_lay.addWidget(QLabel("إجمالي الفاتورة:"))
        tot_lay.addWidget(self.lbl_purch_total)
        right.addWidget(tot_grp)

        sup_grp = QGroupBox("المورد وطريقة الدفع")
        sup_lay = QGridLayout(sup_grp)
        self.purch_sup_combo = QComboBox()
        self.purch_sup_combo.setMinimumWidth(200)
        sup_lay.addWidget(QLabel("المورد:"), 0, 0)
        sup_lay.addWidget(self.purch_sup_combo, 0, 1, 1, 3)
        sup_lay.addWidget(make_btn("💵  شراء نقدي",  "#2E7D32", self.purchase_cash,    140), 1, 0)
        sup_lay.addWidget(make_btn("📋  شراء آجل",   "#C62828", self.purchase_credit,  140), 1, 1)
        sup_lay.addWidget(make_btn("💳  شراء جزئي",  "#E65100", self.purchase_partial, 140), 1, 2)
        sup_lay.addWidget(make_btn("🗑  إفراغ",      "#757575", self.clear_purchase_cart, 100), 1, 3)
        right.addWidget(sup_grp)

        lay.addLayout(left,  52)
        lay.addLayout(right, 48)

    def refresh_purchases_products(self, text=""):
        data = rows(
            "SELECT id, name, unit, cost, quantity FROM products "
            "WHERE name LIKE ? ORDER BY name",
            (f"%{text}%",)
        )
        fill_table(self.purch_products, data, red_col=4, red_thresh=0.001)

    def add_to_purchase_cart(self):
        row = self.purch_products.currentRow()
        if row == -1:
            QMessageBox.warning(self, "تنبيه", "اختر منتجاً من القائمة أولاً"); return

        pid          = int(self.purch_products.item(row, 0).text())
        name         = self.purch_products.item(row, 1).text()
        unit         = self.purch_products.item(row, 2).text()
        current_cost = n(self.purch_products.item(row, 3).text())

        try:
            qty       = n(self.purch_qty.text())
            cost_text = self.purch_cost.text().strip()
            cost      = n(cost_text) if cost_text else current_cost
            if qty <= 0: raise ValueError()
        except Exception:
            QMessageBox.warning(self, "خطأ", "أدخل كمية وسعر شراء صحيحَين"); return

        for item in self.purchase_cart:
            if item["pid"] == pid:
                item["qty"]   = round(item["qty"] + qty, 6)
                item["cost"]  = cost
                item["total"] = round(item["qty"] * cost, 4)
                self.refresh_purchase_cart()
                return

        self.purchase_cart.append({
            "pid": pid, "name": name, "unit": unit,
            "cost": cost, "qty": qty,
            "total": round(cost * qty, 4)
        })
        self.refresh_purchase_cart()

    def refresh_purchase_cart(self):
        self.purch_cart_table.setRowCount(len(self.purchase_cart))
        for i, item in enumerate(self.purchase_cart):
            for j, v in enumerate([
                item["name"], item["unit"],
                fmt_qty(item["qty"]),
                money(item["cost"]),
                money(item["total"]),
                "❌"
            ]):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignCenter)
                if j == 5:
                    cell.setForeground(QColor("#C62828"))
                self.purch_cart_table.setItem(i, j, cell)

        total = sum(i["total"] for i in self.purchase_cart)
        self.lbl_purch_total.setText(money(total))
        self.purch_cart_table.resizeColumnsToContents()

    def _purch_cart_remove(self, row, col):
        if col == 5 and row < len(self.purchase_cart):
            del self.purchase_cart[row]
            self.refresh_purchase_cart()

    def clear_purchase_cart(self):
        self.purchase_cart.clear()
        self.refresh_purchase_cart()

    def purchase_cash(self):
        self._process_purchase(mode="cash")

    def purchase_credit(self):
        self._process_purchase(mode="credit")

    def purchase_partial(self):
        self._process_purchase(mode="partial")

    def _process_purchase(self, mode):
        """mode: 'cash' | 'credit' | 'partial'"""
        if not self.purchase_cart:
            QMessageBox.warning(self, "تنبيه", "سلة الشراء فارغة!"); return

        sup_id   = self.purch_sup_combo.currentData()
        sup_name = self.purch_sup_combo.currentText()

        if mode in ("credit", "partial") and not sup_id:
            QMessageBox.warning(self, "خطأ", "اختر مورداً للشراء الآجل أو الجزئي"); return

        total = sum(i["total"] for i in self.purchase_cart)

        if mode == "cash":
            paid_amount = total
            remaining   = 0.0
            ptype       = "نقدي"
        elif mode == "credit":
            paid_amount = 0.0
            remaining   = total
            ptype       = "آجل"
        else:
            dlg = PartialPaymentDialog(total, mode="purchase", parent=self)
            if dlg.exec() != QDialog.Accepted:
                return
            paid_amount = dlg.result_paid
            remaining   = dlg.result_remaining
            ptype       = "جزئي"

        date = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

        q(
            "INSERT INTO purchases(supplier_id,supplier_name,payment_type,total,paid_amount,remaining,purchase_date) "
            "VALUES(?,?,?,?,?,?,?)",
            (sup_id if mode != "cash" else None,
             sup_name if mode != "cash" else "نقدي",
             ptype, total, paid_amount, remaining, date)
        )
        purch_id = one("SELECT last_insert_rowid()")[0]

        for item in self.purchase_cart:
            q(
                "INSERT INTO purchase_items"
                "(purchase_id,product_id,product_name,unit,cost,quantity,total) "
                "VALUES(?,?,?,?,?,?,?)",
                (purch_id, item["pid"], item["name"], item["unit"],
                 item["cost"], item["qty"], item["total"])
            )
            q("UPDATE products SET quantity=ROUND(quantity+?,6), cost=? WHERE id=?",
              (item["qty"], item["cost"], item["pid"]))

        # ── Update supplier debt for remaining only ──
        if mode in ("credit", "partial") and remaining > 0:
            q("UPDATE suppliers SET total_debt=total_debt+? WHERE id=?", (remaining, sup_id))
            details = (
                f"فاتورة شراء #{purch_id} — إجمالي: {total:.2f}"
                + (f" — دفع كاش: {paid_amount:.2f}" if mode == "partial" else "")
            )
            q(
                "INSERT INTO supplier_ledger(supplier_id,type,details,amount,date) "
                "VALUES(?,?,?,?,?)",
                (sup_id,
                 "مشتريات آجل" if mode == "credit" else "مشتريات جزئية",
                 details, remaining, date)
            )

        msg = (
            f"رقم الفاتورة : #{purch_id}\n"
            f"الإجمالي     : {total:.2f}"
        )
        if mode == "partial":
            msg += f"\n\nالمدفوع نقداً : {paid_amount:.2f}\nالمتبقي آجل  : {remaining:.2f}"
            msg += f"\nأُضيف لحساب  : {sup_name}"
        elif mode == "credit":
            msg += f"\n\nأُضيف لحساب المورد: {sup_name}"

        QMessageBox.information(self, "✅ تم الشراء", msg)

        self.purchase_cart.clear()
        self.refresh_purchase_cart()
        self.refresh_purchases_products()
        self.refresh_inventory()
        self.refresh_pos_products()
        self.refresh_purchases_history()
        self.refresh_suppliers()

    def refresh_purchases_history(self):
        data = rows(
            "SELECT id, supplier_name, payment_type, total, paid_amount, remaining, purchase_date "
            "FROM purchases ORDER BY id DESC LIMIT 30"
        )
        fill_table(self.purch_history, [(*r, "🔍 عرض") for r in data])

    def _show_purchase_detail(self, row, col):
        item = self.purch_history.item(row, 0)
        if item:
            PurchaseDetailDialog(int(item.text()), self).exec()

    # ══════════════════════════════════════════════
    #  TAB 4 — العملاء
    # ══════════════════════════════════════════════
    def setup_customers_tab(self, w):
        lay = QVBoxLayout(w)

        add_grp = QGroupBox("➕  إضافة عميل جديد")
        add_lay = QHBoxLayout(add_grp)
        self.cust_name  = inp("اسم العميل")
        self.cust_phone = inp("رقم الهاتف", 140)
        add_lay.addWidget(self.cust_name)
        add_lay.addWidget(self.cust_phone)
        add_lay.addWidget(make_btn("➕ إضافة", "#388E3C", self.add_customer))

        self.cust_table = make_table(
            ["ID", "اسم العميل", "الهاتف", "إجمالي الديون"], min_h=400
        )

        ops_grp = QGroupBox("العمليات")
        ops_lay = QHBoxLayout(ops_grp)
        self.cust_pay_amt = inp("مبلغ السداد", 140)
        ops_lay.addWidget(QLabel("المبلغ:"))
        ops_lay.addWidget(self.cust_pay_amt)
        ops_lay.addWidget(make_btn("✅  تسديد دفعة",  "#2E7D32", self.pay_customer))
        ops_lay.addWidget(make_btn("📄  كشف الحساب",  "#1565C0", self.show_customer_ledger))
        ops_lay.addWidget(make_btn("🧾  فواتيره",     "#4527A0", self.show_customer_invoices))
        ops_lay.addStretch()
        ops_lay.addWidget(make_btn("🗑  حذف",         "#C62828", self.del_customer))

        lay.addWidget(add_grp)
        lay.addWidget(self.cust_table)
        lay.addWidget(ops_grp)

    def refresh_customers(self):
        data = rows("SELECT id, name, phone, total_debt FROM customers ORDER BY name")
        fill_table(self.cust_table, data, amber_col=3)

    def refresh_customer_combos(self):
        data = rows("SELECT id, name FROM customers ORDER BY name")
        self.pos_cust_combo.clear()
        self.pos_cust_combo.addItem("-- اختر عميل --", userData=None)
        for r in data:
            self.pos_cust_combo.addItem(r[1], userData=r[0])

    def add_customer(self):
        name  = self.cust_name.text().strip()
        phone = self.cust_phone.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "أدخل اسم العميل"); return
        q("INSERT INTO customers(name,phone) VALUES(?,?)", (name, phone))
        self.cust_name.clear(); self.cust_phone.clear()
        self.refresh_customers()
        self.refresh_customer_combos()
        QMessageBox.information(self, "✅", f"تم إضافة العميل: {name}")

    def pay_customer(self):
        row = self.cust_table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "تنبيه", "اختر عميلاً أولاً"); return

        cid   = int(self.cust_table.item(row, 0).text())
        cname = self.cust_table.item(row, 1).text()
        debt  = n(self.cust_table.item(row, 3).text())

        try:
            amount = n(self.cust_pay_amt.text())
            if amount <= 0: raise ValueError()
        except Exception:
            QMessageBox.warning(self, "خطأ", "أدخل مبلغاً صحيحاً"); return

        if amount > debt:
            reply = QMessageBox.question(
                self, "⚠️ تنبيه",
                f"المبلغ ({amount:.2f}) أكبر من الدين ({debt:.2f}). هل تريد المتابعة؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No: return

        date = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        q("UPDATE customers SET total_debt=total_debt-? WHERE id=?", (amount, cid))
        q("INSERT INTO customer_ledger(customer_id,type,details,amount,date) VALUES(?,?,?,?,?)",
          (cid, "سداد دفعة", f"سداد نقدي — المتبقي: {max(0, debt-amount):.2f}", amount, date))

        self.cust_pay_amt.clear()
        self.refresh_customers()
        QMessageBox.information(self, "✅",
            f"تم تسديد {amount:.2f} من حساب {cname}\nالمتبقي: {max(0, debt - amount):.2f}")

    def show_customer_ledger(self):
        row = self.cust_table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "تنبيه", "اختر عميلاً أولاً"); return
        cid   = int(self.cust_table.item(row, 0).text())
        cname = self.cust_table.item(row, 1).text()
        LedgerDialog(cid, cname, "customer_ledger", self).exec()

    def show_customer_invoices(self):
        row = self.cust_table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "تنبيه", "اختر عميلاً أولاً"); return
        cid   = int(self.cust_table.item(row, 0).text())
        cname = self.cust_table.item(row, 1).text()

        data = rows(
            "SELECT invoice_no, payment_type, total, paid_amount, remaining, profit, sale_date "
            "FROM sales WHERE customer_id=? ORDER BY id DESC",
            (cid,)
        )
        total_inv   = sum(n(r[2]) for r in data)
        total_paid  = sum(n(r[3]) for r in data)
        total_rem   = sum(n(r[4]) for r in data)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"فواتير: {cname}")
        dlg.setLayoutDirection(Qt.RightToLeft)
        dlg.resize(780, 480)
        lay = QVBoxLayout(dlg)

        tbl = make_table(["الفاتورة", "الدفع", "الإجمالي", "المدفوع", "المتبقي", "الربح", "التاريخ"])
        fill_table(tbl, data)
        lay.addWidget(tbl)

        def _open_inv(r, c):
            item = tbl.item(r, 0)
            if item:
                inv_no = item.text()
                res = one("SELECT id FROM sales WHERE invoice_no=?", (inv_no,))
                if res: InvoiceDialog(res[0], inv_no, self).exec()
        tbl.cellDoubleClicked.connect(_open_inv)

        lbl = QLabel(
            f"  عدد الفواتير: {len(data)}   |   الإجمالي: {total_inv:.2f}"
            f"   |   المدفوع: {total_paid:.2f}   |   المتبقي: {total_rem:.2f}\n"
            "  💡 انقر مرتين على أي فاتورة لعرض محتوياتها بالتفصيل"
        )
        lbl.setStyleSheet("font-weight:bold;color:#1a237e;padding:6px;")
        lay.addWidget(lbl)
        dlg.exec()

    def del_customer(self):
        row = self.cust_table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "تنبيه", "اختر عميلاً أولاً"); return
        cid   = int(self.cust_table.item(row, 0).text())
        cname = self.cust_table.item(row, 1).text()
        debt  = n(self.cust_table.item(row, 3).text())
        if debt > 0:
            QMessageBox.warning(self, "⚠️", f"لا يمكن الحذف — على {cname} دين: {debt:.2f}"); return
        reply = QMessageBox.question(self, "تأكيد", f"حذف: {cname}؟",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            q("DELETE FROM customers WHERE id=?", (cid,))
            self.refresh_customers()
            self.refresh_customer_combos()

    # ══════════════════════════════════════════════
    #  TAB 5 — الموردون
    # ══════════════════════════════════════════════
    def setup_suppliers_tab(self, w):
        lay = QVBoxLayout(w)

        add_grp = QGroupBox("➕  إضافة مورد جديد")
        add_lay = QHBoxLayout(add_grp)
        self.sup_name  = inp("اسم المورد")
        self.sup_phone = inp("رقم الهاتف", 140)
        add_lay.addWidget(self.sup_name)
        add_lay.addWidget(self.sup_phone)
        add_lay.addWidget(make_btn("➕ إضافة", "#388E3C", self.add_supplier))

        self.sup_table = make_table(
            ["ID", "اسم المورد", "الهاتف", "المديونية (علينا)"], min_h=400
        )

        ops_grp = QGroupBox("العمليات")
        ops_lay = QHBoxLayout(ops_grp)
        self.sup_pay_amt = inp("مبلغ السداد", 140)
        ops_lay.addWidget(QLabel("المبلغ:"))
        ops_lay.addWidget(self.sup_pay_amt)
        ops_lay.addWidget(make_btn("✅  تسديد دفعة",    "#2E7D32", self.pay_supplier))
        ops_lay.addWidget(make_btn("📄  كشف الحساب",    "#1565C0", self.show_supplier_ledger))
        ops_lay.addWidget(make_btn("📋  فواتير الشراء", "#4527A0", self.show_supplier_purchases))
        ops_lay.addStretch()
        ops_lay.addWidget(make_btn("🗑  حذف",           "#C62828", self.del_supplier))

        lay.addWidget(add_grp)
        lay.addWidget(self.sup_table)
        lay.addWidget(ops_grp)

    def refresh_suppliers(self):
        data = rows("SELECT id, name, phone, total_debt FROM suppliers ORDER BY name")
        fill_table(self.sup_table, data, amber_col=3)

    def refresh_supplier_combos(self):
        data = rows("SELECT id, name FROM suppliers ORDER BY name")
        self.purch_sup_combo.clear()
        self.purch_sup_combo.addItem("-- اختر مورد --", userData=None)
        for r in data:
            self.purch_sup_combo.addItem(r[1], userData=r[0])

    def add_supplier(self):
        name  = self.sup_name.text().strip()
        phone = self.sup_phone.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "أدخل اسم المورد"); return
        q("INSERT INTO suppliers(name,phone) VALUES(?,?)", (name, phone))
        self.sup_name.clear(); self.sup_phone.clear()
        self.refresh_suppliers()
        self.refresh_supplier_combos()
        QMessageBox.information(self, "✅", f"تم إضافة المورد: {name}")

    def pay_supplier(self):
        row = self.sup_table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "تنبيه", "اختر مورداً أولاً"); return

        sid   = int(self.sup_table.item(row, 0).text())
        sname = self.sup_table.item(row, 1).text()
        debt  = n(self.sup_table.item(row, 3).text())

        try:
            amount = n(self.sup_pay_amt.text())
            if amount <= 0: raise ValueError()
        except Exception:
            QMessageBox.warning(self, "خطأ", "أدخل مبلغاً صحيحاً"); return

        date = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        q("UPDATE suppliers SET total_debt=total_debt-? WHERE id=?", (amount, sid))
        q("INSERT INTO supplier_ledger(supplier_id,type,details,amount,date) VALUES(?,?,?,?,?)",
          (sid, "سداد دفعة", f"دفع نقدي للمورد — المتبقي: {max(0, debt-amount):.2f}", amount, date))

        self.sup_pay_amt.clear()
        self.refresh_suppliers()
        QMessageBox.information(self, "✅",
            f"تم تسديد {amount:.2f} للمورد {sname}\nالمتبقي: {max(0, debt - amount):.2f}")

    def show_supplier_ledger(self):
        row = self.sup_table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "تنبيه", "اختر مورداً أولاً"); return
        sid   = int(self.sup_table.item(row, 0).text())
        sname = self.sup_table.item(row, 1).text()
        LedgerDialog(sid, sname, "supplier_ledger", self).exec()

    def show_supplier_purchases(self):
        row = self.sup_table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "تنبيه", "اختر مورداً أولاً"); return
        sid   = int(self.sup_table.item(row, 0).text())
        sname = self.sup_table.item(row, 1).text()

        data = rows(
            "SELECT id, payment_type, total, paid_amount, remaining, purchase_date "
            "FROM purchases WHERE supplier_id=? ORDER BY id DESC",
            (sid,)
        )
        total_inv  = sum(n(r[2]) for r in data)
        total_paid = sum(n(r[3]) for r in data)
        total_rem  = sum(n(r[4]) for r in data)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"مشتريات من: {sname}")
        dlg.setLayoutDirection(Qt.RightToLeft)
        dlg.resize(720, 440)
        lay = QVBoxLayout(dlg)

        tbl = make_table(["#", "طريقة الدفع", "الإجمالي", "المدفوع", "المتبقي", "التاريخ"])
        fill_table(tbl, data)
        lay.addWidget(tbl)

        # Double-click to open purchase detail
        def _open_purch(r, c):
            item = tbl.item(r, 0)
            if item:
                PurchaseDetailDialog(int(item.text()), self).exec()
        tbl.cellDoubleClicked.connect(_open_purch)

        lbl = QLabel(
            f"  عدد الفواتير: {len(data)}   |   إجمالي المشتريات: {total_inv:.2f}"
            f"   |   المدفوع: {total_paid:.2f}   |   المتبقي علينا: {total_rem:.2f}\n"
            "  💡 انقر مرتين على أي فاتورة لعرض محتوياتها"
        )
        lbl.setStyleSheet("font-weight:bold;color:#C62828;padding:6px;")
        lay.addWidget(lbl)
        dlg.exec()

    def del_supplier(self):
        row = self.sup_table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "تنبيه", "اختر مورداً أولاً"); return
        sid   = int(self.sup_table.item(row, 0).text())
        sname = self.sup_table.item(row, 1).text()
        debt  = n(self.sup_table.item(row, 3).text())
        if debt > 0:
            QMessageBox.warning(self, "⚠️", f"لا يمكن الحذف — لديكم دين: {debt:.2f}"); return
        reply = QMessageBox.question(self, "تأكيد", f"حذف: {sname}؟",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            q("DELETE FROM suppliers WHERE id=?", (sid,))
            self.refresh_suppliers()
            self.refresh_supplier_combos()

    # ══════════════════════════════════════════════
    #  TAB 6 — التقارير
    # ══════════════════════════════════════════════
    def setup_reports_tab(self, w):
        lay = QVBoxLayout(w)

        btns_grp = QGroupBox("اختر التقرير")
        btns_lay = QHBoxLayout(btns_grp)
        for text, color, cb in [
            ("📅  مبيعات اليوم",   "#1565C0", self.rpt_daily),
            ("📆  مبيعات الشهر",   "#4527A0", self.rpt_monthly),
            ("💰  أرباح شهرية",    "#E65100", self.rpt_profit_monthly),
            ("🧾  كل الفواتير",    "#00695C", self.rpt_all_invoices),
            ("📦  أداء المنتجات",  "#558B2F", self.rpt_products),
            ("👥  ديون العملاء",   "#C62828", self.rpt_customer_debts),
            ("🏭  ديون الموردين",  "#4E342E", self.rpt_supplier_debts),
        ]:
            btns_lay.addWidget(make_btn(text, color, cb, 120))

        self.rpt_title = QLabel("اختر تقريراً من الأعلى ↑")
        self.rpt_title.setFont(QFont("Arial", 12, QFont.Bold))
        self.rpt_title.setAlignment(Qt.AlignCenter)
        self.rpt_title.setStyleSheet("color:#1a237e;padding:8px;")

        self.rpt_table = make_table(["—"], min_h=460)
        self.rpt_table.cellDoubleClicked.connect(self._rpt_invoice_detail)

        self.rpt_summary = QLabel()
        self.rpt_summary.setStyleSheet(
            "font-weight:bold;color:#333;padding:6px;"
            "background:#e8eaf6;border-radius:4px;"
        )

        lay.addWidget(btns_grp)
        lay.addWidget(self.rpt_title)
        lay.addWidget(self.rpt_table)
        lay.addWidget(self.rpt_summary)

    def _set_report(self, title, headers, data, summary=""):
        self.rpt_title.setText(title)
        self.rpt_table.setColumnCount(len(headers))
        self.rpt_table.setHorizontalHeaderLabels(headers)
        fill_table(self.rpt_table, data)
        self.rpt_summary.setText(summary)

    def _rpt_invoice_detail(self, row, col):
        item = self.rpt_table.item(row, 0)
        if not item: return
        cell = item.text()
        if cell.startswith("INV-"):
            res = one("SELECT id FROM sales WHERE invoice_no=?", (cell,))
            if res:
                InvoiceDialog(res[0], cell, self).exec()

    def rpt_daily(self):
        today = datetime.now().strftime("%Y-%m-%d")
        data  = rows(
            "SELECT invoice_no, customer_name, payment_type, total, paid_amount, remaining, profit, sale_date "
            "FROM sales WHERE sale_date LIKE ? ORDER BY id DESC",
            (today + "%",)
        )
        total  = sum(n(r[3]) for r in data)
        paid   = sum(n(r[4]) for r in data)
        rem    = sum(n(r[5]) for r in data)
        profit = sum(n(r[6]) for r in data)
        self._set_report(
            f"📅  مبيعات اليوم — {today}",
            ["الفاتورة", "العميل", "الدفع", "الإجمالي", "المدفوع", "المتبقي", "الربح", "الوقت"],
            data,
            f"عدد الفواتير: {len(data)}   |   الإجمالي: {total:.2f}"
            f"   |   المحصل: {paid:.2f}   |   المتبقي: {rem:.2f}   |   الأرباح: {profit:.2f}"
            f"   ✦  انقر مرتين على الفاتورة لعرض تفاصيلها"
        )

    def rpt_monthly(self):
        month = datetime.now().strftime("%Y-%m")
        data  = rows(
            "SELECT invoice_no, customer_name, payment_type, total, paid_amount, remaining, profit, sale_date "
            "FROM sales WHERE sale_date LIKE ? ORDER BY id DESC",
            (month + "%",)
        )
        total  = sum(n(r[3]) for r in data)
        paid   = sum(n(r[4]) for r in data)
        rem    = sum(n(r[5]) for r in data)
        profit = sum(n(r[6]) for r in data)
        self._set_report(
            f"📆  مبيعات الشهر — {month}",
            ["الفاتورة", "العميل", "الدفع", "الإجمالي", "المدفوع", "المتبقي", "الربح", "التاريخ"],
            data,
            f"عدد الفواتير: {len(data)}   |   الإجمالي: {total:.2f}"
            f"   |   المحصل: {paid:.2f}   |   المتبقي: {rem:.2f}   |   الأرباح: {profit:.2f}"
        )

    def rpt_profit_monthly(self):
        data = rows("""
            SELECT SUBSTR(sale_date, 1, 7),
                   COUNT(*),
                   ROUND(SUM(total),2),
                   ROUND(SUM(paid_amount),2),
                   ROUND(SUM(remaining),2),
                   ROUND(SUM(profit),2)
            FROM sales GROUP BY 1 ORDER BY 1 DESC
        """)
        res    = one("SELECT COUNT(*), SUM(total), SUM(paid_amount), SUM(remaining), SUM(profit) FROM sales")
        total  = n(res[1]) if res else 0
        paid   = n(res[2]) if res else 0
        rem    = n(res[3]) if res else 0
        profit = n(res[4]) if res else 0
        self._set_report(
            "💰  الأرباح — تفصيل شهري",
            ["الشهر", "عدد الفواتير", "الإيراد", "المحصل", "المتبقي", "الربح"],
            data,
            f"الإجمالي الكلي: {total:.2f}   |   المحصل: {paid:.2f}"
            f"   |   المتبقي: {rem:.2f}   |   الأرباح: {profit:.2f}"
        )

    def rpt_all_invoices(self):
        data = rows(
            "SELECT invoice_no, customer_name, payment_type, total, paid_amount, remaining, profit, sale_date "
            "FROM sales ORDER BY id DESC LIMIT 2000"
        )
        total  = sum(n(r[3]) for r in data)
        paid   = sum(n(r[4]) for r in data)
        rem    = sum(n(r[5]) for r in data)
        profit = sum(n(r[6]) for r in data)
        self._set_report(
            "🧾  كل الفواتير",
            ["الفاتورة", "العميل", "الدفع", "الإجمالي", "المدفوع", "المتبقي", "الربح", "التاريخ"],
            data,
            f"إجمالي الفواتير: {len(data)}   |   الإيراد: {total:.2f}"
            f"   |   المحصل: {paid:.2f}   |   المتبقي: {rem:.2f}   |   الأرباح: {profit:.2f}"
            f"   ✦  انقر مرتين على الفاتورة لعرض تفاصيلها"
        )

    def rpt_products(self):
        data = rows("""
            SELECT si.product_name, si.unit,
                   SUM(si.quantity)        AS sold,
                   ROUND(SUM(si.total),2)  AS revenue,
                   ROUND(SUM(si.profit),2) AS profit,
                   ROUND(AVG(si.price),2)  AS avg_price
            FROM sale_items si
            GROUP BY si.product_id, si.product_name
            ORDER BY sold DESC
        """)
        self._set_report(
            "📦  أداء المنتجات — الأكثر مبيعاً",
            ["المنتج", "الوحدة", "الكمية المباعة", "الإيراد", "الربح", "متوسط السعر"],
            data,
            f"إجمالي المنتجات: {len(data)}"
        )

    def rpt_customer_debts(self):
        data = rows("""
            SELECT name, phone, ROUND(total_debt,2)
            FROM customers WHERE total_debt > 0
            ORDER BY total_debt DESC
        """)
        total = sum(n(r[2]) for r in data)
        self._set_report(
            "👥  ديون العملاء",
            ["اسم العميل", "الهاتف", "الدين المتبقي"],
            data,
            f"عدد العملاء المدينين: {len(data)}   |   إجمالي الديون: {total:.2f}"
        )

    def rpt_supplier_debts(self):
        data = rows("""
            SELECT name, phone, ROUND(total_debt,2)
            FROM suppliers WHERE total_debt > 0
            ORDER BY total_debt DESC
        """)
        total = sum(n(r[2]) for r in data)
        self._set_report(
            "🏭  ديون للموردين (علينا)",
            ["اسم المورد", "الهاتف", "المبلغ المتبقي"],
            data,
            f"عدد الموردين الدائنين: {len(data)}   |   إجمالي ما علينا: {total:.2f}"
        )


# ═══════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Arial", 11))
    app.setLayoutDirection(Qt.RightToLeft)
    window = ShopApp()
    window.show()
    sys.exit(app.exec())