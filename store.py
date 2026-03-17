"""
برنامج إدارة المحل — النسخة 5.0
الإصلاحات:
  ✅ إصلاح نظام المرتجع (transaction management)
  ✅ إعادة البيع بالمبلغ
  ✅ إضافة تقرير المرتجعات
  ✅ إصلاح LedgerDialog مع running balance
  ✅ إصلاح transaction conflicts
  ✅ UI حديث ومنيمالست
"""
import sys, sqlite3, shutil, os, re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QTimer, QDate, QRect
from PySide6.QtGui import QColor, QFont, QDoubleValidator, QBrush, QPainter, QPalette

# ══════════════════════════════════════════════════════
#  الثوابت والإعدادات
# ══════════════════════════════════════════════════════
DB_PATH       = "shop.db"
SETTINGS_PATH = "settings.db"
BACKUP_DIR    = "backup"
LOW_STOCK     = 5

UNITS = ["قطعة","كيلو","جرام","لتر","مللي","متر","سنتيمتر",
         "كرتون","علبة","كيس","دزينة","باكيت"]

# ── ألوان الـ UI الحديث ──
COLORS = {
    "bg":        "#0F1117",
    "surface":   "#1A1D27",
    "surface2":  "#22263A",
    "border":    "#2E3248",
    "accent":    "#6C63FF",
    "accent2":   "#FF6584",
    "green":     "#00C896",
    "red":       "#FF4757",
    "orange":    "#FFA502",
    "blue":      "#2979FF",
    "text":      "#E8EAF6",
    "text2":     "#8892A4",
    "yellow":    "#FFD600",
}

STYLESHEET = f"""
QWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: 'Segoe UI', Tahoma, Arial;
    font-size: 10pt;
}}
QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    background: {COLORS['surface']};
}}
QTabBar::tab {{
    background: {COLORS['surface2']};
    color: {COLORS['text2']};
    padding: 10px 18px;
    min-width: 120px;
    border: none;
    font-weight: bold;
    font-size: 10pt;
}}
QTabBar::tab:selected {{
    background: {COLORS['accent']};
    color: white;
    border-radius: 6px 6px 0 0;
}}
QTabBar::tab:hover:!selected {{
    background: {COLORS['border']};
    color: {COLORS['text']};
}}
QTableWidget {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    gridline-color: {COLORS['border']};
    color: {COLORS['text']};
    selection-background-color: {COLORS['accent']};
}}
QTableWidget::item {{
    padding: 6px;
    border-bottom: 1px solid {COLORS['border']};
}}
QTableWidget::item:alternate {{
    background: {COLORS['surface2']};
}}
QHeaderView::section {{
    background: {COLORS['surface2']};
    color: {COLORS['text2']};
    padding: 8px;
    border: none;
    border-bottom: 2px solid {COLORS['accent']};
    font-weight: bold;
    font-size: 9pt;
    text-transform: uppercase;
}}
QLineEdit {{
    background: {COLORS['surface2']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    color: {COLORS['text']};
    font-size: 10pt;
}}
QLineEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}
QLineEdit::placeholder {{
    color: {COLORS['text2']};
}}
QComboBox {{
    background: {COLORS['surface2']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 7px 12px;
    color: {COLORS['text']};
    min-width: 100px;
}}
QComboBox:focus {{
    border: 1px solid {COLORS['accent']};
}}
QComboBox::drop-down {{
    border: none;
    padding-left: 8px;
}}
QComboBox QAbstractItemView {{
    background: {COLORS['surface2']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['accent']};
    color: {COLORS['text']};
}}
QGroupBox {{
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px 8px 8px 8px;
    background: {COLORS['surface']};
    font-weight: bold;
    color: {COLORS['text2']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top right;
    padding: 0 10px;
    color: {COLORS['accent']};
    font-size: 10pt;
}}
QScrollBar:vertical {{
    background: {COLORS['surface']};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS['accent']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {COLORS['surface']};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS['border']};
    border-radius: 4px;
}}
QListWidget {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 8px;
    border-radius: 4px;
}}
QListWidget::item:selected {{
    background: {COLORS['accent']};
    color: white;
}}
QListWidget::item:hover:!selected {{
    background: {COLORS['surface2']};
}}
QTreeWidget {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
}}
QTreeWidget::item {{
    padding: 6px;
    border-radius: 4px;
}}
QTreeWidget::item:selected {{
    background: {COLORS['accent']};
    color: white;
}}
QTreeWidget::item:hover:!selected {{
    background: {COLORS['surface2']};
}}
QCheckBox {{
    color: {COLORS['text']};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 2px solid {COLORS['border']};
    border-radius: 4px;
    background: {COLORS['surface2']};
}}
QCheckBox::indicator:checked {{
    background: {COLORS['accent']};
    border-color: {COLORS['accent']};
}}
QDoubleSpinBox, QSpinBox {{
    background: {COLORS['surface2']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px;
    color: {COLORS['text']};
}}
QDateEdit {{
    background: {COLORS['surface2']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {COLORS['text']};
}}
QCalendarWidget {{
    background: {COLORS['surface']};
    color: {COLORS['text']};
}}
QCalendarWidget QAbstractItemView {{
    background: {COLORS['surface']};
    selection-background-color: {COLORS['accent']};
    color: {COLORS['text']};
}}
QDialog {{
    background: {COLORS['surface']};
}}
QMessageBox {{
    background: {COLORS['surface']};
    color: {COLORS['text']};
}}
QInputDialog {{
    background: {COLORS['surface']};
    color: {COLORS['text']};
}}
QLabel {{
    color: {COLORS['text']};
    background: transparent;
}}
"""

# ══════════════════════════════════════════════════════
#  إعدادات المستخدم
# ══════════════════════════════════════════════════════
def _open_settings():
    s = sqlite3.connect(SETTINGS_PATH)
    s.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)")
    s.commit()
    return s

def get_setting(key, default=""):
    s = _open_settings()
    r = s.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    s.close()
    return r[0] if r else default

def set_setting(key, value):
    s = _open_settings()
    s.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
    s.commit(); s.close()

# ══════════════════════════════════════════════════════
#  قاعدة البيانات — بدون WAL وبدون isolation_level=None
#  لتجنب تعارض التعاملات
# ══════════════════════════════════════════════════════
DB = sqlite3.connect(DB_PATH)
DB.execute("PRAGMA foreign_keys = ON")
DB.execute("PRAGMA journal_mode = DELETE")
C  = DB.cursor()

def q(sql, params=()):
    """تنفيذ استعلام مع commit تلقائي."""
    C.execute(sql, params)
    DB.commit()

def q_many(sqls_params):
    """تنفيذ مجموعة استعلامات في transaction واحدة."""
    try:
        for sql, params in sqls_params:
            C.execute(sql, params)
        DB.commit()
    except Exception as e:
        DB.rollback()
        raise e

def rows(sql, params=()):
    C.execute(sql, params); return C.fetchall()

def one(sql, params=()):
    C.execute(sql, params); return C.fetchone()

# ══════════════════════════════════════════════════════
#  دوال التحويل
# ══════════════════════════════════════════════════════
def D(value) -> Decimal:
    try:
        if value is None or str(value).strip() == "": return Decimal("0")
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")

def money(v) -> str:
    return f"{D(v).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"

def fmt_qty(v, unit="") -> str:
    d = D(v)
    s = str(int(d)) if d == d.to_integral_value() else f"{d:.3f}".rstrip("0")
    return f"{s} {unit}".strip() if unit else s

def is_positive(text) -> bool:
    try: return D(str(text).strip()) > 0
    except: return False

def dbl_validator(dec=2):
    v = QDoubleValidator(0.0, 1e9, dec)
    v.setNotation(QDoubleValidator.StandardNotation)
    return v

# ══════════════════════════════════════════════════════
#  Migration
# ══════════════════════════════════════════════════════
def _fix_ledger(table, id_col):
    try:
        C.execute(f"SELECT type FROM {table} LIMIT 1")
    except sqlite3.OperationalError:
        tmp = f"{table}_bak"
        try:
            C.execute(f"ALTER TABLE {table} RENAME TO {tmp}")
            C.execute(f"CREATE TABLE {table}(id INTEGER PRIMARY KEY AUTOINCREMENT,"
                      f"{id_col} INTEGER, type TEXT, details TEXT, amount REAL, date TEXT)")
            for ot, od in [("transaction_type","transaction_date"),("type","date")]:
                try:
                    C.execute(f"INSERT INTO {table}(id,{id_col},type,details,amount,date) "
                              f"SELECT id,{id_col},{ot},details,amount,{od} FROM {tmp}")
                    break
                except sqlite3.OperationalError:
                    continue
            C.execute(f"DROP TABLE IF EXISTS {tmp}")
        except Exception:
            pass

def migrate_database():
    _fix_ledger("customer_ledger", "customer_id")
    _fix_ledger("supplier_ledger", "supplier_id")
    try:
        C.execute("SELECT invoice_no FROM sales LIMIT 1")
    except sqlite3.OperationalError:
        try: C.execute("ALTER TABLE sales RENAME TO sales_legacy")
        except: pass

    C.executescript("""
        CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit TEXT DEFAULT 'قطعة',
            cost REAL DEFAULT 0,
            price REAL DEFAULT 0,
            quantity REAL DEFAULT 0,
            category_id INTEGER DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS customers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            total_debt REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS customer_ledger(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER, type TEXT,
            details TEXT, amount REAL, date TEXT
        );
        CREATE TABLE IF NOT EXISTS suppliers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            total_debt REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS supplier_ledger(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER, type TEXT,
            details TEXT, amount REAL, date TEXT
        );
        CREATE TABLE IF NOT EXISTS sales(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT,
            customer_id INTEGER DEFAULT NULL,
            customer_name TEXT DEFAULT 'كاش',
            payment_type TEXT DEFAULT 'كاش',
            total REAL DEFAULT 0,
            paid_amount REAL DEFAULT 0,
            remaining REAL DEFAULT 0,
            profit REAL DEFAULT 0,
            sale_date TEXT
        );
        CREATE TABLE IF NOT EXISTS sale_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER, product_id INTEGER,
            product_name TEXT, unit TEXT DEFAULT 'قطعة',
            cost REAL, price REAL, quantity REAL, total REAL, profit REAL
        );
        CREATE TABLE IF NOT EXISTS purchases(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER DEFAULT NULL,
            supplier_name TEXT DEFAULT 'نقدي',
            payment_type TEXT DEFAULT 'نقدي',
            total REAL DEFAULT 0,
            paid_amount REAL DEFAULT 0,
            remaining REAL DEFAULT 0,
            purchase_date TEXT
        );
        CREATE TABLE IF NOT EXISTS purchase_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id INTEGER, product_id INTEGER,
            product_name TEXT, unit TEXT DEFAULT 'قطعة',
            cost REAL, quantity REAL, total REAL
        );
        CREATE TABLE IF NOT EXISTS returns(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            return_no TEXT,
            sale_id INTEGER,
            original_invoice TEXT,
            customer_id INTEGER DEFAULT NULL,
            customer_name TEXT DEFAULT '',
            payment_type TEXT DEFAULT 'كاش',
            total REAL DEFAULT 0,
            return_date TEXT
        );
        CREATE TABLE IF NOT EXISTS return_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            return_id INTEGER, product_id INTEGER,
            product_name TEXT, unit TEXT DEFAULT 'قطعة',
            price REAL DEFAULT 0, quantity REAL DEFAULT 0, total REAL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_products_name  ON products(name);
        CREATE INDEX IF NOT EXISTS idx_sales_date     ON sales(sale_date);
        CREATE INDEX IF NOT EXISTS idx_purchases_date ON purchases(purchase_date);
    """)

    for sql in [
        "ALTER TABLE products       ADD COLUMN unit TEXT DEFAULT 'قطعة'",
        "ALTER TABLE products       ADD COLUMN cost REAL DEFAULT 0",
        "ALTER TABLE products       ADD COLUMN category_id INTEGER DEFAULT NULL",
        "ALTER TABLE customers      ADD COLUMN phone TEXT DEFAULT ''",
        "ALTER TABLE sale_items     ADD COLUMN unit TEXT DEFAULT 'قطعة'",
        "ALTER TABLE purchase_items ADD COLUMN unit TEXT DEFAULT 'قطعة'",
        "ALTER TABLE sales          ADD COLUMN paid_amount REAL DEFAULT 0",
        "ALTER TABLE sales          ADD COLUMN remaining   REAL DEFAULT 0",
        "ALTER TABLE purchases      ADD COLUMN paid_amount REAL DEFAULT 0",
        "ALTER TABLE purchases      ADD COLUMN remaining   REAL DEFAULT 0",
    ]:
        try: C.execute(sql)
        except sqlite3.OperationalError: pass

    try:
        C.execute("""UPDATE sales SET paid_amount=total, remaining=0
                     WHERE (paid_amount IS NULL OR paid_amount=0) AND payment_type='كاش'""")
        C.execute("""UPDATE sales SET paid_amount=0, remaining=total
                     WHERE (paid_amount IS NULL OR paid_amount=0) AND payment_type='آجل'""")
        C.execute("""UPDATE purchases SET paid_amount=total, remaining=0
                     WHERE (paid_amount IS NULL OR paid_amount=0) AND payment_type='نقدي'""")
        C.execute("""UPDATE purchases SET paid_amount=0, remaining=total
                     WHERE (paid_amount IS NULL OR paid_amount=0) AND payment_type='آجل'""")
    except Exception:
        pass
    DB.commit()

migrate_database()
LOW_STOCK = int(get_setting("low_stock_threshold", "5"))

# ══════════════════════════════════════════════════════
#  النسخ الاحتياطي
# ══════════════════════════════════════════════════════
def make_backup(manual=False) -> bool:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if not os.path.exists(DB_PATH): return False
    dst = os.path.join(BACKUP_DIR,
        f"backup_manual_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.db"
        if manual else
        f"backup_{datetime.now().strftime('%Y_%m_%d')}.db")
    if manual or not os.path.exists(dst):
        shutil.copy2(DB_PATH, dst); return True
    return False

# ══════════════════════════════════════════════════════
#  مساعدات واجهة المستخدم
# ══════════════════════════════════════════════════════
def inp(ph, max_w=None):
    w = QLineEdit(); w.setPlaceholderText(ph)
    if max_w: w.setMaximumWidth(max_w)
    return w

