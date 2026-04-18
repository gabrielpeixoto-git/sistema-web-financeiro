## Produção (PostgreSQL) — Runbook enxuto

### Requisitos
- **PostgreSQL** acessível pela app (rede/SG liberados).
- **Migrações Alembic** como fonte de verdade (a app não roda `create_all()` em `prod`).
- **Segredo forte** em `APP_SECRET_KEY` (>= 16 chars).

### Variáveis de ambiente mínimas
- `APP_ENV=prod`
- `APP_SECRET_KEY=<secreto forte>`
- `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname`

Opcional:
- `APP_TIMEZONE=America/Sao_Paulo` (padrão)

### Checklist antes de subir
- `DATABASE_URL` **não** pode ser SQLite em `prod`.
- `APP_SECRET_KEY` **não** pode ser fraca/default (`change-me`, `dev-secret`, etc.).
- Banco existe e credenciais têm permissão de DDL para aplicar migrações.

### Aplicar migrações
Rode no ambiente com as env vars configuradas:

```bash
alembic upgrade head
```

### Subir a aplicação

```bash
python -m uvicorn financas_app.app.main:app --host 0.0.0.0 --port 8000
```

O startup em `prod` valida conexão com o banco; se falhar, a app não sobe.

### Verificações rápidas pós-deploy
- `GET /health` deve responder `ok`
- Login, criação de transação e dashboard carregando sem erro

### Notificações em lote (cron / scheduler)
A UI expõe “Gerar notificações” por usuário logado. Em produção, você pode agendar o mesmo trabalho para **todos os usuários** sem HTTP:

```bash
python -m financas_app.scripts.generate_notifications
```

Use as mesmas variáveis de ambiente da app (`APP_ENV`, `APP_SECRET_KEY`, `DATABASE_URL`, etc.). O comando imprime `users=N notifications_created=M` e encerra. Opcional: `NOTIFICATION_*` em `.env.example` ajustam percentuais e deduplicação.

