# from PySide6.QtCore import QProcess
# from PySide6.QtGui import QIcon
# from PySide6.QtCore import QProcessEnvironment
# import subprocess
# import sys
# from pathlib import Path
# from PySide6.QtWidgets import (
#     QMainWindow,
#     QWidget,
#     QVBoxLayout,
#     QHBoxLayout,
#     QPushButton,
#     QLabel,
#     QTextEdit
# )
# from datetime import datetime

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QTabWidget,
)

import subprocess
import sys
from pathlib import Path
from datetime import datetime


BASE_DIR = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent.parent
)

ICON_PATH = BASE_DIR / "assets" / "icon.ico"


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("SigCorp IA")
        self.resize(1200, 700)
        self.setWindowIcon(QIcon(str(ICON_PATH)))

        # --------------------------------------------------
        # Processos
        # --------------------------------------------------

        self.worker = QProcess()
        self.api = QProcess()

        self._configurar_processo(self.worker, "WORKER")
        self._configurar_processo(self.api, "API")

        # --------------------------------------------------
        # Layout Principal
        # --------------------------------------------------

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ==================================================
        # HEADER: Controles Worker e API Lado a Lado
        # ==================================================
        header_layout = QHBoxLayout()

        # --------------------------------------------------
        # Bloco Worker (Esquerda)
        # --------------------------------------------------
        worker_section = QVBoxLayout()
        self.status_worker = QLabel("Worker: 🔴 Offline")
        
        worker_btns = QHBoxLayout()
        self.btn_start_worker = QPushButton("▶ Iniciar Worker")
        self.btn_stop_worker = QPushButton("🟥 Parar Worker")
        self.btn_clear_worker = QPushButton("🗑 Limpar Worker")

        self.btn_stop_worker.setEnabled(False)

        # Conexões Worker
        self.btn_start_worker.clicked.connect(self.start_worker)
        self.btn_stop_worker.clicked.connect(self.stop_worker)
        self.btn_clear_worker.clicked.connect(self.logs_worker_clear)

        worker_btns.addWidget(self.btn_start_worker)
        worker_btns.addWidget(self.btn_stop_worker)
        worker_btns.addWidget(self.btn_clear_worker)

        worker_section.addWidget(self.status_worker)
        worker_section.addLayout(worker_btns)

        # --------------------------------------------------
        # Bloco API (Direita)
        # --------------------------------------------------
        api_section = QVBoxLayout()
        self.status_api = QLabel("API: 🔴 Offline")

        api_btns = QHBoxLayout()
        self.btn_start_api = QPushButton("▶ Iniciar API")
        self.btn_stop_api = QPushButton("🟥 Parar API")
        self.btn_clear_api = QPushButton("🗑 Limpar API")

        self.btn_stop_api.setEnabled(False)

        # Conexões API
        self.btn_start_api.clicked.connect(self.start_api)
        self.btn_stop_api.clicked.connect(self.stop_api)
        self.btn_clear_api.clicked.connect(self.logs_api_clear)

        api_btns.addWidget(self.btn_start_api)
        api_btns.addWidget(self.btn_stop_api)
        api_btns.addWidget(self.btn_clear_api)

        api_section.addWidget(self.status_api)
        api_section.addLayout(api_btns)

        # Adicionando Blocos ao Header
        header_layout.addLayout(worker_section)
        header_layout.addSpacing(30) # Espaçamento entre os dois painéis
        header_layout.addLayout(api_section)

        # ==================================================
        # LOGS E ABAS
        # ==================================================

        self.logs_monitor = QTextEdit()
        self.logs_worker = QTextEdit()
        self.logs_api = QTextEdit()

        for log in (self.logs_monitor, self.logs_worker, self.logs_api):
            log.setReadOnly(True)
            log.setStyleSheet("""
                QTextEdit{
                    background:#0d1117;
                    color:white;
                    border:1px solid #30363d;
                    font-family:Consolas;
                    font-size:11pt;
                }
            """)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.logs_monitor, "Sistema")
        self.tabs.addTab(self.logs_worker, "Worker")
        self.tabs.addTab(self.logs_api, "API")

        # --------------------------------------------------
        # Botão Limpar Monitor (No canto da barra de abas)
        # --------------------------------------------------
        self.btn_clear_monitor = QPushButton("🗑 Limpar Monitor")
        self.btn_clear_monitor.clicked.connect(self.logs_monitor_clear)
        self.tabs.setCornerWidget(self.btn_clear_monitor, Qt.TopRightCorner)

        # --------------------------------------------------
        # Montagem Final do Layout
        # --------------------------------------------------
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.tabs)

        central.setLayout(main_layout)


    # ======================================================
    # Funções de Limpeza de Logs
    # ======================================================

    def logs_worker_clear(self):
        self.logs_worker.clear()

    def logs_api_clear(self):
        self.logs_api.clear()

    def logs_monitor_clear(self):
        self.logs_monitor.clear()

    # ======================================================
    # Configuração Processo
    # ======================================================

    def _configurar_processo(self, process, nome):

        process.readyReadStandardOutput.connect(
            lambda p=process: self.read_stdout(p)
        )

        process.readyReadStandardError.connect(
            lambda p=process: self.read_stderr(p)
        )

        process.finished.connect(
            lambda *_,
            p=process,
            n=nome: self.process_finished(p, n)
        )

    # ======================================================
    # Inicialização
    # ======================================================

    def _start(self, process, exe, nome):

        if process.state() == QProcess.Running:
            return

        arquivo = BASE_DIR / exe

        self.add_log(f"{nome} -> {arquivo}")

        if not arquivo.exists():
            self.add_log(f"{exe} não encontrado", "ERROR")
            return

        env = QProcessEnvironment.systemEnvironment()

        env.remove("_PYI_ARCHIVE_FILE")
        env.remove("_PYI_APPLICATION_HOME_DIR")
        env.remove("_MEIPASS2")

        process.setProcessEnvironment(env)
        process.start(str(arquivo))

        if process.waitForStarted(3000):

            self.add_log(f"{nome} iniciado. PID {process.processId()}")

            if nome == "WORKER":
                self.status_worker.setText("Worker: 🟢 Online")
                self.btn_start_worker.setEnabled(False)
                self.btn_stop_worker.setEnabled(True)
            else:
                self.status_api.setText("API: 🟢 Online")
                self.btn_start_api.setEnabled(False)
                self.btn_stop_api.setEnabled(True)
        else:
            self.add_log(f"Falha ao iniciar {nome}", "ERROR")

    # ======================================================
    # Encerramento
    # ======================================================

    def _stop(self, process, nome):

        pid = process.processId()

        if pid <= 0:
            return

        self.add_log(f"Finalizando {nome} ({pid})")

        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True
        )

        process.close()

        if nome == "WORKER":
            self.status_worker.setText("Worker: 🔴 Offline")
            self.btn_start_worker.setEnabled(True)
            self.btn_stop_worker.setEnabled(False)
        else:
            self.status_api.setText("API: 🔴 Offline")
            self.btn_start_api.setEnabled(True)
            self.btn_stop_api.setEnabled(False)

    # ======================================================
    # Botões de Processo
    # ======================================================

    def start_worker(self):
        self._start(self.worker, "SigCorpInterpretador.exe", "WORKER")

    def stop_worker(self):
        self._stop(self.worker, "WORKER")

    def start_api(self):
        self._start(self.api, "SigCorpAPI.exe", "API")

    def stop_api(self):
        self._stop(self.api, "API")

    # ======================================================
    # Processo Finalizado
    # ======================================================

    def process_finished(self, process, nome):

        self.add_log(f"{nome} encerrado")

        if nome == "WORKER":
            self.status_worker.setText("Worker: 🔴 Offline")
            self.btn_start_worker.setEnabled(True)
            self.btn_stop_worker.setEnabled(False)
        else:
            self.status_api.setText("API: 🔴 Offline")
            self.btn_start_api.setEnabled(True)
            self.btn_stop_api.setEnabled(False)

    # ======================================================
    # STDOUT
    # ======================================================

    def read_stdout(self, process):

        data = process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="ignore")

        if not text.strip():
            return

        if process == self.worker:
            self.logs_worker.append(text.rstrip())
        elif process == self.api:
            self.logs_api.append(text.rstrip())

    # ======================================================
    # STDERR
    # ======================================================

    def read_stderr(self, process):

        data = process.readAllStandardError()
        text = bytes(data).decode("utf-8", errors="ignore")

        if not text.strip():
            return

        if process == self.worker:
            self.logs_worker.append(text.rstrip())
        elif process == self.api:
            self.logs_api.append(text.rstrip())

    # ======================================================
    # Log do Monitor
    # ======================================================

    def add_log(self, message, level="INFO"):

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logs_monitor.append(f"[{timestamp}] [{level}] ➔ {message}")