def make_btn(text, color, cb=None, min_w=90):
    b = QPushButton(text)
    b.setStyleSheet(
        f"QPushButton {{"
        f"background:{color};color:white;font-weight:600;"
        f"padding:8px 14px;border-radius:6px;font-size:10pt;"
        f"border:none;letter-spacing:0.3px;"
        f"}}"
        f"QPushButton:hover {{"
        f"opacity:0.85;"
        f"}}"
    )
    b.setMinimumWidth(min_w)
    b.setCursor(Qt.PointingHandCursor)
    if cb: b.clicked.connect(cb)
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
    t.setShowGrid(False)
    t.setFrameShape(QFrame.NoFrame)
    if min_h: t.setMinimumHeight(min_h)
    return t

def fill_table(t, data, col_colors=None):
    t.setRowCount(len(data))
    for i, row in enumerate(data):
        t.setRowHeight(i, 38)
        for j, val in enumerate(row):
            text = "" if val is None else str(val)
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            if col_colors:
                for c_col, c_func, c_bg, c_fg in col_colors:
                    if j == c_col:
                        try:
                            if c_func(val):
                                item.setBackground(QColor(c_bg))
                                item.setForeground(QColor(c_fg))
                        except: pass
            t.setItem(i, j, item)
    t.resizeColumnsToContents()

def make_stat_card(title, value, color, icon=""):
    """بطاقة إحصاء صغيرة."""
    frame = QFrame()
    frame.setStyleSheet(f"""
        QFrame {{
            background: {COLORS['surface']};
            border: 1px solid {color}40;
            border-radius: 10px;
            padding: 4px;
        }}
    """)
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(16, 10, 16, 10)
    lay.setSpacing(2)

    title_lbl = QLabel(f"{icon}  {title}")
    title_lbl.setStyleSheet(f"color:{COLORS['text2']};font-size:11px;font-weight:500;")
    lay.addWidget(title_lbl)

    val_lbl = QLabel(str(value))
    val_lbl.setStyleSheet(f"color:{color};font-size:22px;font-weight:700;")
    lay.addWidget(val_lbl)

    return frame, val_lbl

# ══════════════════════════════════════════════════════
#  تقويم ملون
# ══════════════════════════════════════════════════════
class SalesCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sale_days = set()
        self.setGridVisible(True)
        self.setMinimumSize(310, 230)

    def set_sale_days(self, days: set):
        self._sale_days = days
        self.updateCells()

    def paintCell(self, painter: QPainter, rect: QRect, date: QDate):
        super().paintCell(painter, rect, date)
        if date.toString("yyyy-MM-dd") in self._sale_days:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(COLORS['green'])))
            r = 4
            cx = rect.center().x()
            cy = rect.bottom() - r - 2
            painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
            painter.restore()

# ══════════════════════════════════════════════════════
#  نافذة الدفع الجزئي
# ══════════════════════════════════════════════════════
class PartialPaymentDialog(QDialog):
    def __init__(self, total, mode="sale", parent=None):
        super().__init__(parent)
        self.total = total
        self.result_paid = None
        self.result_remaining = None
        title = "دفع جزئي — فاتورة بيع" if mode == "sale" else "دفع جزئي — فاتورة شراء"
        self.setWindowTitle(title)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedSize(400, 200)
        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        total_lbl = QLabel(f"إجمالي الفاتورة:  {total:.2f}")
        total_lbl.setStyleSheet(f"font-size:15px;font-weight:700;color:{COLORS['accent']};")
        lay.addWidget(total_lbl)

        form = QFormLayout()
        form.setSpacing(10)
        self.inp_paid = QLineEdit()
        self.inp_paid.setPlaceholderText("0.00  (فارغ = آجل كامل)")
        self.inp_paid.setValidator(dbl_validator(2))
        self.inp_paid.textChanged.connect(self._update_remaining)
        form.addRow("المدفوع الآن:", self.inp_paid)

        self.lbl_remaining = QLabel(f"{total:.2f}")
        self.lbl_remaining.setStyleSheet(f"font-weight:700;color:{COLORS['red']};font-size:14px;")
        form.addRow("المتبقي (آجل):", self.lbl_remaining)
        lay.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(make_btn("✓  تأكيد", COLORS['green'], self._confirm))
        btns.addWidget(make_btn("✕  إلغاء", COLORS['red'], self.reject))
        lay.addLayout(btns)

    def _update_remaining(self, text):
        paid = D(text)
        remaining = max(Decimal("0"), D(self.total) - paid)
        self.lbl_remaining.setText(f"{remaining:.2f}")
        clr = COLORS['red'] if remaining > 0 else COLORS['green']
        self.lbl_remaining.setStyleSheet(f"font-weight:700;font-size:14px;color:{clr};")

    def _confirm(self):
        paid = 0.0 if not self.inp_paid.text().strip() else float(D(self.inp_paid.text()))
        if paid < 0 or paid > self.total + 1e-6:
            QMessageBox.warning(self, "خطأ", f"المبلغ يجب أن يكون بين 0 و {self.total:.2f}")
            return
        self.result_paid = min(paid, self.total)
        self.result_remaining = max(0.0, self.total - self.result_paid)
        self.accept()

# ══════════════════════════════════════════════════════
#  كشف الحساب مع الرصيد التراكمي (مُصلح)
# ══════════════════════════════════════════════════════
TYPE_AR = {"sale":"مشتريات آجل","payment":"سداد","purchase":"مشتريات (مورد)","return":"مرتجع"}

class LedgerDialog(QDialog):
    def __init__(self, entity_id, entity_name, ledger_table, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"كشف حساب: {entity_name}")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(780, 540)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        title = QLabel(f"كشف حساب تفصيلي:  {entity_name}")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color:{COLORS['accent']};padding:8px;")
        lay.addWidget(title)

        hint = QLabel("💡 انقر مرتين على أي سجل لعرض الفاتورة")
        hint.setStyleSheet(f"color:{COLORS['text2']};font-size:11px;padding:2px;")
        lay.addWidget(hint)

        # جدول مع عمود الرصيد التراكمي
        tbl = make_table(["التاريخ", "النوع", "التفاصيل", "المبلغ", "الرصيد التراكمي"])
        lay.addWidget(tbl)

        id_col = "customer_id" if "customer" in ledger_table else "supplier_id"
        data = rows(f"SELECT date,type,details,amount FROM {ledger_table} "
                    f"WHERE {id_col}=? ORDER BY id ASC", (entity_id,))

        balance = Decimal("0")
        total_debt = Decimal("0")
        total_paid = Decimal("0")
        total_return = Decimal("0")

        tbl.setRowCount(len(data))
        for i, (date, typ, details, amount) in enumerate(data):
            amt = D(amount)
            is_payment = (typ == "payment" or "سداد" in str(typ))
            is_return = (typ == "return" or "مرتجع" in str(typ))

            if is_payment or is_return:
                balance -= amt
                if is_payment: total_paid += amt
                else: total_return += amt
            else:
                balance += amt
                total_debt += amt

            type_ar = TYPE_AR.get(typ, typ)
            vals = [date or "", type_ar, details or "", money(amt), money(balance)]
            for j, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignCenter)
                if is_payment or is_return:
                    item.setForeground(QColor(COLORS['green']))
                else:
                    item.setForeground(QColor(COLORS['red']))
                if j == 4:
                    item.setFont(QFont("Segoe UI", 10, QFont.Bold))
                    if balance > 0:
                        item.setBackground(QColor(COLORS['orange'] + "30"))
                    else:
                        item.setBackground(QColor(COLORS['green'] + "20"))
                tbl.setItem(i, j, item)

        tbl.resizeColumnsToContents()
        tbl.cellDoubleClicked.connect(lambda r, c, t=tbl: self._try_open_inv(t, r))

        # ملخص
        summary = QFrame()
        summary.setStyleSheet(f"background:{COLORS['surface2']};border-radius:8px;padding:2px;")
        sl = QHBoxLayout(summary)
        for lbl, val, clr in [
            ("إجمالي المديونية", money(total_debt), COLORS['red']),
            ("إجمالي السدادات",  money(total_paid), COLORS['green']),
            ("المرتجعات",        money(total_return), COLORS['orange']),
            ("الرصيد المتبقي",   money(balance), COLORS['accent']),
        ]:
            col = QVBoxLayout()
            col.addWidget(QLabel(lbl) if True else None)
            l1 = QLabel(lbl); l1.setStyleSheet(f"color:{COLORS['text2']};font-size:10px;")
            l2 = QLabel(val); l2.setStyleSheet(f"color:{clr};font-size:15px;font-weight:700;")
            l1.setAlignment(Qt.AlignCenter); l2.setAlignment(Qt.AlignCenter)
            col.addWidget(l1); col.addWidget(l2)
            sl.addLayout(col)
            if lbl != "الرصيد المتبقي":
                sep = QFrame(); sep.setFrameShape(QFrame.VLine)
                sep.setStyleSheet(f"color:{COLORS['border']};")
                sl.addWidget(sep)
        lay.addWidget(summary)

        close_btn = make_btn("✕  إغلاق", COLORS['surface2'], self.close, 100)
        close_btn.setStyleSheet(close_btn.styleSheet() + f"color:{COLORS['text2']};border:1px solid {COLORS['border']};")
        btn_lay = QHBoxLayout()
        btn_lay.addStretch(); btn_lay.addWidget(close_btn)
        lay.addLayout(btn_lay)

    def _try_open_inv(self, tbl, row):
        for col in range(tbl.columnCount()):
            cell = tbl.item(row, col)
            if not cell: continue
            m = re.search(r"INV-\d+", cell.text())
            if m:
                res = one("SELECT id FROM sales WHERE invoice_no=?", (m.group(),))
                if res:
                    InvoiceDialog(res[0], m.group(), self).exec()
                    return

# ══════════════════════════════════════════════════════
#  نافذة تفاصيل الفاتورة
# ══════════════════════════════════════════════════════
class InvoiceDialog(QDialog):
    def __init__(self, sale_id, invoice_no, parent=None):
        super().__init__(parent)
        self.sale_id = sale_id
        self.invoice_no = invoice_no
        self.setWindowTitle(f"فاتورة: {invoice_no}")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(820, 520)
        lay = QVBoxLayout(self)

        sale = one(
            "SELECT customer_name,payment_type,total,paid_amount,remaining,profit,sale_date "
            "FROM sales WHERE id=?", (sale_id,))
        if not sale:
            lay.addWidget(QLabel("فاتورة غير موجودة")); return

        cname, ptype, total, paid, remaining, profit, sdate = sale

        hdr = QLabel(f"🧾  {invoice_no}")
        hdr.setFont(QFont("Segoe UI", 13, QFont.Bold))
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setStyleSheet(f"color:{COLORS['accent']};padding:6px;")
        lay.addWidget(hdr)

        info_frame = QFrame()
        info_frame.setStyleSheet(f"background:{COLORS['surface2']};border-radius:8px;padding:2px;")
        info_lay = QHBoxLayout(info_frame)
        for label, val, color in [
            ("العميل", cname, COLORS['text']),
            ("نوع الدفع", ptype, COLORS['accent']),
            ("التاريخ", sdate, COLORS['text2']),
        ]:
            lbl = QLabel(f"<span style='color:{COLORS['text2']};font-size:10px;'>{label}</span><br>"
                         f"<span style='color:{color};font-weight:600;'>{val}</span>")
            lbl.setAlignment(Qt.AlignCenter)
            info_lay.addWidget(lbl)
        lay.addWidget(info_frame)

        tbl = make_table(["المنتج","الوحدة","الكمية","سعر الشراء","سعر البيع","الإجمالي","الربح"])
        data = rows("SELECT product_name,unit,quantity,cost,price,total,profit "
                    "FROM sale_items WHERE sale_id=?", (sale_id,))
        display = [(r[0],r[1],fmt_qty(r[2]),money(r[3]),money(r[4]),money(r[5]),money(r[6])) for r in data]
        fill_table(tbl, display)
        lay.addWidget(tbl)

        # ملخص الدفع
        pay_frame = QFrame()
        pay_frame.setStyleSheet(f"background:{COLORS['surface2']};border-radius:8px;padding:4px;")
        pay_lay = QHBoxLayout(pay_frame)
        for label, val, color in [
            ("الإجمالي", money(total), COLORS['accent']),
            ("المدفوع",  money(paid),  COLORS['green']),
            ("المتبقي",  money(remaining), COLORS['red'] if D(remaining) > 0 else COLORS['green']),
            ("الربح",    money(profit), COLORS['yellow']),
        ]:
            col = QVBoxLayout()
            l1 = QLabel(label); l1.setStyleSheet(f"color:{COLORS['text2']};font-size:10px;")
            l2 = QLabel(val);   l2.setStyleSheet(f"color:{color};font-size:16px;font-weight:700;")
            l1.setAlignment(Qt.AlignCenter); l2.setAlignment(Qt.AlignCenter)
            col.addWidget(l1); col.addWidget(l2)
            pay_lay.addLayout(col)
        lay.addWidget(pay_frame)

        btn_row = QHBoxLayout()
        btn_row.addWidget(make_btn("🔄  إنشاء مرتجع", COLORS['red'], self._open_return, 140))
        btn_row.addStretch()
        btn_row.addWidget(make_btn("✕  إغلاق", COLORS['surface2'], self.close, 90))
        lay.addLayout(btn_row)

    def _open_return(self):
        dlg = ReturnDialog(self.sale_id, self.invoice_no, self)
        if dlg.exec() == QDialog.Accepted:
            # ابحث عن ShopApp في topLevelWidgets
            shop = None
            for w in QApplication.topLevelWidgets():
                if isinstance(w, ShopApp):
                    shop = w; break
            if isinstance(shop, ShopApp):
                shop._refresh_all_products()
                shop.customers_tab.refresh_table()
                shop._refresh_stats()
            self.close()

