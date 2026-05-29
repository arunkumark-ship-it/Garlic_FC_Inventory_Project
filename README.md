# 📦 Inventory Manager — Streamlit + Google Sheets

A full-featured inventory management app with:
- 🔐 Login page (admin / operator roles)
- 📦 SKU & material type differentiation
- 📥 Inbound (receive stock) with operator tracking
- 📤 Outbound (dispatch stock) with operator tracking
- 📊 Dashboard with low-stock alerts & charts
- ☁️ All data stored in Google Sheets

---

## 🚀 Setup Instructions

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create a Google Sheet
- Go to [sheets.google.com](https://sheets.google.com)
- Create a new blank spreadsheet
- Name it exactly: **`Inventory Manager`**
- The app will auto-create these tabs on first run:
  - `users`, `items`, `inbound`, `outbound`

### 3. Set up Google Cloud Service Account
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project (or use existing)
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **IAM & Admin → Service Accounts → Create Service Account**
5. Download the JSON key file
6. **Share your Google Sheet** with the service account email (give Editor access)

### 4. Configure secrets
Create `.streamlit/secrets.toml` and fill in your service account values:
```toml
[google_sheets]
spreadsheet_name = "Inventory Manager"

[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email = "your-sa@your-project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

### 5. Run the app
```bash
streamlit run app.py
```

---

## 🔑 Default Login
| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Admin |
| `operator1` | `pass123` | Operator |

> **Admin** can: add/delete items, manage users, record inbound & outbound
> **Operator** can: record inbound & outbound, view dashboard

---

## 📋 SKU Naming Convention (suggested)
| Prefix | Material Type | Example |
|--------|--------------|---------|
| `RAW-` | Raw Material | `RAW-ST-001` (Steel) |
| `SFG-` | Semi-Finished | `SFG-WD-012` |
| `FGD-` | Finished Goods | `FGD-WGT-001` |
| `PKG-` | Packaging | `PKG-BOX-05` |
| `ELC-` | Electronics | `ELC-PCB-102` |
| `HWR-` | Hardware | `HWR-BLT-045` |
| `CON-` | Consumables | `CON-GLS-007` |
| `SPR-` | Spare Parts | `SPR-MTR-022` |

---

## 🗂️ Google Sheet Structure

### `users` tab
| username | password | role | full_name |

### `items` tab
| item_id | sku | name | category | material_type | storage_location | unit | qty | min_qty | created_at |

### `inbound` tab
| tx_id | item_id | sku | item_name | qty | date | po_ref | supplier | operator | note | timestamp |

### `outbound` tab
| tx_id | item_id | sku | item_name | qty | date | so_ref | customer | operator | note | timestamp |

---

## ☁️ Deploy to Streamlit Cloud
1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo
4. Add secrets under **App Settings → Secrets** (paste your secrets.toml content)
