from typing import List

from brain_brew.representation.configuration.global_config import GlobalConfig
from brain_brew.representation.json.json_file import JsonFile
from brain_brew.constants.deckpart_keys import *
from enum import Enum

from brain_brew.representation.json.deck_part_notemodel import DeckPartNoteModel


class CANoteKeys(Enum):
    NOTE_MODEL = "note_model_uuid"
    FLAGS = "flags"
    GUID = "guid"
    TAGS = "tags"
    FIELDS = "fields"


class DeckPartNotes(JsonFile):
    _data: dict = {}
    global_config: GlobalConfig = None
    note_models: List[DeckPartNoteModel]
    flags: DeckPartNoteFlags

    @classmethod
    def formatted_file_location(cls, location):
        return cls.get_json_file_location(GlobalConfig.get_instance().deck_parts.notes, location)

    def __init__(self, location, read_now=True, data_override=None):
        self.global_config = GlobalConfig.get_instance()
        self.flags = DeckPartNoteFlags()
        super().__init__(
            self.formatted_file_location(location),
            read_now=read_now, data_override=data_override
        )

    def set_data(self, data_override, deck_part_flags_included=False):
        if not deck_part_flags_included:
            data_override = {**self.flags.get_formatted_dict(), **{DeckPartNoteKeys.NOTES.value: data_override}}

        super().set_data(data_override)
        self.interpret_data()

    def write_file(self, data_override=None):
        super().write_file(data_override or self.implement_note_structure())

    def read_file(self):
        super().read_file()
        self.interpret_data()

    def interpret_data(self):
        self.verify_data()

        self.read_note_config()
        self._data = self.remove_notes_structure()
        self.read_note_config()

        self.sort_notes()

    def read_note_config(self):
        self.flags.group_by_note_model = self._data[DeckPartNoteKeys.FLAGS.value][NoteFlagKeys.GROUP_BY_NOTE_MODEL.value]
        self.flags.extract_shared_tags = self._data[DeckPartNoteKeys.FLAGS.value][NoteFlagKeys.EXTRACT_SHARED_TAGS.value]

    def verify_data(self):
        errors = []
        if DeckPartNoteKeys.FLAGS.value not in self._data:
            errors.append(KeyError(f"Missing '{DeckPartNoteKeys.FLAGS.value}' key in '{self.file_location}'"))
        else:
            for flag in NoteFlagKeys:
                if flag.value not in self._data[DeckPartNoteKeys.FLAGS.value]:
                    errors.append(KeyError(f"Missing '{flag.value}' flag in '{self.file_location}'"))

        if errors:
            raise Exception(errors)

    def get_all_known_note_model_names(self):
        model_set = {note[DeckPartNoteKeys.NOTE_MODEL.value] for note in self._data[DeckPartNoteKeys.NOTES.value]}
        return sorted(list(model_set))

    def sort_notes(self):
        if not self.global_config.flags.note_sort_order:
            return

        notes: list = self._data[DeckPartNoteKeys.NOTES.value]

        if self.global_config.flags.sort_case_insensitive:
            sort_method = lambda i: tuple((i[c] == "", i[c].lower()) for c in self.global_config.flags.note_sort_order)
        else:
            sort_method = lambda i: tuple((i[c] == "", i[c]) for c in self.global_config.flags.note_sort_order)

        notes = sorted(notes, key=sort_method)

        if self.global_config.flags.reverse_sort:
            notes = list(reversed(notes))

        self._data[DeckPartNoteKeys.NOTES.value] = notes

    def implement_note_structure(self):
        """
        :return: the notes structured based on the settings in the Global Config file
        """
        if not self.global_config.deck_part_notes_flags.any_enabled():
            return self._data

        def top_level_structure():
            if self.global_config.deck_part_notes_flags.extract_shared_tags:
                return {DeckPartNoteKeys.SHARED_TAGS.value: [], DeckPartNoteKeys.NOTES.value: []}
            else:
                return {DeckPartNoteKeys.NOTES.value: []}

        if self.global_config.deck_part_notes_flags.group_by_note_model:
            structured_notes: dict = {name: top_level_structure() for name in self.get_all_known_note_model_names()}
            for note in self._data[DeckPartNoteKeys.NOTES.value]:
                for name in structured_notes:
                    if note[DeckPartNoteKeys.NOTE_MODEL.value] == name:
                        structured_notes[name][DeckPartNoteKeys.NOTES.value].append(note)
                        break
                del note[DeckPartNoteKeys.NOTE_MODEL.value]
        else:
            structured_notes = top_level_structure()
            structured_notes[DeckPartNoteKeys.NOTES.value] = self._data

        if self.global_config.deck_part_notes_flags.extract_shared_tags:
            def extract_shared_tags(notes):
                shared_tags = notes[0][DeckPartNoteKeys.TAGS.value]

                for note in notes:
                    shared_tags = [tag for tag in note[DeckPartNoteKeys.TAGS.value] if tag in shared_tags]
                    if not shared_tags:
                        break

                if shared_tags:
                    for note in notes:
                        for tag in shared_tags:
                            note[DeckPartNoteKeys.TAGS.value].remove(tag)

                return shared_tags

            if self.global_config.deck_part_notes_flags.group_by_note_model:
                for name in structured_notes:
                    structured_notes[name][DeckPartNoteKeys.SHARED_TAGS.value] = extract_shared_tags(
                        structured_notes[name][DeckPartNoteKeys.NOTES.value]
                    )
            else:
                structured_notes[DeckPartNoteKeys.SHARED_TAGS.value] = extract_shared_tags(
                    structured_notes[DeckPartNoteKeys.NOTES.value]
                )

        final_structure = self.global_config.deck_part_notes_flags.get_formatted_dict()
        for key in structured_notes:
            final_structure.setdefault(key, structured_notes[key])

        return final_structure

    def remove_notes_structure(self):
        """
        :return: notes with their global config structure removed
        """
        if not self.flags.any_enabled():
            return self._data

        unstructured_notes = self._data.copy()

        if self.flags.extract_shared_tags:
            def resolve_shared_tags(toplevel):
                sharedtags = toplevel[DeckPartNoteKeys.SHARED_TAGS.value]
                if sharedtags:
                    for note in toplevel[DeckPartNoteKeys.NOTES.value]:
                        note[DeckPartNoteKeys.TAGS.value] += sharedtags

                del toplevel[DeckPartNoteKeys.SHARED_TAGS.value]

            if self.flags.group_by_note_model:
                for group in unstructured_notes:
                    if group[0] != "_":
                        resolve_shared_tags(unstructured_notes[group])
            else:
                resolve_shared_tags(unstructured_notes)

            unstructured_notes[DeckPartNoteKeys.FLAGS.value][NoteFlagKeys.EXTRACT_SHARED_TAGS.value] = False

        if self.flags.group_by_note_model:
            ungrouped_notes = []
            for group in unstructured_notes:
                if group[0] != "_":
                    for note in unstructured_notes[group][DeckPartNoteKeys.NOTES.value]:
                        note[DeckPartNoteKeys.NOTE_MODEL.value] = group
                        ungrouped_notes.append(note)

            toplevel = {group: unstructured_notes[group] for group in unstructured_notes if group[0] == "_"}
            toplevel.setdefault(DeckPartNoteKeys.NOTES.value, ungrouped_notes)
            unstructured_notes = toplevel

            unstructured_notes[DeckPartNoteKeys.FLAGS.value][NoteFlagKeys.GROUP_BY_NOTE_MODEL.value] = False

        return unstructured_notes