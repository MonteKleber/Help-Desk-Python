class Chamado:
    def __init__(self, id, titulo, descricao):
        self.id = id
        self.titulo = titulo
        self.descricao = descricao
        self.status = "ABERTO"

    def iniciar_atendimento(self):
        if self.status == "ABERTO":
            self.status = "EM ANDAMENTO"
            return True
        else:
            return False

    def encerrar_atendimento(self):
        if self.status == "EM ANDAMENTO":
            self.status = "ENCERRADO"
            return True
        else:
            return False