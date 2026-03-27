import pytest

from app.models import Coupon, Product
from app.services.pricing import appliquer_coupon, calcul_prix_ttc, calculer_total


@pytest.mark.unit
class TestCalculPrixTtc:
    def test_prix_normal(self):
        """Prix HT 100€ -> TTC 120€ avec TVA 20%."""
        assert calcul_prix_ttc(100.0) == 120.0

    def test_prix_zero(self):
        assert calcul_prix_ttc(0.0) == 0.0

    def test_arrondi_deux_decimales(self):
        # pas 12.000000001
        assert calcul_prix_ttc(10.0) == 12.0

    def test_prix_negatif_leve_exception(self):
        with pytest.raises(ValueError, match="invalide"):
            calcul_prix_ttc(-5.0)

    @pytest.mark.parametrize(
        "ht,ttc",
        [
            (50.0, 60.0),
            (199.99, 239.99),
            (0.01, 0.01),
        ],
    )
    def test_parametrise(self, ht, ttc):
        assert calcul_prix_ttc(ht) == ttc


@pytest.mark.unit
class TestAppliquerCoupon:
    def test_reduction_20_pourcent(self, coupon_sample):
        result = appliquer_coupon(100.0, coupon_sample)
        assert result == 80.0

    def test_coupon_inactif_leve_exception(self, db_session):
        coupon_inactif = Coupon(code="OLD", reduction=10.0, actif=False)
        with pytest.raises(ValueError, match="inactif"):
            appliquer_coupon(100.0, coupon_inactif)

    def test_reduction_invalide(self, coupon_sample):
        coupon_invalide = Coupon(code="BAD", reduction=150.0, actif=True)
        with pytest.raises(ValueError):
            appliquer_coupon(100.0, coupon_invalide)


# Paramétrisation avancée (Q2.2)
@pytest.mark.parametrize(
    "reduction,prix_initial,prix_attendu",
    [
        (10, 100.0, 90.0),  # -10%
        (50, 200.0, 100.0),  # -50%
        (100, 50.0, 0.0),  # -100% gratuit
        (1, 100.0, 99.0),  # -1% minimal
    ],
)
def test_coupon_reductions_diverses(reduction, prix_initial, prix_attendu, db_session):
    coupon = Coupon(code=f"TEST{reduction}", reduction=float(reduction), actif=True)
    assert appliquer_coupon(prix_initial, coupon) == prix_attendu


# Q2.3 : Test calculer_total avec coupon
def test_calculer_total_avec_coupon(coupon_sample, db_session):
    """Crée 2 produits (50€ et 30€ HT), total TTC avec PROMO20."""
    p1 = Product(name="P1", price=50.0, stock=5)
    p2 = Product(name="P2", price=30.0, stock=5)
    # Total HT = 80€ -> TTC = 96€ -> -20% = 76.80€
    produits = [(p1, 1), (p2, 1)]
    total = calculer_total(produits, coupon_sample)
    assert total == 76.80
