from dataclasses import dataclass
from typing import List, Optional, Union

from brain_brew.representation.deck_part_transformers.tr_notes_generic import TrNotesGeneric
from brain_brew.representation.json.crowd_anki_export import CrowdAnkiExport


@dataclass
class TrNotesCrowdAnki(TrNotesGeneric):
    @dataclass
    class Representation:
        file: str
        sort_order: Optional[Union[str, List[str]]]
        media: Optional[bool]
        useless_note_keys: Optional[dict]

    crowdanki_file: CrowdAnkiExport
    sort_order: Optional[List[str]]
    media: Optional[bool]
    useless_note_keys: Optional[dict]

# TODO: Make Unique classes for Notes <-> CrowdAnki
