from datetime import datetime, timedelta, timezone
from enum import Enum


def gerar_timestamp_utc() -> str:
    """Retorna a data e hora atual em formato ISO 8601 com fuso horário UTC explícito."""
    return datetime.now(timezone.utc).isoformat()


def validar_timestamp_utc(valor: str, nome_campo: str = "timestamp") -> str:
    """Valida se a string está em formato ISO 8601 válido e com fuso horário UTC (+00:00)."""
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"O campo {nome_campo} deve ser uma string ISO 8601 não vazia.")

    try:
        dt = datetime.fromisoformat(valor)
    except ValueError as erro:
        raise ValueError(f"O campo {nome_campo} não está em formato ISO 8601 válido.") from erro

    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise ValueError(f"O campo {nome_campo} deve possuir fuso horário UTC explícito.")

    return valor


class StatusChamado(str, Enum):
    """Enumeração que representa os estados válidos de um chamado."""

    ABERTO = "ABERTO"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    ENCERRADO = "ENCERRADO"

    def __str__(self) -> str:
        return self.value


class Chamado:
    """Representa um chamado de suporte técnico e controla seu ciclo de vida."""

    _TRANSICOES_VALIDAS: dict[StatusChamado, set[StatusChamado]] = {
        StatusChamado.ABERTO: {StatusChamado.EM_ANDAMENTO},
        StatusChamado.EM_ANDAMENTO: {StatusChamado.ENCERRADO},
        StatusChamado.ENCERRADO: set(),
    }

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

        criado_em_final = (
            validar_timestamp_utc(criado_em, "criado_em")
            if criado_em is not None
            else gerar_timestamp_utc()
        )
        iniciado_em_final = (
            validar_timestamp_utc(iniciado_em, "iniciado_em")
            if iniciado_em is not None
            else None
        )
        encerrado_em_final = (
            validar_timestamp_utc(encerrado_em, "encerrado_em")
            if encerrado_em is not None
            else None
        )

        self.id: int | None = id
        self.titulo: str = titulo.strip()
        self.descricao: str = descricao.strip()
        self._status: StatusChamado = status
        self._criado_em: str = criado_em_final
        self._iniciado_em: str | None = iniciado_em_final
        self._encerrado_em: str | None = encerrado_em_final

    @property
    def status(self) -> StatusChamado:
        """Retorna o status atual do chamado (somente leitura; altere via métodos de domínio)."""
        return self._status

    @property
    def criado_em(self) -> str:
        """Retorna o timestamp UTC de abertura do chamado."""
        return self._criado_em

    @property
    def iniciado_em(self) -> str | None:
        """Retorna o timestamp UTC de início do atendimento."""
        return self._iniciado_em

    @property
    def encerrado_em(self) -> str | None:
        """Retorna o timestamp UTC de encerramento do atendimento."""
        return self._encerrado_em

    @classmethod
    def transicao_permitida(
        cls, status_atual: StatusChamado, novo_status: StatusChamado
    ) -> bool:
        """Verifica se a mudança de status_atual para novo_status é permitida pelo domínio."""
        if not isinstance(status_atual, StatusChamado) or not isinstance(
            novo_status, StatusChamado
        ):
            return False
        return novo_status in cls._TRANSICOES_VALIDAS.get(status_atual, set())

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
        if self.transicao_permitida(self._status, StatusChamado.EM_ANDAMENTO):
            self._status = StatusChamado.EM_ANDAMENTO
            self._iniciado_em = gerar_timestamp_utc()
            return True
        return False

    def encerrar_atendimento(self) -> bool:
        """Transiciona o status de EM_ANDAMENTO para ENCERRADO e registra encerrado_em."""
        if self.transicao_permitida(self._status, StatusChamado.ENCERRADO):
            self._status = StatusChamado.ENCERRADO
            self._encerrado_em = gerar_timestamp_utc()
            return True
        return False

    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, Chamado):
            return False
        return (
            self.id == outro.id
            and self.titulo == outro.titulo
            and self.descricao == outro.descricao
            and self._status == outro._status
            and self._criado_em == outro._criado_em
            and self._iniciado_em == outro._iniciado_em
            and self._encerrado_em == outro._encerrado_em
        )

