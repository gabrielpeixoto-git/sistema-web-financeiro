# AI Context - Finanças App

## 1. Objetivo do projeto

Construir um sistema full stack de finanças pessoais com aparência de produto real, mantendo arquitetura simples, modular e de baixo acoplamento.  
Princípio aplicado: complexidade nas regras de negócio, não na arquitetura.

Escopo funcional alvo:
- autenticação segura por usuário
- gestão financeira pessoal (contas, categorias, transações)
- visão analítica (dashboard e relatórios)
- rastreabilidade (auditoria) e operações utilitárias (CSV, tarefas em background)

---

## 2. Tecnologias utilizadas

### Backend e app
- Python 3.11+
- FastAPI
- Starlette + Jinja2 templates (renderização server-side)
- HTMX (interações progressivas no frontend)
- Tailwind via CDN

### Dados e migração
- SQLModel (ORM/modelos)
- SQLAlchemy (base do SQLModel)
- Alembic (migrações)
- SQLite em desenvolvimento (`dev.db`)
- PostgreSQL como alvo de produção (via `DATABASE_URL`)
- **`psycopg` + `psycopg-binary`** em `requirements.txt` (Windows: wrapper `libpq` sem instalação manual)

### Segurança e autenticação
- `passlib` (hash de senha com `pbkdf2_sha256`)
- `python-jose` para JWT
- Access token + refresh token
- Cookies HttpOnly para sessão (`access_token`, `refresh_jwt`, `refresh_cookie`)

### Qualidade e testes
- pytest (incl. `test_transactions_import_html.py`, `test_script_generate_notifications.py`, `test_rate_limit.py`)
- ruff (lint + format)
- **`python-dotenv`** em `requirements.txt` — carregamento opcional de `.env` na raiz (via `settings.py`)

### Dados de tempo
- `zoneinfo` (stdlib) + pacote **`tzdata`** no ambiente (necessário no Windows para IANA completo)
- variável `APP_TIMEZONE` (padrão `America/Sao_Paulo`): fallback global para “hoje” de competência
- **Timezone por usuário:** campo opcional `User.timezone` (IANA); `today_in_app(tz)` usa timezone do usuário nas rotas HTML quando preenchido
- **Notificações (env):** `NOTIFICATION_BUDGET_NEAR_PERCENT`, `NOTIFICATION_GOAL_NEAR_PERCENT`, `NOTIFICATION_DEDUPE_HOURS` — ver `settings.py` e `.env.example`

---

## 3. Estrutura de pastas

Estrutura principal atual:

```text
.
├─ AI_CONTEXT.md
├─ compose.yaml
├─ PROD_RUNBOOK.md
├─ financas_app/
│  ├─ app/
│     ├─ main.py
│     ├─ routes.py
│     ├─ settings.py
│     ├─ deps.py
│     ├─ common/
│     │  ├─ errors.py
│     │  ├─ money.py
│     │  ├─ dates.py
│     │  ├─ finance.py
│     │  ├─ security.py
│     │  ├─ rate_limit.py
│     │  └─ tasks.py
│     ├─ db/
│     │  ├─ engine.py          # get_engine() cacheado por DATABASE_URL
│     │  ├─ models.py
│     │  └─ migrations/
│     │     ├─ env.py
│     │     └─ versions/
│     │        ├─ 95786821c177_auth_tables.py
│     │        ├─ d7283f554f1f_financial_tables.py
│     │        ├─ daef646fda44_audit_notifications.py
│     │        ├─ b4e8a1c2d3f4_password_reset_token.py
│     │        ├─ c5f9b2e1a3d4_transaction_transfer_group.py
│     │        ├─ d6a0c3f2b4e5_recurring_rules.py
│     │        ├─ f8a2e5b6c7d9_monthly_budget.py
│     │        ├─ g9b3f6c8d0e1_financial_goal.py
│     │        ├─ e1c2a3b4d5f6_user_timezone.py
│     │        └─ 9580053f4420_add_profile_image_url_to_user_table.py
│     ├─ modules/
│     │  ├─ auth/
│     │  ├─ accounts/
│     │  ├─ categories/
│     │  ├─ transactions/        # service, routes_api/html, import_task.py (CSV compartilhado)
│     │  ├─ dashboard/
│     │  ├─ reports/
│     │  ├─ audit/             # service + routes_html (/audit)
│     │  ├─ notifications/
│     │  ├─ budgets/
│     │  ├─ goals/
│     │  └─ recurring/
│     ├─ templates/
│     │  ├─ base.html
│     │  ├─ home.html
│     │  ├─ account/
│     │  ├─ audit/
│     │  ├─ auth/
│     │  ├─ accounts/
│     │  ├─ categories/
│     │  ├─ transactions/
│     │  ├─ dashboard/
│     │  ├─ reports/
│     │  ├─ recurring/
│     │  ├─ budgets/
│     │  ├─ goals/
│     │  └─ notifications/
│     └─ static/
│  └─ scripts/
│     └─ generate_notifications.py   # cron: notificações para todos os usuários
├─ tests/
│  ├─ conftest.py
│  ├─ test_smoke.py
│  ├─ test_auth_flow.py
│  ├─ test_settings.py
│  ├─ test_main_startup.py
│  ├─ test_rate_limit.py
│  ├─ test_financial_rules.py
│  ├─ test_dashboard_reports.py
│  ├─ test_csv_import_export.py
│  ├─ test_audit_notifications.py
│  ├─ test_audit_ui.py
│  ├─ test_notifications_ui.py
│  ├─ test_account_timezone.py
│  ├─ test_recurring.py
│  ├─ test_budgets.py
│  ├─ test_goals.py
│  ├─ test_dates.py
│  ├─ test_categories.py
│  ├─ test_finance_common.py
│  ├─ test_transactions_import_api.py
│  ├─ test_transactions_import_html.py
│  ├─ test_script_generate_notifications.py
│  ├─ test_postgres_smoke.py
│  └─ test_postgres_migrations.py
├─ requirements.txt
├─ pyproject.toml
├─ alembic.ini
├─ .env.example
└─ README.md
```

