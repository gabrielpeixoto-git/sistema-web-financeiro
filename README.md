# Finanças App

Aplicação completa de gestão financeira pessoal construída com **FastAPI**, **SQLModel**, **HTMX** e **Tailwind CSS**. Sistema monolítico modular com interface moderna, responsiva e modo escuro.

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-green.svg)](https://fastapi.tiangolo.com)
[![HTMX](https://img.shields.io/badge/HTMX-1.9+-orange.svg)](https://htmx.org)
[![Tailwind](https://img.shields.io/badge/Tailwind-3.0+-cyan.svg)](https://tailwindcss.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Funcionalidades

### Core
- **Autenticação JWT** - Login, registro, refresh token, recuperação de senha
- **Dashboard** - Visão geral com gráficos de evolução do saldo e contribuição por categoria
- **Gestão de Contas** - CRUD de contas bancárias com saldo em tempo real
- **Categorias** - Organização personalizada de receitas e despesas

### Transações
- **CRUD Completo** - Lançamentos com data, valor, descrição, conta e categoria
- **Transferências** - Movimentação entre contas com registro automático
- **Importação CSV** - Upload em lote com preview, validação e processamento em background
- **Exportação CSV** - Download dos lançamentos no formato compatível com importação

### Planejamento
- **Recorrência** - Regras automáticas (diária, semanal, mensal) com materialização de transações
- **Orçamentos** - Definição de limites mensais por categoria com alertas de proximidade
- **Metas** - Objetivos financeiros com acompanhamento de progresso e prazos

### Relatórios & Análise
- **Relatórios Filtrados** - Por período, conta e categoria com KPIs visuais
- **Gráficos Interativos** - Chart.js com gráficos de pizza (categorias) e barras (tendência mensal)
- **Exportação PDF** - Geração de relatórios profissionais para download
- **Auditoria** - Log completo de ações do usuário para rastreabilidade

### Notificações
- **Notificações In-App** - Alertas sobre orçamentos estourados, metas próximas e resumo diário
- **Lembretes por Email** - Notificações automáticas de contas a pagar (SMTP configurável)
- **Preferências** - Usuário pode habilitar/desabilitar lembretes por email

### UX/UI
- **Design Moderno** - Interface dark mode com paleta de cores profissional
- **Responsivo** - Sidebar adaptável, menu mobile, layout fluido
- **HTMX** - Interações dinâmicas sem recarregar a página
- **Ícones Lucide** - Biblioteca de ícones consistente

---

## Stack Tecnológico

| Camada | Tecnologia |
|--------|------------|
| Backend | FastAPI + SQLModel + Pydantic |
| Banco de Dados | SQLite (dev) / PostgreSQL (prod) |
| Migrations | Alembic |
| Frontend | HTMX + Jinja2 Templates |
| CSS | Tailwind CSS (CDN) |
| Gráficos | Chart.js |
| Ícones | Lucide Icons |
| PDF | ReportLab |
| Email | SMTP (Python smtplib) |
| Testes | Pytest |

---

## Arquitetura

```
financas_app/
├── app/
│   ├── common/           # Utilitários (datas, moeda, email, pdf, tasks)
│   ├── db/              # Configuração do banco e migrations
│   ├── deps.py          # Dependências FastAPI (sessão, auth)
│   ├── modules/         # Módulos de negócio
│   │   ├── accounts/    # Contas bancárias
│   │   ├── auth/        # Autenticação
│   │   ├── budgets/     # Orçamentos
│   │   ├── categories/  # Categorias
│   │   ├── dashboard/   # Dashboard e KPIs
│   │   ├── goals/       # Metas financeiras
│   │   ├── notifications/ # Notificações e email
│   │   ├── recurring/   # Transações recorrentes
│   │   ├── reports/     # Relatórios e PDF
│   │   └── transactions/# Transações e CSV
│   ├── routes.py        # Rotas principais
│   ├── settings.py      # Configurações
│   └── templates/       # Templates Jinja2
├── tests/               # Testes automatizados
├── alembic.ini          # Configuração Alembic
├── docker-compose.yml   # Docker para PostgreSQL
├── Dockerfile           # Container da aplicação
└── requirements.txt     # Dependências Python
```

---

## Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/financas-app.git
cd financas-app
```

### 2. Crie o ambiente virtual

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz:

```bash
# Obrigatório
APP_SECRET_KEY=sua-chave-secreta-aqui

# Banco de dados (dev)
DATABASE_URL=sqlite:///./dev.db

# Banco de dados (prod)
# DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/financas

# Timezone
APP_TIMEZONE=America/Sao_Paulo

# SMTP para lembretes por email (opcional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-app
SMTP_FROM=seu-email@gmail.com
SMTP_TLS=true
EMAIL_REMINDER_DAYS=3

# Notificações
NOTIFICATION_BUDGET_NEAR_PERCENT=80
NOTIFICATION_GOAL_NEAR_PERCENT=80
NOTIFICATION_DEDUPE_HOURS=24
```

---

## Execução

### Desenvolvimento

```bash
python -m uvicorn financas_app.app.main:app --reload
```

Acesse: http://localhost:8000

### Produção

```bash
# Usando Uvicorn
gunicorn financas_app.app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Ou Docker
docker-compose up -d
```

---

## Uso do CLI

```bash
# Enviar lembretes por email para todos os usuários
python -m financas_app.cli send-email-reminders
```

---

## Capturas de Tela

<img width="1902" height="947" alt="Captura de tela_18-4-2026_13038_localhost"
src="https://github.com/user-attachments/assets/b0b50f67-c6e6-4e07-aa0c-32a53689342a" />

<img width="1794" height="975" alt="Captura de tela_18-4-2026_1340_localhost" src="https://github.com/user-attachments/assets/376acdf9-c23a-45f9-a452-112955cdcc8e" />

<img width="1794" height="889" alt="Captura de tela_18-4-2026_13419_localhost" src="https://github.com/user-attachments/assets/f1782655-3d5f-4c1c-a6ff-490b8ccb6c9b" />

## Funcionalidades Detalhadas

### Importação/Exportação CSV
- Formato: `date,kind,account_name,category_name,amount,description`
- Validação automática de contas e categorias
- Preview antes de confirmar importação
- Processamento em background ( não bloqueia a UI)

### Relatórios PDF
- Resumo do período (receitas, despesas, resultado)
- Despesas por categoria (top 10)
- Evolução mensal
- Layout profissional com tabelas estilizadas

### Notificações por Email
- Lembrete de contas a pagar (dias configuráveis antes do vencimento)
- Detecção automática de recorrências
- Cooldown de 24h (evita spam)
- Template HTML responsivo

### Segurança
- Senhas hasheadas com bcrypt
- Tokens JWT com expiração configurável
- Rate limiting em endpoints sensíveis
- Proteção contra CSRF via cookies SameSite

---

## Testes

```bash
pytest
```

---

## Roadmap

- [x] Autenticação JWT
- [x] Dashboard com gráficos
- [x] CRUD de transações
- [x] Transferências entre contas
- [x] Importação/Exportação CSV
- [x] Recorrência de transações
- [x] Orçamentos e metas
- [x] Relatórios com filtros
- [x] Exportação PDF
- [x] Notificações por email
- [ ] Multi-moeda (USD, EUR)
- [ ] API pública com webhooks
- [ ] Anexos em transações (comprovantes)
- [ ] Modo offline/PWA
- [ ] Importação OFX (extratos bancários)

---

## Contribuição

Contribuições são bem-vindas! Abra uma issue ou pull request.

---

## Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.

---

## Autor

**Gabriel Azambuja Peixoto**

Desenvolvedor Python focado em aplicações web e automação.

- GitHub: https://github.com/gabrielpeixoto-git

---

## Links

- [FastAPI](https://fastapi.tiangolo.com)
- [SQLModel](https://sqlmodel.tiangolo.com)
- [HTMX](https://htmx.org)
- [Tailwind CSS](https://tailwindcss.com)
