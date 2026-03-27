# tests/integration/test_cart_api.py
import pytest


@pytest.mark.integration
class TestCart:
    def _creer_produit(self, client, stock=10):
        r = client.post("/products/", json={
            "name": "Produit Test", "price": 50.0, "stock": stock
        })
        assert r.status_code == 201
        return r.json()

    def test_ajout_produit_au_panier(self, client):
        p = self._creer_produit(client)
        response = client.post("/cart/?user_id=100", json={
            "product_id": p["id"], "quantity": 2
        })
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == 100
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2

    def test_sous_total_calcule(self, client):
        """50€ HT × 2 × 1.20 TVA = 120€ TTC."""
        p = self._creer_produit(client)
        client.post("/cart/?user_id=101", json={
            "product_id": p["id"], "quantity": 2
        })
        response = client.get("/cart/101")
        assert response.status_code == 200
        assert response.json()["sous_total"] == pytest.approx(120.0, rel=1e-2)

    def test_ajout_stock_insuffisant_400(self, client):
        p = self._creer_produit(client, stock=0)
        response = client.post("/cart/?user_id=102", json={
            "product_id": p["id"], "quantity": 1
        })
        assert response.status_code == 400

    def test_ajout_meme_produit_incremente_quantite(self, client):
        p = self._creer_produit(client, stock=20)
        client.post("/cart/?user_id=103", json={
            "product_id": p["id"], "quantity": 2
        })
        client.post("/cart/?user_id=103", json={
            "product_id": p["id"], "quantity": 3
        })
        cart = client.get("/cart/103").json()
        assert cart["items"][0]["quantity"] == 5

    def test_vider_panier(self, client):
        p = self._creer_produit(client)
        client.post("/cart/?user_id=104", json={
            "product_id": p["id"], "quantity": 1
        })
        response = client.delete("/cart/104")
        assert response.status_code == 204
        cart = client.get("/cart/104").json()
        assert cart["items"] == []