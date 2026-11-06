from datetime import datetime, timedelta
import pytest

from chamados import Chamado, StatusChamado
from repositorio import RepositorioMemoria
from sistema_chamados import SistemaChamados


# =========================================================
# 1. Testes da Entidade Chamado (Criação e Validação)
# =========================================================

def test_criar_chamado_valido() -> None:
    chamado = Chamado(1, "O computador travou", "O computador da produção travou")

    assert chamado.id == 1
    assert chamado.titulo == "O computador travou"
    assert chamado.descricao == "O computador da produção travou"
    assert chamado.status == StatusChamado.ABERTO
    assert str(chamado.status) == "ABERTO"


def test_criar_chamado_remove_espacos_extras() -> None:
    chamado = Chamado(2, "  Impressora sem conexão  ", "  Cabo de rede desconectado  ")

    assert chamado.titulo == "Impressora sem conexão"
    assert chamado.descricao == "Cabo de rede desconectado"


@pytest.mark.parametrize("titulo_invalido", ["", "   ", "\n\t"])
def test_rejeitar_titulo_vazio(titulo_invalido: str) -> None:
    with pytest.raises(ValueError, match="O título do chamado não pode ser vazio"):
        Chamado(1, titulo_invalido, "Descrição válida")


@pytest.mark.parametrize("descricao_invalida", ["", "   ", "\n\t"])
def test_rejeitar_descricao_vazia(descricao_invalida: str) -> None:
    with pytest.raises(ValueError, match="A descrição do chamado não pode ser vazia"):
        Chamado(1, "Título válido", descricao_invalida)


@pytest.mark.parametrize("id_invalido", [0, -1, -99, True, "1"])
def test_rejeitar_id_invalido(id_invalido: object) -> None:
    with pytest.raises(ValueError, match="O ID do chamado deve ser um número inteiro positivo"):
        Chamado(id_invalido, "Título válido", "Descrição válida")  # type: ignore[arg-type]


@pytest.mark.parametrize("titulo_tipo_invalido", [None, 123, ["lista"], True])
def test_rejeitar_titulo_com_tipo_invalido(titulo_tipo_invalido: object) -> None:
    with pytest.raises(ValueError, match="O título do chamado não pode ser vazio"):
        Chamado(1, titulo_tipo_invalido, "Descrição válida")  # type: ignore[arg-type]


@pytest.mark.parametrize("descricao_tipo_invalido", [None, 456, {"chave": "valor"}, False])
def test_rejeitar_descricao_com_tipo_invalido(descricao_tipo_invalido: object) -> None:
    with pytest.raises(ValueError, match="A descrição do chamado não pode ser vazia"):
        Chamado(1, "Título válido", descricao_tipo_invalido)  # type: ignore[arg-type]


# =========================================================
# 2. Testes de Validação de Timestamps UTC
# =========================================================

def test_validar_timestamps_utc_gerados_pelo_dominio() -> None:
    chamado = Chamado(1, "Servidor offline", "Ping não responde")
    assert datetime.fromisoformat(chamado.criado_em).utcoffset() == timedelta(0)

    chamado.iniciar_atendimento()
    assert chamado.iniciado_em is not None
    assert datetime.fromisoformat(chamado.iniciado_em).utcoffset() == timedelta(0)

    chamado.encerrar_atendimento()
    assert chamado.encerrado_em is not None
    assert datetime.fromisoformat(chamado.encerrado_em).utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    "timestamp_invalido",
    [
        "2026-11-05T10:00:00",        # Sem fuso horário (naive)
        "2026-11-05T10:00:00-03:00",  # Fuso diferente de UTC
        "data-invalida",              # Formato não ISO
        "",                           # String vazia
    ],
)
def test_rejeitar_timestamp_invalido_ou_fora_de_utc(timestamp_invalido: str) -> None:
    with pytest.raises(ValueError):
        Chamado(1, "Título", "Descrição", criado_em=timestamp_invalido)


# =========================================================
# 3. Testes de Transição de Estado (Máquina de Estados)
# =========================================================

def test_iniciar_atendimento_com_sucesso() -> None:
    chamado = Chamado(1, "Erro no ERP", "Sistema não abre tela de login")

    resultado = chamado.iniciar_atendimento()

    assert resultado is True
    assert chamado.status == StatusChamado.EM_ANDAMENTO


def test_encerrar_atendimento_com_sucesso() -> None:
    chamado = Chamado(1, "Erro no ERP", "Sistema não abre tela de login")
    chamado.iniciar_atendimento()

    resultado = chamado.encerrar_atendimento()

    assert resultado is True
    assert chamado.status == StatusChamado.ENCERRADO