# ══════════════════════════════════════════════════════
#  نافذة تفاصيل الشراء
# ══════════════════════════════════════════════════════
class PurchaseDetailDialog(QDialog):
    def __init__(self, purchase_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"فاتورة شراء: #{purchase_id}")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(720, 460)
        lay = QVBoxLayout(self)

        purch = one("SELECT supplier_name,payment_type,total,paid_amount,remaining,purchase_date "
                    "FROM purchases WHERE id=?", (purchase_id,))
        if not purch:
            lay.addWidget(QLabel("فاتورة غير موجودة")); return

        sname, ptype, total, paid, remaining, pdate = purch

        hdr = QLabel(f"📦  فاتورة شراء  #{purchase_id}")
        hdr.setFont(QFont("Segoe UI", 13, QFont.Bold))
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setStyleSheet(f"color:{COLORS['red']};padding:6px;")
        lay.addWidget(hdr)

        info_frame = QFrame()
        info_frame.setStyleSheet(f"background:{COLORS['surface2']};border-radius:8px;padding:2px;")
        info_lay = QHBoxLayout(info_frame)
        for label, val, color in [("المورد",sname,COLORS['text']),("نوع الدفع",ptype,COLORS['accent']),("التاريخ",pdate,COLORS['text2'])]:
            lbl = QLabel(f"<span style='color:{COLORS['text2']};font-size:10px;'>{label}</span><br>"
                         f"<span style='color:{color};font-weight:600;'>{val}</span>")
            lbl.setAlignment(Qt.AlignCenter)
            info_lay.addWidget(lbl)
        lay.addWidget(info_frame)

        tbl = make_table(["المنتج","الوحدة","الكمية","سعر الشراء","الإجمالي"])
        data = rows("SELECT product_name,unit,quantity,cost,total FROM purchase_items WHERE purchase_id=?", (purchase_id,))
        display = [(r[0],r[1],fmt_qty(r[2]),money(r[3]),money(r[4])) for r in data]
        fill_table(tbl, display)
        lay.addWidget(tbl)

        pay_frame = QFrame()
        pay_frame.setStyleSheet(f"background:{COLORS['surface2']};border-radius:8px;padding:4px;")
        pay_lay = QHBoxLayout(pay_frame)
        for label, val, color in [
            ("الإجمالي", money(total),     COLORS['red']),
            ("المدفوع",  money(paid),      COLORS['green']),
            ("المتبقي",  money(remaining), COLORS['red'] if D(remaining) > 0 else COLORS['green']),
        ]:
            col = QVBoxLayout()
            l1 = QLabel(label); l1.setStyleSheet(f"color:{COLORS['text2']};font-size:10px;")
            l2 = QLabel(val);   l2.setStyleSheet(f"color:{color};font-size:16px;font-weight:700;")
            l1.setAlignment(Qt.AlignCenter); l2.setAlignment(Qt.AlignCenter)
            col.addWidget(l1); col.addWidget(l2)
            pay_lay.addLayout(col)
        lay.addWidget(pay_frame)

