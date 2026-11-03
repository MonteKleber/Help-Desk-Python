class SistemaChamados:
    def __init__(self):
        self.chamados = []

    def cadastrar_chamado(self, chamado):
        self.chamados.append(chamado)

    def listar_chamados(self):
        for chamado in self.chamados:
            print ("--- CHAMADO ---")
            print(f"ID:", chamado.id)
            print(f"Título:", chamado.titulo)
            print(f"Status:",chamado.status)
            print ("----------------")

    def buscar_chamado(self, id_chamado):
        for chamado in self.chamados:
            if chamado.id == id_chamado:
                return chamado
        return None