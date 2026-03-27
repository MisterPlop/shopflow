# tests/unit/test_order_service.py
import pytest

from app.models import Product
from app.services.cart import ajouter_au_panier, get_or_create_cart
from app.services.order import creer_commande, mettre_a_jour_statut

REDIS_MOCK_PATH = "app.services.stock.redis_client"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_product(db_session, name="Produit", price=100.0, stock=10):
    p = Product(name=name, price=price, stock=stock)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def _panier_avec_produit(db_session, mocker, user_id=1, price=100.0, qty=1):
    """Crée un panier avec un produit, mock Redis."""
    mocker.patch(REDIS_MOCK_PATH)
    p = _make_product(db_session, price=price)
    cart = ajouter_au_panier(p, qty, user_id=user_id, session=db_session)
    return cart, p


# ---------------------------------------------------------------------------
# creer_commande
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreerCommande:
    def test_commande_nominale(self, db_session, mocker):
        """Panier valide → Order créée avec statut 'pending'."""
        cart, p = _panier_avec_produit(db_session, mocker)
        order = creer_commande(user_id=1, cart=cart, session=db_session)

        assert order.id is not None
        assert order.status == "pending"
        assert order.user_id == 1

    def test_total_ht_correct(self, db_session, mocker):
        """2 × 50€ HT → total_ht = 100€."""
        cart, p = _panier_avec_produit(db_session, mocker, price=50.0, qty=2)
        order = creer_commande(user_id=1, cart=cart, session=db_session)
        assert order.total_ht == 100.0

    def test_total_ttc_correct(self, db_session, mocker):
        """100€ HT → 120€ TTC (TVA 20%)."""
        cart, p = _panier_avec_produit(db_session, mocker, price=100.0, qty=1)
        order = creer_commande(user_id=1, cart=cart, session=db_session)
        assert order.total_ttc == 120.0

    def test_commande_avec_coupon(self, db_session, mocker, coupon_sample):
        """120€ TTC avec coupon 20% → 96€."""
        cart, p = _panier_avec_produit(db_session, mocker, price=100.0, qty=1)
        order = creer_commande(
            user_id=1, cart=cart, session=db_session, coupon=coupon_sample
        )
        assert order.total_ttc == 96.0
        assert order.coupon_code == "PROMO20"

    def test_coupon_code_enregistre(self, db_session, mocker, coupon_sample):
        cart, p = _panier_avec_produit(db_session, mocker)
        order = creer_commande(
            user_id=1, cart=cart, session=db_session, coupon=coupon_sample
        )
        assert order.coupon_code == coupon_sample.code

    def test_sans_coupon_coupon_code_est_none(self, db_session, mocker):
        cart, p = _panier_avec_produit(db_session, mocker)
        order = creer_commande(user_id=1, cart=cart, session=db_session)
        assert order.coupon_code is None

    def test_panier_vide_leve_exception(self, db_session, mocker):
        mocker.patch(REDIS_MOCK_PATH)
        cart = get_or_create_cart(user_id=99, session=db_session)
        with pytest.raises(ValueError, match="vide"):
            creer_commande(user_id=99, cart=cart, session=db_session)

    def test_stock_decremente_apres_commande(self, db_session, mocker):
        """La création d'une commande doit réserver le stock."""
        cart, p = _panier_avec_produit(db_session, mocker, qty=3)
        stock_avant = p.stock
        creer_commande(user_id=1, cart=cart, session=db_session)
        db_session.refresh(p)
        assert p.stock == stock_avant - 3

    def test_panier_vide_apres_commande(self, db_session, mocker):
        """Le panier doit être vidé une fois la commande créée."""
        cart, p = _panier_avec_produit(db_session, mocker)
        creer_commande(user_id=1, cart=cart, session=db_session)
        db_session.refresh(cart)
        assert len(cart.items) == 0

    def test_order_items_crees(self, db_session, mocker):
        """Les OrderItems doivent refléter les CartItems."""
        cart, p = _panier_avec_produit(db_session, mocker, qty=2)
        order = creer_commande(user_id=1, cart=cart, session=db_session)
        assert len(order.items) == 1
        assert order.items[0].quantity == 2
        assert order.items[0].unit_price == p.price


# ---------------------------------------------------------------------------
# mettre_a_jour_statut
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMettreAJourStatut:
    def _creer_order(self, db_session, mocker, status="pending"):
        cart, p = _panier_avec_produit(db_session, mocker)
        order = creer_commande(user_id=1, cart=cart, session=db_session)
        if status != "pending":
            # On force manuellement le statut pour tester d'autres transitions
            order.status = status
            db_session.commit()
            db_session.refresh(order)
        return order

    def test_pending_vers_confirmed(self, db_session, mocker):
        order = self._creer_order(db_session, mocker)
        updated = mettre_a_jour_statut(order.id, "confirmed", db_session)
        assert updated.status == "confirmed"

    def test_pending_vers_cancelled(self, db_session, mocker):
        order = self._creer_order(db_session, mocker)
        updated = mettre_a_jour_statut(order.id, "cancelled", db_session)
        assert updated.status == "cancelled"

    def test_confirmed_vers_shipped(self, db_session, mocker):
        order = self._creer_order(db_session, mocker, status="confirmed")
        updated = mettre_a_jour_statut(order.id, "shipped", db_session)
        assert updated.status == "shipped"

    def test_confirmed_vers_cancelled(self, db_session, mocker):
        order = self._creer_order(db_session, mocker, status="confirmed")
        updated = mettre_a_jour_statut(order.id, "cancelled", db_session)
        assert updated.status == "cancelled"

    def test_transition_invalide_leve_exception(self, db_session, mocker):
        """shipped → confirmed est interdit."""
        order = self._creer_order(db_session, mocker, status="shipped")
        with pytest.raises(ValueError, match="invalide"):
            mettre_a_jour_statut(order.id, "confirmed", db_session)

    def test_cancelled_immuable(self, db_session, mocker):
        """Une commande annulée ne peut plus changer de statut."""
        order = self._creer_order(db_session, mocker, status="cancelled")
        with pytest.raises(ValueError):
            mettre_a_jour_statut(order.id, "confirmed", db_session)

    def test_order_inexistante_leve_exception(self, db_session, mocker):
        mocker.patch(REDIS_MOCK_PATH)
        with pytest.raises(ValueError, match="non trouvée"):
            mettre_a_jour_statut(
                order_id=99999, nouveau_statut="confirmed", session=db_session
            )

    @pytest.mark.parametrize("statut_final", ["shipped", "cancelled"])
    def test_transitions_invalides_depuis_shipped(
        self, statut_final, db_session, mocker
    ):
        order = self._creer_order(db_session, mocker, status="shipped")
        with pytest.raises(ValueError):
            mettre_a_jour_statut(order.id, statut_final, db_session)
