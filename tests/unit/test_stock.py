import pytest

from app.services import stock
from app.services.stock import liberer_stock, reserver_stock, verifier_stock

# Point clé : Redis est MOCKÉ dans tous les tests qui appellent reserver_stock
# ou liberer_stock car ces fonctions appellent redis_client.delete() ou set().
REDIS_MOCK_PATH = "app.services.stock.redis_client"


@pytest.mark.unit
class TestVerifierStock:
    def test_stock_suffisant(self, product_sample):
        # Cas nominal : stock = 10, demande = 5 -> True
        assert verifier_stock(product_sample, 5) is True

    def test_stock_insuffisant(self, product_sample):
        # Cas d'erreur : stock = 10, demande = 999 -> False
        assert verifier_stock(product_sample, 999) is False

    def test_stock_exactement_disponible(self, product_sample):
        # Cas limite : demander exactement le stock disponible (10) -> True
        assert verifier_stock(product_sample, 10) is True

    def test_quantite_zero_leve_exception(self, product_sample):
        with pytest.raises(ValueError):
            verifier_stock(product_sample, 0)

    def test_quantite_negative_leve_exception(self, product_sample):
        with pytest.raises(ValueError):
            verifier_stock(product_sample, -1)


@pytest.mark.unit
class TestReserverStock:
    """
    Cette fonction fait 3 choses :
    1. Vérifie que le stock est suffisant
    2. Décrémente product.stock en BDD (session.commit)
    3. Invalide le cache Redis (redis_client.delete)
    """

    def test_reservation_reussie(self, product_sample, db_session, mocker):
        # Étape 1 : Mocker Redis (faux objet qui accepte tous les appels)
        mock_redis = mocker.patch.object(stock, "redis_client")
        stock_avant = product_sample.stock  # = 10

        # Étape 2 : Appeler la fonction
        updated = reserver_stock(product_sample, 3, db_session)

        # Étape 3 : Vérifier que le stock a bien diminué (10 - 3 = 7)
        assert updated.stock == stock_avant - 3

        # Étape 4 : Vérifier que Redis.delete() a été appelé 1 fois
        mock_redis.delete.assert_called_once()

    def test_reservation_verifie_cle_redis(self, product_sample, db_session, mocker):
        """Vérifie que Redis.delete() est appelé avec la BONNE clé product:(id):stock."""
        mock_redis = mocker.patch(REDIS_MOCK_PATH)
        reserver_stock(product_sample, 1, db_session)

        expected_key = f"product:{product_sample.id}:stock"
        mock_redis.delete.assert_called_once_with(expected_key)

    def test_stock_insuffisant_leve_exception(self, product_sample, db_session, mocker):
        mocker.patch(REDIS_MOCK_PATH)
        with pytest.raises(ValueError, match="insuffisant"):
            reserver_stock(product_sample, 999, db_session)

    def test_stock_insuffisant_ne_modifie_pas_bdd(
        self, product_sample, db_session, mocker
    ):
        mocker.patch(REDIS_MOCK_PATH)
        stock_avant = product_sample.stock
        with pytest.raises(ValueError):
            reserver_stock(product_sample, 999, db_session)
        assert product_sample.stock == stock_avant

    def test_redis_non_appele_si_exception(self, product_sample, db_session, mocker):
        mock_redis = mocker.patch(REDIS_MOCK_PATH)
        with pytest.raises(ValueError):
            reserver_stock(product_sample, 999, db_session)
        mock_redis.delete.assert_not_called()


# Q3.2 : Test liberer_stock
def test_liberation_stock(product_sample, db_session, mocker):
    """Cas nominal : libérer 2 unités, le stock augmente et le cache est mis à jour."""
    mock_redis = mocker.patch(REDIS_MOCK_PATH)
    # Action
    liberer_stock(product_sample, 2, db_session)
    # Vérification BDD
    assert product_sample.stock == 12
    # Vérification Redis.set() (clé et valeur)
    mock_redis.set.assert_called_once_with(f"product:{product_sample.id}:stock", 12)
