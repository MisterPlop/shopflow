# tests/unit/test_cart_service.py
import pytest

from app.models import Product
from app.services.cart import (
    ajouter_au_panier,
    calculer_sous_total,
    calculer_total_ttc,
    get_or_create_cart,
    retirer_du_panier,
    vider_panier,
)

REDIS_MOCK_PATH = "app.services.stock.redis_client"


# ---------------------------------------------------------------------------
# get_or_create_cart
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetOrCreateCart:
    def test_cree_panier_si_absent(self, db_session):
        """Aucun panier pour user 42 → doit en créer un."""
        cart = get_or_create_cart(user_id=42, session=db_session)
        assert cart is not None
        assert cart.user_id == 42
        assert cart.id is not None

    def test_retourne_panier_existant(self, db_session):
        """Appel deux fois pour le même user → même panier retourné."""
        cart1 = get_or_create_cart(user_id=1, session=db_session)
        cart2 = get_or_create_cart(user_id=1, session=db_session)
        assert cart1.id == cart2.id

    def test_paniers_differents_par_user(self, db_session):
        """Deux users distincts → deux paniers distincts."""
        cart_a = get_or_create_cart(user_id=10, session=db_session)
        cart_b = get_or_create_cart(user_id=11, session=db_session)
        assert cart_a.id != cart_b.id


# ---------------------------------------------------------------------------
# ajouter_au_panier
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAjouterAuPanier:
    def test_ajout_nominal(self, product_sample, db_session):
        """Ajout d'un produit avec stock suffisant → CartItem créé."""
        cart = ajouter_au_panier(product_sample, 2, user_id=1, session=db_session)
        assert len(cart.items) == 1
        assert cart.items[0].quantity == 2
        assert cart.items[0].product_id == product_sample.id

    def test_ajout_incremente_si_produit_deja_present(self, product_sample, db_session):
        """Même produit ajouté deux fois → quantity cumulée."""
        ajouter_au_panier(product_sample, 3, user_id=1, session=db_session)
        cart = ajouter_au_panier(product_sample, 2, user_id=1, session=db_session)
        assert cart.items[0].quantity == 5

    def test_quantite_zero_leve_exception(self, product_sample, db_session):
        with pytest.raises(ValueError, match="invalide"):
            ajouter_au_panier(product_sample, 0, user_id=1, session=db_session)

    def test_quantite_negative_leve_exception(self, product_sample, db_session):
        with pytest.raises(ValueError, match="invalide"):
            ajouter_au_panier(product_sample, -3, user_id=1, session=db_session)

    def test_stock_insuffisant_leve_exception(self, product_sample, db_session):
        """Demander plus que le stock disponible → ValueError."""
        with pytest.raises(ValueError, match="insuffisant"):
            ajouter_au_panier(product_sample, 999, user_id=1, session=db_session)

    def test_plusieurs_produits_dans_panier(self, db_session):
        """Deux produits différents → deux CartItems distincts."""
        p1 = Product(name="Clavier", price=50.0, stock=5)
        p2 = Product(name="Souris", price=25.0, stock=8)
        db_session.add_all([p1, p2])
        db_session.commit()
        db_session.refresh(p1)
        db_session.refresh(p2)

        ajouter_au_panier(p1, 1, user_id=2, session=db_session)
        cart = ajouter_au_panier(p2, 2, user_id=2, session=db_session)
        assert len(cart.items) == 2


# ---------------------------------------------------------------------------
# retirer_du_panier
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRetirerDuPanier:
    def test_retrait_nominal(self, product_sample, db_session):
        """Produit présent dans le panier → supprimé sans erreur."""
        cart = ajouter_au_panier(product_sample, 1, user_id=3, session=db_session)
        cart = retirer_du_panier(cart, product_sample.id, session=db_session)
        assert len(cart.items) == 0

    def test_retrait_produit_absent_leve_exception(self, product_sample, db_session):
        """Produit inexistant dans le panier → ValueError."""
        cart = get_or_create_cart(user_id=4, session=db_session)
        with pytest.raises(ValueError, match="non trouvé"):
            retirer_du_panier(cart, product_id=9999, session=db_session)


# ---------------------------------------------------------------------------
# vider_panier
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestViderPanier:
    def test_vider_supprime_tous_les_items(self, db_session):
        """Panier avec 2 produits → vide après appel."""
        p1 = Product(name="A", price=10.0, stock=5)
        p2 = Product(name="B", price=20.0, stock=5)
        db_session.add_all([p1, p2])
        db_session.commit()
        db_session.refresh(p1)
        db_session.refresh(p2)

        ajouter_au_panier(p1, 1, user_id=5, session=db_session)
        cart = ajouter_au_panier(p2, 1, user_id=5, session=db_session)
        cart = vider_panier(cart, session=db_session)
        assert len(cart.items) == 0

    def test_vider_panier_deja_vide(self, db_session):
        """Vider un panier déjà vide ne lève pas d'exception."""
        cart = get_or_create_cart(user_id=6, session=db_session)
        cart = vider_panier(cart, session=db_session)
        assert len(cart.items) == 0


# ---------------------------------------------------------------------------
# calculer_sous_total / calculer_total_ttc
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCalculerSousTotal:
    def test_sous_total_panier_vide(self, db_session):
        cart = get_or_create_cart(user_id=7, session=db_session)
        assert calculer_sous_total(cart) == 0.0

    def test_sous_total_un_produit(self, db_session):
        """1 × 50€ = 50€ HT."""
        p = Product(name="Item", price=50.0, stock=5)
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)

        cart = ajouter_au_panier(p, 1, user_id=8, session=db_session)
        assert calculer_sous_total(cart) == 50.0

    def test_sous_total_plusieurs_produits(self, db_session):
        """2 × 30€ + 1 × 20€ = 80€ HT."""
        p1 = Product(name="X", price=30.0, stock=5)
        p2 = Product(name="Y", price=20.0, stock=5)
        db_session.add_all([p1, p2])
        db_session.commit()
        db_session.refresh(p1)
        db_session.refresh(p2)

        ajouter_au_panier(p1, 2, user_id=9, session=db_session)
        cart = ajouter_au_panier(p2, 1, user_id=9, session=db_session)
        assert calculer_sous_total(cart) == 80.0

    def test_total_ttc_applique_tva(self, db_session):
        """100€ HT → 120€ TTC (TVA 20%)."""
        p = Product(name="Z", price=100.0, stock=5)
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)

        cart = ajouter_au_panier(p, 1, user_id=10, session=db_session)
        assert calculer_total_ttc(cart) == 120.0
