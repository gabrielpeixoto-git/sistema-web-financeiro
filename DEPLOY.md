# 🚀 Deploy - Finanças App

Guia de deploy para produção usando Docker e PostgreSQL.

## 📋 Pré-requisitos

- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM mínimo
- 10GB espaço em disco

## 🚀 Deploy com Docker Compose

### 1. Configurar variáveis de ambiente

```bash
# Copiar exemplo
cp .env.example .env

# Editar .env com valores seguros
APP_SECRET_KEY=your-super-secret-key-here-min-32-chars
```

### 2. Subir serviços

```bash
# Build e start
docker-compose up --build -d

# Ver logs
docker-compose logs -f app

# Verificar status
docker-compose ps
```

### 3. Primeiro acesso

- Acesse: http://localhost:8000
- Crie uma conta de usuário
- O sistema está pronto para uso!

## 🔄 Comandos úteis

```bash
# Parar serviços
docker-compose down

# Parar e remover volumes (⚠️ perde dados!)
docker-compose down -v

# Reiniciar app
docker-compose restart app

# Ver logs
docker-compose logs -f

# Executar comandos no container
docker-compose exec app alembic revision --autogenerate -m "description"
docker-compose exec app python -m financas_app.scripts.generate_notifications
```

## 🗄️ Backup do banco

```bash
# Backup
docker-compose exec db pg_dump -U financas financas > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T db psql -U financas financas < backup_20240101.sql
```

## ☁️ Deploy em produção (VPS/Cloud)

### 1. Preparar servidor

```bash
# Instalar Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo apt install docker-compose-plugin
```

### 2. Copiar arquivos

```bash
# Via SCP ou git clone
scp -r . user@server:/opt/financas-app/
ssh user@server "cd /opt/financas-app && docker-compose up -d"
```

### 3. Configurar Nginx (reverse proxy)

```nginx
server {
    listen 80;
    server_name financas.seudominio.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static {
        alias /opt/financas-app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location /uploads {
        alias /opt/financas-app/uploads;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 4. SSL com Certbot

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d financas.seudominio.com
```

## 🔒 Segurança em produção

### Variáveis obrigatórias

```env
APP_ENV=prod
APP_SECRET_KEY=gerar-chave-segura-32-caracteres+
DATABASE_URL=postgresql://user:pass@host:5432/db
RATE_LIMIT_ENABLED=true
```

### Gerar secret key segura

```python
import secrets
print(secrets.token_urlsafe(32))
```

### Firewall recomendado

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

## 📊 Monitoramento

### Health check

```bash
# Verificar saúde da aplicação
curl http://localhost:8000/health

# Health check do Docker
docker-compose exec app curl -f http://localhost:8000/ || exit 1
```

### Logs centralizados (opcional)

```yaml
# Adicionar ao docker-compose.yml
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
```

## 🔄 CI/CD (GitHub Actions exemplo)

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to VPS
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/financas-app
            git pull origin main
            docker-compose down
            docker-compose up --build -d
```

## 📞 Suporte

Em caso de problemas:
1. Verifique logs: `docker-compose logs -f`
2. Verifique saúde: `docker-compose ps`
3. Verifique conexão DB: `docker-compose exec db pg_isready -U financas`

---
**Pronto para produção!** 🎉
