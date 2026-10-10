from datetime import date, datetime
from decimal import Decimal

import pytest

from traceur.moteur.normalisation import (
    empreinte_ligne,
    empreinte_table,
    normaliser_valeur,
    valeur_json,
)


def test_nul_distinct_du_texte_vide_et_de_zero() -> None:
    assert len({normaliser_valeur(v) for v in (None, "", 0, "N:", Decimal("0"))}) == 5


def test_types_distincts_a_valeur_egale() -> None:
    assert normaliser_valeur(1) != normaliser_valeur("1") != normaliser_valeur(Decimal("1"))
    assert normaliser_valeur(True) != normaliser_valeur(1)


def test_espace_final_est_une_donnee() -> None:
    assert normaliser_valeur("ACH") != normaliser_valeur("ACH ")


def test_texte_nfc() -> None:
    assert normaliser_valeur("é") == normaliser_valeur("é")


def test_decimal_exact_sans_notation_scientifique() -> None:
    assert normaliser_valeur(Decimal("1234.56")) == "M:1234.56"
    assert normaliser_valeur(Decimal("1E+3")) == "M:1000"
    assert normaliser_valeur(Decimal("0.10")) != normaliser_valeur(Decimal("0.1"))


def test_float_repr_et_dates_iso() -> None:
    assert normaliser_valeur(0.1) == "F:0.1"
    assert normaliser_valeur(date(2025, 1, 15)) == "J:2025-01-15"
    assert normaliser_valeur(datetime(2025, 1, 15)) == "D:2025-01-15T00:00:00"
    assert normaliser_valeur(date(2025, 1, 15)) != normaliser_valeur(datetime(2025, 1, 15))


def test_binaire_par_hash_du_contenu() -> None:
    assert normaliser_valeur(b"abc") == normaliser_valeur(bytearray(b"abc"))
    assert normaliser_valeur(b"abc") != normaliser_valeur(b"abd")


def test_type_inconnu_refuse() -> None:
    with pytest.raises(TypeError):
        normaliser_valeur(object())


def test_empreinte_ligne_sans_collision_de_concatenation() -> None:
    assert empreinte_ligne(("ab", "c")) != empreinte_ligne(("a", "bc"))
    assert empreinte_ligne(("a", None)) != empreinte_ligne((None, "a"))


def test_empreinte_table_independante_de_l_ordre_mais_comptant_les_doublons() -> None:
    a, b = empreinte_ligne((1,)), empreinte_ligne((2,))
    assert empreinte_table([a, b]) == empreinte_table([b, a])
    assert empreinte_table([a, a, b]) != empreinte_table([a, b])


def test_valeur_json_jamais_de_flottant() -> None:
    assert valeur_json(Decimal("1234.56")) == "1234.56"
    assert valeur_json(0.5) == "0.5"
    assert valeur_json(True) == 1
    assert valeur_json(datetime(2025, 1, 15)) == "2025-01-15T00:00:00"
    assert valeur_json(None) is None
    assert valeur_json(b"x").startswith("sha256:")
