from datetime import datetime
from pathlib import Path
import sqlite3
import pytest

from chamados import Chamado, StatusChamado
from main import main
from repositorio import RepositorioChamados
from repositorio_sqlite import RepositorioSQLite
from sistema_chamados import SistemaChamados


@pytest.fixture
def caminho_db(tmp_path: Path) -> Path:
    """Fornece um caminho de arquivo SQLite isolado por teste usando tmp_path."""
    return tmp_path / "test_helpdesk.db"


@pytest.fixture
def sistema_sqlite(caminho_db: Path) -> SistemaChamados:
    """Instancia o SistemaChamados conectado ao banco SQLite temporário."""
    repositorio = RepositorioSQLite(caminho_db)
    return SistemaChamados(repositorio=repositorio)


# =========================================================
# 1. Criação, Gravação e Geração Automática de IDs
# =========================================================

def test_repositorio_sqlite_cumpre_protocolo(caminho_db: Path) -> None:
    repositorio = RepositorioSQLite(caminho_db)
    assert isinstance(repositorio, RepositorioChamados)


def test_criar_e_gravar_chamado_no_sqlite(sistema_sqlite: SistemaChamados, caminho_db: Path) -> None:
    chamado = sistema_sqlite.criar_chamado(
        "Falha no servidor de arquivos",
        "Pasta compartilhada do financeiro está inacessível",
    )

    assert chamado.id == 1
    assert chamado.titulo == "Falha no servidor de arquivos"
    assert chamado.status == StatusChamado.ABERTO

    # Verifica diretamente no SQLite que o valor salvo é exatamente 'ABERTO'
    with sqlite3.connect(caminho_db) as conn:
        linha = conn.execute("SELECT id, titulo, status FROM chamados WHERE id = ?", (1,)).fetchone()
        assert linha == (1, "Falha no servidor de arquivos", "ABERTO")


def test_geracao_automatica_sequencial_de_ids(sistema_sqlite: SistemaChamados) -> None:
    c1 = sistema_sqlite.criar_chamado("Chamado 1", "Descrição 1")
    c2 = sistema_sqlite.criar_chamado("Chamado 2", "Descrição 2")
    c3 = sistema_sqlite.criar_chamado("Chamado 3", "Descrição 3")

    assert c1.id == 1
    assert c2.id == 2
    assert c3.id == 3


