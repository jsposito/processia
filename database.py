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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checklist_estado (
                processo_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                marcado INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (processo_id, item_id),
                FOREIGN KEY (processo_id) REFERENCES processos (id)
            )
            """
        )
        conn.commit()


def salvar_estado_checklist(processo_id: int, item_id: str, marcado: bool) -> None:
    """Salva (insere ou atualiza) o estado de um item de checklist para um processo."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO checklist_estado (processo_id, item_id, marcado)
            VALUES (?, ?, ?)
            ON CONFLICT (processo_id, item_id) DO UPDATE SET marcado = excluded.marcado
            """,
            (processo_id, item_id, int(marcado)),
        )
        conn.commit()


def carregar_estado_checklist(processo_id: int) -> dict:
    """Carrega o estado dos itens de checklist de um processo como {item_id: marcado}."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT item_id, marcado FROM checklist_estado WHERE processo_id = ?",
            (processo_id,),
        ).fetchall()
    return {row["item_id"]: bool(row["marcado"]) for row in rows}
