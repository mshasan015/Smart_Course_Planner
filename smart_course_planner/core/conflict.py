"""
ConflictChecker module for course schedule clash detection.
Answers: 'does X clash with my selection?' and computes pairwise clashes efficiently.
Golden Rule 3: Start and end compared as minutes: same day and startA < endB and startB < endA.
"""

from typing import List, Tuple, Optional, Set, Dict
from core.models import Section, Meeting


class ConflictChecker:
    """
    Computes and caches clashes among sections.
    """

    def __init__(self, sections: Optional[List[Section]] = None):
        self.clash_pairs: Set[Tuple[str, str]] = set()
        self.clash_map: Dict[str, Set[str]] = {}
        if sections:
            self.precompute_clashes(sections)

    def _section_key(self, sec: Section) -> str:
        return f"{sec.course_code}_{sec.section_name}"

    def precompute_clashes(self, sections: List[Section]) -> None:
        """
        Precomputes all pairwise clashes between sections for instant O(1) lookups.
        """
        self.clash_pairs.clear()
        self.clash_map.clear()
        n = len(sections)
        for i in range(n):
            s1 = sections[i]
            k1 = self._section_key(s1)
            self.clash_map.setdefault(k1, set())
            for j in range(i + 1, n):
                s2 = sections[j]
                k2 = self._section_key(s2)
                self.clash_map.setdefault(k2, set())

                if s1.clashes_with(s2):
                    self.clash_pairs.add((k1, k2))
                    self.clash_pairs.add((k2, k1))
                    self.clash_map[k1].add(k2)
                    self.clash_map[k2].add(k1)

    def does_clash_with_selection(
        self, candidate: Section, selected: List[Section]
    ) -> Tuple[bool, Optional[Section]]:
        """
        Checks if candidate section clashes with any section in the currently selected list.
        Returns (has_clash, first_clashing_section).
        """
        cand_key = self._section_key(candidate)
        for sec in selected:
            # Same course is a conflict (cannot pick two sections of same course)
            if candidate.course_code == sec.course_code:
                if candidate.section_name != sec.section_name:
                    return True, sec

            sec_key = self._section_key(sec)
            # Use precomputed cache if present, otherwise direct check
            if cand_key in self.clash_map:
                if sec_key in self.clash_map[cand_key]:
                    return True, sec
            else:
                if candidate.clashes_with(sec):
                    return True, sec

        return False, None

    def get_clashing_sections(self, candidate: Section, all_sections: List[Section]) -> List[Section]:
        """
        Returns all sections from the provided list that clash with candidate.
        """
        clashing = []
        for sec in all_sections:
            if candidate != sec and candidate.clashes_with(sec):
                clashing.append(sec)
        return clashing
