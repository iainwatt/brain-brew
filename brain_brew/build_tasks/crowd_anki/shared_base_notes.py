from dataclasses import dataclass, field
from typing import Optional, Union, List

from brain_brew.representation.build_config.representation_base import RepresentationBase


@dataclass
class SharedBaseNotes:
    @staticmethod
    def _get_sort_order(sort_order: Optional[Union[str, List[str]]]):
        if isinstance(sort_order, list):
            return sort_order
        elif isinstance(sort_order, str):
            return [sort_order]
        return []

    @staticmethod
    def _get_reverse_sort(reverse_sort: Optional[bool]):
        return reverse_sort or False

    # sort_order: Optional[List[str]]
    # reverse_sort: Optional[bool]
