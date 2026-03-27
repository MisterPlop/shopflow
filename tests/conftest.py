import pytest
from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Coupon, Product

fake = Faker("fr_FR")


# FIXTURES BASE DE DONNÉES
@pytest.fixture(scope="function")
def db_engine():
    """
    Crée un moteur SQLite en mémoire (RAM) pour les tests.
    scope="function" : une nouvelle BDD est créée pour CHAQUE test.
    Cela garantit que les tests sont totalement isolés, les données
    insérées par test_A ne sont jamais visibles par test_B.

    sqlite:///:memory: : BDD en RAM (pas de fichier sur le disque).
    StaticPool : oblige SQLite à utiliser une seule connexion partagée.
    Obligatoire avec :memory: sinon chaque thread voit une BDD différente.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Crée toutes les tables définies dans app/models.py
    Base.metadata.create_all(engine)
    yield engine
    # Teardown automatique : supprime toutes les tables après le test
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Fournit une session SQLAlchemy fraîche pour chaque test.
    Le rollback() final annule toutes les écritures du test :
    même si on oublie de nettoyer les données dans le test,
    la prochaine session repart d'une BDD propre.
    """
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    # Teardown : annule toutes les modifications du test
    session.rollback()
    session.close()


# FIXTURES DE DONNÉES : objets prêts à l'emploi dans les tests
@pytest.fixture
def product_sample(db_session):
    """
    Crée et insère un produit exemple dans la BDD de test.
    Données : Laptop Pro, 999.99€ HT, stock 10.
    """
    p = Product(
        name="Laptop Pro",
        price=999.99,  # prix HT en euros
        stock=10,  # 10 unités disponibles
    )
    db_session.add(p)
    db_session.commit()  # INSERT en base
    db_session.refresh(p)  # recharge l'objet pour récupérer l'id auto-généré
    return p


@pytest.fixture
def coupon_sample(db_session):
    """
    Crée et insère un coupon de réduction exemple dans la BDD de test.
    Données : PROMO20, 20% de réduction, actif.
    """
    c = Coupon(
        code="PROMO20",
        reduction=20.0,  # 20% de réduction
        actif=True,  # coupon utilisable
    )
    db_session.add(c)
    db_session.commit()  # INSERT en base
    return c


@pytest.fixture
def fake_product_data():
    return {
        "name": fake.catch_phrase()[:50],
        "price": round(fake.pyfloat(min_value=1, max_value=2000, right_digits=2), 2),
        "stock": fake.random_int(min=0, max=500),
        "category": fake.random_element(
            ["informatique", "peripheriques", "audio", "gaming"]
        ),
        "description": fake.sentence(nb_words=10),
    }


@pytest.fixture
def multiple_products(client):
    faker_inst = Faker()
    products = []
    for i in range(5):
        r = client.post(
            "/products/",
            json={
                "name": faker_inst.word().capitalize() + f" {i}",
                "price": round(10.0 + i * 20, 2),
                "stock": 10,
            },
        )
        products.append(r.json())
    yield products
    for p in products:
        client.delete(f"/products/{p['id']}")
