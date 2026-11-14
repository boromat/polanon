"""A person's token comes back in the case the model asks for: "Szanowny Panie <OSOBA_1:wołacz>"."""

import pytest

from polanon._inflection import CASE_NAMES, inflected


@pytest.mark.parametrize(
    ("value", "case", "expected"),
    [
        ("Jana Kowalskiego", "wołacz", "Janie Kowalski"),
        ("Jana Kowalskiego", "mianownik", "Jan Kowalski"),
        ("Jan Kowalski", "dopełniacz", "Jana Kowalskiego"),
        ("Jan Kowalski", "celownik", "Janowi Kowalskiemu"),
        ("Jan Kowalski", "narzędnik", "Janem Kowalskim"),
        ("Jan Kowalski", "miejscownik", "Janie Kowalskim"),
        ("Anna Nowak", "biernik", "Annę Nowak"),
        ("Annie Nowak", "mianownik", "Anna Nowak"),
        ("Jan Nowak", "dopełniacz", "Jana Nowaka"),
        ("Tomaszowi Bednarkowi", "dopełniacz", "Tomasza Bednarka"),
        ("Anną Dudą", "celownik", "Annie Dudzie"),
        ("Janem Mickiewiczem", "wołacz", "Janie Mickiewiczu"),
        ("Maria Nowak-Kowalska", "dopełniacz", "Marii Nowak-Kowalskiej"),
        ("Zielińskiego", "wołacz", "Zieliński"),
        ("Kowalskiej", "biernik", "Kowalską"),
        ("Kowalski Jan", "dopełniacz", "Kowalskiego Jana"),
        ("JANA KOWALSKIEGO", "mianownik", "JAN KOWALSKI"),
        ("jana kowalskiego", "mianownik", "jan kowalski"),
        ("Lukasza Zielinskiego", "wołacz", "Lukaszu Zielinski"),
        ("dr Jana Kowalskiego", "mianownik", "dr Jan Kowalski"),
    ],
)
def test_a_name_polanon_can_read_is_declined_into_the_case(value, case, expected):
    assert inflected(value, "PERSON", case) == expected


@pytest.mark.parametrize("case", ["Wołacz", "WOLACZ", "wolacz", " wołacz "])
def test_a_case_is_read_in_any_letter_case_and_without_polish_letters(case):
    assert inflected("Jana Kowalskiego", "PERSON", case) == "Janie Kowalski"


@pytest.mark.parametrize(
    ("value", "entity_type", "case"),
    [
        ("Nowak", "PERSON", "dopełniacz"),  # a man or a woman: the form would be a guess
        ("John Smith", "PERSON", "dopełniacz"),
        ("Jan Maria Kowalski", "PERSON", "dopełniacz"),
        ("pana Jana Kowalskiego", "PERSON", "mianownik"),  # "pan" itself would need declining
        ("Jan Kowalski", "PERSON", "przypadek"),
        ("Jan Kowalski", "PERSON", ""),
        ("Orlen", "ORG", "dopełniacz"),
        ("Warszawie", "LOCATION", "mianownik"),
    ],
)
def test_what_cannot_be_declined_for_sure_is_not(value, entity_type, case):
    assert inflected(value, entity_type, case) is None


def test_every_polish_case_has_a_name():
    assert sorted(set(CASE_NAMES.values())) == ["acc", "dat", "gen", "ins", "loc", "nom", "voc"]


def test_a_declension_without_the_case_gives_none_rather_than_fail(monkeypatch):
    from polanon.guards import names_pl

    monkeypatch.setattr(names_pl, "decline_masculine", lambda name: {name: {"nom"}})
    assert inflected("Jan Kowalski", "PERSON", "dopełniacz") is None
    assert inflected("Jan Nowak", "PERSON", "dopełniacz") is None
