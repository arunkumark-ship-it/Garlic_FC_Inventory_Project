import streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials
import json

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Inventory Manager",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        border: 1px solid #E9ECEF;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        text-align: center;
    }
    .metric-card .label { font-size: 0.75rem; color: #6C757D; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
    .metric-card .value { font-size: 2rem; font-weight: 600; }
    .metric-card .value.green { color: #0F6E56; }
    .metric-card .value.red   { color: #C0392B; }
    .metric-card .value.blue  { color: #185FA5; }
    .metric-card .value.amber { color: #854F0B; }

    .badge-in  { background:#D1FAE5; color:#065F46; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .badge-out { background:#FEE2E2; color:#991B1B; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .badge-ok  { background:#D1FAE5; color:#065F46; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .badge-low { background:#FEF3C7; color:#92400E; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .badge-critical { background:#FEE2E2; color:#991B1B; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }

    .login-box {
        max-width: 400px;
        margin: 4rem auto;
        background: white;
        border-radius: 16px;
        padding: 2.5rem;
        border: 1px solid #E9ECEF;
        box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }
    div[data-testid="stDataFrame"] { border-radius: 10px; border: 1px solid #E9ECEF; }
    .stTabs [data-baseweb="tab"] { font-size: 0.9rem; font-weight: 500; }
    .section-header { font-size: 1.1rem; font-weight: 600; color: #212529; margin-bottom: 0.5rem; }
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── Google Sheets Setup ───────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_TABS = {
    "users":      ["username", "password", "role", "full_name"],
    "items":      ["item_id", "sku", "name", "category", "material_type",
                   "storage_location", "unit", "qty", "min_qty", "created_at"],
    "inbound":    ["tx_id", "item_id", "sku", "item_name", "qty", "date",
                   "po_ref", "supplier", "operator", "note", "timestamp"],
    "outbound":   ["tx_id", "item_id", "sku", "item_name", "qty", "date",
                   "so_ref", "customer", "operator", "note", "timestamp"],
}

@st.cache_resource(show_spinner=False)
def get_gsheet_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception:
        return None

@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    client = get_gsheet_client()
    if not client:
        return None
    try:
        sh = client.open(st.secrets["google_sheets"]["spreadsheet_name"])
        # Ensure all tabs exist
        existing = [ws.title for ws in sh.worksheets()]
        for tab, headers in SHEET_TABS.items():
            if tab not in existing:
                ws = sh.add_worksheet(title=tab, rows=1000, cols=len(headers))
                ws.append_row(headers)
            else:
                ws = sh.worksheet(tab)
                # Seed default admin user if users sheet is empty
                if tab == "users" and len(ws.get_all_values()) <= 1:
                    ws.append_row(["admin", "admin123", "admin", "Administrator"])
                    ws.append_row(["operator1", "pass123", "operator", "John Operator"])
        return sh
    except Exception as e:
        st.error(f"Google Sheets connection error: {e}")
        return None

def read_sheet(tab: str) -> pd.DataFrame:
    sh = get_spreadsheet()
    if sh is None:
        return pd.DataFrame(columns=SHEET_TABS[tab])
    try:
        ws = sh.worksheet(tab)
        data = ws.get_all_records()
        df = pd.DataFrame(data) if data else pd.DataFrame(columns=SHEET_TABS[tab])
        return df
    except Exception:
        return pd.DataFrame(columns=SHEET_TABS[tab])

def append_row(tab: str, row: list):
    sh = get_spreadsheet()
    if sh is None:
        st.warning("⚠️ Google Sheets not connected. Data not saved.")
        return False
    try:
        ws = sh.worksheet(tab)
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Failed to save: {e}")
        return False

def update_item_qty(item_id: str, new_qty: int):
    sh = get_spreadsheet()
    if sh is None:
        return False
    try:
        ws = sh.worksheet("items")
        cell = ws.find(str(item_id), in_column=1)
        if cell:
            headers = ws.row_values(1)
            qty_col = headers.index("qty") + 1
            ws.update_cell(cell.row, qty_col, new_qty)
        return True
    except Exception as e:
        st.error(f"Failed to update qty: {e}")
        return False

def delete_row(tab: str, id_col_val: str, col_index: int = 1):
    sh = get_spreadsheet()
    if sh is None:
        return False
    try:
        ws = sh.worksheet(tab)
        cell = ws.find(str(id_col_val), in_column=col_index)
        if cell:
            ws.delete_rows(cell.row)
        return True
    except Exception as e:
        st.error(f"Failed to delete: {e}")
        return False

# ─── Session State Init ────────────────────────────────────────────────────────
for key, val in {
    "logged_in": False,
    "username": "",
    "role": "",
    "full_name": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ─── Helper: unique ID ─────────────────────────────────────────────────────────
def new_id(prefix=""):
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S%f')[-12:]}"

def stock_status(qty, min_qty):
    qty, min_qty = int(qty or 0), int(min_qty or 0)
    if qty == 0:     return "Out of stock", "critical"
    if qty < min_qty * 0.5: return "Critical", "critical"
    if qty < min_qty:       return "Low stock", "low"
    return "In stock", "ok"

# ─── LOGIN PAGE ────────────────────────────────────────────────────────────────
def login_page():
    st.markdown("""
    <div style='text-align:center; margin-top: 3rem;'>
        <div style='font-size:3rem'>📦</div>
        <h1 style='font-size:1.8rem; font-weight:700; margin-bottom:0.2rem'>Inventory Manager</h1>
        <p style='color:#6C757D; font-size:0.95rem'>Sign in to manage your stock</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("#### 🔐 Sign In")
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")

            if st.button("Sign In", use_container_width=True, type="primary"):
                users_df = read_sheet("users")
                if users_df.empty:
                    # Fallback hardcoded admin if sheet not connected
                    if username == "NC25796" and password == "Ninj@2026":
                        st.session_state.update({
                            "logged_in": True, "username": "NC25796",
                            "role": "admin", "full_name": "Administrator"
                        })
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
                    return
                match = users_df[
                    (users_df["username"] == username) &
                    (users_df["password"] == password)
                ]
                if not match.empty:
                    row = match.iloc[0]
                    st.session_state.update({
                        "logged_in": True,
                        "username": username,
                        "role": row.get("role", "operator"),
                        "full_name": row.get("full_name", username),
                    })
                    st.success(f"Welcome, {row.get('full_name', username)}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password.")

        st.markdown("""
        <p style='text-align:center; font-size:0.8rem; color:#ADB5BD; margin-top:1rem'>
        Default admin: 
        </p>
        """, unsafe_allow_html=True)

# ─── MAIN APP ──────────────────────────────────────────────────────────────────
def main_app():
    # ── Sidebar ──
    with st.sidebar:
        st.markdown(f"""
        <div style='background:white; border-radius:12px; padding:1rem; border:1px solid #E9ECEF; margin-bottom:1rem'>
            <div style='font-size:1.5rem; text-align:center'>📦</div>
            <div style='text-align:center; font-weight:600; font-size:1rem'>{st.session_state.full_name}</div>
            <div style='text-align:center; font-size:0.78rem; color:#6C757D'>
                {'🛡️ Admin' if st.session_state.role == 'admin' else '👤 Operator'}
                &nbsp;·&nbsp; {st.session_state.username}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**Navigation**")
        page = st.radio("", ["📊 Dashboard", "📦 Inventory", "📥 Inbound", "📤 Outbound",
                              "👥 Users" if st.session_state.role == "admin" else None],
                        label_visibility="collapsed")
        page = [p for p in [page] if p][0]

        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            for k in ["logged_in", "username", "role", "full_name"]:
                st.session_state[k] = "" if k != "logged_in" else False
            st.rerun()

        sh_connected = get_spreadsheet() is not None
        status_color = "#0F6E56" if sh_connected else "#C0392B"
        status_text = "Connected" if sh_connected else "Not connected"
        st.markdown(f"<div style='font-size:0.75rem; color:{status_color}; text-align:center'>⬤ Google Sheets: {status_text}</div>", unsafe_allow_html=True)

    # ── Pages ──
    if page == "📊 Dashboard":
        dashboard_page()
    elif page == "📦 Inventory":
        inventory_page()
    elif page == "📥 Inbound":
        inbound_page()
    elif page == "📤 Outbound":
        outbound_page()
    elif page == "👥 Users" and st.session_state.role == "admin":
        users_page()

# ─── DASHBOARD ─────────────────────────────────────────────────────────────────
def dashboard_page():
    st.markdown("## 📊 Dashboard")
    items_df   = read_sheet("items")
    inbound_df = read_sheet("inbound")
    outbound_df= read_sheet("outbound")

    total_items  = len(items_df)
    total_in     = pd.to_numeric(inbound_df["qty"], errors="coerce").sum() if not inbound_df.empty and "qty" in inbound_df else 0
    total_out    = pd.to_numeric(outbound_df["qty"], errors="coerce").sum() if not outbound_df.empty and "qty" in outbound_df else 0
    low_stock    = 0
    if not items_df.empty and "qty" in items_df.columns and "min_qty" in items_df.columns:
        low_stock = int(((pd.to_numeric(items_df["qty"], errors="coerce").fillna(0)) <
                         (pd.to_numeric(items_df["min_qty"], errors="coerce").fillna(0))).sum())

    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, color in [
        (c1, "Total SKUs", total_items, "blue"),
        (c2, "Total Inbound", int(total_in), "green"),
        (c3, "Total Outbound", int(total_out), "red"),
        (c4, "Low / Out of Stock", low_stock, "amber"),
    ]:
        with col:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='label'>{label}</div>
                <div class='value {color}'>{val:,}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 🔴 Low Stock Alerts")
        if items_df.empty:
            st.info("No items found.")
        else:
            items_df["qty"] = pd.to_numeric(items_df["qty"], errors="coerce").fillna(0)
            items_df["min_qty"] = pd.to_numeric(items_df["min_qty"], errors="coerce").fillna(0)
            low = items_df[items_df["qty"] < items_df["min_qty"]][["sku","name","qty","min_qty","material_type","storage_location"]]
            if low.empty:
                st.success("✅ All items above minimum stock level.")
            else:
                st.dataframe(low.rename(columns={
                    "sku":"SKU","name":"Item","qty":"Current Qty",
                    "min_qty":"Min Qty","material_type":"Material","storage_location":"Location"
                }), use_container_width=True, hide_index=True)

    with col_b:
        st.markdown("#### 📋 Recent Transactions")
        rows = []
        if not inbound_df.empty:
            for _, r in inbound_df.tail(5).iterrows():
                rows.append({"Type":"📥 IN","SKU":r.get("sku",""),"Item":r.get("item_name",""),
                              "Qty":r.get("qty",""),"Operator":r.get("operator",""),"Date":r.get("date","")})
        if not outbound_df.empty:
            for _, r in outbound_df.tail(5).iterrows():
                rows.append({"Type":"📤 OUT","SKU":r.get("sku",""),"Item":r.get("item_name",""),
                              "Qty":r.get("qty",""),"Operator":r.get("operator",""),"Date":r.get("date","")})
        if rows:
            recent_df = pd.DataFrame(rows).sort_values("Date", ascending=False).head(8)
            st.dataframe(recent_df, use_container_width=True, hide_index=True)
        else:
            st.info("No transactions yet.")

    if not items_df.empty and "material_type" in items_df.columns:
        st.markdown("#### 📦 Stock by Material Type")
        mat_summary = items_df.groupby("material_type")["qty"].sum().reset_index()
        mat_summary.columns = ["Material Type", "Total Qty"]
        st.bar_chart(mat_summary.set_index("Material Type"))

# ─── INVENTORY ─────────────────────────────────────────────────────────────────
MATERIAL_TYPES = [
    "Raw Material", "Semi-Finished", "Finished Goods",
    "Spare Parts", "Packaging", "Consumables", "Electronics", "Hardware", "Other"
]
STORAGE_LOCATIONS = [
    "Rack A", "Rack B", "Rack C", "Cold Storage", "Bonded Warehouse",
    "Shelf 1", "Shelf 2", "Floor Storage", "Loading Bay","Office Room", "Other"
]

def inventory_page():
    st.markdown("## 📦 Inventory — SKU & Material Management")
    items_df = read_sheet("items")

    # ── Add Item Form ──
    if st.session_state.role == "admin":
        with st.expander("➕ Add New Item / SKU", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                sku      = st.text_input("SKU *", placeholder="e.g. RAW-ST-001")
                name     = st.text_input("Item Name *", placeholder="e.g. Steel Rod 6mm")
                category = st.text_input("Category", placeholder="e.g. Metal, Plastic")
            with c2:
                material_type     = st.selectbox("Material Type *", MATERIAL_TYPES)
                storage_location  = st.selectbox("Storage Location *", STORAGE_LOCATIONS)
                unit              = st.text_input("Unit *", placeholder="pcs / kg / box / litre")
            with c3:
                qty     = st.number_input("Opening Qty", min_value=0, value=0)
                min_qty = st.number_input("Minimum Stock Level", min_value=0, value=10)

            if st.button("✅ Add Item", type="primary"):
                if not sku or not name or not unit:
                    st.error("SKU, Name, and Unit are required.")
                elif not items_df.empty and sku in items_df["sku"].values:
                    st.error(f"SKU '{sku}' already exists.")
                else:
                    item_id = new_id("ITM-")
                    ok = append_row("items", [
                        item_id, sku, name, category, material_type,
                        storage_location, unit, qty, min_qty,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ])
                    if ok:
                        st.success(f"✅ Item '{name}' ({sku}) added!")
                        st.cache_resource.clear()
                        st.rerun()

    st.divider()

    # ── Filters ──
    fc1, fc2, fc3, fc4 = st.columns([2, 1.5, 1.5, 1.5])
    with fc1: search = st.text_input("🔍 Search SKU / Name", placeholder="Search...")
    with fc2: filter_mat  = st.selectbox("Material Type", ["All"] + MATERIAL_TYPES)
    with fc3: filter_loc  = st.selectbox("Storage Location", ["All"] + STORAGE_LOCATIONS)
    with fc4: filter_stat = st.selectbox("Stock Status", ["All", "In stock", "Low stock", "Critical", "Out of stock"])

    if items_df.empty:
        st.info("No items yet. Add your first SKU above.")
        return

    items_df["qty"] = pd.to_numeric(items_df["qty"], errors="coerce").fillna(0).astype(int)
    items_df["min_qty"] = pd.to_numeric(items_df["min_qty"], errors="coerce").fillna(0).astype(int)
    items_df["status"] = items_df.apply(lambda r: stock_status(r["qty"], r["min_qty"])[0], axis=1)

    df = items_df.copy()
    if search:
        df = df[df["sku"].str.contains(search, case=False, na=False) |
                df["name"].str.contains(search, case=False, na=False)]
    if filter_mat  != "All": df = df[df["material_type"] == filter_mat]
    if filter_loc  != "All": df = df[df["storage_location"] == filter_loc]
    if filter_stat != "All": df = df[df["status"] == filter_stat]

    st.markdown(f"Showing **{len(df)}** items")

    display_cols = ["sku", "name", "category", "material_type", "storage_location", "unit", "qty", "min_qty", "status"]
    display_df = df[display_cols].rename(columns={
        "sku": "SKU", "name": "Item Name", "category": "Category",
        "material_type": "Material Type", "storage_location": "Storage Location",
        "unit": "Unit", "qty": "Current Qty", "min_qty": "Min Qty", "status": "Status"
    })

    def color_status(val):
        colors = {"In stock": "background-color:#D1FAE5;color:#065F46",
                  "Low stock": "background-color:#FEF3C7;color:#92400E",
                  "Critical": "background-color:#FEE2E2;color:#991B1B",
                  "Out of stock": "background-color:#FEE2E2;color:#991B1B"}
        return colors.get(val, "")

    styled = display_df.style.map(color_status, subset=["Status"])
    st.dataframe(styled, use_container_width=True, hide_index=True, height=420)

    # ── Delete item (admin only) ──
    if st.session_state.role == "admin":
        with st.expander("🗑️ Delete Item"):
            sku_list = items_df["sku"].tolist()
            del_sku = st.selectbox("Select SKU to delete", sku_list)
            if st.button("Delete Item", type="secondary"):
                row = items_df[items_df["sku"] == del_sku]
                if not row.empty:
                    delete_row("items", row.iloc[0]["item_id"])
                    st.cache_resource.clear()
                    st.success(f"Deleted {del_sku}")
                    st.rerun()

# ─── INBOUND ───────────────────────────────────────────────────────────────────
def inbound_page():
    st.markdown("## 📥 Inbound — Receive Stock")
    items_df = read_sheet("items")

    with st.expander("➕ Record Inbound", expanded=True):
        if items_df.empty:
            st.warning("No items in inventory. Add items first.")
        else:
            sku_options = {f"{r['sku']} — {r['name']} ({r['material_type']})": r
                           for _, r in items_df.iterrows()}
            c1, c2, c3 = st.columns(3)
            with c1:
                selected = st.selectbox("Select SKU / Item *", list(sku_options.keys()))
                item_row = sku_options[selected]
                st.caption(f"📍 Location: **{item_row.get('storage_location','')}** | Current stock: **{item_row.get('qty',0)} {item_row.get('unit','')}**")
                qty = st.number_input("Quantity Received *", min_value=1, value=1)
            with c2:
                recv_date = st.date_input("Received Date *", value=date.today())
                po_ref = st.text_input("PO / Reference No.", placeholder="e.g. PO-2025-001")
                supplier = st.text_input("Supplier / Source", placeholder="e.g. Acme Suppliers Ltd")
            with c3:
                note = st.text_area("Notes", placeholder="Optional notes...", height=80)
                st.markdown(f"**Operator:** {st.session_state.full_name}")

            if st.button("✅ Record Inbound", type="primary"):
                tx_id  = new_id("IN-")
                new_qty = int(item_row.get("qty", 0)) + qty
                ok1 = append_row("inbound", [
                    tx_id, item_row["item_id"], item_row["sku"], item_row["name"],
                    qty, str(recv_date), po_ref, supplier,
                    st.session_state.full_name, note,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ])
                ok2 = update_item_qty(item_row["item_id"], new_qty) if ok1 else False
                if ok1 and ok2:
                    st.success(f"✅ Inbound recorded! {item_row['sku']} stock: {item_row['qty']} → {new_qty} {item_row['unit']}")
                    st.cache_resource.clear()
                    st.rerun()

    st.divider()
    st.markdown("#### 📋 Inbound History")
    inbound_df = read_sheet("inbound")
    if inbound_df.empty:
        st.info("No inbound records yet.")
    else:
        cols = ["date","sku","item_name","qty","po_ref","supplier","operator","note"]
        show = inbound_df[[c for c in cols if c in inbound_df.columns]].rename(columns={
            "date":"Date","sku":"SKU","item_name":"Item","qty":"Qty",
            "po_ref":"PO Ref","supplier":"Supplier","operator":"Operator","note":"Note"
        })
        st.dataframe(show.sort_values("Date", ascending=False) if "Date" in show.columns else show,
                     use_container_width=True, hide_index=True, height=380)

# ─── OUTBOUND ──────────────────────────────────────────────────────────────────
def outbound_page():
    st.markdown("## 📤 Outbound — Dispatch Stock")
    items_df = read_sheet("items")
    items_df["qty"] = pd.to_numeric(items_df["qty"], errors="coerce").fillna(0).astype(int)

    with st.expander("➕ Record Outbound", expanded=True):
        if items_df.empty:
            st.warning("No items in inventory. Add items first.")
        else:
            sku_options = {f"{r['sku']} — {r['name']} (Stock: {r['qty']} {r['unit']})": r
                           for _, r in items_df.iterrows()}
            c1, c2, c3 = st.columns(3)
            with c1:
                selected = st.selectbox("Select SKU / Item *", list(sku_options.keys()))
                item_row = sku_options[selected]
                current_qty = int(item_row.get("qty", 0))
                st.caption(f"📍 Location: **{item_row.get('storage_location','')}** | Material: **{item_row.get('material_type','')}**")
                qty = st.number_input("Quantity to Dispatch *", min_value=1, max_value=max(1, current_qty), value=1)
                if qty > current_qty:
                    st.error(f"⚠️ Insufficient stock. Available: {current_qty}")
            with c2:
                disp_date = st.date_input("Dispatch Date *", value=date.today())
                so_ref = st.text_input("SO / Reference No.", placeholder="e.g. SO-2025-045")
                customer = st.text_input("Customer / Destination", placeholder="e.g. Client XYZ")
            with c3:
                note = st.text_area("Notes", placeholder="Optional notes...", height=80)
                st.markdown(f"**Operator:** {st.session_state.full_name}")

            if st.button("✅ Record Outbound", type="primary"):
                if qty > current_qty:
                    st.error("Cannot dispatch more than available stock.")
                else:
                    tx_id   = new_id("OUT-")
                    new_qty = current_qty - qty
                    ok1 = append_row("outbound", [
                        tx_id, item_row["item_id"], item_row["sku"], item_row["name"],
                        qty, str(disp_date), so_ref, customer,
                        st.session_state.full_name, note,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ])
                    ok2 = update_item_qty(item_row["item_id"], new_qty) if ok1 else False
                    if ok1 and ok2:
                        st.success(f"✅ Outbound recorded! {item_row['sku']} stock: {current_qty} → {new_qty} {item_row['unit']}")
                        st.cache_resource.clear()
                        st.rerun()

    st.divider()
    st.markdown("#### 📋 Outbound History")
    outbound_df = read_sheet("outbound")
    if outbound_df.empty:
        st.info("No outbound records yet.")
    else:
        cols = ["date","sku","item_name","qty","so_ref","customer","operator","note"]
        show = outbound_df[[c for c in cols if c in outbound_df.columns]].rename(columns={
            "date":"Date","sku":"SKU","item_name":"Item","qty":"Qty",
            "so_ref":"SO Ref","customer":"Customer","operator":"Operator","note":"Note"
        })
        st.dataframe(show.sort_values("Date", ascending=False) if "Date" in show.columns else show,
                     use_container_width=True, hide_index=True, height=380)

# ─── USERS (admin only) ────────────────────────────────────────────────────────
def users_page():
    st.markdown("## 👥 User Management")
    users_df = read_sheet("users")

    with st.expander("➕ Add New User", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1: new_uname = st.text_input("Username *")
        with c2: new_pass  = st.text_input("Password *", type="password")
        with c3: new_role  = st.selectbox("Role", ["operator", "admin"])
        with c4: new_fname = st.text_input("Full Name")
        if st.button("Add User", type="primary"):
            if not new_uname or not new_pass:
                st.error("Username and password required.")
            elif not users_df.empty and new_uname in users_df["username"].values:
                st.error("Username already exists.")
            else:
                ok = append_row("users", [new_uname, new_pass, new_role, new_fname])
                if ok:
                    st.success(f"User '{new_uname}' added.")
                    st.cache_resource.clear()
                    st.rerun()

    st.divider()
    st.markdown("#### Current Users")
    if users_df.empty:
        st.info("No users.")
    else:
        display = users_df[["username","full_name","role"]].rename(columns={
            "username":"Username","full_name":"Full Name","role":"Role"
        })
        st.dataframe(display, use_container_width=True, hide_index=True)

# ─── Entry Point ───────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    login_page()
else:
    main_app()
