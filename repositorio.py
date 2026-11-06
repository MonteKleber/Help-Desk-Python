from typing import Protocol, runtime_checkable

from chamados import Chamado


@runtime_checkable
class RepositorioChamados(Protocol):
    """Contrato de persistência para armazenamento e recuperação de chamados."""

    def salvar(self, chamado: Chamado) -> Chamado:
        """Persiste um novo chamado, atribuindo seu ID caso ainda não possua."""
        ...

    def buscar_por_id(self, id_chamado: int) -> Chamado | None:
        """Recupera um chamado pelo seu identificador único ou retorna None."""
        ...

    def listar_todos(self) -> list[Chamado]:
        """Retorna todos os chamados armazenados."""
        ...

    def atualizar(self, chamado: Chamado) -> Chamado:
        """Atualiza os dados de um chamado já existente na persistência."""
        ...


class RepositorioMemoria:
    """Implementação em memória do contrato RepositorioChamados."""

    def __init__(self) -> None:
        self._chamados: list[Chamado] = []
        self._sequencia_id: int = 0

    def salvar(self, chamado: Chamado) -> Chamado:
        if chamado.id is not None:
            if self.buscar_por_id(chamado.id) is not None:
                raise ValueError(f"Já existe um chamado cadastrado com o ID {chamado.id}.")
            if chamado.id > self._sequencia_id:
                self._sequencia_id = chamado.id
        else:
            self._sequencia_id += 1
            chamado.atribuir_id(self._sequencia_id)

        self._chamados.append(chamado)
        return chamado

    def buscar_por_id(self, id_chamado: int) -> Chamado | None:
        for chamado in self._chamados:
            if chamado.id == id_chamado:
                return chamado
        return None

    def listar_todos(self) -> list[Chamado]:
        return list(self._chamados)

    def atualizar(self, chamado: Chamado) -> Chamado:
        if chamado.id is None:
            raise ValueError("Não é possível atualizar um chamado sem ID.")

        for indice, item in enumerate(self._chamados):
            if item.id == chamado.id:
                self._chamados[indice] = chamado
                return chamado

        raise ValueError(f"Chamado com ID {chamado.id} não encontrado para atualização.")

