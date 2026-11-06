from datetime import datetime, timezone
from enum import Enum


def gerar_timestamp_utc() -> str:
    """Retorna a data e hora atual em formato ISO 8601 com fuso horário UTC explícito."""
    return datetime.now(timezone.utc).isoformat()


class StatusChamado(str, Enum):
    """Enumeração que representa os estados válidos de um chamado."""

    ABERTO = "ABERTO"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    ENCERRADO = "ENCERRADO"

    def __str__(self) -> str:
        return self.value


class Chamado:
    """Representa um chamado de suporte técnico e controla seu ciclo de vida."""

    def __init__(
        self,
        id: int | None = None,
        titulo: str = "",
        descricao: str = "",
        *,
        status: StatusChamado = StatusChamado.ABERTO,
        criado_em: str | None = None,
        iniciado_em: str | None = None,
        encerrado_em: str | None = None,
    ) -> None:
        if id is not None:
            self._validar_id(id)

        if not isinstance(titulo, str) or not titulo.strip():
            raise ValueError("O título do chamado não pode ser vazio.")

        if not isinstance(descricao, str) or not descricao.strip():
            raise ValueError("A descrição do chamado não pode ser vazia.")

        if not isinstance(status, StatusChamado):
            raise ValueError("O status informado deve ser um StatusChamado válido.")

        self.id: int | None = id
        self.titulo: str = titulo.strip()
        self.descricao: str = descricao.strip()
        self.status: StatusChamado = status
        self.criado_em: str = criado_em if criado_em is not None else gerar_timestamp_utc()
        self.iniciado_em: str | None = iniciado_em
        self.encerrado_em: str | None = encerrado_em

    @staticmethod
    def _validar_id(id_valor: int) -> None:
        if isinstance(id_valor, bool) or not isinstance(id_valor, int) or id_valor <= 0:
            raise ValueError("O ID do chamado deve ser um número inteiro positivo.")

    def atribuir_id(self, novo_id: int) -> None:
        """Associa o ID gerado pela camada de persistência ao chamado ainda não identificado."""
        self._validar_id(novo_id)
        if self.id is not None and self.id != novo_id:
            raise ValueError("Este chamado já possui um ID atribuído e não pode ser sobrescrito.")
        self.id = novo_id

    def iniciar_atendimento(self) -> bool:
        """Transiciona o status de ABERTO para EM_ANDAMENTO e registra iniciado_em."""
        if self.status == StatusChamado.ABERTO:
            self.status = StatusChamado.EM_ANDAMENTO
            self.iniciado_em = gerar_timestamp_utc()
            return True
        return False

    def encerrar_atendimento(self) -> bool:
        """Transiciona o status de EM_ANDAMENTO para ENCERRADO e registra encerrado_em."""
        if self.status == StatusChamado.EM_ANDAMENTO:
            self.status = StatusChamado.ENCERRADO
            self.encerrado_em = gerar_timestamp_utc()
            return True
        return False