def test_impedir_encerramento_direto_de_chamado_aberto() -> None:
    chamado = Chamado(1, "Erro no ERP", "Sistema não abre tela de login")

    resultado = chamado.encerrar_atendimento()

    assert resultado is False
    assert chamado.status == StatusChamado.ABERTO


def test_impedir_inicio_duplo_de_atendimento() -> None:
    chamado = Chamado(1, "Erro no ERP", "Sistema não abre tela de login")
    chamado.iniciar_atendimento()

    resultado_segunda_tentativa = chamado.iniciar_atendimento()

    assert resultado_segunda_tentativa is False
    assert chamado.status == StatusChamado.EM_ANDAMENTO


def test_impedir_transicoes_apos_chamado_encerrado() -> None:
    chamado = Chamado(1, "Erro no ERP", "Sistema não abre tela de login")
    chamado.iniciar_atendimento()
    chamado.encerrar_atendimento()

    assert chamado.iniciar_atendimento() is False
    assert chamado.encerrar_atendimento() is False
    assert chamado.status == StatusChamado.ENCERRADO


def test_impedir_alteracao_direta_do_atributo_status() -> None:
    chamado = Chamado(1, "Erro no ERP", "Sistema não abre tela de login")

    with pytest.raises(AttributeError):
        chamado.status = StatusChamado.ENCERRADO  # type: ignore[misc]

    assert chamado.status == StatusChamado.ABERTO


def test_impedir_transicao_invalida_no_repositorio_memoria() -> None:
    repositorio = RepositorioMemoria()
    chamado = Chamado(1, "Erro no ERP", "Sistema não abre tela de login")
    repositorio.salvar(chamado)

    chamado_forjado = Chamado(
        1,
        "Erro no ERP",
        "Sistema não abre tela de login",
        status=StatusChamado.ENCERRADO,
    )

    with pytest.raises(ValueError, match="Transição de status inválida"):
        repositorio.atualizar(chamado_forjado)


# =========================================================
# 4. Testes da Classe SistemaChamados (Cadastro, Busca e Listagem)
# =========================================================

def test_cadastrar_e_listar_chamados() -> None:
    sistema = SistemaChamados()
    chamado1 = Chamado(1, "Monitor piscando", "Monitor da recepção piscando")
    chamado2 = Chamado(2, "Sem internet", "Queda de link no 2º andar")

    sistema.cadastrar_chamado(chamado1)
    sistema.cadastrar_chamado(chamado2)

    lista = sistema.listar_chamados()
    assert len(lista) == 2
    assert lista[0] == chamado1
    assert lista[1] == chamado2


def test_listar_chamados_retorna_copia_protegida() -> None:
    sistema = SistemaChamados()
    chamado = Chamado(1, "Teclado com defeito", "Tecla Enter não funciona")
    sistema.cadastrar_chamado(chamado)

    lista_externa = sistema.listar_chamados()
    lista_externa.clear()

    assert len(sistema.listar_chamados()) == 1


def test_impedir_cadastro_com_id_duplicado() -> None:
    sistema = SistemaChamados()
    chamado1 = Chamado(1, "Chamado Original", "Descrição 1")
    chamado_duplicado = Chamado(1, "Chamado Duplicado", "Descrição 2")

    sistema.cadastrar_chamado(chamado1)

    with pytest.raises(ValueError, match="Já existe um chamado cadastrado com o ID 1"):
        sistema.cadastrar_chamado(chamado_duplicado)

    assert len(sistema.listar_chamados()) == 1


def test_rejeitar_cadastro_de_objeto_invalido() -> None:
    sistema = SistemaChamados()

    with pytest.raises(TypeError, match="O objeto informado deve ser uma instância de Chamado"):
        sistema.cadastrar_chamado({"id": 1})  # type: ignore[arg-type]


def test_buscar_chamado_existente() -> None:
    sistema = SistemaChamados()
    chamado = Chamado(10, "Acesso VPN", "Solicitação de liberação de VPN")
    sistema.cadastrar_chamado(chamado)

    encontrado = sistema.buscar_chamado(10)

    assert encontrado is not None
    assert encontrado.id == 10
    assert encontrado.titulo == "Acesso VPN"


def test_buscar_chamado_inexistente() -> None:
    sistema = SistemaChamados()
    sistema.cadastrar_chamado(Chamado(1, "Teste", "Descrição teste"))

    encontrado = sistema.buscar_chamado(999)

    assert encontrado is None


# =========================================================
# 5. Testes de Isolamento de Referências no RepositorioMemoria
# =========================================================

def test_buscar_por_id_nao_retorna_mesma_instancia_armazenada() -> None:
    repositorio = RepositorioMemoria()
    original = Chamado(1, "Servidor lento", "CPU em 100%")
    repositorio.salvar(original)

    busca_1 = repositorio.buscar_por_id(1)
    busca_2 = repositorio.buscar_por_id(1)

    assert busca_1 is not None
    assert busca_2 is not None
    assert busca_1 is not original
    assert busca_1 is not busca_2
    assert busca_1 == original


