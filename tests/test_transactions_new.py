"""Testes para a rota /transactions/new (página dedicada de nova transação)."""


class TestTransactionsNewPage:
    """Testes para página de nova transação."""

    def test_new_transaction_page_requires_auth(self, client):
        """Testa que página requer autenticação."""
        response = client.get("/transactions/new", follow_redirects=False)
        
        # Deve redirecionar para login (aceita 302, 303, 307)
        assert response.status_code in [302, 303, 307]
        assert "/login" in response.headers.get("location", "")

    def test_new_transaction_page_loads(self, client):
        """Testa que página carrega corretamente para usuário autenticado."""
        # Criar usuário
        client.post("/auth/register", data={
            "email": "txnew@test.com",
            "name": "Tx New Test",
            "password": "testpass123"
        })
        
        # Fazer login
        client.post("/auth/login", data={
            "email": "txnew@test.com",
            "password": "testpass123"
        })
        
        # Acessar página
        response = client.get("/transactions/new")
        
        assert response.status_code == 200
        # Verificar elementos da página
        assert "Nova Transação" in response.text
        assert "Receita" in response.text
        assert "Despesa" in response.text

    def test_new_transaction_page_has_form(self, client):
        """Testa que página contém formulário completo."""
        # Criar usuário e logar
        client.post("/auth/register", data={
            "email": "txform@test.com",
            "name": "Tx Form Test",
            "password": "testpass123"
        })
        client.post("/auth/login", data={
            "email": "txform@test.com",
            "password": "testpass123"
        })
        
        response = client.get("/transactions/new")
        
        assert response.status_code == 200
        # Verificar campos do formulário
        assert 'name="kind"' in response.text
        assert 'name="account_id"' in response.text
        assert 'name="amount"' in response.text
        assert 'name="occurred_on"' in response.text
        assert 'name="category_id"' in response.text
        assert 'name="description"' in response.text

    def test_new_transaction_page_has_accounts_dropdown(self, client):
        """Testa que dropdown de contas é preenchido."""
        # Criar usuário e logar
        client.post("/auth/register", data={
            "email": "txacc@test.com",
            "name": "Tx Acc Test",
            "password": "testpass123"
        })
        client.post("/auth/login", data={
            "email": "txacc@test.com",
            "password": "testpass123"
        })
        
        # Criar uma conta
        client.post("/accounts/", data={
            "name": "Conta Teste",
            "kind": "checking"
        })
        
        response = client.get("/transactions/new")
        
        assert response.status_code == 200
        # Deve conter a conta criada no dropdown
        assert "Conta Teste" in response.text

    def test_new_transaction_page_has_categories_dropdown(self, client):
        """Testa que dropdown de categorias é preenchido."""
        # Criar usuário e logar
        client.post("/auth/register", data={
            "email": "txcat@test.com",
            "name": "Tx Cat Test",
            "password": "testpass123"
        })
        client.post("/auth/login", data={
            "email": "txcat@test.com",
            "password": "testpass123"
        })
        
        # Criar uma categoria
        client.post("/categories/", data={
            "name": "Categoria Teste",
            "kind": "expense"
        })
        
        response = client.get("/transactions/new")
        
        assert response.status_code == 200
        # Deve conter a categoria criada no dropdown
        assert "Categoria Teste" in response.text

    def test_new_transaction_page_form_submission(self, client):
        """Testa que formulário envia para o endpoint correto."""
        # Criar usuário e logar
        client.post("/auth/register", data={
            "email": "txsubmit@test.com",
            "name": "Tx Submit Test",
            "password": "testpass123"
        })
        client.post("/auth/login", data={
            "email": "txsubmit@test.com",
            "password": "testpass123"
        })
        
        # Criar conta
        client.post("/accounts/", data={
            "name": "Conta Submit",
            "kind": "checking"
        })
        
        response = client.get("/transactions/new")
        
        assert response.status_code == 200
        # Verificar que o form posta para /transactions/
        assert 'action="/transactions/"' in response.text or "action=/transactions/" in response.text
        assert 'method="post"' in response.text
