# backend/context.py

class CourseContext:
    def __init__(self, course_title: str):
        self.course_title = course_title
        self.previous_slide_summary = ""

    def update_context(self, new_content: str):
        # On ajoute le contenu de la slide au contexte global, séparé par un saut de ligne.
        self.previous_slide_summary += new_content + "\n"
