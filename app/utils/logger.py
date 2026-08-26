import os
import sys
import logging
from logging.handlers import RotatingFileHandler

def configurar_logger(nome_logger: str = "SigCorpAgents", pasta: str = "logs", arquivo: str = "logs.txt") -> logging.Logger:
    """
    Configura um sistema de logs duplo:
    1. Saída em tempo real no Terminal (Stdout)
    2. Gravação persistente em arquivo de texto com rotação automática.
    """

    try:
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace"
        )

        sys.stderr.reconfigure(
            encoding="utf-8",
            errors="replace"
        )
    except Exception:
        pass

    logger = logging.getLogger(nome_logger)

    # Se o logger já tiver handlers configurados, evita duplicá-los ao reimportar
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)

    # Formato padrão do Log: [Data/Hora] [NÍVEL] -> Mensagem
    formato = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] ➔ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Com identificador de arquivo e linha
    # formato = logging.Formatter(
    #     fmt="[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] ➔ %(message)s",
    #     datefmt="%Y-%m-%d %H:%M:%S"
    # )

    # --- 1. CONFIGURAÇÃO PARA O TERMINAL (TEMPO REAL) ---
    handler_terminal = logging.StreamHandler(sys.stdout)
    handler_terminal.setFormatter(formato)
    logger.addHandler(handler_terminal)

    # # --- 2. CONFIGURAÇÃO PARA O ARQUIVO TXT/LOG ---
    # pasta_logs = "logs"

    # if not os.path.exists(pasta_logs):
    #     os.makedirs(pasta_logs)

    # caminho_arquivo = os.path.join(
    #     pasta_logs,
    #     "logs.txt"
    # )

    os.makedirs(pasta, exist_ok=True)

    caminho_arquivo = os.path.join(
        pasta,
        arquivo
    )

    # RotatingFileHandler: Quando o arquivo atingir 5MB,
    # cria automaticamente logs.txt.1, logs.txt.2 etc.
    handler_arquivo = RotatingFileHandler(
        caminho_arquivo,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )

    handler_arquivo.setFormatter(formato)
    logger.addHandler(handler_arquivo)

    return logger


# Instancia o logger global para ser importado nos nós do Grafo
logger = configurar_logger(
    nome_logger="ORCAMENTO",
    pasta="logs/orcamento",
    arquivo="orcamento_log.log"
)

logger_monitor = configurar_logger(
    nome_logger="MONITOR",
    pasta="logs/monitor",
    arquivo="monitor_log.log"
)

logger_api = configurar_logger(
    nome_logger="API",
    pasta="logs/api",
    arquivo="api_log.log"
)