import pytest

from chamados import Chamado, StatusChamado
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


# =========================================================
# 2. Testes de Transição de Estado (Máquina de Estados)
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


# =========================================================
# 3. Testes da Classe SistemaChamados (Cadastro, Busca e Listagem)
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

