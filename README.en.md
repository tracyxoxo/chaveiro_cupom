# 🔑 Chaveiro Brotero - Receipt System

> **Português:** [Ler em português](README.md)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg) ![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Complete system for issuing fiscal receipts with ESC/POS printer integration, electronic service invoice (NFSe) issuance, and cloud storage**

[Features](#-features) • [Installation](#-installation) • [Configuration](#-configuration) • [Usage](#-usage) • [Documentation](#-documentation)

---

## Screenshots

![Initial Screen]()

<!-- 
Example of how to add screenshots:
![Main Screen](docs/screenshots/main-screen.png)
![History](docs/screenshots/history.png)
![NFSe Issuance](docs/screenshots/nfse.png)
-->

## Features

### 🧾 Receipt Issuance
-  Modern, responsive web interface
-  Support for multiple items per receipt
-  Automatic total calculation
-  Preview before issuing
-  Direct printing to ESC/POS printers
-  Automatic saving to .txt file

### 🏥 Custom Receipts
-  Special mode for customizable services
-  Required field for work order number
-  Different formatting on the receipt
-  Period-specific reports

### 📄 Electronic Service Invoice (NFSe)
-  Automatic NFSe issuance via NFSe.gov.br portal
-  Automatic lookup of customer legal name
-  DANFSE PDF generation
-  Automatic upload to Google Drive
-  Public link for sharing
-  WhatsApp integration for sending to customer
-  File name format: `DANFSE_RAZAOSOCIAL_data.pdf`

### 📊 History and Reports
-  Full history of all issued receipts
-  Paginated history view
-  Receipt cancellation
-  Reports by period
-  Daily cash closing
-  Custom reports for work-order services
-  HTML export for print/PDF

### 🎨 Interface
-  Modern, intuitive design
-  Dark/light mode
-  Responsive (works on tablets and phones)
-  Visual feedback on all actions
-  History with visual badges (Standard/Custom/NFSe)

## Installation

### Prerequisites

- Python 3.10 or higher
- ESC/POS printer (optional, for physical printing)
- NFSe.gov.br portal account (optional, for issuing invoices)
- Google account with Google Drive (optional, for PDF storage)

### Step by Step

1. **Clone the repository**
   ```bash
   git clone https://github.com/seu-usuario/chaveiro_cupom.git
   cd chaveiro_cupom
   ```

2. **Create a virtual environment**
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # Linux/Mac
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r app/requirements.txt
   ```

4. **Configure environment variables**
   
   Copy the `.env.example` file and configure as needed:
   ```bash
   # Windows
   copy .env.example .env

   # Linux/Mac
   cp .env.example .env
   ```

   Edit the `.env` file or set environment variables directly.

## ⚙️ Configuration

### 1. Receipt History (Optional)

Configure the directory where history will be saved. A cloud-synced folder (OneDrive, Dropbox, etc.) is recommended:

```bash
# Windows
set HISTORICO_CUPONS_DIR=C:\Users\YourUser\OneDrive\Chaveiro

# Linux/Mac
export HISTORICO_CUPONS_DIR=/home/user/Dropbox/Chaveiro
```

**File**: `app/history.py` (line 16)

### 2. Google Drive (Optional - for NFSe upload)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API
4. Go to **APIs & Services > Credentials**
5. Create an **OAuth 2.0 Client ID** of type **Desktop app**
6. Download the JSON file and save it as `app/client_secrets.json`
7. Configure the Drive folder in `app/drive_upload.py` (line 60)

**Note**: On first run, the system will open the browser for authorization. A `token.json` file will be created automatically.

### 3. NFSe - Electronic Service Invoice (Optional)

Configure your NFSe.gov.br portal credentials:

```bash
# Windows
set NFSE_INSCRICAO=your_registration_number
set NFSE_SENHA=your_password
set NFSE_SERVICO_ID=favorite_service_id

# Linux/Mac
export NFSE_INSCRICAO=your_registration_number
export NFSE_SENHA=your_password
export NFSE_SERVICO_ID=favorite_service_id
```

**File**: `app/nfse_service.py` (lines 31-33)

**Important**: You must have a favorite service registered on the NFSe.gov.br portal. The service ID can be found after registering it.

📖 **Full guide**: See [NFSE_SETUP.md](NFSE_SETUP.md) for more details.

### 4. ESC/POS Printer (Optional)

The system auto-detects compatible USB printers. If needed, configure manually:

```bash
set USB_VENDOR_ID=0x04e8
set USB_PRODUCT_ID=0x0202
set PRINTER_BACKEND=usb
```

##   Usage

### Starting the Server

**Windows:**
```bash
start_chaveiro.bat
```

**Linux/Mac:**
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The system will open at `http://127.0.0.1:8000`

### Issuing a Receipt

1. Open the web interface
2. Fill in the receipt items:
   - Service description
   - Quantity
   - Unit price
3. (Optional) Check "Custom service" and enter the work order number
4. (Optional) Check "Issue Invoice (NFSe)" and enter the customer's CPF/CNPJ
5. Click "Preview" to see how the receipt will look
6. Click "Issue receipt" to print and save

### Issuing NFSe

1. Check the "Issue Invoice (NFSe)" option
2. Enter the customer's CPF or CNPJ (with or without formatting)
3. (Optional) Check "Print invoice on printer" for a physical copy
4. Click "Issue receipt"
5. After issuance you will have:
   - DANFSE PDF available for download
   - Google Drive link (if configured)
   - Button to send via WhatsApp

### Viewing History

- History appears automatically on the main page
- Use "Load more" to see older receipts
- Click "Details" for full information
- Use "Cancel" to cancel a receipt (sets status to CANCELLED)

### Reports

1. Click "Reports" in the side menu
2. Choose the report type:
   - **By Period**: Filter by start/end date and status
   - **Cash Closing**: Report for the current day
   - **Custom Closing**: Report for work-order services
3. View results and export to HTML/PDF with Ctrl+P

## 📁 Project Structure

```
chaveiro_cupom/
├── app/
│   ├── static/
│   │   └── style.css          # CSS styles
│   ├── templates/
│   │   ├── index.html         # Main interface
│   │   └── relatorios.html    # Reports page
│   ├── cupom_core.py          # Receipt formatting logic
│   ├── drive_upload.py        # Google Drive integration
│   ├── history.py             # History management
│   ├── main.py                # Main FastAPI application
│   ├── nfse_client.py         # HTTP client for NFSe.gov.br
│   ├── nfse_service.py        # NFSe issuance service
│   ├── printer.py             # ESC/POS printer integration
│   ├── requirements.txt       # Python dependencies
│   └── client_secrets.json    # Google OAuth credentials (not versioned)
├── _cupons/                   # Standard receipts saved (.txt)
├── _nfse/                     # Temporary NFSe PDFs
├── arquitetura.md             # Architecture documentation
├── NFSE_SETUP.md             # NFSe configuration guide
├── .env.example              # Environment variables example
├── start_chaveiro.bat        # Startup script (Windows)
└── README.md                  # This file
```

##  Technologies

- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern, fast web framework
- **[Uvicorn](https://www.uvicorn.org/)** - ASGI server
- **[Jinja2](https://jinja.palletsprojects.com/)** - Template engine
- **[BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)** - HTML parsing (NFSe)
- **[Requests](https://requests.readthedocs.io/)** - HTTP client
- **[Google API Python Client](https://github.com/googleapis/google-api-python-client)** - Google Drive integration
- **[Python ESC/POS](https://github.com/python-escpos/python-escpos)** - Printer communication

##  Documentation

- **[System Architecture](arquitetura.md)** - Full technical documentation
- **[NFSe Configuration](NFSE_SETUP.md)** - Step-by-step NFSe setup guide

## Security

- Sensitive credentials must not be committed to the repository
- Use environment variables for sensitive configuration
- The `token.json` file (Google OAuth) is generated automatically and must not be shared
- The `client_secrets.json` file contains OAuth credentials and must not be versioned

## Troubleshooting

### Printer does not print
- Check that the printer is connected and powered on
- Try unplugging and reconnecting the USB cable
- The system will save the receipt to a .txt file even if the printer fails

### NFSe does not issue
- Verify that credentials are correct
- Confirm that the favorite service is registered on the portal
- Check the console logs for specific error messages
- The receipt will be issued normally even if NFSe fails

### Google Drive does not upload
- Verify that the `client_secrets.json` file is present
- Confirm that the Google Drive API is enabled
- Check that the Drive folder is configured correctly
- On first run, authorize access when the browser opens

### History does not appear
- Verify that the configured directory exists and has write permissions
- Confirm that the `historico_cupons.json` file can be created/written

## Contributing

Contributions are welcome! Feel free to:

1. Fork the project
2. Create a branch for your feature (`git checkout -b feature/MyFeature`)
3. Commit your changes (`git commit -m 'Add MyFeature'`)
4. Push to the branch (`git push origin feature/MyFeature`)
5. Open a Pull Request

## 📝 License

This project is under the MIT license. See the `LICENSE` file for details.

## 👤 Author

**Matheus Silvestre**

---

<div align="center">

**⭐ If this project was useful to you, consider giving it a star! ⭐**

Made with ❤️ to simplify fiscal receipt management

</div>
