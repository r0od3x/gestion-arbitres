"""Hachage des mots de passe et jetons JWT."""

import uuid

import pytest

from app.core.security import (
    TokenError,
    create_access_token,
    create_invite_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_le_hash_est_sale_et_verifiable() -> None:
    password = "MonMotDePasse!2026"
    first, second = hash_password(password), hash_password(password)

    assert first != second, "deux hachages du même mot de passe doivent différer (sel)"
    assert password not in first
    assert verify_password(password, first)
    assert verify_password(password, second)


def test_mauvais_mot_de_passe_rejete() -> None:
    assert not verify_password("mauvais", hash_password("MonMotDePasse!2026"))


def test_hash_corrompu_ne_leve_pas() -> None:
    assert not verify_password("peu-importe", "pas-un-hash-argon2")


def test_aller_retour_du_jeton_d_acces() -> None:
    user_id = uuid.uuid4()
    payload = decode_token(create_access_token(user_id, "admin"), "access")

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "admin"
    assert payload["exp"] > payload["iat"]


def test_les_types_de_jeton_ne_sont_pas_interchangeables() -> None:
    user_id = uuid.uuid4()
    access = create_access_token(user_id, "referee")
    refresh = create_refresh_token(user_id)
    invite = create_invite_token(user_id, "a@b.ma")

    for token, wrong_type in ((access, "refresh"), (refresh, "access"), (invite, "access")):
        with pytest.raises(TokenError):
            decode_token(token, wrong_type)  # type: ignore[arg-type]


def test_jeton_signe_avec_une_autre_cle_rejete() -> None:
    import jwt

    autre_cle = "une-autre-cle-suffisamment-longue-pour-hmac-sha256"
    forged = jwt.encode({"sub": str(uuid.uuid4()), "type": "access"}, autre_cle)
    with pytest.raises(TokenError):
        decode_token(forged, "access")


def test_jeton_illisible_rejete() -> None:
    with pytest.raises(TokenError):
        decode_token("n'importe.quoi.ici", "access")
