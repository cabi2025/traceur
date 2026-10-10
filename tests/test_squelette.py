"""Test minimal J0 : le paquet s'importe."""


def test_import_paquet() -> None:
    import traceur
    import traceur.moteur
    import traceur.securite
    import traceur.sources

    assert traceur is not None