# BASE_DIR = Path(__file__).resolve().parent.parent

# ICON_PATH = BASE_DIR / "assets" / "icon.ico"


# class MainWindow(QMainWindow):

#     def __init__(self):
#         super().__init__()

#         self.setWindowTitle("SigCorp IA")
#         self.resize(1200, 700)

#         self.setWindowIcon(QIcon(str(ICON_PATH)))

#         self.process = QProcess()

#         self.process.readyReadStandardOutput.connect(
#             self.read_stdout
#         )

#         self.process.readyReadStandardError.connect(
#             self.read_stderr
#         )

#         self.process.finished.connect(
#             self.process_finished
#         )

#         central = QWidget()
#         self.setCentralWidget(central)

#         layout = QVBoxLayout()

#         self.status = QLabel("🔴 Offline")

#         self.btn_start = QPushButton("Iniciar")
#         self.btn_stop = QPushButton("Parar")

#         self.btn_stop.setEnabled(False)

#         self.btn_start.clicked.connect(self.start_app)
#         self.btn_stop.clicked.connect(self.stop_app)

#         buttons = QHBoxLayout()
#         buttons.addWidget(self.btn_start)
#         buttons.addWidget(self.btn_stop)

#         self.logs = QTextEdit()
#         self.logs.setReadOnly(True)

