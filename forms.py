from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp


EMAIL_VALIDATOR = Regexp(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    message="Введите корректный email.",
)


class RegisterForm(FlaskForm):
    username = StringField(
        "Имя пользователя",
        validators=[DataRequired(), Length(min=3, max=100)],
    )
    email = StringField(
        "Email",
        validators=[DataRequired(), EMAIL_VALIDATOR, Length(max=120)],
    )
    password = PasswordField(
        "Пароль",
        validators=[DataRequired(), Length(min=6, max=128)],
    )
    password_again = PasswordField(
        "Повторите пароль",
        validators=[
            DataRequired(),
            EqualTo("password", message="Пароли должны совпадать."),
        ],
    )
    submit = SubmitField("Создать аккаунт")


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(), EMAIL_VALIDATOR, Length(max=120)],
    )
    password = PasswordField(
        "Пароль",
        validators=[DataRequired(), Length(min=6, max=128)],
    )
    submit = SubmitField("Войти")


class AvatarForm(FlaskForm):
    avatar = FileField(
        "Аватар",
        validators=[FileAllowed(["jpg", "jpeg", "png", "gif", "webp"], "Нужен файл изображения.")],
    )
    submit = SubmitField("Обновить аватар")


class TrackUploadForm(FlaskForm):
    title = StringField(
        "Название трека",
        validators=[DataRequired(), Length(min=1, max=150)],
    )
    track_file = FileField(
        "Файл трека",
        validators=[FileAllowed(["mp3", "wav", "ogg", "flac", "m4a"], "Нужен аудиофайл.")],
    )
    submit = SubmitField("Загрузить трек")
