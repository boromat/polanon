"""A person's name in the grammatical case a model asks for, as in ``<OSOBA_1:wołacz>``.

A token stands for a value as the text wrote it: ``<OSOBA_1>`` is "Jana Kowalskiego" when the text
said "wniosek Jana Kowalskiego". The model puts the token in a sentence of its own, where another
case may be needed, so it may write the case after a colon, and the name is declined: "Szanowny
Panie <OSOBA_1:wołacz>" comes back as "Szanowny Panie Janie Kowalski".

Only a name the rules read for sure is declined: one or two words, a first name from the lists
and a surname of a shape they know (Kowalski, Nowak, Bednarek, Mickiewicz, Duda), agreeing in
gender. Anything else, a surname alone that could be a man's or a woman's, a foreign name, a
company or a place, gives None, and the value comes back as written.
"""

from __future__ import annotations

from polanon import _canonical as canonical
from polanon._matching import reading
from polanon.guards import names_pl as names
from polanon.guards.names_pl import Tag

#: The Polish name of a case, as a model writes it after the colon, -> the case.
CASE_NAMES: dict[str, str] = {
    "mianownik": "nom",
    "dopełniacz": "gen",
    "celownik": "dat",
    "biernik": "acc",
    "narzędnik": "ins",
    "miejscownik": "loc",
    "wołacz": "voc",
}
_CASES = {names.fold(name): case for name, case in CASE_NAMES.items()}

#: The endings of a surname declined as an adjective, after the stem "Kowalsk".
_ADJECTIVE_ENDINGS = {
    "m": {"nom": "i", "gen": "iego", "dat": "iemu", "acc": "iego", "ins": "im", "loc": "im"},
    "f": {"nom": "a", "gen": "iej", "dat": "iej", "acc": "ą", "ins": "ą", "loc": "iej"},
}
_ADJECTIVE_ENDINGS["m"]["voc"] = "i"
_ADJECTIVE_ENDINGS["f"]["voc"] = "a"
_ADJECTIVE_NOMINATIVE = {"m": ("ski", "cki", "dzki"), "f": ("ska", "cka", "dzka")}
_A_SURNAMES = frozenset(names.fold(name) for name in names._A_SURNAMES)
_POLISH_LETTERS = frozenset("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")


def case_of(name: str) -> str | None:
    """Return the case a model named after a token's colon, or None for no case Polish has."""
    return _CASES.get(names.fold(name.strip()))


def inflected(value: str, entity_type: str, case_name: str) -> str | None:
    """Return a person's `value` declined into the case `case_name` names, or None.

    Args:
        value: the value a token stands for, as the text wrote it.
        entity_type: its type; only ``PERSON`` is declined.
        case_name: the case in Polish, such as "wołacz", in any letter case and with or without
            Polish letters.

    Returns:
        The name in that case, written as the value was: in capitals, in lowercase or without
        Polish letters. None when the case is no case or the name cannot be declined for sure.
    """
    case = case_of(case_name)
    if entity_type != "PERSON" or case is None:
        return None
    words = reading(value).split(" ")
    titles: list[str] = []
    while len(words) > 1 and canonical._is_title(words[0]):
        if names.fold(words[0].rstrip(".")) not in names._ABBREVIATIONS:
            return None  # "pana" would need declining along with the name
        titles.append(words.pop(0))
    reading_of = _reading(words)
    if reading_of is None:
        return None
    gender, lemmas, kinds = reading_of
    forms = [
        _declined(lemma, kind, gender, case) for lemma, kind in zip(lemmas, kinds, strict=True)
    ]
    declined = [form for form in forms if form is not None]
    if len(declined) < len(forms):
        return None
    plain = not any(letter in _POLISH_LETTERS for letter in value)
    if plain and any(letter in _POLISH_LETTERS for lemma in lemmas for letter in lemma):
        declined = [form.translate(canonical._PLAIN) for form in declined]
    written = [_written_like(form, word) for form, word in zip(declined, words, strict=True)]
    return " ".join([*titles, *written])


def _reading(words: list[str]) -> tuple[str, list[str], list[str]] | None:
    """Return the one gender, nominatives and kinds ("first", "surname") of a name, or None."""
    if len(words) == 1:
        found = {(tag[0], lemma, "first") for tag, lemma in _first_names(words[0])}
        found |= {(tag[0], lemma, "surname") for tag, lemma in _surnames(words[0])}
        if len(found) != 1:
            return None
        gender, lemma, kind = found.pop()
        return gender, [lemma], [kind]
    if len(words) != 2:
        return None
    readings = set()
    for first, last, kinds in ((0, 1, ("first", "surname")), (1, 0, ("surname", "first"))):
        first_names = _by_tag(_first_names(words[first]))
        surnames = _by_tag(_surnames(words[last]))
        for tag in first_names.keys() & surnames.keys():
            for first_name in first_names[tag]:
                for surname in surnames[tag]:
                    lemmas = (first_name, surname) if first == 0 else (surname, first_name)
                    readings.add((tag[0], lemmas, kinds))
    if len(readings) != 1:
        return None
    gender, lemmas, kinds = readings.pop()
    return gender, list(lemmas), list(kinds)


def _first_names(word: str) -> set[tuple[Tag, str]]:
    """Readings of a word as a listed first name, each with its nominative as the list spells it."""
    if "-" in word:
        return set()
    return set(canonical._FIRST_NAMES().get(names.fold(word), ()))


def _surnames(word: str) -> set[tuple[Tag, str]]:
    """Readings of a word as a surname, each with its nominative, parts of a double one joined."""
    return {(tag, lemma) for tag, lemmas in canonical._surname(word).items() for lemma in lemmas}


def _by_tag(readings: set[tuple[Tag, str]]) -> dict[Tag, set[str]]:
    table: dict[Tag, set[str]] = {}
    for tag, lemma in readings:
        table.setdefault(tag, set()).add(lemma)
    return table


def _declined(lemma: str, kind: str, gender: str, case: str) -> str | None:
    """Return one name in the nominative, `lemma`, declined into `case`, or None."""
    if kind == "first":
        decline = names.decline_masculine if gender == "m" else names.decline_feminine
        return _form(decline(lemma.lower()), case)
    parts = [_surname_part(part, gender, case) for part in lemma.split("-")]
    declined = [part for part in parts if part is not None]
    return "-".join(declined) if len(declined) == len(parts) else None


def _surname_part(lemma: str, gender: str, case: str) -> str | None:
    key = names.fold(lemma)
    if key.endswith(_ADJECTIVE_NOMINATIVE[gender]):
        return lemma[:-1].lower() + _ADJECTIVE_ENDINGS[gender][case]
    if key in _A_SURNAMES:
        return _form(names.decline_feminine(lemma.lower()), case)
    if gender == "f":
        return lemma.lower()  # "Anna Nowak": a woman's surname of this shape does not change
    return _form(names.decline_masculine(lemma.lower()), case)


def _form(forms: dict[str, set[str]], case: str) -> str | None:
    """The form of a declension table in `case`: the shortest, then the first, of two or more."""
    found = [form for form, cases in forms.items() if case in cases]
    return min(found, key=lambda form: (len(form), form)) if found else None


def _written_like(form: str, written: str) -> str:
    """Write a declined name the way the value wrote it: capitals, lowercase, or capitalised."""
    if written.isupper():
        return form.upper()
    if written.islower():
        return form.lower()
    return "-".join(part[:1].upper() + part[1:] for part in form.split("-"))