#         self.logs.setStyleSheet("""
#             QTextEdit {
#                 background-color: #0d1117;
#                 color: #ffffff;
#                 border: 1px solid #30363d;
#                 font-family: Consolas;
#                 font-size: 11pt;
#             }
#         """)

#         layout.addWidget(self.status)
#         layout.addLayout(buttons)
#         layout.addWidget(self.logs)

#         central.setLayout(layout)

#     def start_app(self):

#         if self.process.state() == QProcess.Running:
#             return

#         worker = Path("SigCorpWorker.exe").resolve()

#         self.add_log(
#             f"Launcher: {sys.executable}"
#         )

#         self.add_log(
#             f"Pasta atual: {Path.cwd()}"
#         )

#         self.add_log(
#             f"Worker: {worker}"
#         )

#         if not worker.exists():

#             self.add_log(
#                 "SigCorpWorker.exe não encontrado",
#                 "ERROR"
#             )

#             return
        
#         env = QProcessEnvironment.systemEnvironment()

#         env.remove("_PYI_ARCHIVE_FILE")
#         env.remove("_PYI_APPLICATION_HOME_DIR")
#         env.remove("_MEIPASS2")

#         self.process.setProcessEnvironment(env)

#         self.process.start(str(worker))

#         self.process.waitForStarted()

#         self.add_log(
#                 f"PID iniciado: {self.process.processId()}"
#                 )

#         if self.process.waitForStarted(3000):

#             self.add_log(
#                 "Serviço iniciado com sucesso"
#             )

#             self.status.setText("🟢 Online")

#             self.btn_start.setEnabled(False)
#             self.btn_stop.setEnabled(True)

#         else:

#             self.add_log(
#                 "Falha ao iniciar serviço",
#                 "ERROR"
#             )

#     def stop_app(self):

#         pid = self.process.processId()

#         if pid <= 0:
#             self.add_log("Nenhum processo em execução")
#             return

#         self.add_log(
#             f"Finalizando PID {pid}"
#         )

#         try:

#             resultado = subprocess.run(
#                 [
#                     "taskkill",
#                     "/F",
#                     "/T",
#                     "/PID",
#                     str(pid)
#                 ],
#                 capture_output=True,
#                 text=True
#             )

#             if resultado.stdout:
#                 self.add_log(resultado.stdout.strip())

#             if resultado.stderr:
#                 self.add_log(resultado.stderr.strip(), "ERROR")

#         except Exception as e:

#             self.add_log(
#                 f"Erro ao finalizar processo: {e}",
#                 "ERROR"
#             )

#         self.process.close()

#         self.status.setText("🔴 Offline")

#         self.btn_start.setEnabled(True)
#         self.btn_stop.setEnabled(False)

#         self.add_log("Serviço parado")

#     def process_finished(self):
#         self.add_log("Aplicação encerrada")

#         self.status.setText("🔴 Offline")

#         self.btn_stop.setEnabled(False)
#         self.btn_start.setEnabled(True)

#     def read_stdout(self):

#         data = self.process.readAllStandardOutput()

#         text = bytes(data).decode(
#             "utf-8",
#             errors="ignore"
#         )

#         self.logs.append(text.rstrip())

#     def read_stderr(self):

#         data = self.process.readAllStandardError()

#         text = bytes(data).decode(
#             "utf-8",
#             errors="ignore"
#         )

#         self.add_log(
#             f"ERRO: {text}"
#         )

#     def add_log(self, message, level="INFO"):

#         timestamp = datetime.now().strftime(
#             "%Y-%m-%d %H:%M:%S"
#         )

#         self.logs.append(
#             f"[{timestamp}] [{level}] ➔ {message}"
#         )