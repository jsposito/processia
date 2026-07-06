"""Camada de acesso a dados (SQLite nativo) do Processia."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "processia.db"


def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão SQLite com row_factory configurado."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Cria as tabelas do banco caso ainda não existam."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT,
                tipo TEXT,
                status TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                processo_id INTEGER NOT NULL,
                conteudo TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (processo_id) REFERENCES processos (id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS minutas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                processo_id INTEGER NOT NULL,
                conteudo TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (processo_id) REFERENCES processos (id)
            )
            """
        )
        conn.commit()
