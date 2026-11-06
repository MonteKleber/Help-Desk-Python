# Sistema de Chamados de TI (Evolução para AI Help Desk)

Projeto desenvolvido em Python aplicando Programação Orientada a Objetos (POO), arquitetura desacoplada em camadas, persistência relacional com **SQLite** e testes automatizados com **Pytest**.

## Sobre o Projeto

O sistema realiza o gerenciamento do ciclo de vida de solicitações de suporte técnico, garantindo integridade de domínio, máquina de estados protegida e persistência transacional em banco de dados SQLite.

## Arquitetura Atual

O projeto adota separação de responsabilidades (SOLID) e o padrão **Repository**:

- **Domínio ([`chamados.py`](chamados.py)):**
  - `StatusChamado` (`Enum`): Estados canônicos `ABERTO`, `EM_ANDAMENTO` e `ENCERRADO`.
  - `Chamado`: Entidade que encapsula validações de entrada, proteção de leitura (`@property`) e regras de transição de status (`ABERTO` → `EM_ANDAMENTO` → `ENCERRADO`), registrando timestamps ISO 8601 em fuso horário **UTC** (`criado_em`, `iniciado_em`, `encerrado_em`).
- **Contrato e Persistência ([`repositorio.py`](repositorio.py) e [`repositorio_sqlite.py`](repositorio_sqlite.py)):**
  - `RepositorioChamados` (`Protocol`): Contrato de persistência desacoplado do banco.
  - `RepositorioMemoria`: Implementação em memória para testes rápidos de unidade.
  - `RepositorioSQLite`: Implementação concreta utilizando `sqlite3` nativo, queries parametrizadas (`?`) contra SQL Injection e atribuição de ID (`AUTOINCREMENT`) somente após a confirmação (`COMMIT`) da transação.
- **Serviço de Aplicação ([`sistema_chamados.py`](sistema_chamados.py)):**
  - `SistemaChamados`: Orquestra a criação, listagem, busca e mudanças de estado dos chamados persistindo as alterações por meio do repositório injetado.
- **Interface CLI ([`main.py`](main.py)):**
  - Ponto de entrada no terminal integrado ao `RepositorioSQLite` e operando exclusivamente através dos métodos de `SistemaChamados`.

## Banco de Dados SQLite

A tabela `chamados` é inicializada automaticamente no arquivo `helpdesk.db` (ignorado pelo Git) com a seguinte estrutura:

| Coluna | Tipo | Restrição | Descrição |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Identificador único gerado pelo banco |
| `titulo` | `TEXT` | `NOT NULL` | Título resumido do chamado |
| `descricao` | `TEXT` | `NOT NULL` | Descrição detalhada do problema |
| `status` | `TEXT` | `NOT NULL` | `ABERTO`, `EM_ANDAMENTO` ou `ENCERRADO` |
| `criado_em` | `TEXT` | `NOT NULL` | Timestamp ISO 8601 UTC de abertura |
| `iniciado_em` | `TEXT` | `NULL` | Timestamp ISO 8601 UTC de início do atendimento |
| `encerrado_em` | `TEXT` | `NULL` | Timestamp ISO 8601 UTC de encerramento |

## Dependências

O núcleo de persistência utiliza a biblioteca padrão do Python (`sqlite3`, `datetime`, `enum`, `typing`, `pathlib`). As dependências externas em [`requirements.txt`](requirements.txt) são:

- `pytest>=8.3.0` — Execução da suíte de testes automatizados.
- `python-dotenv>=1.0.1` — Gerenciamento seguro de variáveis de ambiente (`.env`).

## Como Executar

1. Clone este repositório e acesse a pasta do projeto.
2. Crie e ative o ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Execute a aplicação principal:

```powershell
python main.py
```

## Como Executar os Testes Automatizados

Os testes utilizam bancos temporários isolados (`tmp_path` do Pytest), sem afetar o banco de desenvolvimento `helpdesk.db`:

```powershell
# Executar toda a suíte de testes
pytest -v

# Ou diretamente pelo interpretador do ambiente virtual
.\.venv\Scripts\python.exe -m pytest -v
```
