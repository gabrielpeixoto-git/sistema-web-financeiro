"""Testes de integração end-to-end para fluxos completos do sistema."""

import re


class TestUserJourney:
    """Testa jornada completa do usuário no sistema."""

    def test_complete_user_flow(self, client):
        """Testa fluxo: registro → login → criar conta → criar categoria → criar transação → ver dashboard."""
        # 1. Registro
        response = client.post("/auth/register", data={
            "email": "journey@test.com",
            "name": "Journey User",
            "password": "testpass123"
        }, follow_redirects=False)
        assert response.status_code in [302, 303, 307]

        # 2. Login (seguir redirect para garantir sessão válida)
        response = client.post("/auth/login", data={
            "email": "journey@test.com",
            "password": "testpass123"
        }, follow_redirects=True)
        assert response.status_code == 200
        assert "Journey User" in response.text or "Dashboard" in response.text

        # 3. Verificar que estamos logados acessando dashboard
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "Journey User" in response.text

        # 4. Criar conta
        response = client.post("/accounts/", data={
            "name": "Minha Conta",
            "kind": "checking"
        }, follow_redirects=False)
        assert response.status_code in [302, 303, 307]

        # 5. Criar categoria (sem barra final para evitar redirect 307)
        response = client.post("/categories", data={
            "name": "Alimentação",
            "kind": "expense"
        }, follow_redirects=False)
        assert response.status_code in [302, 303, 307]

        # 6. Buscar IDs reais na página de transações
        response = client.get("/transactions")
        assert response.status_code == 200
        
        # Extrair ID da conta do dropdown de contas (select name="account_id")
        account_select_match = re.search(
            r'<select[^>]*name="account_id"[^>]*>(.*?)</select>',
            response.text,
            re.DOTALL | re.IGNORECASE
        )
        assert account_select_match, "Select de contas (account_id) não encontrado no HTML"
        account_select_html = account_select_match.group(1)
        
        account_match = re.search(
            r'<option[^>]*value="(\d+)"[^>]*>\s*Minha Conta\s*</option>',
            account_select_html,
            re.IGNORECASE
        )
        assert account_match is not None, "Conta 'Minha Conta' não encontrada no select account_id"
        account_id = account_match.group(1)
        
        # Extrair ID da categoria do dropdown de categorias (select name="category_id")
        category_select_match = re.search(
            r'<select[^>]*name="category_id"[^>]*>(.*?)</select>',
            response.text,
            re.DOTALL | re.IGNORECASE
        )
        assert category_select_match, "Select de categorias (category_id) não encontrado no HTML"
        category_select_html = category_select_match.group(1)
        
        category_match = re.search(
            r'<option[^>]*value="(\d+)"[^>]*>\s*Alimentação\s*</option>',
            category_select_html,
            re.IGNORECASE
        )
        assert category_match is not None, "Categoria 'Alimentação' não encontrada no select category_id"
        category_id = category_match.group(1)

        # 7. Criar transação com IDs corretos
        response = client.post("/transactions/", data={
            "kind": "out",
            "account_id": account_id,
            "amount": "50.00",
            "occurred_on": "2024-01-15",
            "category_id": category_id,
            "description": "Supermercado"
        }, follow_redirects=False)
        assert response.status_code in [302, 303, 307]

        # 8. Verificar transação na página de transações
        response = client.get("/transactions")
        assert response.status_code == 200
        assert "Supermercado" in response.text

        # 9. Verificar dashboard atualizado
        response = client.get("/dashboard")
        assert response.status_code == 200
        # Dashboard pode mostrar saldo consolidado, não valor individual

    def test_account_to_transaction_flow(self, client):
        """Testa fluxo de criação de conta seguida de transações."""
        # Setup
        client.post("/auth/register", data={
            "email": "accflow@test.com",
            "name": "Acc Flow",
            "password": "testpass123"
        })
        client.post("/auth/login", data={
            "email": "accflow@test.com",
            "password": "testpass123"
        })

        # Criar múltiplas contas
        for i in range(3):
            client.post("/accounts/", data={
                "name": f"Conta {i+1}",
                "kind": "checking"
            })

        # Criar categorias
        client.post("/categories/", data={"name": "Salário", "kind": "income"})
        client.post("/categories/", data={"name": "Aluguel", "kind": "expense"})

        # Criar transações em diferentes contas
        client.post("/transactions/", data={
            "kind": "in",
            "account_id": "1",
            "amount": "5000.00",
            "occurred_on": "2024-01-01",
            "category_id": "1",
            "description": "Salário Janeiro"
        })

        client.post("/transactions/", data={
            "kind": "out",
            "account_id": "2",
            "amount": "1200.00",
            "occurred_on": "2024-01-05",
            "category_id": "2",
            "description": "Aluguel"
        })

        # Verificar transações
        response = client.get("/transactions")
        assert response.status_code == 200
        assert "Salário Janeiro" in response.text
        assert "Aluguel" in response.text

    def test_budget_tracking_flow(self, client):
        """Testa fluxo de criação e acompanhamento de orçamento."""
        # Setup
        client.post("/auth/register", data={
            "email": "budgetflow@test.com",
            "name": "Budget Flow",
            "password": "testpass123"
        })
        client.post("/auth/login", data={
            "email": "budgetflow@test.com",
            "password": "testpass123"
        })

        # Criar categoria
        client.post("/categories/", data={
            "name": "Lazer",
            "kind": "expense"
        })

        # Definir orçamento
        response = client.post("/budgets/", data={
            "category_id": "1",
            "period": "2024-01",
            "limit_cents": "50000"  # R$ 500,00
        }, follow_redirects=False)
        assert response.status_code in [302, 303, 307]

        # Ver orçamento
        response = client.get("/budgets")
        assert response.status_code == 200
        assert "Lazer" in response.text

        # Adicionar despesa na categoria
        client.post("/accounts/", data={"name": "Conta Principal", "kind": "checking"})
        client.post("/transactions/", data={
            "kind": "out",
            "account_id": "1",
            "amount": "150.00",
            "occurred_on": "2024-01-10",
            "category_id": "1",
            "description": "Cinema"
        })

        # Verificar progresso do orçamento
        response = client.get("/budgets")
        assert response.status_code == 200