def test_id_permanece_none_em_caso_de_falha_na_gravacao(
    caminho_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repositorio = RepositorioSQLite(caminho_db)
    chamado = Chamado(None, "Chamado não persistido", "Falha simulada na transação")

    class ConexaoComFalhaNoCommit:
        def __init__(self, conn_real: sqlite3.Connection) -> None:
            self._conn = conn_real

        def execute(self, *args: object, **kwargs: object) -> sqlite3.Cursor:
            return self._conn.execute(*args, **kwargs)  # type: ignore[arg-type]

        def __enter__(self) -> "ConexaoComFalhaNoCommit":
            self._conn.__enter__()
            return self

        def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
            self._conn.rollback()
            raise sqlite3.OperationalError("Falha simulada ao confirmar transação (COMMIT)")

        def close(self) -> None:
            self._conn.close()

    conn_real = sqlite3.connect(caminho_db)
    monkeypatch.setattr(repositorio, "_conectar", lambda: ConexaoComFalhaNoCommit(conn_real))

    with pytest.raises(sqlite3.OperationalError, match="Falha simulada ao confirmar transação"):
        repositorio.salvar(chamado)

    # Garante que o objeto em memória não recebeu um ID de uma transação que falhou
    assert chamado.id is None


# =========================================================
# 2. Busca por ID, Busca Inexistente e Listagem
# =========================================================

def test_buscar_chamado_por_id_no_sqlite(sistema_sqlite: SistemaChamados) -> None:
    criado = sistema_sqlite.criar_chamado("Impressora fiscal", "Erro de comunicação USB")

    assert criado.id is not None
    encontrado = sistema_sqlite.buscar_chamado(criado.id)

    assert encontrado is not None
    assert encontrado.id == criado.id
    assert encontrado.titulo == "Impressora fiscal"
    assert encontrado.descricao == "Erro de comunicação USB"
    assert encontrado.status == StatusChamado.ABERTO


def test_buscar_chamado_inexistente_no_sqlite(sistema_sqlite: SistemaChamados) -> None:
    sistema_sqlite.criar_chamado("Chamado existente", "Descrição")

    assert sistema_sqlite.buscar_chamado(999) is None


def test_listar_todos_os_chamados_no_sqlite(sistema_sqlite: SistemaChamados) -> None:
    sistema_sqlite.criar_chamado("Problema de Wi-Fi", "Sinal fraco na sala de reunião")
    sistema_sqlite.criar_chamado("Troca de mouse", "Botão esquerdo falhando")

    chamados = sistema_sqlite.listar_chamados()

    assert len(chamados) == 2
    assert [c.id for c in chamados] == [1, 2]
    assert [c.titulo for c in chamados] == ["Problema de Wi-Fi", "Troca de mouse"]


# =========================================================
# 3. Atualização de Status e Valores Exatos do Enum no Banco
# =========================================================

def test_atualizar_status_iniciar_e_encerrar_no_sqlite(
    sistema_sqlite: SistemaChamados, caminho_db: Path
) -> None:
    chamado = sistema_sqlite.criar_chamado("Lentidão no banco", "Queries demorando mais de 30s")
    assert chamado.id is not None

    # Transição 1: ABERTO -> EM_ANDAMENTO
    assert sistema_sqlite.iniciar_atendimento(chamado.id) is True

    with sqlite3.connect(caminho_db) as conn:
        status_banco = conn.execute(
            "SELECT status FROM chamados WHERE id = ?", (chamado.id,)
        ).fetchone()[0]
        assert status_banco == "EM_ANDAMENTO"

    # Transição 2: EM_ANDAMENTO -> ENCERRADO via atualizar_status
    assert sistema_sqlite.atualizar_status(chamado.id, StatusChamado.ENCERRADO) is True

    with sqlite3.connect(caminho_db) as conn:
        status_banco_final = conn.execute(
            "SELECT status FROM chamados WHERE id = ?", (chamado.id,)
        ).fetchone()[0]
        assert status_banco_final == "ENCERRADO"


def test_persistencia_de_mudancas_realizadas_pelo_servico(
    sistema_sqlite: SistemaChamados, caminho_db: Path
) -> None:
    chamado = sistema_sqlite.criar_chamado("Switch travado", "Portas 1 a 8 sem link")
    assert chamado.id == 1

    # Modificar apenas o objeto recuperado em memória NÃO altera o banco sem passar pelo serviço
    copia_local = sistema_sqlite.buscar_chamado(1)
    assert copia_local is not None
    copia_local.iniciar_atendimento()
    no_banco_ainda_aberto = sistema_sqlite.buscar_chamado(1)
    assert no_banco_ainda_aberto is not None
    assert no_banco_ainda_aberto.status == StatusChamado.ABERTO

    # Mudança via serviço SistemaChamados persiste no SQLite
    assert sistema_sqlite.iniciar_atendimento(1) is True
    assert sistema_sqlite.encerrar_atendimento(1) is True

    recarregado = SistemaChamados(repositorio=RepositorioSQLite(caminho_db)).buscar_chamado(1)
    assert recarregado is not None
    assert recarregado.status == StatusChamado.ENCERRADO
    assert recarregado.iniciado_em is not None
    assert recarregado.encerrado_em is not None


def test_main_integra_sqlite_e_persiste_mudanca_via_servico(
    caminho_db: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    respostas = iter(["1", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(respostas))

    main(caminho_banco=caminho_db)

    saida = capsys.readouterr().out
    assert "Chamado encontrado!" in saida
    assert "Atendimento iniciado com sucesso!" in saida
    assert "Novo status: EM_ANDAMENTO" in saida

    # Verifica no banco SQLite que a transição realizada pelo main.py foi persistida
    sistema_verificacao = SistemaChamados(repositorio=RepositorioSQLite(caminho_db))
    chamado_persistido = sistema_verificacao.buscar_chamado(1)
    assert chamado_persistido is not None
    assert chamado_persistido.status == StatusChamado.EM_ANDAMENTO
    assert chamado_persistido.iniciado_em is not None


# =========================================================
# 4. Registro de Datas ISO 8601 com Fuso Horário UTC
# =========================================================

def test_registro_de_datas_utc_em_cada_etapa(sistema_sqlite: SistemaChamados) -> None:
    chamado = sistema_sqlite.criar_chamado("Backup falhou", "Job noturno retornou erro")
    assert chamado.id is not None

    # Abertura registra apenas criado_em
    aberto = sistema_sqlite.buscar_chamado(chamado.id)
    assert aberto is not None
    assert aberto.criado_em is not None
    assert aberto.iniciado_em is None
    assert aberto.encerrado_em is None
    dt_criado = datetime.fromisoformat(aberto.criado_em)
    assert dt_criado.tzinfo is not None

    # Início registra iniciado_em
    sistema_sqlite.iniciar_atendimento(chamado.id)
    em_andamento = sistema_sqlite.buscar_chamado(chamado.id)
    assert em_andamento is not None
    assert em_andamento.iniciado_em is not None
    assert em_andamento.encerrado_em is None
    dt_iniciado = datetime.fromisoformat(em_andamento.iniciado_em)
    assert dt_iniciado.tzinfo is not None
    assert dt_iniciado >= dt_criado

    # Encerramento registra encerrado_em
    sistema_sqlite.encerrar_atendimento(chamado.id)
    encerrado = sistema_sqlite.buscar_chamado(chamado.id)
    assert encerrado is not None
    assert encerrado.encerrado_em is not None
    dt_encerrado = datetime.fromisoformat(encerrado.encerrado_em)
    assert dt_encerrado.tzinfo is not None
    assert dt_encerrado >= dt_iniciado


# =========================================================
# 5. Persistência Real Após Fechar e Reabrir Conexão/Instância
# =========================================================

def test_persistencia_apos_fechar_e_reabrir_banco(caminho_db: Path) -> None:
    # Sessão 1: cria chamado e inicia atendimento
    sistema_sessao_1 = SistemaChamados(repositorio=RepositorioSQLite(caminho_db))
    criado = sistema_sessao_1.criar_chamado("Queda de VPN", "Túnel IPSec caiu na filial")
    assert criado.id == 1
    sistema_sessao_1.iniciar_atendimento(1)
    del sistema_sessao_1

    # Sessão 2: nova instância lendo do mesmo arquivo .db
    sistema_sessao_2 = SistemaChamados(repositorio=RepositorioSQLite(caminho_db))
    recuperado = sistema_sessao_2.buscar_chamado(1)

    assert recuperado is not None
    assert recuperado.id == 1
    assert recuperado.titulo == "Queda de VPN"
    assert recuperado.status == StatusChamado.EM_ANDAMENTO
    assert recuperado.iniciado_em is not None
    assert recuperado.encerrado_em is None


# =========================================================
# 6. Impedimento de Transições Inválidas e IDs Duplicados
# =========================================================

def test_impedir_transicoes_invalidas_no_sqlite(sistema_sqlite: SistemaChamados) -> None:
    chamado = sistema_sqlite.criar_chamado("Erro de login", "Usuário bloqueado no AD")
    assert chamado.id is not None

    # 1. Chamado ABERTO não pode ser encerrado diretamente
    assert sistema_sqlite.encerrar_atendimento(chamado.id) is False
    atual = sistema_sqlite.buscar_chamado(chamado.id)
    assert atual is not None
    assert atual.status == StatusChamado.ABERTO
    assert atual.encerrado_em is None

    # 2. Inicia normalmente e tenta iniciar uma segunda vez (deve rejeitar)
    assert sistema_sqlite.iniciar_atendimento(chamado.id) is True
    primeiro_inicio = sistema_sqlite.buscar_chamado(chamado.id)
    assert primeiro_inicio is not None
    timestamp_inicio_original = primeiro_inicio.iniciado_em

    assert sistema_sqlite.iniciar_atendimento(chamado.id) is False
    apos_tentativa_dupla = sistema_sqlite.buscar_chamado(chamado.id)
    assert apos_tentativa_dupla is not None
    assert apos_tentativa_dupla.iniciado_em == timestamp_inicio_original

    # 3. Encerra normalmente e tenta alterar chamado já ENCERRADO (deve rejeitar)
    assert sistema_sqlite.encerrar_atendimento(chamado.id) is True
    assert sistema_sqlite.iniciar_atendimento(chamado.id) is False
    assert sistema_sqlite.encerrar_atendimento(chamado.id) is False
    assert sistema_sqlite.atualizar_status(chamado.id, StatusChamado.ABERTO) is False


def test_impedir_contorno_de_transicao_direto_no_repositorio_sqlite(
    caminho_db: Path,
) -> None:
    repositorio = RepositorioSQLite(caminho_db)
    chamado = repositorio.salvar(Chamado(None, "Falha de DNS", "Servidor interno não resolve"))
    assert chamado.id == 1

    # Tenta forçar atualização direta de ABERTO -> ENCERRADO no repositório
    chamado_invalido = Chamado(
        id=1,
        titulo="Falha de DNS",
        descricao="Servidor interno não resolve",
        status=StatusChamado.ENCERRADO,
    )
    with pytest.raises(ValueError, match="Transição de status inválida"):
        repositorio.atualizar(chamado_invalido)

    persistido = repositorio.buscar_por_id(1)
    assert persistido is not None
    assert persistido.status == StatusChamado.ABERTO


def test_erro_ao_iniciar_ou_encerrar_chamado_inexistente(sistema_sqlite: SistemaChamados) -> None:
    with pytest.raises(ValueError, match="Chamado com ID 404 não encontrado"):
        sistema_sqlite.iniciar_atendimento(404)

    with pytest.raises(ValueError, match="Chamado com ID 404 não encontrado"):
        sistema_sqlite.encerrar_atendimento(404)


def test_impedir_id_duplicado_no_sqlite(sistema_sqlite: SistemaChamados) -> None:
    chamado_1 = Chamado(10, "Chamado Manual 1", "Descrição 1")
    chamado_duplicado = Chamado(10, "Chamado Manual Duplicado", "Descrição 2")

    sistema_sqlite.cadastrar_chamado(chamado_1)

    with pytest.raises(ValueError, match="Já existe um chamado cadastrado com o ID 10"):
        sistema_sqlite.cadastrar_chamado(chamado_duplicado)

    assert len(sistema_sqlite.listar_chamados()) == 1