def test_alterar_objeto_recuperado_por_busca_nao_modifica_armazenamento_interno() -> None:
    repositorio = RepositorioMemoria()
    original = Chamado(1, "Servidor lento", "CPU em 100%")
    repositorio.salvar(original)

    recuperado = repositorio.buscar_por_id(1)
    assert recuperado is not None

    # Altera o objeto recuperado sem chamar atualizar()
    recuperado.iniciar_atendimento()
    recuperado.titulo = "Título alterado externamente"

    armazenado = repositorio.buscar_por_id(1)
    assert armazenado is not None
    assert armazenado.status == StatusChamado.ABERTO
    assert armazenado.iniciado_em is None
    assert armazenado.titulo == "Servidor lento"


def test_listar_todos_retorna_copias_independentes() -> None:
    repositorio = RepositorioMemoria()
    original = Chamado(1, "Erro de rede", "Sem acesso externo")
    repositorio.salvar(original)

    lista_1 = repositorio.listar_todos()
    lista_2 = repositorio.listar_todos()

    assert len(lista_1) == 1
    assert lista_1[0] is not original
    assert lista_1[0] is not lista_2[0]
    assert lista_1[0] == original


def test_alterar_copia_da_listagem_nao_afeta_dados_internos() -> None:
    repositorio = RepositorioMemoria()
    repositorio.salvar(Chamado(1, "Erro de rede", "Sem acesso externo"))

    lista = repositorio.listar_todos()
    lista[0].iniciar_atendimento()
    lista[0].titulo = "Modificado na lista"

    interno = repositorio.buscar_por_id(1)
    assert interno is not None
    assert interno.status == StatusChamado.ABERTO
    assert interno.titulo == "Erro de rede"


def test_atualizar_aceita_transicoes_validas_com_isolamento() -> None:
    repositorio = RepositorioMemoria()
    repositorio.salvar(Chamado(None, "Queda de link", "Fibra rompida"))

    # 1. ABERTO -> EM_ANDAMENTO
    em_atendimento = repositorio.buscar_por_id(1)
    assert em_atendimento is not None
    assert em_atendimento.iniciar_atendimento() is True

    # Antes de atualizar(), o repositório interno ainda deve estar ABERTO
    antes_do_update = repositorio.buscar_por_id(1)
    assert antes_do_update is not None
    assert antes_do_update.status == StatusChamado.ABERTO

    # atualizar() compara ABERTO (interno) com EM_ANDAMENTO (novo) e persiste cópia
    repositorio.atualizar(em_atendimento)
    apos_inicio = repositorio.buscar_por_id(1)
    assert apos_inicio is not None
    assert apos_inicio.status == StatusChamado.EM_ANDAMENTO
    assert apos_inicio is not em_atendimento

    # 2. EM_ANDAMENTO -> ENCERRADO
    para_encerrar = repositorio.buscar_por_id(1)
    assert para_encerrar is not None
    assert para_encerrar.encerrar_atendimento() is True

    antes_do_encerramento = repositorio.buscar_por_id(1)
    assert antes_do_encerramento is not None
    assert antes_do_encerramento.status == StatusChamado.EM_ANDAMENTO

    repositorio.atualizar(para_encerrar)
    apos_encerramento = repositorio.buscar_por_id(1)
    assert apos_encerramento is not None
    assert apos_encerramento.status == StatusChamado.ENCERRADO
    assert apos_encerramento.encerrado_em is not None


def test_fluxo_completo_servico_com_repositorio_memoria() -> None:
    sistema = SistemaChamados(repositorio=RepositorioMemoria())
    criado = sistema.criar_chamado("Falha no backup", "Disco cheio no servidor")
    assert criado.id == 1
    assert criado.status == StatusChamado.ABERTO

    # ABERTO -> EM_ANDAMENTO via serviço
    assert sistema.iniciar_atendimento(1) is True
    em_andamento = sistema.buscar_chamado(1)
    assert em_andamento is not None
    assert em_andamento.status == StatusChamado.EM_ANDAMENTO
    assert em_andamento.iniciado_em is not None

    # Tentativa inválida de iniciar novamente
    assert sistema.iniciar_atendimento(1) is False

    # EM_ANDAMENTO -> ENCERRADO via serviço
    assert sistema.encerrar_atendimento(1) is True
    encerrado = sistema.buscar_chamado(1)
    assert encerrado is not None
    assert encerrado.status == StatusChamado.ENCERRADO
    assert encerrado.encerrado_em is not None

    # Tentativa inválida após encerrado
    assert sistema.encerrar_atendimento(1) is False
    assert sistema.iniciar_atendimento(1) is False
