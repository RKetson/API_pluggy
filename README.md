# API Pluggy — Analisador Financeiro e Consolidador de Carteira 🏦✨

Uma API robusta, construída em Python com [FastAPI](https://fastapi.tiangolo.com/), projetada para integrar com o ecossistema de Open Finance via [Pluggy.ai](https://pluggy.ai/). Este submódulo permite sincronizar, anonimizar, categorizar e armazenar localmente o histórico financeiro e a carteira de investimentos do usuário, garantindo **100% de privacidade** e independência de serviços de nuvem pagos.

## 🔒 Foco em Privacidade e Segurança (Privacy-by-Design)

Este projeto foi desenhado sob o princípio de que **dados financeiros são altamente sensíveis**. Por isso, a arquitetura conta com:

- **Banco de Dados Local (Serverless):** Todo o histórico financeiro é armazenado localmente em um arquivo SQLite (`data/pluggy_db.sqlite`), sem necessidade de hospedar dados em nuvens como AWS ou GCP.
- **Criptografia de PII:** Dados como Nome do Titular e CPF/CNPJ são salvos no banco de dados fortemente criptografados (padrão militar `Fernet`), protegendo sua identidade caso o arquivo do banco de dados seja acessado indevidamente.
- **Mascaramento de Logs:** O sistema de logs intercepta e substitui CPFs e E-mails por `***` (asteriscos) antes de imprimi-los no console, garantindo que suas credenciais nunca vazem no terminal.
- **Integração Somente-Leitura:** A integração com a Pluggy é baseada no escopo Open Finance de leitura. A API **não tem poder transacional** (não realiza transferências, PIX ou pagamentos).

---

## 🛠️ Tecnologias Utilizadas

- **[FastAPI](https://fastapi.tiangolo.com/):** Framework web assíncrono e de alta performance.
- **[SQLAlchemy (2.0+)](https://www.sqlalchemy.org/):** ORM para modelagem e consulta do banco de dados.
- **[Pydantic V2](https://docs.pydantic.dev/latest/):** Validação estrita de dados e serialização.
- **[Structlog](https://www.structlog.org/en/stable/):** Logs estruturados e mascaramento de PII.
- **[Cryptography](https://cryptography.io/en/latest/):** Criptografia de ponta a ponta (Fernet).
- **[Pytest](https://docs.pytest.org/):** Cobertura de testes unitários e de integração.

---

## 🚀 Como Executar o Projeto Localmente

### 1. Pré-requisitos
- Python 3.10 ou superior instalado na máquina.
- Uma conta de desenvolvedor na [Pluggy.ai](https://dashboard.pluggy.ai/) para obter suas chaves (Client ID e Client Secret).

### 2. Configuração do Ambiente

Abra o terminal na pasta raiz da API (`API_pluggy/`) e siga os passos:

```bash
# 1. Crie um ambiente virtual
python -m venv .venv

# 2. Ative o ambiente virtual
# No Windows:
.venv\Scripts\activate
# No Linux/Mac:
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt
```

### 3. Configuração de Variáveis (O `.env`)

1. Localize o arquivo `.env.example` na pasta do projeto.
2. Crie uma cópia dele e renomeie a cópia para `.env`.
3. Preencha o `.env` com suas credenciais da Pluggy.
4. Gere uma chave de criptografia Fernet rodando o comando abaixo no seu terminal e cole-a no campo `DB_ENCRYPTION_KEY` do `.env`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> ⚠️ **ATENÇÃO:** O arquivo `.env` já está configurado no `.gitignore`. **Nunca** faça o commit das suas chaves de API reais para repositórios públicos.

### 4. Iniciando o Servidor

Com tudo configurado, rode o comando abaixo para iniciar o servidor web:

```bash
uvicorn main:app --reload
```

A API estará rodando no endereço `http://localhost:8000`.

---

## 📖 Testando a Integração (Swagger UI)

O FastAPI gera automaticamente uma documentação interativa das suas rotas. Para testar o funcionamento:

1. Acesse: **[http://localhost:8000/docs](http://localhost:8000/docs)**
2. **Gerar Token:** Utilize a rota `POST /api/v1/connect-token` para gerar um token de autorização.
3. **Conectar Banco:** O token gerado deve ser repassado ao seu Frontend (ou ao Dashboard da Pluggy) para gerar a conexão com o banco e obter um **`item_id`**.
4. **Sincronizar Dados:** Com o `item_id` em mãos, utilize a rota `POST /api/v1/items/{item_id}/sync` (deixando a data nula para puxar todo o histórico). Neste momento, a API se comunicará com o banco de dados, criará o arquivo SQLite e processará as transações.
5. **Consultas:** Brinque com os endpoints `GET /api/v1/transactions` e `GET /api/v1/investments/summary` para verificar seus relatórios financeiros locais e processados.

---

## 📁 Estrutura de Diretórios

```text
API_pluggy/
├── api/             # Rotas e controladores da API FastAPI
├── core/            # Configurações sensíveis, Logging e Criptografia
├── models/          # Modelagem das tabelas do Banco de Dados (SQLAlchemy)
├── schemas/         # Validação de I/O de dados (Pydantic)
├── services/        # Regras de Negócio, Conexão HTTP (Pluggy) e Algoritmos de Carteira
├── tests/           # Suite de testes com Pytest (Mocks e DB em Memória)
├── main.py          # Arquivo inicializador do Uvicorn e FastAPI
└── requirements.txt # Bibliotecas do projeto
```

*Nota: O banco de dados real (`pluggy_db.sqlite`) será gerado uma pasta acima (`../data/`), a fim de permitir o compartilhamento direto de dados com a raiz do projeto (ex: Frontend em Streamlit).*

---

## 🤝 Contribuindo
Sinta-se à vontade para realizar *forks*, abrir *issues* e enviar *Pull Requests*. O ecossistema financeiro brasileiro tem muito a se beneficiar com ferramentas open-source consolidadas.

**Lembre-se:** Antes de abrir um PR, rode a suite de testes localmente (`pytest`) para garantir a integridade do banco e do módulo de categorização.
