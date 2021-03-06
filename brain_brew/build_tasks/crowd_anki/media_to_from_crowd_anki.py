import logging
from dataclasses import dataclass
from typing import Union, List, Set

from brain_brew.file_manager import FileManager
from brain_brew.representation.build_config.representation_base import RepresentationBase
from brain_brew.representation.generic.media_file import MediaFile
from brain_brew.representation.json.crowd_anki_export import CrowdAnkiExport
from brain_brew.representation.yaml.note_model_repr import NoteModel
from brain_brew.representation.yaml.note_repr import Notes


@dataclass
class MediaToFromCrowdAnki:
    @dataclass
    class Representation(RepresentationBase):
        from_notes: bool
        from_note_models: bool

    @classmethod
    def from_repr(cls, data: Union[Representation, dict, bool]):
        rep: cls.Representation
        if isinstance(data, cls.Representation):
            rep = data
        elif isinstance(data, dict):
            rep = cls.Representation.from_dict(data)
        else:
            rep = cls.Representation(from_notes=data, from_note_models=data)  # Support single boolean for default

        return cls(
            from_notes=rep.from_notes,
            from_note_models=rep.from_note_models
        )

    from_notes: bool
    from_note_models: bool

    file_manager: FileManager = None

    def __post_init__(self):
        if not MediaToFromCrowdAnki.file_manager:
            MediaToFromCrowdAnki.file_manager = FileManager.get_instance()

    def move_to_crowd_anki(self, notes: Notes, note_models: List[NoteModel], ca_export: CrowdAnkiExport) -> Set[MediaFile]:
        resolved_media: Set[MediaFile] = set()
        missing_media: Set[str] = set()

        if self.from_notes:
            res, miss = self.resolve_media_references_to_deck_parts(notes.get_all_media_references())
            resolved_media, missing_media = resolved_media.union(res), missing_media.union(miss)
            self._move_ca(res, ca_export)

        if self.from_note_models:
            for model in note_models:
                res, miss = self.resolve_media_references_to_deck_parts(model.get_all_media_references())
                resolved_media, missing_media = resolved_media.union(res), missing_media.union(miss)
                self._move_ca(res, ca_export)

        if len(missing_media) > 0:
            logging.error(f"Unresolved references in DeckParts to {len(missing_media)} files: {missing_media}")

        return resolved_media

    def move_to_deck_parts(self, notes: Notes, note_models: List[NoteModel], ca_export: CrowdAnkiExport) -> Set[MediaFile]:
        resolved_media: Set[MediaFile] = set()
        missing_media: Set[str] = set()

        if self.from_notes:
            res, miss = self.resolve_media_references_to_ca(notes.get_all_media_references(), ca_export)
            resolved_media, missing_media = resolved_media.union(res), missing_media.union(miss)
            self._move_dps(res)

        if self.from_note_models:
            for model in note_models:
                res, miss = self.resolve_media_references_to_ca(model.get_all_media_references(), ca_export)
                resolved_media, missing_media = resolved_media.union(res), missing_media.union(miss)
                self._move_dps(res)

        if len(missing_media) > 0:
            logging.error(f"Unresolved media in CrowdAnki to {len(missing_media)} files: {missing_media}")

        return resolved_media

    @classmethod
    def resolve_media_references_to_ca(cls, filenames: Set[str], ca_export: CrowdAnkiExport) -> (List[MediaFile], List[str]):
        resolved_media: List[MediaFile] = []
        missing_media: List[str] = []
        for filename in filenames:
            if filename in ca_export.known_media.keys():
                resolved_media.append(ca_export.known_media[filename])
            else:
                missing_media.append(filename)
        return resolved_media, missing_media

    @classmethod
    def resolve_media_references_to_deck_parts(cls, filenames: Set[str]) -> (List[MediaFile], List[str]):
        resolved_media: List[MediaFile] = []
        missing_media: List[str] = []
        for filename in filenames:
            media_file = cls.file_manager.media_file_if_exists(filename)
            if media_file:
                resolved_media.append(media_file)
            else:
                missing_media.append(filename)
        return resolved_media, missing_media

    @classmethod
    def _move_ca(cls, media_files: List[MediaFile], ca_export: CrowdAnkiExport):
        for file in media_files:
            if file.filename in ca_export.known_media:
                ca_export.known_media[file.filename].set_override(file.source_loc)
            else:
                ca_export.known_media.setdefault(
                    file.filename, MediaFile(ca_export.media_loc + file.filename,
                                             file.filename, MediaFile.ManagementType.TO_BE_CLONED, file.source_loc)
                )

    @classmethod
    def _move_dps(cls, media_files: List[MediaFile]):
        for file in media_files:
            dp_media_file = cls.file_manager.media_file_if_exists(file.filename)
            if dp_media_file:
                dp_media_file.set_override(file.source_loc)
            else:
                cls.file_manager.new_media_file(file.filename, file.source_loc)
