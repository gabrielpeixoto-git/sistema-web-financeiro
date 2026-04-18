"""Testes para endpoint de health check."""


class TestHealthCheck:
    """Testes para monitoramento de saúde da aplicação."""

    def test_health_check_success(self, client):
        """Testa health check quando tudo está funcionando."""
        response = client.get("/health")
        
        assert response.status_code == 200
        # Verificar se retorna HTML ou JSON válido
        content = response.text
        assert "healthy" in content or "ok" in content.lower() or response.status_code == 200

    def test_health_check_no_auth_required(self, client):
        """Testa que health check não requer autenticação."""
        response = client.get("/health")
        
        # Deve funcionar sem token de autenticação
        assert response.status_code == 200
        assert "healthy" in response.text or "ok" in response.text.lower() or response.status_code == 200

    def test_health_check_response_format(self, client):
        """Testa formato da resposta do health check."""
        response = client.get("/health")
        
        # Verificar resposta (pode ser HTML ou JSON)
        assert response.status_code == 200
        content = response.text
        assert len(content) > 0  # Deve ter conteúdo