---

## 4. Estado atual e funcionalidades implementadas

### Snapshot (abril/2026)

O núcleo do produto está **implementado e coberto por testes**. Com `pytest` no padrão do repositório: **89 testes coletados**, **87 passando** e **2 em skip** (PostgreSQL opcional: `test_postgres_smoke`, `test_postgres_migrations`) quando `TEST_DATABASE_URL` não está definida.

### Infra e persistência
- **`.env` na raiz do repositório:** carregado por **`python-dotenv`** em `get_settings()` (`override=False`: não sobrescreve variáveis já definidas no ambiente).
- **`get_engine()`** em `db/engine.py`: engine criado/cacheado por `DATABASE_URL`, evitando inconsistência entre testes que trocam o banco por fixture; `deps.get_session()` e `lifespan` usam `get_engine()`.
- **Docker Compose** (`compose.yaml`) para Postgres local de dev/test.
- **`PROD_RUNBOOK.md`**: checklist mínimo de deploy com PostgreSQL, Alembic e **job de notificações** (`python -m financas_app.scripts.generate_notifications`).
- **Testes Postgres:** `test_postgres_migrations.py` limpa o schema `public` antes de rodar Alembic (compatível com smoke que usa `create_all`).
- **Tarefas em memória:** `common/tasks.py` — `TaskState` com campo opcional **`meta`** (JSON leve) usado na importação CSV para `created` / `skipped` / `skip_reasons`.

### Autenticação e usuários
- cadastro, login, logout; `/me`; recuperação de senha; JWT + cookies; rate limit e headers; redirects HTML/HTMX
- páginas do menu exigem login (incl. **`/audit`**); testes cobrem redirect 303 para `/auth/login?msg=...`
- **`/account`:** perfil + edição de **timezone IANA** (`POST /account/timezone`)

### Núcleo financeiro
- CRUD contas, categorias, transações; transferências; recorrência; orçamentos; metas; isolamento por usuário; detalhe de categoria com período

### CSV (exportação e importação)
- **Módulo compartilhado:** `modules/transactions/import_task.py` — `read_import_csv_strict()` e `run_import_csv_task()` usados pela **API** e pelo **HTML** (uma única validação e um único worker).
- **Exportação:** `GET /api/transactions/export.csv` (JWT)
- **Importação assíncrona:** `POST /api/transactions/import` + `GET /api/transactions/tasks/{task_id}`; validação de extensão `.csv`, UTF-8 e cabeçalho mínimo
- **Erros 400 da API de import:** corpo JSON com **`detail`** (português), **`code`** estável (`invalid_file_extension`, `invalid_csv_encoding`, `invalid_csv_header`) e, no caso de cabeçalho, **`missing_columns`**
- **Resultado do processamento:** `import_csv_content` retorna `created`, `skipped`, **`skip_reasons`** (agregados) e até **20 entradas** em **`skip_samples`** (`line` no arquivo CSV, `reason`); o `detail` da tarefa em background inclui resumo dos motivos; **`GET /api/transactions/tasks/{id}`** expõe **`meta`** com `created`, `skipped`, `skip_reasons`, `skip_samples`
- **UI:** em `/transactions`, importação via HTMX (`POST /transactions/import`) com polling em **`GET /transactions/import-status/{task_id}`** e mensagens de erro de validação em fragmentos HTML

