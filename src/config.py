"""Configuration used when reading and analyzing grade spreadsheets."""

GRADES = [
    "PREESCOLAR", "PRIMERO", "SEGUNDO", "TERCERO", "CUARTO", "QUINTO",
    "SEXTO", "SÉPTIMO", "OCTAVO", "NOVENO", "DÉCIMO", "ONCE",
]
GRADE_TO_NUMBER = {grade: index for index, grade in enumerate(GRADES)}
GRADE_NUMBERS = ["UNO", "DOS", "TRES", "CUATRO", "CINCO"]
PERIODS = ["1/4", "2/4", "3/4", "4/4"]
SUBJECTS = [
    "NOMBRE", "Ciencias naturales", "Ciencias sociales y cátedra de la paz",
    "Comportamiento", "Educación artística", "Educación física", "Ética",
    "Informática", "Inglés", "Investigación", "Español", "Matemáticas",
    "Pedagogía", "Religión",
]
CATEGORIES = ["SUPERIOR", "ALTO", "BASICO", "BAJO"]
SCORE_THRESHOLDS = {
    "superior": 50,
    "alto": 45,
    "basico": 40,
    "bajo": 30,
}
