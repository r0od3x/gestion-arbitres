"""Normalisation des numéros en E.164 (région par défaut : Maroc)."""

import pytest

from app.services.errors import ValidationError
from app.services.phone import is_valid_e164, normalize_phone


@pytest.mark.parametrize(
    ("saisie", "attendu"),
    [
        ("0612345678", "+212612345678"),
        ("06 12 34 56 78", "+212612345678"),
        ("+212612345678", "+212612345678"),
        ("+212 612-345-678", "+212612345678"),
        ("00212612345678", "+212612345678"),
    ],
)
def test_normalisation_vers_e164(saisie: str, attendu: str) -> None:
    assert normalize_phone(saisie) == attendu


@pytest.mark.parametrize("saisie", ["", "   ", "abc", "123", "06123"])
def test_numeros_invalides_rejetes(saisie: str) -> None:
    with pytest.raises(ValidationError):
        normalize_phone(saisie)


def test_numero_francais_avec_region_explicite() -> None:
    assert normalize_phone("06 12 34 56 78", region="FR") == "+33612345678"


def test_is_valid_e164() -> None:
    assert is_valid_e164("+212612345678")
    assert not is_valid_e164("0612345678")  # valide mais pas en forme E.164
    assert not is_valid_e164("pas-un-numero")
