# tests/integration/test_orders_api.py
import pytest


@pytest.mark.integration
class TestOrders:
    def _setup_panier(self, client, user_id, stock=10, price=100.0, quantity=2):
        p = client.post(
            "/products/",
            json={"name": "Produit Commande", "price": price, "stock": stock},
        ).json()
        client.post(
            f"/cart/?user_id={user_id}",
            json={"product_id": p["id"], "quantity": quantity},
        )
        return p

    def test_creation_commande_valide(self, client):
        self._setup_panier(client, user_id=200)
        response = client.post("/orders/", json={"user_id": 200})
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["total_ttc"] > 0

    def test_total_ttc_correct(self, client):
        """100€ HT x 2 x 1.20 = 240€ TTC."""
        self._setup_panier(client, user_id=201, price=100.0, quantity=2)
        order = client.post("/orders/", json={"user_id": 201}).json()
        assert order["total_ht"] == pytest.approx(200.0, rel=1e-2)
        assert order["total_ttc"] == pytest.approx(240.0, rel=1e-2)

    def test_commande_decremente_stock(self, client):
        """Après commande de 2, le stock passe de 10 à 8."""
        p = self._setup_panier(client, user_id=202, stock=10, quantity=2)
        client.post("/orders/", json={"user_id": 202})
        updated = client.get(f"/products/{p['id']}").json()
        assert updated["stock"] == 8

    def test_commande_vide_le_panier(self, client):
        self._setup_panier(client, user_id=203)
        client.post("/orders/", json={"user_id": 203})
        cart = client.get("/cart/203").json()
        assert cart["items"] == []

    def test_panier_vide_retourne_400(self, client):
        response = client.post("/orders/", json={"user_id": 9999})
        assert response.status_code == 400

    def test_commande_avec_coupon(self, client, api_coupon):
        """100€ HT × 1 × 1.20 = 120€ TTC → -10% = 108€."""
        p = client.post(
            "/products/", json={"name": "PC", "price": 100.0, "stock": 5}
        ).json()
        client.post("/cart/?user_id=204", json={"product_id": p["id"], "quantity": 1})
        order = client.post(
            "/orders/", json={"user_id": 204, "coupon_code": api_coupon["code"]}
        ).json()
        assert order["total_ttc"] == pytest.approx(108.0, rel=1e-2)
        assert order["coupon_code"] == api_coupon["code"]

    def test_statut_pending_vers_confirmed(self, client):
        self._setup_panier(client, user_id=205)
        order = client.post("/orders/", json={"user_id": 205}).json()
        response = client.patch(
            f"/orders/{order['id']}/status", json={"status": "confirmed"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    def test_transition_invalide_400(self, client):
        """pending → shipped directement est interdit."""
        self._setup_panier(client, user_id=206)
        order = client.post("/orders/", json={"user_id": 206}).json()
        response = client.patch(
            f"/orders/{order['id']}/status", json={"status": "shipped"}
        )
        assert response.status_code == 400

    # Q3.3
    def test_coupon_inexistant_retourne_404(self, client):
        """Un coupon inexistant lors de la commande → 404."""
        self._setup_panier(client, user_id=207)
        response = client.post(
            "/orders/", json={"user_id": 207, "coupon_code": "FAKECODE"}
        )
        assert response.status_code == 404

    # Q3.4
    def test_get_commande_par_id(self, client):
        """Créer une commande puis la récupérer par son id."""
        self._setup_panier(client, user_id=208)
        order = client.post("/orders/", json={"user_id": 208}).json()
        response = client.get(f"/orders/{order['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == order["id"]
        assert data["total_ttc"] == pytest.approx(order["total_ttc"], rel=1e-2)
        assert data["status"] == "pending"
