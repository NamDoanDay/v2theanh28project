"""
LAN Server module for Multi-PC Driving License Dossier Lookup.
Provides FastAPI REST API, PDF/Excel streaming, and Web Client for local network.
"""
import os
import io
import socket
import threading
import time
from typing import Optional, Dict, Any, List

import uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
import qrcode

from src.database import DatabaseManager
from src.config import PROVINCE_CODES, get_resource_path
from src.logger import get_logger

logger = get_logger(__name__)

def get_lan_ip() -> str:
    """
    Detects the primary LAN IP address of this machine.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Dummy connect to determine outgoing interface
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# Initialize FastAPI application
app = FastAPI(
    title="Hệ Thống Tra Cứu GPLX Mạng LAN",
    description="Máy chủ tra cứu hồ sơ GPLX nội bộ dùng cho mạng LAN văn phòng",
    version="1.0.0"
)

# Enable CORS for cross-origin LAN clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_manager = DatabaseManager()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
INDEX_HTML_PATH = get_resource_path(os.path.join("src", "server", "static", "index.html"))
if not os.path.exists(INDEX_HTML_PATH):
    INDEX_HTML_PATH = os.path.join(STATIC_DIR, "index.html")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the standalone Web Client for LAN users."""
    if os.path.exists(INDEX_HTML_PATH):
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Hệ thống Tra cứu GPLX - Mạng LAN</h1><p>Đang khởi tạo giao diện web...</p>"

@app.get("/api/status")
async def get_status():
    """Returns server status, LAN IP, and database statistics."""
    stats = db_manager.get_stats()
    ip = get_lan_ip()
    return {
        "status": "online",
        "ip": ip,
        "port": getattr(app.state, "port", 8080),
        "url": f"http://{ip}:{getattr(app.state, 'port', 8080)}",
        "stats": stats,
        "message": "Máy chủ mạng LAN đang hoạt động ổn định"
    }

@app.get("/api/provinces")
async def get_provinces():
    """Returns list of provinces present in the system."""
    code_to_name = {p["code"]: p["name"] for p in PROVINCE_CODES if "code" in p}
    provinces_list = []
    # Query distinct province codes from dossiers
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT province_code FROM dossiers ORDER BY province_code ASC")
        rows = cursor.fetchall()
        for r in rows:
            code = str(r[0])
            name = code_to_name.get(code, f"Tỉnh {code}")
            provinces_list.append({"code": code, "name": name})
    
    # If empty, provide default from configuration
    if not provinces_list:
        for p in PROVINCE_CODES[:15]:
            provinces_list.append({"code": p.get("code", "01"), "name": p.get("name", "Hà Nội")})

    return {"provinces": provinces_list}

@app.get("/api/search")
async def search_citizens(
    q: str = Query("", description="Từ khóa tìm kiếm (Họ tên, Số bằng, Năm sinh)"),
    province: str = Query("all", description="Mã tỉnh hoặc 'all'"),
    limit: int = Query(50, ge=1, le=200, description="Số lượng kết quả tối đa")
):
    """Searches citizens using fast FTS5 SQLite index."""
    start_time = time.time()
    results = db_manager.search(query=q, province_code=province, limit=limit)
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return {
        "query": q,
        "province": province,
        "total": len(results),
        "latency_ms": elapsed_ms,
        "results": results
    }

@app.get("/api/pdf")
async def stream_pdf(path: str = Query(..., description="Đường dẫn tuyệt đối hoặc tương đối tới file PDF")):
    """
    Streams PDF file safely over LAN for browser viewing with page jumping support.
    """
    if not os.path.isfile(path) or not path.lower().endswith(".pdf"):
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp PDF hoặc định dạng không hợp lệ.")
    
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=os.path.basename(path),
        content_disposition_type="inline",
        headers={"Accept-Ranges": "bytes"},
    )

@app.get("/api/excel")
async def download_excel(path: str = Query(..., description="Đường dẫn tới file Excel tương ứng")):
    """
    Serves the companion Excel file for downloading by LAN client PCs.
    """
    if not os.path.isfile(path) or not path.lower().endswith(".xlsx"):
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp Excel.")
    
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(path),
    )

@app.get("/api/qr")
async def get_qr_code(url: Optional[str] = None):
    """
    Generates and returns a PNG QR code pointing to the LAN access URL.
    """
    port = getattr(app.state, "port", 8080)
    target_url = url or f"http://{get_lan_ip()}:{port}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=2,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1E293B", back_color="#FFFFFF")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    
    return Response(content=buf.getvalue(), media_type="image/png")


class LANServerManager:
    """
    Manages the lifecycle of the LAN FastAPI server in a background thread.
    Allows easy start/stop directly from the Tkinter GUI.
    """
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.server: Optional[uvicorn.Server] = None
        self.thread: Optional[threading.Thread] = None
        self.is_running = False

    def start(self, port: Optional[int] = None) -> str:
        """Starts the server in background thread if not already running."""
        if self.is_running:
            return self.get_url()

        if port:
            self.port = port

        logger.info("Starting LAN server on %s:%s", self.host, self.port)
        app.state.port = self.port
        app.state.host = self.host

        config = uvicorn.Config(
            app=app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
            # Windowed PyInstaller builds have sys.stdout/sys.stderr=None;
            # Uvicorn's default formatter calls sys.stdout.isatty().
            log_config=None,
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        self.is_running = True

        # Give it a brief moment to bind socket
        time.sleep(0.5)
        logger.info("LAN server thread started; access URL: %s", self.get_url())
        return self.get_url()

    def stop(self):
        """Stops the running server."""
        if self.server and self.is_running:
            logger.info("Stopping LAN server on port %s", self.port)
            self.server.should_exit = True
            self.is_running = False
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2.0)
            self.server = None
            self.thread = None
            logger.info("LAN server stopped")

    def get_lan_ip(self) -> str:
        return get_lan_ip()

    def get_url(self) -> str:
        return f"http://{self.get_lan_ip()}:{self.port}"


# Global server manager singleton
lan_server = LANServerManager()
