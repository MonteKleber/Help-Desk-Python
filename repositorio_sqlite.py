from contextlib import closing
from pathlib import Path
import sqlite3

from chamados import Chamado, StatusChamado


class RepositorioSQLite:
    """Implementação concreta de persistência utilizando banco de dados SQLite."""

    def __init__(self, caminho_banco: str | Path = "helpdesk.db") -> None:
        self.caminho_banco: Path = Path(caminho_banco)
        self._inicializar_tabela()

    def _conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(self.caminho_banco)
        conexao.row_factory = sqlite3.Row
        return conexao

    def _inicializar_tabela(self) -> None:
        sql_criar_tabela = """
        CREATE TABLE IF NOT EXISTS chamados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            status TEXT NOT NULL,
            criado_em TEXT NOT NULL,
            iniciado_em TEXT NULL,
            encerrado_em TEXT NULL
        )
        """
        with closing(self._conectar()) as conexao:
            with conexao:
                conexao.execute(sql_criar_tabela)

    @staticmethod
    def _hidratar_chamado(linha: sqlite3.Row) -> Chamado:
        return Chamado(
            id=int(linha["id"]),
            titulo=str(linha["titulo"]),
            descricao=str(linha["descricao"]),
            status=StatusChamado(str(linha["status"])),
            criado_em=str(linha["criado_em"]),
            iniciado_em=str(linha["iniciado_em"]) if linha["iniciado_em"] is not None else None,
            encerrado_em=str(linha["encerrado_em"]) if linha["encerrado_em"] is not None else None,
        )

    def salvar(self, chamado: Chamado) -> Chamado:
        try:
            with closing(self._conectar()) as conexao:
                with conexao:
                    if chamado.id is None:
                        cursor = conexao.execute(
                            """
                            INSERT INTO chamados (
                                titulo, descricao, status, criado_em, iniciado_em, encerrado_em
                            ) VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                chamado.titulo,
                                chamado.descricao,
                                chamado.status.value,
                                chamado.criado_em,
                                chamado.iniciado_em,
                                chamado.encerrado_em,
                            ),
                        )
                        if cursor.lastrowid is None:
                            raise RuntimeError("Falha ao obter o ID gerado pelo SQLite.")
                        chamado.atribuir_id(int(cursor.lastrowid))
                    else:
                        conexao.execute(
                            """
                            INSERT INTO chamados (
                                id, titulo, descricao, status, criado_em, iniciado_em, encerrado_em
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                chamado.id,
                                chamado.titulo,
                                chamado.descricao,
                                chamado.status.value,
                                chamado.criado_em,
                                chamado.iniciado_em,
                                chamado.encerrado_em,
                            ),
                        )
            return chamado
        except sqlite3.IntegrityError as erro:
            raise ValueError(
                f"Já existe um chamado cadastrado com o ID {chamado.id}."
            ) from erro

    def buscar_por_id(self, id_chamado: int) -> Chamado | None:
        with closing(self._conectar()) as conexao:
            cursor = conexao.execute(
                """
                SELECT id, titulo, descricao, status, criado_em, iniciado_em, encerrado_em
                FROM chamados
                WHERE id = ?
                """,
                (id_chamado,),
            )
            linha = cursor.fetchone()
            if linha is None:
                return None
            return self._hidratar_chamado(linha)

    def listar_todos(self) -> list[Chamado]:
        with closing(self._conectar()) as conexao:
            cursor = conexao.execute(
                """
                SELECT id, titulo, descricao, status, criado_em, iniciado_em, encerrado_em
                FROM chamados
                ORDER BY id ASC
                """
            )
            linhas = cursor.fetchall()
            return [self._hidratar_chamado(linha) for linha in linhas]

    def atualizar(self, chamado: Chamado) -> Chamado:
        if chamado.id is None:
            raise ValueError("Não é possível atualizar um chamado sem ID.")

        with closing(self._conectar()) as conexao:
            with conexao:
                cursor = conexao.execute(
                    """
                    UPDATE chamados
                    SET titulo = ?,
                        descricao = ?,
                        status = ?,
                        iniciado_em = ?,
                        encerrado_em = ?
                    WHERE id = ?
                    """,
                    (
                        chamado.titulo,
                        chamado.descricao,
                        chamado.status.value,
                        chamado.iniciado_em,
                        chamado.encerrado_em,
                        chamado.id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Chamado com ID {chamado.id} não encontrado para atualização.")
        return chamado

