from chamados import Chamado, StatusChamado
from repositorio import RepositorioChamados, RepositorioMemoria


class SistemaChamados:
    """Serviço de aplicação responsável por orquestrar operações de chamados."""

    def __init__(self, repositorio: RepositorioChamados | None = None) -> None:
        self._repositorio: RepositorioChamados = (
            repositorio if repositorio is not None else RepositorioMemoria()
        )

    @property
    def chamados(self) -> list[Chamado]:
        """Propriedade de compatibilidade que retorna os chamados armazenados."""
        return self._repositorio.listar_todos()

    def criar_chamado(self, titulo: str, descricao: str) -> Chamado:
        """Cria um novo chamado sem ID prévio, delegando a geração do ID ao repositório."""
        novo_chamado = Chamado(id=None, titulo=titulo, descricao=descricao)
        return self._repositorio.salvar(novo_chamado)

    def cadastrar_chamado(self, chamado: Chamado) -> Chamado:
        """Cadastra uma instância de Chamado no repositório configurado."""
        if not isinstance(chamado, Chamado):
            raise TypeError("O objeto informado deve ser uma instância de Chamado.")

        return self._repositorio.salvar(chamado)

    def listar_chamados(self) -> list[Chamado]:
        """Retorna a lista de todos os chamados persistidos."""
        return self._repositorio.listar_todos()

    def buscar_chamado(self, id_chamado: int) -> Chamado | None:
        """Busca e retorna um chamado pelo seu identificador ou None se não existir."""
        return self._repositorio.buscar_por_id(id_chamado)

    def iniciar_atendimento(self, id_chamado: int) -> bool:
        """Registra o início do atendimento aplicando a regra de domínio e persistindo o estado."""
        chamado = self.buscar_chamado(id_chamado)
        if chamado is None:
            raise ValueError(f"Chamado com ID {id_chamado} não encontrado.")

        if not chamado.iniciar_atendimento():
            return False

        self._repositorio.atualizar(chamado)
        return True

    def encerrar_atendimento(self, id_chamado: int) -> bool:
        """Registra o encerramento do atendimento aplicando a regra de domínio e persistindo o estado."""
        chamado = self.buscar_chamado(id_chamado)
        if chamado is None:
            raise ValueError(f"Chamado com ID {id_chamado} não encontrado.")

        if not chamado.encerrar_atendimento():
            return False

        self._repositorio.atualizar(chamado)
        return True

    def atualizar_status(self, id_chamado: int, novo_status: StatusChamado) -> bool:
        """Atualiza o status de um chamado respeitando estritamente as transições do domínio."""
        if not isinstance(novo_status, StatusChamado):
            raise ValueError("O novo status deve ser uma instância válida de StatusChamado.")

        if novo_status == StatusChamado.EM_ANDAMENTO:
            return self.iniciar_atendimento(id_chamado)
        if novo_status == StatusChamado.ENCERRADO:
            return self.encerrar_atendimento(id_chamado)

        # Não é permitido retornar um chamado para o status ABERTO
        if self.buscar_chamado(id_chamado) is None:
            raise ValueError(f"Chamado com ID {id_chamado} não encontrado.")
        return False
