# Windows Log Gathering Agent

A modern, enterprise-level Windows log collection and analysis system with real-time monitoring, AI-powered analysis, and a beautiful React frontend.

![System Architecture](https://img.shields.io/badge/Architecture-MCP%20Based-blue)
![Frontend](https://img.shields.io/badge/Frontend-React%2018%20%2B%20TypeScript-61dafb)
![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20Python-green)
![AI Analysis](https://img.shields.io/badge/AI-Local%20LLM%20Integration-orange)

## ✨ Features

### 🔍 **Real-time Log Analysis**
- Live log collection from Windows systems via WinRM/PowerShell
- SMB-based log file access for historical data
- Real-time system monitoring with CPU and memory metrics
- Automated log categorization and filtering

### 🤖 **AI-Powered Analysis**
- Local LLM integration for intelligent log analysis
- Context-aware analysis for different log types (CBS, Windows Update, Event Logs)
- Automated error detection and actionable recommendations
- Support for multiple LLM endpoints (OpenAI-compatible)

### 🎨 **Modern Web Interface**
- Beautiful React 18 + TypeScript frontend
- Dark theme with orange accent colors and glass morphism effects
- Real-time log viewer with autoscroll functionality
- Interactive system status monitoring
- Responsive design for desktop and mobile

### 🏗️ **MCP Architecture**
- Model Context Protocol (MCP) based design
- Separate PowerShell and SMB MCP servers
- Modular and scalable architecture
- Easy integration with external systems

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  React Frontend │    │   FastAPI API    │    │  LLM Analyzer   │
│  ├─ Dashboard   │◄──►│  ├─ REST Routes  │◄──►│  ├─ Local LLM   │
│  ├─ Live Logs   │    │  ├─ WebSocket    │    │  ├─ Analysis    │
│  └─ Chat UI     │    │  └─ Health Check │    │  └─ Results     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   MCP Servers    │    │   LLM Endpoint  │
                       │  ├─ PowerShell   │    │  (Local Model)  │
                       │  └─ SMB Server   │    │                 │
                       └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Windows Clients  │
                       │  ├─ CBS Logs     │
                       │  ├─ Event Logs   │
                       │  └─ System Info  │
                       └──────────────────┘
```

## 🚀 Installation

### 1. Repository Setup
```bash
git clone <repository>
cd loggatheringagent
```

### 2. Python Environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -e .
```

### 3. MCP Server Dependencies
```bash
# PowerShell MCP Server
pip install -r mcp_servers/powershell_server/requirements.txt

# SMB MCP Server  
pip install -r mcp_servers/smb_server/requirements.txt
```

### 4. Konfiguration
Bearbeiten Sie `src/loggatheringagent/config/machines.yaml`:

```yaml
credentials:
  domain_admin:
    username: "DOMAIN\\admin"
    password: "your_password"  # Verwenden Sie Umgebungsvariablen in Produktion
    domain: "COMPANY.LOCAL"

clients:
  - name: "CLIENT-01"
    hostname: "client-01.company.local"
    ip: "192.168.1.100"
    credentials: "domain_admin"
    log_paths:
      sccm_logs:
        - "C$/Windows/CCM/Logs/WUAHandler.log"
        - "C$/Windows/CCM/Logs/CAS.log"
      system_logs:
        - "C$/Windows/Logs/CBS/CBS.log"
    powershell_commands:
      - "Get-WindowsUpdateLog"
      - "Get-WinEvent -LogName System -MaxEvents 100"

llm_config:
  endpoint: "http://localhost:11434/v1"  # Ollama
  model: "llama3.1:8b"
  max_tokens: 4000
  temperature: 0.1
```

## 📋 Verwendung

### CLI Interface
```bash
# Server starten
loggatheringagent serve

# Clients auflisten
loggatheringagent list-clients

# Einzelnen Client analysieren
loggatheringagent analyze CLIENT-01

# Alle Clients analysieren
loggatheringagent analyze

# Connectivity testen
loggatheringagent test-connection CLIENT-01

# Konfiguration verwalten
loggatheringagent config --show
loggatheringagent config --validate
```

### REST API
```bash
# Server starten
loggatheringagent serve --host 0.0.0.0 --port 8000

# API Endpoints:
curl http://localhost:8000/clients
curl -X POST http://localhost:8000/analyze -H "Content-Type: application/json" -d '{"client_names": ["CLIENT-01"]}'
curl http://localhost:8000/analyze/{request_id}
```

### Web Interface
Öffnen Sie `http://localhost:8000` für die einfache Web-Oberfläche.

### Chat Interface
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze CLIENT-01 for Windows Update issues"}'
```

## 🔧 MCP Server Setup

### PowerShell MCP Server
```bash
cd mcp_servers/powershell_server
python server.py
```

### SMB MCP Server
```bash
cd mcp_servers/smb_server
python server.py
```

## 🎛️ Konfiguration

### Umgebungsvariablen
```bash
# .env Datei
LGA_CONFIG_FILE=path/to/machines.yaml
LGA_LOG_TAIL_LINES=1000
LGA_API_HOST=0.0.0.0
LGA_API_PORT=8000
LGA_DEBUG=false
```

### Windows-Berechtigungen
Stellen Sie sicher, dass der verwendete Account folgende Berechtigungen hat:
- **SMB**: Lesezugriff auf `C$` Shares der Ziel-Clients
- **WinRM**: PowerShell Remoting aktiviert und Zugriff konfiguriert
- **Domain**: Domain-Admin oder entsprechende delegierte Berechtigungen

### WinRM Setup auf Ziel-Clients
```powershell
# Auf Ziel-Clients ausführen
Enable-PSRemoting -Force
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
Restart-Service WinRM
```

## 📊 Log-Analyse Features

### Unterstützte Log-Typen
- **SCCM WUAHandler.log**: Windows Update Agent Handler Logs
- **SCCM CAS.log**: Content Access Service Logs  
- **CBS.log**: Component-Based Servicing Logs
- **Windows Update Logs**: Via `Get-WindowsUpdateLog` Cmdlet
- **Event Logs**: System/Application Events

### LLM-Analyse
- Identifiziert Fehler und Warnungen
- Kategorisiert Schweregrade (Info/Warning/Error/Critical)
- Generiert actionable Empfehlungen
- Erstellt Zusammenfassungen für mehrere Clients

### Ausgabe-Format
```json
{
  "client_name": "CLIENT-01",
  "overall_status": "issues",
  "summary": "Windows Update installation failures detected...",
  "action_items": [
    "Clear Windows Update cache",
    "Restart BITS service"
  ],
  "log_analyses": [
    {
      "source": "SMB:C$/Windows/CCM/Logs/WUAHandler.log",
      "severity": "error",
      "issues_found": ["Update installation timeout"],
      "recommendations": ["Increase timeout values"],
      "confidence": 0.85
    }
  ]
}
```

## 🐛 Troubleshooting

### Häufige Probleme

**SMB-Verbindung schlägt fehl:**
- Überprüfen Sie Netzwerk-Connectivity
- Validieren Sie Credentials und Domain-Konfiguration
- Stellen Sie sicher, dass Admin-Shares aktiviert sind

**PowerShell-Verbindung schlägt fehl:**
- Überprüfen Sie WinRM-Konfiguration auf Ziel-Client
- Validieren Sie Firewall-Einstellungen (Port 5985/5986)
- Testen Sie mit `Test-WSMan -ComputerName <client>`

**LLM-Analyse schlägt fehl:**
- Überprüfen Sie LLM-Endpoint Verfügbarkeit
- Validieren Sie Model-Konfiguration
- Prüfen Sie Token-Limits und Timeout-Einstellungen

### Debug-Modus
```bash
LGA_DEBUG=true loggatheringagent serve
```

## 🤝 Entwicklung

### Projektstruktur
```
loggatheringagent/
├── src/loggatheringagent/
│   ├── core/                 # Kernlogik
│   ├── mcp_clients/         # MCP Client Implementierungen
│   ├── api/                 # FastAPI Server
│   ├── config/              # Konfiguration
│   └── cli.py               # CLI Interface
├── mcp_servers/             # MCP Server Implementierungen
│   ├── powershell_server/
│   └── smb_server/
└── tests/                   # Test Suite
```

### Code-Style
```bash
black --line-length 100 src/
isort --profile black src/
flake8 src/
mypy src/
```

### Tests
```bash
pytest tests/
```

## 📄 Lizenz

MIT License - siehe LICENSE Datei für Details.

## 🆘 Support

Bei Problemen oder Fragen:
1. Prüfen Sie die Troubleshooting-Sektion
2. Aktivieren Sie Debug-Modus für detaillierte Logs
3. Erstellen Sie ein Issue mit Log-Ausgaben