# ══════════════════════════════════════════════════════
#  نافذة المرتجع (مُصلحة — q_many بدل begin/commit اليدوي)
# ══════════════════════════════════════════════════════
class ReturnDialog(QDialog):
    def __init__(self, sale_id, invoice_no, parent=None):
        super().__init__(parent)
        self.sale_id = sale_id
        self.invoice_no = invoice_no
        self.setWindowTitle(f"مرتجع: {invoice_no}")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(820, 540)

        sale_info = one("SELECT customer_id,customer_name,payment_type FROM sales WHERE id=?", (sale_id,))
        self.cust_id   = sale_info[0] if sale_info else None
        self.cust_name = sale_info[1] if sale_info else "كاش"
        self.pay_type  = sale_info[2] if sale_info else "كاش"

        self.items = rows("SELECT product_id,product_name,unit,price,quantity "
                          "FROM sale_items WHERE sale_id=?", (sale_id,))

        # الكميات المرتجعة سابقاً
        self.prev_ret = {}
        for it in self.items:
            pid = it[0]
            r = one("SELECT COALESCE(SUM(ri.quantity),0) FROM return_items ri "
                    "JOIN returns ret ON ri.return_id=ret.id "
                    "WHERE ret.sale_id=? AND ri.product_id=?", (sale_id, pid))
            self.prev_ret[pid] = D(r[0]) if r else Decimal("0")

        lay = QVBoxLayout(self)

        hdr = QLabel(f"🔄  مرتجع: {invoice_no}  |  {self.cust_name}")
        hdr.setFont(QFont("Segoe UI", 12, QFont.Bold))
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setStyleSheet(f"color:{COLORS['red']};padding:6px;")
        lay.addWidget(hdr)

        headers = ["✓","المنتج","الوحدة","مباع","مرتجع سابق","متاح للإرجاع","الكمية"]
        self.tbl = QTableWidget()
        self.tbl.setColumnCount(len(headers))
        self.tbl.setHorizontalHeaderLabels(headers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setShowGrid(False)
        self.tbl.setRowCount(len(self.items))
        lay.addWidget(self.tbl)

        self.cbs = []; self.spins = []
        for i, it in enumerate(self.items):
            pid, pname, unit, price, qty = it
            prev    = self.prev_ret.get(pid, Decimal("0"))
            max_ret = D(qty) - prev
            can_ret = max_ret > 0

            cb = QCheckBox(); cb.setEnabled(can_ret)
            cb.stateChanged.connect(self._update_total)
            self.cbs.append(cb)
            self.tbl.setCellWidget(i, 0, cb)

            for j, v in enumerate([pname, unit, fmt_qty(qty), fmt_qty(prev), fmt_qty(max_ret)], 1):
                ci = QTableWidgetItem(v); ci.setTextAlignment(Qt.AlignCenter)
                if not can_ret: ci.setForeground(QColor(COLORS['text2']))
                self.tbl.setItem(i, j, ci)

            spin = QDoubleSpinBox()
            spin.setMinimum(0.001)
            spin.setMaximum(float(max_ret) if can_ret else 0.001)
            spin.setValue(float(max_ret) if can_ret else 0)
            spin.setDecimals(3)
            spin.setEnabled(can_ret)
            spin.valueChanged.connect(self._update_total)
            self.spins.append(spin)
            self.tbl.setCellWidget(i, 6, spin)
            self.tbl.setRowHeight(i, 42)

        self.total_lbl = QLabel("إجمالي المرتجع:  0.00")
        self.total_lbl.setStyleSheet(f"font-weight:700;color:{COLORS['red']};font-size:14px;padding:6px;")
        lay.addWidget(self.total_lbl)

        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(make_btn("✓  تأكيد المرتجع", COLORS['red'], self._confirm, 150))
        btns.addWidget(make_btn("✕  إلغاء", COLORS['surface2'], self.reject, 90))
        lay.addLayout(btns)

    def _update_total(self):
        total = Decimal("0")
        for i, (cb, spin) in enumerate(zip(self.cbs, self.spins)):
            if cb.isChecked():
                total += D(self.items[i][3]) * D(str(spin.value()))
        self.total_lbl.setText(f"إجمالي المرتجع:  {money(total)}")

    def _confirm(self):
        selected = []
        for i, (cb, spin) in enumerate(zip(self.cbs, self.spins)):
            if cb.isChecked():
                it = self.items[i]; qty = D(str(spin.value()))
                if qty > 0:
                    selected.append({"pid": it[0], "name": it[1], "unit": it[2],
                                     "price": D(it[3]), "qty": qty, "total": D(it[3]) * qty})
        if not selected:
            QMessageBox.warning(self, "تنبيه", "لم تختر أي منتج للإرجاع"); return

        total = sum(i["total"] for i in selected)
        date  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ✅ استخدام q_many بدلاً من begin/commit اليدوي
        try:
            # الخطوة 1: إدراج سجل المرتجع
            C.execute("INSERT INTO returns(sale_id,original_invoice,customer_id,"
                      "customer_name,payment_type,total,return_date) VALUES(?,?,?,?,?,?,?)",
                      (self.sale_id, self.invoice_no, self.cust_id,
                       self.cust_name, self.pay_type, float(total), date))
            ret_id = C.lastrowid
            ret_no = f"RET-{ret_id:05d}"
            C.execute("UPDATE returns SET return_no=? WHERE id=?", (ret_no, ret_id))

            # الخطوة 2: إدراج بنود المرتجع وتحديث المخزون
            for it in selected:
                C.execute("INSERT INTO return_items(return_id,product_id,product_name,"
                          "unit,price,quantity,total) VALUES(?,?,?,?,?,?,?)",
                          (ret_id, it["pid"], it["name"], it["unit"],
                           float(it["price"]), float(it["qty"]), float(it["total"])))
                C.execute("UPDATE products SET quantity=quantity+? WHERE id=?",
                          (float(it["qty"]), it["pid"]))

            # الخطوة 3: تحديث دين العميل وفاتورة البيع لو بيع آجل أو جزئي
            if self.cust_id and self.pay_type in ("آجل", "جزئي"):
                # احسب المتبقي الفعلي في الفاتورة الأصلية
                sale_row = one("SELECT remaining FROM sales WHERE id=?", (self.sale_id,))
                cur_remaining = D(sale_row[0]) if sale_row else Decimal("0")
                # المرتجع لا يتجاوز المتبقي (الجزء الآجل فعلاً)
                debt_reduction = min(total, cur_remaining)

                if debt_reduction > 0:
                    # تقليل الدين من حساب العميل
                    C.execute("UPDATE customers SET total_debt=MAX(0,total_debt-?) WHERE id=?",
                              (float(debt_reduction), self.cust_id))
                    # تحديث الفاتورة الأصلية — تقليل المتبقي وزيادة المدفوع
                    C.execute("""UPDATE sales
                                 SET remaining  = MAX(0, remaining  - ?),
                                     paid_amount= MIN(total, paid_amount + ?)
                                 WHERE id=?""",
                              (float(debt_reduction), float(debt_reduction), self.sale_id))
                    # إضافة حركة في كشف الحساب
                    C.execute("INSERT INTO customer_ledger(customer_id,type,details,amount,date) "
                              "VALUES(?,?,?,?,?)",
                              (self.cust_id, "return",
                               f"مرتجع {ret_no} من {self.invoice_no}",
                               float(debt_reduction), date))

            DB.commit()

            QMessageBox.information(self, "✅ تم المرتجع",
                f"رقم المرتجع: {ret_no}\n"
                f"الإجمالي: {money(total)}"
                + (f"\nتم خصم {money(total)} من حساب {self.cust_name}"
                   if self.cust_id and self.pay_type == "آجل" else ""))
            self.accept()

        except Exception as e:
            DB.rollback()
            QMessageBox.critical(self, "خطأ", f"فشل المرتجع:\n{e}")

# ══════════════════════════════════════════════════════
#  نافذة تعديل الكمية
# ══════════════════════════════════════════════════════
class EditQtyDialog(QDialog):
    def __init__(self, name, cur_qty, max_qty, unit, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"تعديل كمية: {name}")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedSize(320, 150)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.addWidget(QLabel(f"المتاح في المخزون: {fmt_qty(max_qty, unit)}"))
        row = QHBoxLayout()
        row.addWidget(QLabel("الكمية الجديدة:"))
        self.qty_edit = QLineEdit(fmt_qty(cur_qty))
        self.qty_edit.setValidator(dbl_validator(3))
        self.qty_edit.selectAll()
        row.addWidget(self.qty_edit)
        lay.addLayout(row)
        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(make_btn("✓", COLORS['green'], self.accept, 60))
        btns.addWidget(make_btn("✕", COLORS['red'], self.reject, 60))
        lay.addLayout(btns)

    def get_qty(self) -> Decimal:
        return D(self.qty_edit.text())

# ══════════════════════════════════════════════════════
#  نافذة الإعدادات
# ══════════════════════════════════════════════════════
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("الإعدادات")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedSize(380, 160)
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        grp = QGroupBox("إعدادات المخزون")
        gl = QFormLayout(grp)
        self.spin = QSpinBox()
        self.spin.setRange(1, 10000)
        self.spin.setValue(int(get_setting("low_stock_threshold","5")))
        self.spin.setSuffix("  وحدة")
        gl.addRow("حد المخزون المنخفض:", self.spin)
        lay.addWidget(grp)
        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(make_btn("💾  حفظ", COLORS['accent'], self._save))
        btns.addWidget(make_btn("إلغاء", COLORS['surface2'], self.reject, 80))
        lay.addLayout(btns)

    def _save(self):
        set_setting("low_stock_threshold", str(self.spin.value()))
        self.accept()

# ══════════════════════════════════════════════════════
#  تاب العملاء / الموردين
# ══════════════════════════════════════════════════════
class PartyTab(QWidget):
    def __init__(self, app, party_type):
        super().__init__()
        self.app = app
        self.is_cust = (party_type == "customer")
        self.tbl_name   = f"{party_type}s"
        self.ledger_tbl = f"{party_type}_ledger"
        self.id_col     = f"{party_type}_id"
        self.lbl        = "العميل"     if self.is_cust else "المورد"
        self.debt_lbl   = "ديون عليه" if self.is_cust else "ديون علينا"
        self.setLayoutDirection(Qt.RightToLeft)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        # إضافة
        add_grp = QGroupBox(f"إضافة {self.lbl} جديد")
        gl = QHBoxLayout(add_grp)
        self.name_edit  = inp(f"اسم {self.lbl}")
        self.phone_edit = inp("رقم الهاتف", 160)
        gl.addWidget(self.name_edit); gl.addWidget(self.phone_edit)
        gl.addWidget(make_btn("➕  إضافة", COLORS['green'], self.add_party))
        lay.addWidget(add_grp)

        self.search_edit = inp("🔍  بحث بالاسم أو الهاتف...")
        self.search_edit.textChanged.connect(lambda _: self.refresh_table())
        lay.addWidget(self.search_edit)

        self.table = make_table(["ID", f"اسم {self.lbl}", "الهاتف", self.debt_lbl], min_h=370)
        lay.addWidget(self.table)

        ops = QGroupBox("العمليات")
        ol = QHBoxLayout(ops)
        self.pay_edit = inp("المبلغ", 150)
        self.pay_edit.setValidator(dbl_validator(2))
        ol.addWidget(QLabel("المبلغ:")); ol.addWidget(self.pay_edit)
        ol.addWidget(make_btn("✓  تسديد", COLORS['green'], self.pay))
        ol.addWidget(make_btn("📄  كشف الحساب", COLORS['blue'], self.show_ledger))
        if self.is_cust:
            ol.addWidget(make_btn("🧾  فواتيره", COLORS['accent'], self.show_invoices))
        else:
            ol.addWidget(make_btn("📋  فواتير الشراء", COLORS['accent'], self.show_purchases))
        ol.addStretch()
        ol.addWidget(make_btn("🗑  حذف", COLORS['red'], self.delete_party))
        lay.addWidget(ops)
        self.refresh_table()

    def _sel(self, col):
        r = self.table.currentRow()
        return None if r == -1 else (self.table.item(r, col).text() if self.table.item(r, col) else None)

    def sel_id(self):   v = self._sel(0); return int(v) if v else None
    def sel_name(self): return self._sel(1) or ""
    def sel_debt(self): return D(self._sel(3) or "0")

    def refresh_table(self):
        text = self.search_edit.text()
        data = rows(f"SELECT id,name,phone,total_debt FROM {self.tbl_name} "
                    f"WHERE name LIKE ? OR phone LIKE ? ORDER BY name",
                    (f"%{text}%", f"%{text}%"))
        display = [(str(r[0]), r[1], r[2], money(r[3])) for r in data]
        fill_table(self.table, display,
                   col_colors=[(3, lambda v: D(v) > 0, COLORS['orange']+"30", COLORS['orange'])])

    def add_party(self):
        name  = self.name_edit.text().strip()
        phone = self.phone_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", f"أدخل اسم {self.lbl}"); return
        try:
            q(f"INSERT INTO {self.tbl_name}(name,phone) VALUES(?,?)", (name, phone))
            self.name_edit.clear(); self.phone_edit.clear()
            self.refresh_table()
            (self.app.refresh_customer_combos if self.is_cust else self.app.refresh_supplier_combos)()
            QMessageBox.information(self, "✅", f"تم إضافة {self.lbl}: {name}")
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "خطأ", f"{self.lbl} موجود مسبقاً")

    def pay(self):
        pid = self.sel_id()
        if not pid:
            QMessageBox.warning(self, "تنبيه", f"اختر {self.lbl} أولاً"); return
        name = self.sel_name(); debt = self.sel_debt()
        if not is_positive(self.pay_edit.text()):
            QMessageBox.warning(self, "خطأ", "أدخل مبلغاً صحيحاً"); return
        amount = D(self.pay_edit.text())
        if self.is_cust and amount > debt:
            if QMessageBox.question(
                self, "⚠️ تنبيه",
                f"المبلغ ({money(amount)}) أكبر من الدين ({money(debt)}). متابعة؟",
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.No: return
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            q(f"UPDATE {self.tbl_name} SET total_debt=total_debt-? WHERE id=?", (float(amount), pid))
            q(f"INSERT INTO {self.ledger_tbl}({self.id_col},type,details,amount,date) VALUES(?,?,?,?,?)",
              (pid, "payment", "سداد نقدي", float(amount), date))
            self.pay_edit.clear(); self.refresh_table()
            QMessageBox.information(self, "✅",
                f"تم تسديد {money(amount)} من حساب {name}\nالمتبقي: {money(debt - amount)}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))

    def show_ledger(self):
        pid = self.sel_id()
        if not pid:
            QMessageBox.warning(self, "تنبيه", f"اختر {self.lbl} أولاً"); return
        LedgerDialog(pid, self.sel_name(), self.ledger_tbl, self).exec()

    def show_invoices(self):
        pid = self.sel_id()
        if not pid:
            QMessageBox.warning(self, "تنبيه", "اختر عميلاً أولاً"); return
        name = self.sel_name()
        data = rows("SELECT invoice_no,payment_type,total,paid_amount,remaining,profit,sale_date "
                    "FROM sales WHERE customer_id=? ORDER BY id DESC", (pid,))
        display = [(r[0],r[1],money(r[2]),money(r[3]),money(r[4]),money(r[5]),r[6]) for r in data]
        total = sum(D(r[2]) for r in data); paid = sum(D(r[3]) for r in data)
        rem   = sum(D(r[4]) for r in data); profit = sum(D(r[5]) for r in data)

        dlg = QDialog(self); dlg.setWindowTitle(f"فواتير: {name}")
        dlg.setLayoutDirection(Qt.RightToLeft); dlg.resize(720, 480)
        lay = QVBoxLayout(dlg)
        tbl = make_table(["الفاتورة","الدفع","الإجمالي","المدفوع","المتبقي","الربح","التاريخ"])
        fill_table(tbl, display)
        def open_inv(r, c, t=tbl):
            cell = t.item(r, 0)
            if cell and cell.text().startswith("INV-"):
                res = one("SELECT id FROM sales WHERE invoice_no=?", (cell.text(),))
                if res: InvoiceDialog(res[0], cell.text(), self).exec()
        tbl.cellDoubleClicked.connect(open_inv)
        lay.addWidget(tbl)
        lbl = QLabel(f"  الفواتير: {len(data)}  |  الإجمالي: {money(total)}  |  "
                     f"المدفوع: {money(paid)}  |  المتبقي: {money(rem)}  |  ربح: {money(profit)}")
        lbl.setStyleSheet(f"color:{COLORS['accent']};font-weight:600;padding:6px;")
        lay.addWidget(lbl)
        dlg.exec()

    def show_purchases(self):
        pid = self.sel_id()
        if not pid:
            QMessageBox.warning(self, "تنبيه", "اختر مورداً أولاً"); return
        name = self.sel_name()
        data = rows("SELECT id,payment_type,total,paid_amount,remaining,purchase_date "
                    "FROM purchases WHERE supplier_id=? ORDER BY id DESC", (pid,))
        display = [(str(r[0]),r[1],money(r[2]),money(r[3]),money(r[4]),r[5]) for r in data]
        total = sum(D(r[2]) for r in data); paid = sum(D(r[3]) for r in data)
        rem   = sum(D(r[4]) for r in data)

        dlg = QDialog(self); dlg.setWindowTitle(f"مشتريات من: {name}")
        dlg.setLayoutDirection(Qt.RightToLeft); dlg.resize(700, 460)
        lay = QVBoxLayout(dlg)
        tbl = make_table(["#","طريقة الدفع","الإجمالي","المدفوع","المتبقي","التاريخ"])
        fill_table(tbl, display)
        def open_purch(r, c, t=tbl):
            cell = t.item(r, 0)
            if cell: PurchaseDetailDialog(int(cell.text()), self).exec()
        tbl.cellDoubleClicked.connect(open_purch)
        lay.addWidget(tbl)
        lbl = QLabel(f"  الفواتير: {len(data)}  |  الإجمالي: {money(total)}  |  "
                     f"المدفوع: {money(paid)}  |  المتبقي علينا: {money(rem)}")
        lbl.setStyleSheet(f"color:{COLORS['red']};font-weight:600;padding:6px;")
        lay.addWidget(lbl)
        dlg.exec()

    def delete_party(self):
        pid = self.sel_id()
        if not pid:
            QMessageBox.warning(self, "تنبيه", f"اختر {self.lbl} أولاً"); return
        name = self.sel_name(); debt = self.sel_debt()
        if debt > 0:
            QMessageBox.warning(self, "⚠️", f"لا يمكن الحذف — دين متبقي: {money(debt)}"); return
        if QMessageBox.question(self, "تأكيد", f"حذف: {name}؟",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            q(f"DELETE FROM {self.tbl_name} WHERE id=?", (pid,))
            self.refresh_table()
            (self.app.refresh_customer_combos if self.is_cust else self.app.refresh_supplier_combos)()

# ══════════════════════════════════════════════════════
#  التطبيق الرئيسي
# ══════════════════════════════════════════════════════
class ShopApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("سرجة العلا — نظام إدارة المحل")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(1340, 860)

        self.cart          = []
        self.purchase_cart = []
        self._pos_selected = None
        self._cur_inv_cat  = None

        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(10, 8, 10, 8)

        # ── Header ──
        hdr_row = QHBoxLayout()
        hdr = QLabel("🏪  سرجة العلا")
        hdr.setFont(QFont("Segoe UI", 18, QFont.Bold))
        hdr.setStyleSheet(f"color:white;padding:4px 0;")
        hdr_row.addWidget(hdr, 1)

        for text, color, cb in [
            ("⚙️  الإعدادات",    COLORS['surface2'], self.open_settings),
            ("💾  نسخ احتياطي", COLORS['surface2'], self.manual_backup),
        ]:
            btn = make_btn(text, color, cb, 130)
            btn.setStyleSheet(btn.styleSheet() + f"border:1px solid {COLORS['border']};")
            hdr_row.addWidget(btn)
        root.addLayout(hdr_row)

        # ── شريط الإحصاءات ──
        self.stats_row = QHBoxLayout()
        self.stat_inv_lbl  = QLabel("0")
        self.stat_tot_lbl  = QLabel("0.00")
        self.stat_prf_lbl  = QLabel("0.00")
        self.stat_low_lbl  = QLabel("0")

        for title, val_lbl, color, icon in [
            ("فواتير اليوم",   self.stat_inv_lbl, COLORS['accent'],  "🧾"),
            ("مبيعات اليوم",   self.stat_tot_lbl, COLORS['green'],   "💰"),
            ("أرباح اليوم",    self.stat_prf_lbl, COLORS['yellow'],  "📈"),
            ("مخزون منخفض",   self.stat_low_lbl, COLORS['red'],     "⚠️"),
        ]:
            frame, val_lbl_ref = make_stat_card(title, "...", color, icon)
            # نحتفظ بمرجع الـ label الصحيح
            if title == "فواتير اليوم":   self.stat_inv_lbl = val_lbl_ref
            elif title == "مبيعات اليوم":  self.stat_tot_lbl = val_lbl_ref
            elif title == "أرباح اليوم":   self.stat_prf_lbl = val_lbl_ref
            else:                           self.stat_low_lbl = val_lbl_ref
            self.stats_row.addWidget(frame)
        root.addLayout(self.stats_row)

        # ── Tabs ──
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        self.setup_pos_tab()
        self.setup_inventory_tab()
        self.setup_purchases_tab()

        self.customers_tab = PartyTab(self, "customer")
        self.tabs.addTab(self.customers_tab, "👥  العملاء")
        self.suppliers_tab = PartyTab(self, "supplier")
        self.tabs.addTab(self.suppliers_tab, "🏭  الموردون")

        self.setup_reports_tab()

        self.refresh_purchases_products()
        self.refresh_purchases_history()
        self.refresh_customer_combos()
        self.refresh_supplier_combos()
        self.refresh_inv_cat_tree()
        self.refresh_inventory()
        self._rebuild_pos_tree()
        self._refresh_stats()

        timer = QTimer(self)
        timer.timeout.connect(self._refresh_stats)
        timer.start(60_000)

    # ─── إحصاءات ──────────────────────────────────────
    def _refresh_stats(self):
        today = datetime.now().strftime("%Y-%m-%d")
        res = one("SELECT COUNT(*),COALESCE(SUM(total),0),COALESCE(SUM(profit),0) "
                  "FROM sales WHERE sale_date LIKE ?", (today+"%",))
        low = one("SELECT COUNT(*) FROM products WHERE quantity<?", (LOW_STOCK,))
        cnt, tot, prf = (res[0], D(res[1]), D(res[2])) if res else (0, Decimal("0"), Decimal("0"))
        lc = low[0] if low else 0
        self.stat_inv_lbl.setText(str(cnt))
        self.stat_tot_lbl.setText(money(tot))
        self.stat_prf_lbl.setText(money(prf))
        self.stat_low_lbl.setText(str(lc))
        if lc > 0:
            self.stat_low_lbl.setStyleSheet(f"color:{COLORS['red']};font-size:22px;font-weight:700;")

    # ─── misc ──────────────────────────────────────────
    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            global LOW_STOCK
            LOW_STOCK = int(get_setting("low_stock_threshold", "5"))
            self._refresh_all_products(); self._refresh_stats()

    def manual_backup(self):
        if make_backup(manual=True):
            QMessageBox.information(self, "✅", "تم إنشاء النسخة الاحتياطية")
        else:
            QMessageBox.warning(self, "⚠️", "فشل إنشاء النسخة الاحتياطية")

    def closeEvent(self, event):
        DB.close(); event.accept()

    def refresh_customer_combos(self):
        data = rows("SELECT id,name FROM customers ORDER BY name")
        self.pos_cust_combo.clear()
        self.pos_cust_combo.addItem("-- اختر عميل --", userData=None)
        for r in data: self.pos_cust_combo.addItem(r[1], userData=r[0])

    def refresh_supplier_combos(self):
        data = rows("SELECT id,name FROM suppliers ORDER BY name")
        self.purch_sup_combo.clear()
        self.purch_sup_combo.addItem("-- اختر مورد --", userData=None)
        for r in data: self.purch_sup_combo.addItem(r[1], userData=r[0])

    def _refresh_all_products(self):
        self.refresh_inventory(); self._rebuild_pos_tree()
        self.refresh_purchases_products(); self._refresh_stats()

    def _try_open_invoice(self, table, row):
        for col in range(table.columnCount()):
            cell = table.item(row, col)
            if not cell: continue
            m = re.search(r"INV-\d+", cell.text())
            if m:
                res = one("SELECT id FROM sales WHERE invoice_no=?", (m.group(),))
                if res: InvoiceDialog(res[0], m.group(), self).exec(); return

    # ══════════════════════════════════════════════════
    #  TAB 1 — نقطة البيع
    # ══════════════════════════════════════════════════
    def setup_pos_tab(self):
        w = QWidget(); w.setLayoutDirection(Qt.RightToLeft)
        lay = QHBoxLayout(w); lay.setSpacing(10)

        # ── يسار ──
        left = QVBoxLayout(); left.setSpacing(8)

        search_row = QHBoxLayout()
        self.pos_search = inp("🔍  بحث عن منتج...")
        self._pos_search_timer = QTimer(self); self._pos_search_timer.setSingleShot(True)
        self._pos_search_timer.timeout.connect(lambda: self._filter_pos_tree(self.pos_search.text()))
        self.pos_search.textChanged.connect(lambda _: self._pos_search_timer.start(300))
        search_row.addWidget(self.pos_search)
        left.addLayout(search_row)

        self.pos_tree = QTreeWidget()
        self.pos_tree.setHeaderHidden(True)
        self.pos_tree.setAlternatingRowColors(True)
        self.pos_tree.setMinimumHeight(360)
        self.pos_tree.itemClicked.connect(self._on_pos_tree_clicked)
        self.pos_tree.itemDoubleClicked.connect(self._on_pos_tree_dbl)
        left.addWidget(self.pos_tree)

        self.pos_sel_lbl = QLabel("لم يتم اختيار منتج")
        self.pos_sel_lbl.setStyleSheet(f"color:{COLORS['text2']};font-size:11px;"
                                       f"background:{COLORS['surface2']};padding:6px;border-radius:4px;")
        left.addWidget(self.pos_sel_lbl)

        add_row = QHBoxLayout(); add_row.setSpacing(6)
        self.pos_qty = inp("الكمية", 110); self.pos_qty.setText("1")
        self.pos_qty.setValidator(dbl_validator(3))
        # ✅ استعادة البيع بالمبلغ
        self.pos_amt = inp("أو بمبلغ (جنيه)", 140)
        self.pos_amt.setValidator(dbl_validator(2))
        add_row.addWidget(QLabel("كمية:")); add_row.addWidget(self.pos_qty)
        add_row.addWidget(QLabel("  مبلغ:")); add_row.addWidget(self.pos_amt)
        add_row.addWidget(make_btn("➕  إضافة", COLORS['blue'], self.add_to_cart))
        add_row.addStretch()
        left.addLayout(add_row)

        # ── يمين ──
        right = QVBoxLayout(); right.setSpacing(8)

        cart_hdr = QLabel("سلة البيع")
        cart_hdr.setFont(QFont("Segoe UI", 12, QFont.Bold))
        cart_hdr.setAlignment(Qt.AlignCenter)
        cart_hdr.setStyleSheet(f"background:{COLORS['surface2']};color:{COLORS['accent']};"
                               f"padding:8px;border-radius:6px;")
        right.addWidget(cart_hdr)

        self.cart_table = make_table(["المنتج","الوحدة","الكمية","السعر","الإجمالي","✕"])
        self.cart_table.setMinimumWidth(460); self.cart_table.setMinimumHeight(320)
        self.cart_table.cellClicked.connect(self._cart_cell_clicked)
        self.cart_table.cellDoubleClicked.connect(self._cart_edit_qty)
        right.addWidget(self.cart_table)

        hint = QLabel("  💡 انقر مرتين على صف لتعديل الكمية  |  ✕ لحذف الصنف")
        hint.setStyleSheet(f"color:{COLORS['text2']};font-size:10px;")
        right.addWidget(hint)

        # ملخص الإجماليات
        totals_frame = QFrame()
        totals_frame.setStyleSheet(f"background:{COLORS['surface2']};border-radius:8px;padding:2px;")
        totals_lay = QHBoxLayout(totals_frame)
        self.lbl_items  = QLabel("0 صنف")
        self.lbl_total  = QLabel("0.00")
        self.lbl_profit = QLabel("0.00")
        self.lbl_items.setStyleSheet(f"color:{COLORS['text2']};font-size:12px;font-weight:600;")
        self.lbl_total.setStyleSheet(f"color:{COLORS['accent']};font-size:20px;font-weight:700;")
        self.lbl_profit.setStyleSheet(f"color:{COLORS['green']};font-size:18px;font-weight:700;")
        for label, val_lbl in [("الأصناف", self.lbl_items),
                                ("الإجمالي", self.lbl_total),
                                ("الربح", self.lbl_profit)]:
            col = QVBoxLayout()
            l = QLabel(label); l.setStyleSheet(f"color:{COLORS['text2']};font-size:10px;")
            l.setAlignment(Qt.AlignCenter); val_lbl.setAlignment(Qt.AlignCenter)
            col.addWidget(l); col.addWidget(val_lbl)
            totals_lay.addLayout(col)
        right.addWidget(totals_frame)

        pay_grp = QGroupBox("طريقة الدفع")
        pay_lay = QGridLayout(pay_grp)
        self.pos_cust_combo = QComboBox(); self.pos_cust_combo.setMinimumWidth(220)
        pay_lay.addWidget(QLabel("العميل (للآجل):"), 0, 0)
        pay_lay.addWidget(self.pos_cust_combo, 0, 1, 1, 4)
        pay_lay.addWidget(make_btn("💵  كاش",    COLORS['green'],  self.sell_cash,    110), 1, 0)
        pay_lay.addWidget(make_btn("📋  آجل",    COLORS['red'],    self.sell_credit,  110), 1, 1)
        pay_lay.addWidget(make_btn("💳  جزئي",   COLORS['orange'], self.sell_partial, 110), 1, 2)
        pay_lay.addWidget(make_btn("🗑  إفراغ",  COLORS['surface2'], self.clear_cart, 90),  1, 3)
        right.addWidget(pay_grp)

        lay.addLayout(left, 52); lay.addLayout(right, 48)
        self.tabs.addTab(w, "🛒  نقطة البيع")

    # ── شجرة الفئات ────────────────────────────────────
    def _rebuild_pos_tree(self, search=""):
        self.pos_tree.clear()
        cats     = rows("SELECT id,name FROM categories ORDER BY name")
        all_prod = rows("SELECT id,name,unit,price,quantity,category_id FROM products ORDER BY name")
        by_cat   = {}
        for p in all_prod:
            by_cat.setdefault(p[5], []).append(p)

        for cat in cats:
            cat_item = QTreeWidgetItem([f"📁  {cat[1]}"])
            cat_item.setFont(0, QFont("Segoe UI", 10, QFont.Bold))
            cat_item.setForeground(0, QColor(COLORS['accent']))
            cat_item.setData(0, Qt.UserRole, {"type":"category","cid":cat[0]})
            for p in by_cat.get(cat[0], []):
                cat_item.addChild(self._make_pos_prod_item(p))
            self.pos_tree.addTopLevelItem(cat_item)
            cat_item.setExpanded(True)

        uncat = by_cat.get(None, [])
        if uncat:
            uc = QTreeWidgetItem(["📦  بدون فئة"])
            uc.setFont(0, QFont("Segoe UI", 10, QFont.Bold))
            uc.setForeground(0, QColor(COLORS['text2']))
            uc.setData(0, Qt.UserRole, {"type":"uncat"})
            for p in uncat:
                uc.addChild(self._make_pos_prod_item(p))
            self.pos_tree.addTopLevelItem(uc)
            uc.setExpanded(True)

        if search: self._filter_pos_tree(search)

    def _make_pos_prod_item(self, p):
        pid, name, unit, price, qty, _ = p
        warn = "  ⚠️" if D(qty) < LOW_STOCK else ""
        text = f"  {name}    {money(price)} ج    📦 {fmt_qty(qty)}{warn}"
        item = QTreeWidgetItem([text])
        item.setData(0, Qt.UserRole, {"type":"product","pid":pid,"name":name,
                                      "unit":unit,"price":D(price),"stock":D(qty)})
        if D(qty) < LOW_STOCK:
            item.setForeground(0, QColor(COLORS['red']))
        return item

    def _filter_pos_tree(self, text: str):
        text = text.lower().strip()
        for i in range(self.pos_tree.topLevelItemCount()):
            cat = self.pos_tree.topLevelItem(i)
            has_match = False
            for j in range(cat.childCount()):
                prod = cat.child(j)
                d    = prod.data(0, Qt.UserRole)
                match = (not text) or (text in (d.get("name","") if d else "").lower())
                prod.setHidden(not match)
                if match: has_match = True
            cat.setHidden(bool(text) and not has_match)
            if has_match and text: cat.setExpanded(True)

    def _on_pos_tree_clicked(self, item, col):
        d = item.data(0, Qt.UserRole)
        if d and d.get("type") == "product":
            self._pos_selected = d
            self.pos_sel_lbl.setText(
                f"✓  {d['name']}   —   {money(d['price'])} ج   —   مخزون: {fmt_qty(d['stock'], d['unit'])}")
            self.pos_sel_lbl.setStyleSheet(
                f"color:{COLORS['green']};font-size:11px;font-weight:600;"
                f"background:{COLORS['surface2']};padding:6px;border-radius:4px;")

    def _on_pos_tree_dbl(self, item, col):
        d = item.data(0, Qt.UserRole)
        if d and d.get("type") == "product":
            self._pos_selected = d
            self._add_to_cart(Decimal("1"))

    # ── سلة البيع ──────────────────────────────────────
    def _add_to_cart(self, qty=None):
        if not self._pos_selected:
            QMessageBox.warning(self, "تنبيه", "اختر منتجاً من القائمة أولاً"); return

        pid   = self._pos_selected["pid"]
        name  = self._pos_selected["name"]
        unit  = self._pos_selected["unit"]
        price = self._pos_selected["price"]

        res = one("SELECT quantity,cost FROM products WHERE id=?", (pid,))
        if not res:
            QMessageBox.warning(self, "خطأ", f"المنتج [{name}] غير موجود!"); return
        stock = D(res[0]); cost = D(res[1])

        if qty is None:
            # ✅ البيع بالمبلغ (مستعاد)
            amt_val = self.pos_amt.text().strip()
            if amt_val:
                try:
                    val = D(amt_val)
                    if val <= 0: raise ValueError()
                    if price <= 0:
                        QMessageBox.warning(self, "خطأ", "سعر البيع صفر — لا يمكن الحساب بالمبلغ"); return
                    qty = (val / price).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                except (ValueError, InvalidOperation):
                    QMessageBox.warning(self, "خطأ", "أدخل مبلغاً صحيحاً"); return
            else:
                if not is_positive(self.pos_qty.text()):
                    QMessageBox.warning(self, "خطأ", "أدخل كمية صحيحة (رقم موجب)"); return
                qty = D(self.pos_qty.text())

        if qty > stock:
            QMessageBox.warning(self, "خطأ",
                f"المخزون غير كافٍ!\nالمتاح: {fmt_qty(stock, unit)}\n"
                f"المطلوب: {fmt_qty(qty, unit)}"); return

        for item in self.cart:
            if item["pid"] == pid:
                new_qty = item["qty"] + qty
                if new_qty > stock:
                    QMessageBox.warning(self, "خطأ",
                        f"المخزون غير كافٍ!\nالمتاح: {fmt_qty(stock,unit)}\n"
                        f"في السلة: {fmt_qty(item['qty'],unit)}"); return
                item["qty"] = new_qty; item["total"] = price * new_qty
                item["profit"] = (price - item["cost"]) * new_qty
                self.pos_amt.clear(); self.refresh_cart(); return

        self.cart.append({"pid":pid,"name":name,"unit":unit,"cost":cost,
                           "price":price,"qty":qty,"total":price*qty,
                           "profit":(price-cost)*qty})
        self.pos_amt.clear()
        self.refresh_cart()

    def add_to_cart(self): self._add_to_cart()

    def refresh_cart(self):
        self.cart_table.setRowCount(len(self.cart))
        for i, item in enumerate(self.cart):
            self.cart_table.setRowHeight(i, 38)
            for j, v in enumerate([item["name"],item["unit"],fmt_qty(item["qty"]),
                                    money(item["price"]),money(item["total"]),"✕"]):
                cell = QTableWidgetItem(v); cell.setTextAlignment(Qt.AlignCenter)
                if j == 5: cell.setForeground(QColor(COLORS['red']))
                self.cart_table.setItem(i, j, cell)
        total  = sum(i["total"]  for i in self.cart)
        profit = sum(i["profit"] for i in self.cart)
        self.lbl_total.setText(money(total))
        self.lbl_profit.setText(money(profit))
        self.lbl_items.setText(f"{len(self.cart)} صنف")
        self.cart_table.resizeColumnsToContents()

    def _cart_cell_clicked(self, row, col):
        if col == 5 and row < len(self.cart):
            del self.cart[row]; self.refresh_cart()

    def _cart_edit_qty(self, row, col):
        if col == 5 or row >= len(self.cart): return
        item  = self.cart[row]
        res   = one("SELECT quantity FROM products WHERE id=?", (item["pid"],))
        stock = D(res[0]) if res else item["qty"]
        dlg = EditQtyDialog(item["name"], item["qty"], stock, item["unit"], self)
        if dlg.exec() == QDialog.Accepted:
            nq = dlg.get_qty()
            if nq <= 0:
                QMessageBox.warning(self, "خطأ", "الكمية يجب أن تكون موجبة"); return
            if nq > stock:
                QMessageBox.warning(self, "خطأ",
                    f"المخزون غير كافٍ!\nالمتاح: {fmt_qty(stock, item['unit'])}"); return
            item["qty"] = nq; item["total"] = item["price"] * nq
            item["profit"] = (item["price"] - item["cost"]) * nq
            self.refresh_cart()

    def clear_cart(self):
        if not self.cart: return
        if QMessageBox.question(self, "تأكيد", "تفريغ السلة؟",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.cart.clear(); self.refresh_cart()

    def sell_cash(self):    self._process_sale(mode="cash")
    def sell_credit(self):  self._process_sale(mode="credit")
    def sell_partial(self): self._process_sale(mode="partial")

    def _process_sale(self, mode):
        if not self.cart:
            QMessageBox.warning(self, "تنبيه", "السلة فارغة!"); return

        cust_id   = self.pos_cust_combo.currentData()
        cust_name = self.pos_cust_combo.currentText()

        if mode in ("credit", "partial") and not cust_id:
            QMessageBox.warning(self, "خطأ", "اختر عميلاً للبيع الآجل أو الجزئي"); return

        total  = sum(i["total"]  for i in self.cart)
        profit = sum(i["profit"] for i in self.cart)

        # التحقق من المخزون
        for item in self.cart:
            res = one("SELECT quantity FROM products WHERE id=?", (item["pid"],))
            if not res:
                QMessageBox.warning(self, "خطأ", f"المنتج [{item['name']}] غير موجود!"); return
            if item["qty"] > D(res[0]):
                QMessageBox.warning(self, "خطأ",
                    f"مخزون غير كافٍ: {item['name']}\n"
                    f"المتاح: {fmt_qty(D(res[0]),item['unit'])}\n"
                    f"المطلوب: {fmt_qty(item['qty'],item['unit'])}"); return

        if mode == "cash":
            paid_amount = float(total); remaining = 0.0; ptype = "كاش"
        elif mode == "credit":
            paid_amount = 0.0; remaining = float(total); ptype = "آجل"
        else:
            dlg = PartialPaymentDialog(float(total), mode="sale", parent=self)
            if dlg.exec() != QDialog.Accepted: return
            paid_amount = dlg.result_paid; remaining = dlg.result_remaining; ptype = "جزئي"

        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            C.execute(
                "INSERT INTO sales(customer_id,customer_name,payment_type,"
                "total,paid_amount,remaining,profit,sale_date) VALUES(?,?,?,?,?,?,?,?)",
                (cust_id if mode != "cash" else None,
                 cust_name if mode != "cash" else "كاش",
                 ptype, float(total), paid_amount, remaining, float(profit), date))
            sale_id    = C.lastrowid
            invoice_no = f"INV-{sale_id:05d}"
            C.execute("UPDATE sales SET invoice_no=? WHERE id=?", (invoice_no, sale_id))

            for item in self.cart:
                C.execute(
                    "INSERT INTO sale_items(sale_id,product_id,product_name,unit,"
                    "cost,price,quantity,total,profit) VALUES(?,?,?,?,?,?,?,?,?)",
                    (sale_id, item["pid"], item["name"], item["unit"],
                     float(item["cost"]), float(item["price"]), float(item["qty"]),
                     float(item["total"]), float(item["profit"])))
                C.execute("UPDATE products SET quantity=quantity-? WHERE id=?",
                          (float(item["qty"]), item["pid"]))

            if mode in ("credit", "partial") and remaining > 0:
                C.execute("UPDATE customers SET total_debt=total_debt+? WHERE id=?",
                          (remaining, cust_id))
                details = (f"فاتورة {invoice_no} — إجمالي: {money(total)}"
                           + (f" — كاش: {money(paid_amount)}" if mode == "partial" else ""))
                C.execute("INSERT INTO customer_ledger(customer_id,type,details,amount,date) VALUES(?,?,?,?,?)",
                          (cust_id, "sale", details, remaining, date))

            DB.commit()

            msg = (f"رقم الفاتورة : {invoice_no}\n"
                   f"الإجمالي     : {money(total)}\n"
                   f"الربح        : {money(profit)}")
            if mode == "partial":
                msg += f"\n\nالمدفوع كاش  : {money(paid_amount)}\nالمتبقي آجل  : {money(remaining)}"
            elif mode == "credit":
                msg += f"\n\nأُضيف للحساب  : {cust_name}"
            QMessageBox.information(self, "✅ تم البيع", msg)

            self.cart.clear(); self.refresh_cart()
            self._pos_selected = None
            self.pos_sel_lbl.setText("لم يتم اختيار منتج")
            self.pos_sel_lbl.setStyleSheet(
                f"color:{COLORS['text2']};font-size:11px;"
                f"background:{COLORS['surface2']};padding:6px;border-radius:4px;")
            self._refresh_all_products()
            self.customers_tab.refresh_table()
            self.refresh_customer_combos()

        except Exception as e:
            DB.rollback()
            QMessageBox.critical(self, "خطأ", f"فشلت عملية البيع:\n{e}")

    # ══════════════════════════════════════════════════
    #  TAB 2 — المخزون
    # ══════════════════════════════════════════════════
    def setup_inventory_tab(self):
        w = QWidget(); w.setLayoutDirection(Qt.RightToLeft)
        main_lay = QHBoxLayout(w); main_lay.setSpacing(10)

        # لوحة الفئات
        cat_panel = QWidget(); cat_panel.setMaximumWidth(200)
        cp_lay = QVBoxLayout(cat_panel); cp_lay.setContentsMargins(0,0,0,0); cp_lay.setSpacing(6)

        cat_title = QLabel("الفئات"); cat_title.setFont(QFont("Segoe UI",11,QFont.Bold))
        cat_title.setStyleSheet(f"color:{COLORS['accent']};")
        cp_lay.addWidget(cat_title)

        self.inv_cat_list = QListWidget()
        self.inv_cat_list.itemClicked.connect(self._on_inv_cat_clicked)
        cp_lay.addWidget(self.inv_cat_list)

        self.cat_name_edit = inp("فئة جديدة")
        cp_lay.addWidget(self.cat_name_edit)

        cat_btns = QHBoxLayout()
        cat_btns.addWidget(make_btn("➕", COLORS['green'], self._add_category, 50))
        cat_btns.addWidget(make_btn("✏️", COLORS['blue'],  self._edit_category, 50))
        cat_btns.addWidget(make_btn("🗑", COLORS['red'],   self._del_category,  50))
        cp_lay.addLayout(cat_btns)
        main_lay.addWidget(cat_panel)

        # لوحة المنتجات
        right_panel = QWidget()
        lay = QVBoxLayout(right_panel); lay.setContentsMargins(0,0,0,0); lay.setSpacing(8)

        add_grp = QGroupBox("إضافة / تعديل منتج")
        add_lay = QHBoxLayout(add_grp); add_lay.setSpacing(6)
        self.inv_name  = inp("اسم المنتج")
        self.inv_unit  = QComboBox(); self.inv_unit.addItems(UNITS)
        self.inv_unit.setEditable(True); self.inv_unit.setMinimumWidth(80)
        self.inv_cat_combo = QComboBox(); self.inv_cat_combo.setMinimumWidth(100)
        self.inv_cost  = inp("سعر الشراء", 90); self.inv_cost.setValidator(dbl_validator(2))
        self.inv_price = inp("سعر البيع",  90); self.inv_price.setValidator(dbl_validator(2))
        self.inv_qty   = inp("الكمية",     80); self.inv_qty.setValidator(dbl_validator(3))
        for wg in [self.inv_name,
                   QLabel("الوحدة:"), self.inv_unit,
                   QLabel("فئة:"), self.inv_cat_combo,
                   QLabel("شراء:"), self.inv_cost,
                   QLabel("بيع:"), self.inv_price,
                   QLabel("كمية:"), self.inv_qty,
                   make_btn("➕", COLORS['green'], self.add_product, 45),
                   make_btn("✏️", COLORS['blue'],  self.edit_product, 45),
                   make_btn("🗑", COLORS['red'],   self.del_product,  45)]:
            add_lay.addWidget(wg)

        self.inv_search = inp("🔍  بحث عن منتج...")
        self._inv_search_timer = QTimer(self); self._inv_search_timer.setSingleShot(True)
        self._inv_search_timer.timeout.connect(lambda: self.refresh_inventory(self.inv_search.text()))
        self.inv_search.textChanged.connect(lambda _: self._inv_search_timer.start(300))

        self.inv_table = make_table(
            ["ID","المنتج","الوحدة","الفئة","سعر الشراء","سعر البيع","المخزون","هامش %"], min_h=430)
        self.inv_table.clicked.connect(self._fill_inv_form)

        lay.addWidget(add_grp); lay.addWidget(self.inv_search); lay.addWidget(self.inv_table)
        main_lay.addWidget(right_panel, 1)
        self.tabs.addTab(w, "📦  المخزون")
        self._load_cat_combo()

    def _load_cat_combo(self):
        cats = rows("SELECT id,name FROM categories ORDER BY name")
        self.inv_cat_combo.clear()
        self.inv_cat_combo.addItem("-- بدون فئة --", userData=None)
        for r in cats: self.inv_cat_combo.addItem(r[1], userData=r[0])

    def refresh_inv_cat_tree(self):
        self.inv_cat_list.clear()
        all_item = QListWidgetItem("🗂  الكل")
        all_item.setData(Qt.UserRole, None)
        all_item.setFont(QFont("Segoe UI",10,QFont.Bold))
        self.inv_cat_list.addItem(all_item)
        for cat in rows("SELECT id,name FROM categories ORDER BY name"):
            item = QListWidgetItem(f"📁  {cat[1]}")
            item.setData(Qt.UserRole, cat[0])
            self.inv_cat_list.addItem(item)
        uncat = QListWidgetItem("📦  بدون فئة")
        uncat.setData(Qt.UserRole, -1)
        self.inv_cat_list.addItem(uncat)
        self.inv_cat_list.setCurrentRow(0)

    def _on_inv_cat_clicked(self, item):
        self._cur_inv_cat = item.data(Qt.UserRole)
        self.refresh_inventory()

    def refresh_inventory(self, text=""):
        if isinstance(text, bool): text = ""
        text = text if isinstance(text, str) else (self.inv_search.text() if hasattr(self,"inv_search") else "")
        cat = self._cur_inv_cat

        if cat is None:
            sql    = ("SELECT p.id,p.name,p.unit,COALESCE(c.name,'—'),p.cost,p.price,p.quantity "
                      "FROM products p LEFT JOIN categories c ON p.category_id=c.id "
                      "WHERE p.name LIKE ? ORDER BY p.name")
            params = (f"%{text}%",)
        elif cat == -1:
            sql    = ("SELECT p.id,p.name,p.unit,'—',p.cost,p.price,p.quantity "
                      "FROM products p WHERE p.name LIKE ? AND p.category_id IS NULL ORDER BY p.name")
            params = (f"%{text}%",)
        else:
            sql    = ("SELECT p.id,p.name,p.unit,COALESCE(c.name,'—'),p.cost,p.price,p.quantity "
                      "FROM products p LEFT JOIN categories c ON p.category_id=c.id "
                      "WHERE p.name LIKE ? AND p.category_id=? ORDER BY p.name")
            params = (f"%{text}%", cat)

        raw = rows(sql, params)
        display = []
        for r in raw:
            cost, price = D(r[4]), D(r[5])
            margin = ((price-cost)/price*100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP) if price > 0 else Decimal("0")
            display.append((str(r[0]),r[1],r[2],r[3],money(cost),money(price),fmt_qty(r[6]),f"{margin}%"))
        fill_table(self.inv_table, display,
                   col_colors=[(6, lambda v: D(v) < LOW_STOCK, COLORS['red']+"30", COLORS['red'])])

    def _fill_inv_form(self):
        r = self.inv_table.currentRow()
        if r == -1: return
        self.inv_name.setText(self.inv_table.item(r,1).text())
        unit_val = self.inv_table.item(r,2).text()
        idx = self.inv_unit.findText(unit_val)
        self.inv_unit.setCurrentIndex(idx) if idx >= 0 else self.inv_unit.setCurrentText(unit_val)
        cat_name = self.inv_table.item(r,3).text()
        cidx = self.inv_cat_combo.findText(cat_name)
        self.inv_cat_combo.setCurrentIndex(cidx if cidx >= 0 else 0)
        self.inv_cost.setText(self.inv_table.item(r,4).text())
        self.inv_price.setText(self.inv_table.item(r,5).text())
        self.inv_qty.setText(self.inv_table.item(r,6).text())

    def _add_category(self):
        name = self.cat_name_edit.text().strip()
        if not name: return
        try:
            q("INSERT INTO categories(name) VALUES(?)", (name,))
            self.cat_name_edit.clear(); self._refresh_cat_trees()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "خطأ", "الفئة موجودة مسبقاً")

    def _edit_category(self):
        item = self.inv_cat_list.currentItem()
        if not item or item.data(Qt.UserRole) in (None, -1):
            QMessageBox.warning(self, "تنبيه", "اختر فئة للتعديل"); return
        cid = item.data(Qt.UserRole)
        name, ok = QInputDialog.getText(self, "تعديل الفئة", "الاسم الجديد:",
                                        text=item.text().replace("📁  ",""))
        if ok and name.strip():
            try:
                q("UPDATE categories SET name=? WHERE id=?", (name.strip(), cid))
                self._refresh_cat_trees()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "خطأ", "الاسم موجود مسبقاً")

    def _del_category(self):
        item = self.inv_cat_list.currentItem()
        if not item or item.data(Qt.UserRole) in (None, -1):
            QMessageBox.warning(self, "تنبيه", "اختر فئة للحذف"); return
        cid  = item.data(Qt.UserRole)
        name = item.text().replace("📁  ","")
        if QMessageBox.question(self, "تأكيد", f"حذف الفئة: {name}؟\n(المنتجات ستصبح بدون فئة)",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            q("DELETE FROM categories WHERE id=?", (cid,))
            self._refresh_cat_trees()

    def _refresh_cat_trees(self):
        self.refresh_inv_cat_tree(); self._load_cat_combo()
        self._rebuild_pos_tree(); self.refresh_inventory()

    def add_product(self):
        name = self.inv_name.text().strip()
        if not name:
            QMessageBox.warning(self, "خطأ", "أدخل اسم المنتج"); return
        unit   = self.inv_unit.currentText().strip() or "قطعة"
        cat_id = self.inv_cat_combo.currentData()
        cost   = D(self.inv_cost.text()  or "0")
        price  = D(self.inv_price.text() or "0")
        qty    = D(self.inv_qty.text()   or "0")
        try:
            q("INSERT INTO products(name,unit,category_id,cost,price,quantity) VALUES(?,?,?,?,?,?)",
              (name, unit, cat_id, float(cost), float(price), float(qty)))
            for f in (self.inv_name, self.inv_cost, self.inv_price, self.inv_qty): f.clear()
            self._refresh_all_products()
            QMessageBox.information(self, "✅", f"تم إضافة: {name}")
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "خطأ", "يوجد منتج بنفس الاسم")

    def edit_product(self):
        r = self.inv_table.currentRow()
        if r == -1:
            QMessageBox.warning(self, "تنبيه", "اختر منتجاً للتعديل"); return
        pid  = int(self.inv_table.item(r,0).text())
        name = self.inv_name.text().strip()
        if not name:
            QMessageBox.warning(self, "خطأ", "أدخل اسم المنتج"); return
        unit   = self.inv_unit.currentText().strip() or "قطعة"
        cat_id = self.inv_cat_combo.currentData()
        cost   = D(self.inv_cost.text()  or "0")
        price  = D(self.inv_price.text() or "0")
        qty    = D(self.inv_qty.text()   or "0")
        try:
            q("UPDATE products SET name=?,unit=?,category_id=?,cost=?,price=?,quantity=? WHERE id=?",
              (name, unit, cat_id, float(cost), float(price), float(qty), pid))
            self._refresh_all_products()
            QMessageBox.information(self, "✅", "تم التعديل بنجاح")
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "خطأ", "الاسم موجود مسبقاً")

    def del_product(self):
        r = self.inv_table.currentRow()
        if r == -1:
            QMessageBox.warning(self, "تنبيه", "اختر منتجاً للحذف"); return
        pid  = int(self.inv_table.item(r,0).text())
        name = self.inv_table.item(r,1).text()
        if QMessageBox.question(self, "تأكيد", f"حذف: {name}؟",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            q("DELETE FROM products WHERE id=?", (pid,))
            self._refresh_all_products()

    # ══════════════════════════════════════════════════
    #  TAB 3 — المشتريات
    # ══════════════════════════════════════════════════
    def setup_purchases_tab(self):
        w = QWidget(); w.setLayoutDirection(Qt.RightToLeft)
        lay = QHBoxLayout(w); lay.setSpacing(10)

        left = QVBoxLayout(); left.setSpacing(8)
        self.purch_search = inp("🔍  بحث عن منتج...")
        self.purch_search.textChanged.connect(lambda t: self.refresh_purchases_products(t))
        left.addWidget(self.purch_search)

        self.purch_products = make_table(["ID","المنتج","الوحدة","سعر الشراء","المخزون"], min_h=220)
        left.addWidget(self.purch_products)

        add_row = QHBoxLayout(); add_row.setSpacing(6)
        self.purch_qty  = inp("الكمية", 130); self.purch_qty.setText("1")
        self.purch_cost = inp("سعر الشراء", 130)
        self.purch_qty.setValidator(dbl_validator(3)); self.purch_cost.setValidator(dbl_validator(2))
        add_row.addWidget(QLabel("كمية:")); add_row.addWidget(self.purch_qty)
        add_row.addWidget(QLabel("سعر:")); add_row.addWidget(self.purch_cost)
        add_row.addWidget(make_btn("➕  أضف للسلة", COLORS['blue'], self.add_to_purchase_cart))
        add_row.addStretch()
        left.addLayout(add_row)

        hist_grp = QGroupBox("سجل المشتريات  (انقر مرتين للتفاصيل)")
        hist_lay = QVBoxLayout(hist_grp)
        sr = QHBoxLayout()
        self.purch_hist_search = inp("🔍  اسم المورد...", 180)
        self.purch_hist_from = QDateEdit(); self.purch_hist_from.setCalendarPopup(True)
        self.purch_hist_from.setDate(QDate.currentDate().addMonths(-1))
        self.purch_hist_from.setDisplayFormat("yyyy-MM-dd")
        self.purch_hist_to = QDateEdit(); self.purch_hist_to.setCalendarPopup(True)
        self.purch_hist_to.setDate(QDate.currentDate())
        self.purch_hist_to.setDisplayFormat("yyyy-MM-dd")
        sr.addWidget(QLabel("بحث:")); sr.addWidget(self.purch_hist_search)
        sr.addWidget(QLabel("من:")); sr.addWidget(self.purch_hist_from)
        sr.addWidget(QLabel("لـ:")); sr.addWidget(self.purch_hist_to)
        sr.addWidget(make_btn("🔍", COLORS['blue'], self.refresh_purchases_history, 40))
        sr.addWidget(make_btn("الكل", COLORS['surface2'], self._reset_purch_filter, 55))
        sr.addStretch()
        hist_lay.addLayout(sr)
        self.purch_history = make_table(["#","المورد","الطريقة","الإجمالي","المدفوع","المتبقي","التاريخ",""])
        self.purch_history.setMaximumHeight(200)
        self.purch_history.cellDoubleClicked.connect(self._show_purchase_detail)
        hist_lay.addWidget(self.purch_history)
        left.addWidget(hist_grp)

        right = QVBoxLayout(); right.setSpacing(8)
        cart_hdr = QLabel("سلة الشراء")
        cart_hdr.setFont(QFont("Segoe UI",12,QFont.Bold))
        cart_hdr.setAlignment(Qt.AlignCenter)
        cart_hdr.setStyleSheet(f"background:{COLORS['surface2']};color:{COLORS['red']};"
                               f"padding:8px;border-radius:6px;")
        right.addWidget(cart_hdr)

        self.purch_cart_table = make_table(["المنتج","الوحدة","الكمية","سعر الشراء","الإجمالي","✕"], min_h=240)
        self.purch_cart_table.setMinimumWidth(430)
        self.purch_cart_table.cellClicked.connect(self._purch_cart_remove)
        right.addWidget(self.purch_cart_table)

        tot_frame = QFrame()
        tot_frame.setStyleSheet(f"background:{COLORS['surface2']};border-radius:8px;padding:2px;")
        tot_lay = QHBoxLayout(tot_frame)
        lbl_t = QLabel("إجمالي الفاتورة"); lbl_t.setStyleSheet(f"color:{COLORS['text2']};font-size:11px;")
        self.lbl_purch_total = QLabel("0.00")
        self.lbl_purch_total.setStyleSheet(f"color:{COLORS['red']};font-size:22px;font-weight:700;")
        tot_lay.addWidget(lbl_t); tot_lay.addWidget(self.lbl_purch_total)
        right.addWidget(tot_frame)

        sup_grp = QGroupBox("المورد وطريقة الدفع")
        sup_lay = QGridLayout(sup_grp)
        self.purch_sup_combo = QComboBox(); self.purch_sup_combo.setMinimumWidth(220)
        sup_lay.addWidget(QLabel("المورد:"), 0, 0)
        sup_lay.addWidget(self.purch_sup_combo, 0, 1, 1, 4)
        sup_lay.addWidget(make_btn("💵  نقدي", COLORS['green'],  self.purchase_cash,    110), 1, 0)
        sup_lay.addWidget(make_btn("📋  آجل",  COLORS['red'],    self.purchase_credit,  110), 1, 1)
        sup_lay.addWidget(make_btn("💳  جزئي", COLORS['orange'], self.purchase_partial, 110), 1, 2)
        sup_lay.addWidget(make_btn("🗑  إفراغ",COLORS['surface2'],self.clear_purchase_cart,90), 1, 3)
        right.addWidget(sup_grp)

        lay.addLayout(left, 52); lay.addLayout(right, 48)
        self.tabs.addTab(w, "🚚  المشتريات")

    def refresh_purchases_products(self, text=""):
        if not isinstance(text, str): text = ""
        data = rows("SELECT id,name,unit,cost,quantity FROM products "
                    "WHERE name LIKE ? ORDER BY name", (f"%{text}%",))
        display = [(str(r[0]),r[1],r[2],money(r[3]),fmt_qty(r[4])) for r in data]
        fill_table(self.purch_products, display,
                   col_colors=[(4, lambda v: D(v) < LOW_STOCK, COLORS['red']+"30", COLORS['red'])])

    def refresh_purchases_history(self, _=None):
        sup_text = self.purch_hist_search.text().strip()
        d_from   = self.purch_hist_from.date().toString("yyyy-MM-dd") + " 00:00:00"
        d_to     = self.purch_hist_to.date().toString("yyyy-MM-dd")   + " 23:59:59"
        data = rows("SELECT id,supplier_name,payment_type,total,paid_amount,remaining,purchase_date "
                    "FROM purchases WHERE supplier_name LIKE ? "
                    "AND purchase_date>=? AND purchase_date<=? ORDER BY id DESC LIMIT 100",
                    (f"%{sup_text}%", d_from, d_to))
        fill_table(self.purch_history,
                   [(str(r[0]),r[1],r[2],money(r[3]),money(r[4]),money(r[5]),r[6],"🔍") for r in data])

    def _reset_purch_filter(self):
        self.purch_hist_search.clear()
        self.purch_hist_from.setDate(QDate.currentDate().addMonths(-1))
        self.purch_hist_to.setDate(QDate.currentDate())
        self.refresh_purchases_history()

    def add_to_purchase_cart(self):
        row = self.purch_products.currentRow()
        if row == -1:
            QMessageBox.warning(self, "تنبيه", "اختر منتجاً أولاً"); return
        pid      = int(self.purch_products.item(row,0).text())
        name     = self.purch_products.item(row,1).text()
        unit     = self.purch_products.item(row,2).text()
        cur_cost = D(self.purch_products.item(row,3).text())
        if not is_positive(self.purch_qty.text()):
            QMessageBox.warning(self, "خطأ", "أدخل كمية صحيحة"); return
        qty      = D(self.purch_qty.text())
        cost_txt = self.purch_cost.text().strip()
        cost     = D(cost_txt) if cost_txt and is_positive(cost_txt) else cur_cost
        for item in self.purchase_cart:
            if item["pid"] == pid:
                item["qty"] += qty; item["cost"] = cost; item["total"] = item["qty"] * cost
                self.refresh_purchase_cart(); return
        self.purchase_cart.append({"pid":pid,"name":name,"unit":unit,"cost":cost,"qty":qty,"total":cost*qty})
        self.refresh_purchase_cart()

    def refresh_purchase_cart(self):
        self.purch_cart_table.setRowCount(len(self.purchase_cart))
        for i, item in enumerate(self.purchase_cart):
            self.purch_cart_table.setRowHeight(i, 38)
            for j, v in enumerate([item["name"],item["unit"],fmt_qty(item["qty"]),
                                    money(item["cost"]),money(item["total"]),"✕"]):
                cell = QTableWidgetItem(v); cell.setTextAlignment(Qt.AlignCenter)
                if j == 5: cell.setForeground(QColor(COLORS['red']))
                self.purch_cart_table.setItem(i, j, cell)
        total = sum(i["total"] for i in self.purchase_cart)
        self.lbl_purch_total.setText(money(total))
        self.purch_cart_table.resizeColumnsToContents()

    def _purch_cart_remove(self, row, col):
        if col == 5 and row < len(self.purchase_cart):
            del self.purchase_cart[row]; self.refresh_purchase_cart()

    def clear_purchase_cart(self):
        if not self.purchase_cart: return
        if QMessageBox.question(self, "تأكيد", "تفريغ سلة الشراء؟",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.purchase_cart.clear(); self.refresh_purchase_cart()

    def purchase_cash(self):    self._process_purchase(mode="cash")
    def purchase_credit(self):  self._process_purchase(mode="credit")
    def purchase_partial(self): self._process_purchase(mode="partial")

    def _process_purchase(self, mode):
        if not self.purchase_cart:
            QMessageBox.warning(self, "تنبيه", "سلة الشراء فارغة!"); return
        sup_id   = self.purch_sup_combo.currentData()
        sup_name = self.purch_sup_combo.currentText()
        if mode in ("credit", "partial") and not sup_id:
            QMessageBox.warning(self, "خطأ", "اختر مورداً للشراء الآجل أو الجزئي"); return

        total = sum(i["total"] for i in self.purchase_cart)

        if mode == "cash":
            paid_amount = float(total); remaining = 0.0; ptype = "نقدي"
        elif mode == "credit":
            paid_amount = 0.0; remaining = float(total); ptype = "آجل"
        else:
            dlg = PartialPaymentDialog(float(total), mode="purchase", parent=self)
            if dlg.exec() != QDialog.Accepted: return
            paid_amount = dlg.result_paid; remaining = dlg.result_remaining; ptype = "جزئي"

        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            C.execute(
                "INSERT INTO purchases(supplier_id,supplier_name,payment_type,"
                "total,paid_amount,remaining,purchase_date) VALUES(?,?,?,?,?,?,?)",
                (sup_id if mode != "cash" else None,
                 sup_name if mode != "cash" else "نقدي",
                 ptype, float(total), paid_amount, remaining, date))
            purch_id = C.lastrowid

            for item in self.purchase_cart:
                C.execute(
                    "INSERT INTO purchase_items(purchase_id,product_id,product_name,"
                    "unit,cost,quantity,total) VALUES(?,?,?,?,?,?,?)",
                    (purch_id, item["pid"], item["name"], item["unit"],
                     float(item["cost"]), float(item["qty"]), float(item["total"])))
                C.execute("UPDATE products SET quantity=quantity+?,cost=? WHERE id=?",
                          (float(item["qty"]), float(item["cost"]), item["pid"]))

            if mode in ("credit", "partial") and remaining > 0:
                C.execute("UPDATE suppliers SET total_debt=total_debt+? WHERE id=?", (remaining, sup_id))
                details = (f"فاتورة شراء #{purch_id} — إجمالي: {money(total)}"
                           + (f" — كاش: {money(paid_amount)}" if mode == "partial" else ""))
                C.execute("INSERT INTO supplier_ledger(supplier_id,type,details,amount,date) VALUES(?,?,?,?,?)",
                          (sup_id, "purchase", details, remaining, date))

            DB.commit()

            msg = (f"رقم الفاتورة : #{purch_id}\nالإجمالي     : {money(total)}")
            if mode == "partial":
                msg += f"\n\nالمدفوع نقداً : {money(paid_amount)}\nالمتبقي آجل  : {money(remaining)}"
            elif mode == "credit":
                msg += f"\n\nأُضيف لحساب المورد: {sup_name}"
            QMessageBox.information(self, "✅ تم الشراء", msg)

            self.purchase_cart.clear(); self.refresh_purchase_cart()
            self._refresh_all_products(); self.refresh_purchases_history()
            self.suppliers_tab.refresh_table()

        except Exception as e:
            DB.rollback(); QMessageBox.critical(self, "خطأ", f"فشلت عملية الشراء:\n{e}")

    def _show_purchase_detail(self, row, _col):
        item = self.purch_history.item(row, 0)
        if item: PurchaseDetailDialog(int(item.text()), self).exec()

    # ══════════════════════════════════════════════════
    #  TAB 6 — التقارير
    # ══════════════════════════════════════════════════
    def setup_reports_tab(self):
        # ══════════════════════════════════════════════
        #  تاب التقويم اليومي — مستقل
        # ══════════════════════════════════════════════
        cal_w = QWidget(); cal_w.setLayoutDirection(Qt.RightToLeft)
        cal_main = QVBoxLayout(cal_w); cal_main.setSpacing(10)

        cal_title = QLabel("📅  التقرير اليومي بالتقويم")
        cal_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        cal_title.setAlignment(Qt.AlignCenter)
        cal_title.setStyleSheet(f"color:{COLORS['accent']};padding:6px;")
        cal_main.addWidget(cal_title)

        cal_body = QHBoxLayout()
        self.cal = SalesCalendar()
        self.cal.setMinimumSize(340, 280)
        self.cal.currentPageChanged.connect(self._on_cal_page_changed)
        self.cal.selectionChanged.connect(self._on_cal_date_selected)
        cal_body.addWidget(self.cal, 0)

        cal_right = QVBoxLayout()
        self.cal_day_lbl = QLabel("اختر يوماً من التقويم")
        self.cal_day_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.cal_day_lbl.setStyleSheet(f"color:{COLORS['accent']};padding:4px;")
        cal_right.addWidget(self.cal_day_lbl)

        self.cal_table = make_table(["الفاتورة","العميل","الدفع","الإجمالي","الربح","الوقت"])
        self.cal_table.cellDoubleClicked.connect(lambda r,c: self._try_open_invoice(self.cal_table, r))
        cal_right.addWidget(self.cal_table, 1)

        self.cal_summary_lbl = QLabel()
        self.cal_summary_lbl.setStyleSheet(
            f"font-weight:600;color:{COLORS['green']};padding:6px;"
            f"background:{COLORS['surface2']};border-radius:6px;")
        cal_right.addWidget(self.cal_summary_lbl)
        cal_body.addLayout(cal_right, 1)
        cal_main.addLayout(cal_body)
        self.tabs.addTab(cal_w, "📅  التقويم اليومي")

        # ══════════════════════════════════════════════
        #  تاب التقارير
        # ══════════════════════════════════════════════
        w = QWidget(); w.setLayoutDirection(Qt.RightToLeft)
        main_lay = QVBoxLayout(w); main_lay.setSpacing(10)

        # أزرار التقارير
        btns_grp = QGroupBox("التقارير الجاهزة")
        btns_lay = QHBoxLayout(btns_grp)
        btns_lay.setSpacing(6)
        for text, color, cb in [
            ("📅  اليوم",          COLORS['blue'],   self.rpt_daily),
            ("📆  الشهر",          COLORS['accent'],  self.rpt_monthly),
            ("💰  أرباح شهرية",    COLORS['orange'],  self.rpt_profit_monthly),
            ("🧾  كل الفواتير",    COLORS['green'],   self.rpt_all_invoices),
            ("📦  أداء المنتجات",  "#B8A000",         self.rpt_products),
            ("👥  ديون العملاء",   COLORS['red'],     self.rpt_customer_debts),
            ("🏭  ديون الموردين",  "#795548",         self.rpt_supplier_debts),
            ("⚠️  مخزون منخفض",   COLORS['orange'],  self.rpt_low_stock),
            ("🔄  المرتجعات",      COLORS['red'],     self.rpt_returns),
        ]:
            btns_lay.addWidget(make_btn(text, color, cb, 105))
        main_lay.addWidget(btns_grp)

        # فترة مخصصة
        date_grp = QGroupBox("تقرير بفترة زمنية مخصصة")
        date_lay = QHBoxLayout(date_grp)
        self.rpt_from = QDateEdit(); self.rpt_from.setCalendarPopup(True)
        self.rpt_from.setDate(QDate.currentDate().addMonths(-1))
        self.rpt_from.setDisplayFormat("yyyy-MM-dd")
        self.rpt_to = QDateEdit(); self.rpt_to.setCalendarPopup(True)
        self.rpt_to.setDate(QDate.currentDate())
        self.rpt_to.setDisplayFormat("yyyy-MM-dd")
        self.rpt_type_combo = QComboBox()
        self.rpt_type_combo.addItems(["مبيعات","مشتريات"])
        self.rpt_type_combo.setMinimumWidth(100)
        date_lay.addWidget(QLabel("من:")); date_lay.addWidget(self.rpt_from)
        date_lay.addWidget(QLabel("لـ:")); date_lay.addWidget(self.rpt_to)
        date_lay.addWidget(QLabel("نوع:")); date_lay.addWidget(self.rpt_type_combo)
        date_lay.addWidget(make_btn("🔍  عرض", COLORS['blue'], self.rpt_custom_range, 100))
        date_lay.addStretch()
        main_lay.addWidget(date_grp)

        self.rpt_title = QLabel("اختر تقريراً من الأعلى ↑")
        self.rpt_title.setFont(QFont("Segoe UI",12,QFont.Bold))
        self.rpt_title.setAlignment(Qt.AlignCenter)
        self.rpt_title.setStyleSheet(f"color:{COLORS['accent']};padding:4px;")
        self.rpt_table = make_table(["--"], min_h=280)
        self.rpt_table.cellDoubleClicked.connect(lambda r,c: self._try_open_invoice(self.rpt_table, r))
        self.rpt_summary = QLabel()
        self.rpt_summary.setStyleSheet(f"font-weight:600;color:{COLORS['text2']};padding:6px;"
                                       f"background:{COLORS['surface2']};border-radius:6px;")
        main_lay.addWidget(self.rpt_title)
        main_lay.addWidget(self.rpt_table)
        main_lay.addWidget(self.rpt_summary)
        self.tabs.addTab(w, "📊  التقارير")

        d = QDate.currentDate()
        self._load_cal_sales_dates(d.year(), d.month())

    def _on_cal_page_changed(self, year, month):
        self._load_cal_sales_dates(year, month)

    def _load_cal_sales_dates(self, year, month):
        month_str = f"{year:04d}-{month:02d}"
        data = rows("SELECT DISTINCT date(sale_date) FROM sales WHERE sale_date LIKE ?", (month_str+"%",))
        self.cal.set_sale_days({r[0] for r in data})

    def _on_cal_date_selected(self):
        date_str = self.cal.selectedDate().toString("yyyy-MM-dd")
        data = rows("SELECT invoice_no,customer_name,payment_type,total,profit,sale_date "
                    "FROM sales WHERE sale_date LIKE ? ORDER BY id DESC", (date_str+"%",))
        display = [(r[0],r[1],r[2],money(r[3]),money(r[4]),r[5]) for r in data]
        fill_table(self.cal_table, display)
        total  = sum(D(r[3]) for r in data); profit = sum(D(r[4]) for r in data)
        self.cal_day_lbl.setText(f"📅  {date_str}  —  {len(data)} فاتورة")
        self.cal_summary_lbl.setText(f"  مبيعات: {money(total)}   |   ربح: {money(profit)}"
                                     f"   ✦  انقر مرتين لعرض تفاصيل الفاتورة")

    def _set_report(self, title, headers, data, summary=""):
        self.rpt_title.setText(title)
        self.rpt_table.setColumnCount(len(headers))
        self.rpt_table.setHorizontalHeaderLabels(headers)
        fill_table(self.rpt_table, data)
        self.rpt_summary.setText(summary)

    def rpt_daily(self):
        today = datetime.now().strftime("%Y-%m-%d")
        data  = rows("SELECT invoice_no,customer_name,payment_type,total,paid_amount,remaining,profit,sale_date "
                     "FROM sales WHERE sale_date LIKE ? ORDER BY id DESC", (today+"%",))
        total=sum(D(r[3]) for r in data); paid=sum(D(r[4]) for r in data)
        rem=sum(D(r[5]) for r in data); profit=sum(D(r[6]) for r in data)
        self._set_report(f"📅  مبيعات اليوم — {today}",
            ["الفاتورة","العميل","الدفع","الإجمالي","المدفوع","المتبقي","الربح","الوقت"],
            [(r[0],r[1],r[2],money(r[3]),money(r[4]),money(r[5]),money(r[6]),r[7]) for r in data],
            f"فواتير: {len(data)}   |   مبيعات: {money(total)}   |   "
            f"المدفوع: {money(paid)}   |   المتبقي: {money(rem)}   |   أرباح: {money(profit)}"
            f"   ✦  انقر مرتين على الفاتورة لعرض تفاصيلها")

    def rpt_monthly(self):
        month = datetime.now().strftime("%Y-%m")
        data  = rows("SELECT invoice_no,customer_name,payment_type,total,paid_amount,remaining,profit,sale_date "
                     "FROM sales WHERE sale_date LIKE ? ORDER BY id DESC", (month+"%",))
        total=sum(D(r[3]) for r in data); paid=sum(D(r[4]) for r in data)
        rem=sum(D(r[5]) for r in data); profit=sum(D(r[6]) for r in data)
        self._set_report(f"📆  مبيعات الشهر — {month}",
            ["الفاتورة","العميل","الدفع","الإجمالي","المدفوع","المتبقي","الربح","التاريخ"],
            [(r[0],r[1],r[2],money(r[3]),money(r[4]),money(r[5]),money(r[6]),r[7]) for r in data],
            f"فواتير: {len(data)}   |   مبيعات: {money(total)}   |   "
            f"المدفوع: {money(paid)}   |   المتبقي: {money(rem)}   |   أرباح: {money(profit)}")

    def rpt_profit_monthly(self):
        data = rows("SELECT strftime('%Y-%m',sale_date),COUNT(*),ROUND(SUM(total),2),"
                    "ROUND(SUM(paid_amount),2),ROUND(SUM(remaining),2),ROUND(SUM(profit),2) "
                    "FROM sales GROUP BY 1 ORDER BY 1 DESC")
        res = one("SELECT COUNT(*),SUM(total),SUM(paid_amount),SUM(remaining),SUM(profit) FROM sales")
        total=D(res[1]) if res and res[1] else Decimal("0")
        paid=D(res[2]) if res and res[2] else Decimal("0")
        rem=D(res[3]) if res and res[3] else Decimal("0")
        profit=D(res[4]) if res and res[4] else Decimal("0")
        self._set_report("💰  الأرباح — تفصيل شهري",
            ["الشهر","عدد الفواتير","الإيراد","المدفوع","المتبقي","الربح"],
            [(r[0],str(r[1]),money(r[2]),money(r[3]),money(r[4]),money(r[5])) for r in data],
            f"الإجمالي: {money(total)}   |   المدفوع: {money(paid)}   |   "
            f"المتبقي: {money(rem)}   |   الأرباح: {money(profit)}")

    def rpt_all_invoices(self):
        data = rows("SELECT invoice_no,customer_name,payment_type,total,paid_amount,remaining,profit,sale_date "
                    "FROM sales ORDER BY id DESC LIMIT 2000")
        total=sum(D(r[3]) for r in data); paid=sum(D(r[4]) for r in data)
        rem=sum(D(r[5]) for r in data); profit=sum(D(r[6]) for r in data)
        self._set_report("🧾  كل الفواتير",
            ["الفاتورة","العميل","الدفع","الإجمالي","المدفوع","المتبقي","الربح","التاريخ"],
            [(r[0],r[1],r[2],money(r[3]),money(r[4]),money(r[5]),money(r[6]),r[7]) for r in data],
            f"فواتير: {len(data)}   |   إيراد: {money(total)}   |   "
            f"المدفوع: {money(paid)}   |   المتبقي: {money(rem)}   |   أرباح: {money(profit)}"
            f"   ✦  انقر مرتين على الفاتورة لعرض تفاصيلها")

    def rpt_products(self):
        data = rows("SELECT si.product_name,si.unit,SUM(si.quantity),"
                    "ROUND(SUM(si.total),2),ROUND(SUM(si.profit),2),ROUND(AVG(si.price),2) "
                    "FROM sale_items si GROUP BY si.product_id,si.product_name ORDER BY 3 DESC")
        self._set_report("📦  أداء المنتجات — الأكثر مبيعاً",
            ["المنتج","الوحدة","الكمية المباعة","الإيراد","الربح","متوسط السعر"],
            [(r[0],r[1],fmt_qty(r[2]),money(r[3]),money(r[4]),money(r[5])) for r in data],
            f"إجمالي المنتجات: {len(data)}")

    def rpt_customer_debts(self):
        data = rows("SELECT name,phone,ROUND(total_debt,2) FROM customers WHERE total_debt>0 ORDER BY total_debt DESC")
        total = sum(D(r[2]) for r in data)
        self._set_report("👥  ديون العملاء",["اسم العميل","الهاتف","الدين المتبقي"],
            [(r[0],r[1],money(r[2])) for r in data],
            f"العملاء المدينين: {len(data)}   |   إجمالي الديون: {money(total)}")

    def rpt_supplier_debts(self):
        data = rows("SELECT name,phone,ROUND(total_debt,2) FROM suppliers WHERE total_debt>0 ORDER BY total_debt DESC")
        total = sum(D(r[2]) for r in data)
        self._set_report("🏭  ديون للموردين",["اسم المورد","الهاتف","المبلغ المتبقي"],
            [(r[0],r[1],money(r[2])) for r in data],
            f"الموردين الدائنين: {len(data)}   |   إجمالي ما علينا: {money(total)}")

    def rpt_low_stock(self):
        data = rows("SELECT name,unit,quantity,cost,price FROM products WHERE quantity<? ORDER BY quantity ASC", (LOW_STOCK,))
        self._set_report(f"⚠️  مخزون منخفض (أقل من {LOW_STOCK})",
            ["المنتج","الوحدة","المخزون","سعر الشراء","سعر البيع"],
            [(r[0],r[1],fmt_qty(r[2]),money(r[3]),money(r[4])) for r in data],
            f"منتجات تحتاج إعادة طلب: {len(data)}")

    # ✅ تقرير المرتجعات الجديد
    def rpt_returns(self):
        data = rows("SELECT r.return_no,r.original_invoice,r.customer_name,"
                    "r.payment_type,r.total,r.return_date "
                    "FROM returns r ORDER BY r.id DESC LIMIT 1000")
        total = sum(D(r[4]) for r in data)
        self._set_report("🔄  سجل المرتجعات",
            ["رقم المرتجع","الفاتورة الأصلية","العميل","طريقة الدفع","الإجمالي","التاريخ"],
            [(r[0],r[1],r[2],r[3],money(r[4]),r[5]) for r in data],
            f"إجمالي المرتجعات: {len(data)}   |   القيمة الإجمالية: {money(total)}")

    def rpt_custom_range(self):
        d_from   = self.rpt_from.date().toString("yyyy-MM-dd") + " 00:00:00"
        d_to     = self.rpt_to.date().toString("yyyy-MM-dd")   + " 23:59:59"
        lbl_from = self.rpt_from.date().toString("yyyy-MM-dd")
        lbl_to   = self.rpt_to.date().toString("yyyy-MM-dd")
        rpt_type = self.rpt_type_combo.currentText()
        if rpt_type == "مبيعات":
            data = rows("SELECT invoice_no,customer_name,payment_type,total,paid_amount,remaining,profit,sale_date "
                        "FROM sales WHERE sale_date>=? AND sale_date<=? ORDER BY id DESC", (d_from, d_to))
            total=sum(D(r[3]) for r in data); paid=sum(D(r[4]) for r in data)
            rem=sum(D(r[5]) for r in data); profit=sum(D(r[6]) for r in data)
            self._set_report(f"📆  مبيعات من {lbl_from} لـ {lbl_to}",
                ["الفاتورة","العميل","الدفع","الإجمالي","المدفوع","المتبقي","الربح","التاريخ"],
                [(r[0],r[1],r[2],money(r[3]),money(r[4]),money(r[5]),money(r[6]),r[7]) for r in data],
                f"فواتير: {len(data)}   |   مبيعات: {money(total)}   |   "
                f"المدفوع: {money(paid)}   |   المتبقي: {money(rem)}   |   أرباح: {money(profit)}"
                f"   ✦  انقر مرتين لعرض تفاصيل الفاتورة")
        else:
            data = rows("SELECT id,supplier_name,payment_type,total,paid_amount,remaining,purchase_date "
                        "FROM purchases WHERE purchase_date>=? AND purchase_date<=? ORDER BY id DESC", (d_from, d_to))
            total=sum(D(r[3]) for r in data); paid=sum(D(r[4]) for r in data)
            rem=sum(D(r[4]) for r in data)
            self._set_report(f"🚚  مشتريات من {lbl_from} لـ {lbl_to}",
                ["#","المورد","الطريقة","الإجمالي","المدفوع","المتبقي","التاريخ"],
                [(str(r[0]),r[1],r[2],money(r[3]),money(r[4]),money(r[5]),r[6]) for r in data],
                f"فواتير: {len(data)}   |   إجمالي: {money(total)}   |   "
                f"المدفوع: {money(paid)}   |   المتبقي: {money(rem)}")


# ══════════════════════════════════════════════════════
#  تشغيل البرنامج
# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    make_backup(manual=False)
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 11))
    app.setLayoutDirection(Qt.RightToLeft)
    app.setStyleSheet(STYLESHEET)
    window = ShopApp()
    window.show()
    sys.exit(app.exec())