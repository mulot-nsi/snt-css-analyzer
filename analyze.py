from prettytable import PrettyTable
from pathlib import Path
from bs4 import BeautifulSoup
import zipfile
import shutil

import cssutils


import logging


def student_folder(filename: str):
    return "_".join(filename.split('_')[:2])


def student_name(filename: str):
    return " ".join(filename.split('_')[:2])


def zipfile_index_path(z: zipfile.ZipFile):
    """
    Return index.html file path in a zipfile
    :return:
    """
    for path in z.namelist():
        if 'index.html' in path:
            p = Path(path)
            return str(p.parent)


cssutils.log.setLevel(logging.CRITICAL)


class Validator:
    def __init__(self):
        self.valid = True

    def reset(self):
        self.valid = True

    def correct_if(self, condition):
        self.valid = self.valid and bool(condition)


class Student:
    def __init__(self, f: Path):
        self.file = f
        self.name = student_name(f.name)
        self.folder = student_folder(f.name)
        self.score = 0
        self.total = 0
        self.error = None
        self.html_file_path = None
        self.css_file_path = None
        self._comment = ""

    def comment(self):
        if self.error:
            return self.error
        return self._comment

    def analyze(self):
        print(self.name)
        self.unzip()
        if self._has_error():
            return

        if not self._analyze_html():
            return

        self._analyze_css()

    def add_point(self, valid, points=1):
        self.total += points
        if valid:
            self.score += points

    def _analyze_html(self):
        if self.html_file_path is None or not self.html_file_path.exists():
            self._error('index.html file not found')
            return False

        with (self.html_file_path.open('r') as f):
            soup = BeautifulSoup(f, 'html.parser')

            # Vérifie si association à la feuille de style et présence du titre
            v = Validator()
            v.correct_if(soup.head.link)
            v.correct_if(soup.head.title)
            self.add_point(v.valid)

            # Vérification de la balise du logo
            tag = soup.body.a
            v.reset()
            v.correct_if(tag.string == 'PMDb')
            v.correct_if(tag['href'] == 'https://www.imdb.com/video/vi59285529')
            v.correct_if('class' in tag.attrs and 'logo' in tag['class'])
            self.add_point(v.valid)

            # Vérification de la classe sur l'image de l'affiche
            tag = soup.body.img
            v.reset()
            v.correct_if(tag and 'class' in tag.attrs and ('affiche' in tag['class'] or 'petite-image' in tag['class']))
            self.add_point(v.valid)

        return True

    def _analyze_css(self):
        if self.css_file_path is None or not self.css_file_path.exists():
            self._error('style.css file not found')
            return False

        # Récupération des styles à vérifier.
        rules = {
            'body': None,
            'h1': None,
            'h2': None,
            'image': None,
        }

        selector_count = {}

        sheet = cssutils.parseFile(self.css_file_path)
        for rule in sheet:
            selector = rule.selectorText

            if selector in ['body', 'h1', 'h2']:
                rules[rule.selectorText] = rule
            elif selector in ['.petite-image', '.affiche']:
                rules['image'] = rule

            if selector not in selector_count:
                selector_count[selector] = 1
            else:
                selector_count[selector] += 1

        # Commentaire sur les éléments CSS présents
        self._comment += "CSS["
        self._comment += 'X' if rules['body'] else ' '
        self._comment += 'X' if rules['h1'] else ' '
        self._comment += 'X' if rules['h2'] else ' '
        self._comment += 'X' if rules['image'] else ' '
        self._comment += "]"

        # Absence de selecteurs en double
        multiple = False
        for selector, count in selector_count.items():
            if count > 1:
                multiple = True

        v = Validator()
        v.correct_if(not multiple)
        self.add_point(v.valid)

        # Un style pour la balise h1 est présent
        v.reset()
        v.correct_if(rules['h1'] is not None)
        self.add_point(v.valid)

        # Un style pour la balise h2 est présent
        v.reset()
        v.correct_if(rules['h2'] is not None)
        self.add_point(v.valid)

        # Un style pour l'affiche est présent
        v.reset()
        v.correct_if(rules['image'] is not None)
        self.add_point(v.valid)

        # La couleur de fond de la page a été changé
        has_image = bool(rules['body'].style['background-image'])
        v.reset()
        v.correct_if(has_image or rules['body'].style['background-color'] != 'purple')
        self.add_point(v.valid)

        # La couleur du h1
        v.reset()
        v.correct_if(rules['h1'] and bool(rules['h1'].style['font-size']))
        self.add_point(v.valid)

        # La couleur du h2
        v.reset()
        v.correct_if(rules['h2'] and bool(rules['h2'].style['color']))
        self.add_point(v.valid)

        # Le soulignement du h2
        v.reset()
        v.correct_if(rules['h2'] and rules['h2'].style['text-decoration'] == 'underline')
        self.add_point(v.valid)

        # print(rules)

    def is_zipped(self):
        return self.file.suffix == '.zip'

    def unzip(self):
        # If not zip file, return
        if not self.is_zipped():
            self._error("Regular file, not ZIP")
            return

        zip_root_path = None
        extract_root_path = file.parent.joinpath(self.folder)

        if not extract_root_path.exists():
            # shutil.rmtree(extract_root_path)

            # Unzip
            try:
                with zipfile.ZipFile(self.file, 'r') as z:
                    if len(z.namelist()) == 0:
                        self._error("Empty ZIP")
                        return

                    zip_root_path = zipfile_index_path(z)
                    z.extractall(extract_root_path)
            except zipfile.BadZipFile:
                print("The file is not a ZIP file or it is corrupted.")

            # Cleanup
            if zip_root_path is None:
                return

            extract_files_path = extract_root_path.joinpath(zip_root_path)
            for entry in extract_files_path.glob('*'):
                shutil.move(entry, extract_root_path)
            shutil.rmtree(extract_files_path)

        # Path to important files
        self.html_file_path = extract_root_path.joinpath('index.html')
        self.css_file_path = extract_root_path.joinpath('style.css')

    def _has_error(self):
        return self.error is not None

    def _error(self, message):
        if self.error is None:
            self.error = message


if __name__ == '__main__':
    students = []

    x = PrettyTable()
    x.field_names = ['Student', 'Score', 'Final Score', 'Comment']
    x.align['Student'] = 'l'

    for file in Path('src').glob('*'):
        if file.name in ['.DS_Store', '.gitignore']:
            continue

        if file.is_dir():
            continue

        student = Student(file)
        student.analyze()
        x.add_row([student.name, student.score, student.score if student.score <= 10 else 10, student.comment()])

    print(x.get_string(sortby="Student"))
