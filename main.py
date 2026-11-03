from sistema_chamados import SistemaChamados
from chamados import Chamado

sistema = SistemaChamados()##Instancia o objeto SistemaChamados responsável por gerenciar os chamados
chamado1 = Chamado(
    1,
    "O computador travou",
    "O computador utilizado na produção travou"
)
sistema.cadastrar_chamado(chamado1) #Cadastro o chamado
id_procurado =(int(input("Digite o ID do chamado: ")))#solicita o usuário que digite o id do chamado para que ele realize as busca correta
resultado = sistema.buscar_chamado(id_procurado) #Chama o método declarando como parâmetro a variavel "id_procurado que é digitado pelo o usuário"

if resultado is not None:
    print("Chamado encontrado!")
    print(f"Título do chamado: {resultado.titulo}")
    print(f"Status: {resultado.status}")

    iniciado = resultado.iniciar_atendimento()

    if iniciado:
        print("Atendimento iniciado com sucesso!")
    else:
        print("Não foi possível iniciar o atendimento.")

    print(f"Novo status: {resultado.status}")

else:
    print("Chamado não encontrado.")

input("Pressione ENTER para prosseguir!")