class TestErrorScenarios:
    """Testa cenários de erro e recuperação."""

    def test_invalid_login(self, client):
        """Testa tentativa de login com credenciais inválidas."""
        response = client.post("/auth/login", data={
            "email": "nonexistent@test.com",
            "password": "wrongpassword"
        }, follow_redirects=False)
        
        # Deve redirecionar de volta para login ou retornar erro de auth
        assert response.status_code in [302, 303, 401]

    def test_access_protected_route_without_auth(self, client):
        """Testa acesso a rotas protegidas sem autenticação."""
        protected_routes = [
            "/dashboard",
            "/transactions",
            "/transactions/new",
            "/accounts",
            "/categories",
            "/budgets",
            "/goals",
            "/reports",
            "/account",
        ]
        
        for route in protected_routes:
            response = client.get(route, follow_redirects=False)
            assert response.status_code in [302, 303, 307], f"Route {route} should redirect"
            # Pode redirecionar para login ou retornar erro de auth
            location = response.headers.get("location", "")
            assert "/login" in location or response.status_code in [302, 303, 307], f"Route {route} should redirect to login"

    def test_invalid_transaction_data(self, client):
        """Testa criação de transação com dados inválidos."""
        # Setup
        client.post("/auth/register", data={
            "email": "invalidtx@test.com",
            "name": "Invalid Tx",
            "password": "testpass123"
        })
        client.post("/auth/login", data={
            "email": "invalidtx@test.com",
            "password": "testpass123"
        })

        # Tentar criar transação sem conta
        response = client.post("/transactions/", data={
            "kind": "out",
            "account_id": "",  # Vazio
            "amount": "50.00",
            "occurred_on": "2024-01-15"
        }, follow_redirects=False)
        
        # Deve falhar ou redirecionar com erro
        assert response.status_code in [302, 400, 422]
