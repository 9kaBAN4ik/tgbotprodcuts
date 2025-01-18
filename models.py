# models.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Course(Base):
    __tablename__ = 'courses'
    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    description = Column(Text)
    lessons = relationship('Lesson', backref='course')

class Lesson(Base):
    __tablename__ = 'lessons'
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id'))
    title = Column(String(255))
    description = Column(Text)
    material_link = Column(String(255))  # Ссылка на видео или статью
    questions = relationship('Question', backref='lesson')

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'))
    text = Column(String(255))
    options = Column(Text)  # Список вариантов ответа, разделенных запятыми
    correct_answer = Column(Integer)  # Индекс правильного ответа (например, 1 для первого варианта)
