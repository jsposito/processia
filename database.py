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


def _garantir_colunas_processos(conn: sqlite3.Connection) -> None:
    """Migração leve: adiciona colunas novas de processos caso ainda não existam."""
    colunas_existentes = {row["name"] for row in conn.execute("PRAGMA table_info(processos)").fetchall()}
    colunas_novas = {
        "valor_estimado": "REAL",
        "data_fim_vigencia": "TEXT",
        "unidade_demandante": "TEXT",
        "objeto": "TEXT",
        "urgencia": "TEXT",
        "observacoes": "TEXT",
    }
    for coluna, tipo_sql in colunas_novas.items():
        if coluna not in colunas_existentes:
            conn.execute(f"ALTER TABLE processos ADD COLUMN {coluna} {tipo_sql}")


def _garantir_colunas_minutas(conn: sqlite3.Connection) -> None:
    """Migração leve: garante as colunas tipo/texto em minutas (renomeia conteudo, se existir)."""
    colunas_existentes = {row["name"] for row in conn.execute("PRAGMA table_info(minutas)").fetchall()}
    if "tipo" not in colunas_existentes:
        conn.execute("ALTER TABLE minutas ADD COLUMN tipo TEXT")
    if "texto" not in colunas_existentes:
        if "conteudo" in colunas_existentes:
            conn.execute("ALTER TABLE minutas RENAME COLUMN conteudo TO texto")
        else:
            conn.execute("ALTER TABLE minutas ADD COLUMN texto TEXT")


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
        _garantir_colunas_processos(conn)
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
                tipo TEXT,
                texto TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (processo_id) REFERENCES processos (id)
            )
            """
        )
        _garantir_colunas_minutas(conn)
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


def criar_processo(
    numero: str,
    tipo: str,
    unidade_demandante: str,
    objeto: str,
    valor_estimado,
    data_fim_vigencia,
    urgencia: str,
    observacoes: str,
    status: str = "Aberto",
) -> int:
    """Insere um novo processo e retorna o id gerado."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO processos (
                numero, tipo, status, valor_estimado, data_fim_vigencia,
                unidade_demandante, objeto, urgencia, observacoes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (numero, tipo, status, valor_estimado, data_fim_vigencia, unidade_demandante, objeto, urgencia, observacoes),
        )
        conn.commit()
        return cur.lastrowid


def listar_processos() -> list:
    """Retorna todos os processos cadastrados, mais recentes primeiro."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM processos ORDER BY criado_em DESC").fetchall()
    return [dict(row) for row in rows]


def buscar_processo(processo_id: int):
    """Retorna um processo pelo id, ou None se não existir."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM processos WHERE id = ?", (processo_id,)).fetchone()
    return dict(row) if row else None


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


def listar_analises() -> list:
    """Retorna todas as análises salvas, com número/tipo do processo, mais recentes primeiro."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT a.id, a.processo_id, a.conteudo, a.criado_em,
                   p.numero AS processo_numero, p.tipo AS processo_tipo
            FROM analises a
            JOIN processos p ON p.id = a.processo_id
            ORDER BY a.criado_em DESC, a.id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def listar_minutas() -> list:
    """Retorna todas as minutas salvas, com número/tipo do processo, mais recentes primeiro."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT m.id, m.processo_id, m.tipo, m.texto, m.criado_em,
                   p.numero AS processo_numero, p.tipo AS processo_tipo
            FROM minutas m
            JOIN processos p ON p.id = m.processo_id
            ORDER BY m.criado_em DESC, m.id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def buscar_ultima_analise(processo_id: int):
    """Retorna a última análise salva do processo (conteudo JSON + criado_em), ou None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT conteudo, criado_em FROM analises WHERE processo_id = ? ORDER BY id DESC LIMIT 1",
            (processo_id,),
        ).fetchone()
    return dict(row) if row else None


def salvar_minuta(processo_id: int, tipo: str, texto: str) -> int:
    """Salva uma minuta gerada e retorna o id do registro."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO minutas (processo_id, tipo, texto) VALUES (?, ?, ?)",
            (processo_id, tipo, texto),
        )
        conn.commit()
        return cur.lastrowid