### Notificações
- Listagem `/notifications`; geração em background `/notifications/generate`
- **Políticas em `notifications.service.generate_for_user`:** `daily_summary`, `budget_over`, **`budget_near`**, `goal_overdue`, **`goal_near`**; limiares e deduplicação via env: **`NOTIFICATION_BUDGET_NEAR_PERCENT`**, **`NOTIFICATION_GOAL_NEAR_PERCENT`**, **`NOTIFICATION_DEDUPE_HOURS`** (ver `settings.py` / `.env.example`)
- **Cron / lote:** `python -m financas_app.scripts.generate_notifications` (mesmas envs da app; documentado em `PROD_RUNBOOK.md`)
- **UX:** filtro por `kind` (query); **marcar todas como lidas** (`POST /notifications/read_all`)

### Auditoria
- `AuditLog` em serviço
- **UI `/audit`:** listagem dos últimos eventos do usuário (reaproveita `audit.service.list_recent`)

### UX e frontend
- **Design System:** tema dark moderno, baseado em cores #0F172A (background), #1E293B (cards), #334155 (bordas)
- **Sidebar fixa:** navegação organizada em seções (Principal, Planejamento, Análise) com ícones Lucide
- **Lucide Icons:** ícones consistentes em todas as páginas (via CDN)
- **Chart.js:** gráficos de evolução financeira no dashboard
- **Cards estilizados:** border-radius 14px, hover effects, sombras sutis
- **Inputs dark:** fundo #1E293B, bordas #475569, texto branco, focus ring azul
- **Botões modernos:** gradientes, ícones, estados hover
- **Avatar/Foto de Perfil:** upload/remoção; exibição na sidebar; fallback com inicial do nome
- fragmentos HTMX em `templates/transactions/partials/` (`import_error.html`, `import_status.html`)

### Documentação de operação
- **`README.md`:** variáveis `NOTIFICATION_*`, importação CSV na UI, rate limit (incl. formulário HTMX de import), pasta `financas_app/scripts`

---

## 5. Pendências em relação ao escopo completo

| Área | Situação |
|------|----------|
| Timezone | **Concluído (usuário):** `User.timezone` + `today_in_app(override)` nas rotas relevantes |
| UI/UX Design System | **Concluído:** tema dark moderno aplicado em TODAS as páginas; sidebar fixa; Lucide Icons; cards estilizados; inputs dark; botões modernos |
| UI auditoria | **Concluído:** `/audit` |
| Avatar/Foto de Perfil | **Concluído:** upload/remoção de imagem; exibição consistente na sidebar de TODAS as páginas; fallback com inicial |
| Produção PostgreSQL | **Runbook + testes opcionais prontos;** validação final em ambiente real/deploy conforme necessidade |
| Hardening | Rate limit em memória; em produção, store distribuído só se necessário |
| Notificações | **Concluído:** thresholds + dedupe por env; script de cron em `financas_app/scripts/generate_notifications.py` |
| Importação CSV | **Concluído:** API endurecida + **UI HTMX** com resultado/polling; possível evoluir (preview por linha, relatório detalhado) |

---

## 6. Última frente e próximo passo

**Concluído recentemente (resumo):**
- **Testes Expandidos:** novos arquivos de teste criados:
  - `test_avatar_profile.py` - Testes para upload/remoção de avatar e exibição nas páginas
  - `test_health_check.py` - Testes para endpoint de monitoramento `/health`
  - `test_transactions_new.py` - Testes para rota `/transactions/new` (página dedicada de nova transação)
  - `test_integration_e2e.py` - Testes de integração end-to-end (jornada completa do usuário, fluxos de erro)
