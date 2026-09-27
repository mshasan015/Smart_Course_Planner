"""
Storage module for saving and loading planned schedules to/from JSON files.
"""

import json
import os
from typing import Optional, List
from core.models import Schedule, Section


class PlanStorage:
    """
    Saves and loads selected course schedules as JSON.
    """

    @staticmethod
    def save_plan(schedule: Schedule, file_path: str, plan_name: str = "My Course Plan") -> bool:
        """
        Saves a Schedule to a JSON file.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            data = {
                "plan_name": plan_name,
                "total_credits": schedule.total_credits(),
                "days_used": schedule.days_used(),
                "idle_minutes": schedule.idle_minutes(),
                "sections": [sec.to_dict() for sec in schedule.sections],
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving plan: {e}")
            return False

    @staticmethod
    def load_plan(file_path: str) -> Optional[Schedule]:
        """
        Loads a Schedule from a JSON file.
        """
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sections = [Section.from_dict(s) for s in data.get("sections", [])]
            return Schedule(sections=sections)
        except Exception as e:
            print(f"Error loading plan: {e}")
            return None
