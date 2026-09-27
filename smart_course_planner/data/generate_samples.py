"""
Script to generate sample Excel routines for Smart Course Planner.
Includes standard routine with Day 1 & Day 2, edge case rows, and a changed routine with Day 3.
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

def create_sample_routine(filepath: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Routine"

    headers = [
        "Course Code",
        "Course Title",
        "Section",
        "Faculty",
        "Capacity",
        "Occupied",
        "Credits",
        "Day 1",
        "Room 1",
        "Day 2",
        "Room 2",
    ]

    ws.append(headers)

    # Sample rows with real university routine cases:
    # - Section with extra spaces ("A ")
    # - Dropped section with "(Dropped)"
    # - Section with TBA teacher
    # - Section with up to 3 teachers
    # - Clean regular sections across multiple courses: CSE 1115, CSE 2215, MATH 2103, ENG 1011, DS 1116, PHY 1001
    rows = [
        # CSE 1115 Object Oriented Programming (3.0 credits)
        ["CSE 1115", "Object Oriented Programming", "A ", "Dr. Alan Turing, John von Neumann", "35", "30", "3.0", "Sun 08:30:AM - 09:50:AM", "UB101", "Tue 08:30:AM - 09:50:AM", "UB101"],
        ["CSE 1115", "Object Oriented Programming", "B", "Grace Hopper", "35", "35", "3.0", "Sun 10:00:AM - 11:20:AM", "UB102", "Tue 10:00:AM - 11:20:AM", "UB102"],
        ["CSE 1115", "Object Oriented Programming", "C", "TBA", "35", "12", "3.0", "Mon 11:30:AM - 12:50:PM", "UB103", "Wed 11:30:AM - 12:50:PM", "UB103"],
        ["CSE 1115", "Object Oriented Programming", "D (Dropped)", "Dr. Alan Turing", "35", "0", "3.0", "Mon 01:00:PM - 02:20:PM", "UB104", "Wed 01:00:PM - 02:20:PM", "UB104"],

        # CSE 2215 Data Structures and Algorithms (3.0 credits)
        ["CSE 2215", "Data Structures & Algorithms", "A", "Donald Knuth", "40", "38", "3.0", "Sun 10:00:AM - 11:20:AM", "UB201", "Tue 10:00:AM - 11:20:AM", "UB201"],  # Clashes with CSE 1115 B!
        ["CSE 2215", "Data Structures & Algorithms", "B", "Donald Knuth", "40", "20", "3.0", "Mon 08:30:AM - 09:50:AM", "UB202", "Wed 08:30:AM - 09:50:AM", "UB202"],
        ["CSE 2215", "Data Structures & Algorithms", "C", "Barbara Liskov, Tim Berners-Lee, Edsger Dijkstra", "40", "15", "3.0", "Sun 01:00:PM - 02:20:PM", "UB203", "Tue 01:00:PM - 02:20:PM", "UB203"],

        # MATH 2103 Linear Algebra & Discrete Math (3.0 credits)
        ["MATH 2103", "Linear Algebra & Discrete Math", "A", "Carl Gauss", "45", "42", "3.0", "Sun 11:30:AM - 12:50:PM", "UB301", "Tue 11:30:AM - 12:50:PM", "UB301"],
        ["MATH 2103", "Linear Algebra & Discrete Math", "B ", "Leonhard Euler", "45", "30", "3.0", "Mon 10:00:AM - 11:20:AM", "UB302", "Wed 10:00:AM - 11:20:AM", "UB302"],
        ["MATH 2103", "Linear Algebra & Discrete Math", "C", "Carl Gauss", "45", "10", "3.0", "Sun 02:30:PM - 03:50:PM", "UB303", "Tue 02:30:PM - 03:50:PM", "UB303"],

        # ENG 1011 Academic English & Technical Writing (3.0 credits)
        ["ENG 1011", "Academic English & Communication", "A", "Virginia Woolf", "30", "28", "3.0", "Mon 08:30:AM - 09:50:AM", "UB401", "Wed 08:30:AM - 09:50:AM", "UB401"],  # Clashes with CSE 2215 B!
        ["ENG 1011", "Academic English & Communication", "B", "George Orwell", "30", "18", "3.0", "Sun 01:00:PM - 02:20:PM", "UB402", "Tue 01:00:PM - 02:20:PM", "UB402"],  # Clashes with CSE 2215 C!
        ["ENG 1011", "Academic English & Communication", "C", "George Orwell", "30", "25", "3.0", "Mon 02:30:PM - 03:50:PM", "UB403", "Wed 02:30:PM - 03:50:PM", "UB403"],

        # DS 1116 Data Science Fundamentals (3.0 credits) - all early morning to test hard rule
        ["DS 1116", "Data Science Fundamentals", "A", "Claude Shannon", "35", "32", "3.0", "Sun 08:30:AM - 09:50:AM", "UB501", "Tue 08:30:AM - 09:50:AM", "UB501"],
        ["DS 1116", "Data Science Fundamentals", "B", "Ada Lovelace", "35", "29", "3.0", "Mon 08:30:AM - 09:50:AM", "UB502", "Wed 08:30:AM - 09:50:AM", "UB502"],

        # PHY 1001 Engineering Physics (3.0 credits)
        ["PHY 1001", "Engineering Physics", "A", "Richard Feynman", "40", "39", "3.0", "Sun 11:30:AM - 12:50:PM", "UB601", "Tue 11:30:AM - 12:50:PM", "UB601"],
        ["PHY 1001", "Engineering Physics", "B", "Marie Curie", "40", "20", "3.0", "Mon 01:00:PM - 02:20:PM", "UB602", "Wed 01:00:PM - 02:20:PM", "UB602"],

        # Bad rows for testing error resiliency
        ["", "Invalid Missing Code", "A", "TBA", "30", "0", "3.0", "-", "-", "-", "-"],
        ["BIO 1001", "General Biology", "", "TBA", "30", "0", "3.0", "Sun 10:00:AM - 11:20:AM", "UB701", "-", "-"],
    ]

    for row in rows:
        ws.append(row)

    wb.save(filepath)
    print(f"Created {filepath}")

def create_changed_routine(filepath: str):
    """Creates routine with shuffled columns and Day 3 column to test Golden Rule 2."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Routine"

    # Different column order and 3 Day columns!
    headers = [
        "Section",
        "Course Code",
        "Faculty",
        "Course Title",
        "Credits",
        "Capacity",
        "Occupied",
        "Day 1",
        "Day 2",
        "Day 3",
        "Room 1",
        "Room 2",
        "Room 3",
    ]

    ws.append(headers)

    rows = [
        ["A", "CSE 3311", "Linus Torvalds", "Operating Systems", "3.0", "40", "35", "Sun 08:30:AM - 09:50:AM", "Tue 08:30:AM - 09:50:AM", "Thu 08:30:AM - 09:50:AM", "LAB1", "LAB1", "LAB1"],
        ["B", "CSE 3311", "Ken Thompson", "Operating Systems", "3.0", "40", "20", "Mon 10:00:AM - 11:20:AM", "Wed 10:00:AM - 11:20:AM", " - ", "LAB2", "LAB2", "-"],
        ["A", "CSE 3421", "Dennis Ritchie", "Computer Networks", "3.0", "35", "30", "Sun 11:30:AM - 12:50:PM", "Tue 11:30:AM - 12:50:PM", " - ", "UB204", "UB204", "-"],
        ["B", "CSE 3421", "Vint Cerf", "Computer Networks", "3.0", "35", "10", "Mon 01:00:PM - 02:20:PM", "Wed 01:00:PM - 02:20:PM", " - ", "UB205", "UB205", "-"],
    ]

    for row in rows:
        ws.append(row)

    wb.save(filepath)
    print(f"Created {filepath}")

if __name__ == "__main__":
    create_sample_routine("smart_course_planner/data/routine_sample.xlsx")
    create_changed_routine("smart_course_planner/data/routine_changed.xlsx")