- **UI/UX Design System Redesign:** tema dark premium aplicado em TODAS as páginas; CSS global no `base.html` forçando cores dark; sidebar fixa com navegação organizada; Lucide Icons em todos os elementos; cards com border-radius 14px e hover effects; inputs estilizados com fundo escuro e bordas sutis; botões com gradientes e ícones; páginas atualizadas: Transações, Contas, Categorias, Metas, Orçamentos, Recorrência, Relatórios, Notificações, Auditoria, Minha Conta, Login/Register/Forgot/Reset
- **Avatar/Foto de Perfil:** campo `profile_image_url` no modelo User; rotas `/account/upload-profile` e `/account/remove-profile`; pasta `/uploads` configurada como static files; migração Alembic `9580053f4420` aplicada; todas as rotas HTML passam `user` para templates.
- **Importação CSV:** validação e worker centralizados em **`import_task.py`**; UI em **`/transactions`** (HTMX + polling); API com **`meta`** na consulta de tarefa; rate limit compartilhado entre API e formulário HTML
- **Notificações:** parâmetros **`NOTIFICATION_*`** em `Settings`; geração em lote via **`financas_app.scripts.generate_notifications`**; `generate_for_user` aceita overrides de limiar/dedupe para testes
- **Documentação:** `README.md` e **`AI_CONTEXT.md`** alinhados ao comportamento atual; runbook com cron de notificações
- **Testes:** cobertura ampliada (import HTML, script de notificações, políticas de threshold, `test_rate_limit`)

**Próximo passo de desenvolvimento sugerido:**
1. **Testes de Avatar:** adicionar testes para upload/remoção de foto de perfil, verificação de exibição em templates
2. **Produção:** validação final em deploy real com PostgreSQL, Alembic e job agendado do script de notificações (`PROD_RUNBOOK.md`); validar serving de arquivos de upload em produção
3. **Melhorias de UX (opcional):** crop/redimensionamento automático de imagens; preview antes de confirmar upload
4. **Hardening (só se necessário):** store distribuído para rate limit em ambiente multi-instância; revisão de headers de segurança e CORS se houver front separado

---

## 7. Deploy e Produção

### Docker Compose (recomendado)
- Arquivos: `Dockerfile`, `docker-compose.yml`, `DEPLOY.md`
- Serviços: PostgreSQL 15 + App FastAPI
- Comando: `docker-compose up --build -d`
- Health check: `GET /health-check` retorna status do banco

### Configurações de produção
- `APP_ENV=prod`: modo produção (sem auto-create de tabelas)
- `DATABASE_URL`: PostgreSQL obrigatório (ex: `postgresql://user:pass@db:5432/financas`)
- `APP_SECRET_KEY`: chave forte para JWT (mínimo 32 caracteres)
- `RATE_LIMIT_ENABLED=true`: rate limiting ativado

### Primeiro deploy
```bash
# 1. Configurar .env
cp .env.example .env
# Editar com valores seguros

# 2. Subir serviços
docker-compose up --build -d

# 3. Verificar saúde
curl http://localhost:8000/health-check
```

## 8. Notas rápidas de retomada

- Dev: `DATABASE_URL=sqlite:///./dev.db`; testes: `tmp_path` + env no `conftest` (incl. limites de rate limit altos para estabilidade).
- `prod`: `DATABASE_URL` PostgreSQL obrigatória; `APP_SECRET_KEY` forte; Alembic `upgrade head` antes de subir; startup em `dev` chama `SQLModel.metadata.create_all(get_engine())`; em `prod` apenas valida conexão.
- Arquitetura: monólito modular; serviços com regras; rotas finas.
- **Design System:** tema dark padrão (#0F172A background, #1E293B cards, #334155 bordas); Lucide Icons; Tailwind CSS; classes custom `card`, `card-hover`, `btn-primary`, `btn-secondary`, `btn-danger` definidas em `base.html`.
- **Cron notificações:** com o mesmo `.env` da app, `python -m financas_app.scripts.generate_notifications` (ver `PROD_RUNBOOK.md`).
- **Avatar/Foto de Perfil:** pasta `uploads/` na raiz do projeto; serving via `StaticFiles` em `/uploads`; migração Alembic `9580053f4420` aplicada; todas as rotas HTML passam `user` para templates.
- **Testes isolados:** arquivos que usam `SQLModel.metadata.create_all` em banco temporário devem importar `financas_app.app.db.models` antes do `create_all` (metadata completo, ex. FK `recurring_rule`).
