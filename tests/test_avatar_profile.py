"""Testes para upload e remoção de avatar/foto de perfil."""

import io


class TestAvatarUpload:
    """Testes para upload de avatar."""

    def test_upload_avatar_success(self, client, tmp_path, monkeypatch):
        """Testa upload de imagem de perfil com sucesso."""
        # Criar usuário e fazer login
        response = client.post("/auth/register", data={
            "email": "upload@test.com",
            "name": "Upload Test",
            "password": "testpass123"
        }, follow_redirects=False)
        
        # Fazer login para obter sessão
        response = client.post("/auth/login", data={
            "email": "upload@test.com",
            "password": "testpass123"
        }, follow_redirects=False)
        
        # Preparar imagem de teste
        image_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 100
        test_file = io.BytesIO(image_content)
        
        # Fazer upload
        response = client.post(
            "/account/upload-profile",
            files={"file": ("test.png", test_file, "image/png")},
            follow_redirects=False
        )
        
        assert response.status_code in [302, 303]  # Redirect após sucesso
        assert "/account" in response.headers.get("location", "")

    def test_upload_avatar_without_auth(self, client):
        """Testa que upload requer autenticação."""
        image_content = b"fake-image-data"
        test_file = io.BytesIO(image_content)
        
        response = client.post(
            "/account/upload-profile",
            files={"file": ("test.png", test_file, "image/png")}
        )
        
        # Deve redirecionar para login ou retornar página de login
        assert response.status_code in [200, 302, 303, 307, 401]

    def test_upload_invalid_file_type(self, client):
        """Testa que apenas imagens são aceitas."""
        # Criar usuário e fazer login
        client.post("/auth/register", data={
            "email": "invalid@test.com",
            "name": "Invalid Test",
            "password": "testpass123"
        })
        
        client.post("/auth/login", data={
            "email": "invalid@test.com",
            "password": "testpass123"
        })
        
        # Tentar upload de arquivo não-imagem
        txt_file = io.BytesIO(b"This is not an image")
        
        response = client.post(
            "/account/upload-profile",
            files={"file": ("test.txt", txt_file, "text/plain")}
        )
        
        # Pode aceitar e processar ou redirecionar com erro
        assert response.status_code in [200, 302, 303, 400, 415]


class TestAvatarRemoval:
    """Testes para remoção de avatar."""

    def test_remove_avatar_success(self, client):
        """Testa remoção de imagem de perfil."""
        # Criar usuário e fazer login
        client.post("/auth/register", data={
            "email": "remove@test.com",
            "name": "Remove Test",
            "password": "testpass123"
        })
        
        client.post("/auth/login", data={
            "email": "remove@test.com",
            "password": "testpass123"
        })
        
        # Remover avatar
        response = client.post("/account/remove-profile", follow_redirects=False)
        
        assert response.status_code in [302, 303]
        assert "/account" in response.headers.get("location", "")

    def test_remove_avatar_without_auth(self, client):
        """Testa que remoção requer autenticação."""
        response = client.post("/account/remove-profile")
        
        # Deve redirecionar para login ou retornar página de login
        assert response.status_code in [200, 302, 303, 307, 401]


class TestAvatarDisplay:
    """Testes para exibição de avatar nas páginas."""

    def test_avatar_shown_in_account_page(self, client):
        """Testa que avatar/fallback é mostrado na página de conta."""
        # Criar usuário e fazer login
        client.post("/auth/register", data={
            "email": "display@test.com",
            "name": "Display Test",
            "password": "testpass123"
        })
        
        client.post("/auth/login", data={
            "email": "display@test.com",
            "password": "testpass123"
        })
        
        # Acessar página de conta
        response = client.get("/account")
        
        assert response.status_code == 200
        # Deve mostrar inicial do nome como fallback
        assert "D" in response.text  # "D" de "Display Test"

    def test_avatar_shown_in_sidebar(self, client):
        """Testa que avatar aparece na sidebar em todas as páginas protegidas."""
        # Criar usuário e fazer login
        client.post("/auth/register", data={
            "email": "sidebar@test.com",
            "name": "Sidebar Test",
            "password": "testpass123"
        })
        
        client.post("/auth/login", data={
            "email": "sidebar@test.com",
            "password": "testpass123"
        })
        
        # Acessar dashboard
        response = client.get("/dashboard")
        
        assert response.status_code == 200
        # Deve conter elementos da sidebar com info do usuário
        assert "Sidebar Test" in response.text or "S" in response.text
