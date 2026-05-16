import secrets
from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for

from data import db_session
from data.tracks import Track
from data.users import User
from forms import AvatarForm, LoginForm, RegisterForm, TrackUploadForm


app = Flask(__name__)
app.config["SECRET_KEY"] = "yandexlyceum_secret_key"
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

db_session.global_init("db/blogs.db")

BASE_DIR = Path(__file__).resolve().parent
AVATAR_UPLOAD_DIR = BASE_DIR / "static" / "uploads" / "avatars"
TRACK_UPLOAD_DIR = BASE_DIR / "static" / "uploads" / "tracks"
ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_TRACK_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}


def ensure_upload_directories():
    AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    TRACK_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    db_sess = db_session.create_session()
    try:
        return db_sess.get(User, user_id)
    finally:
        db_sess.close()


def build_avatar_url(user):
    if user and user.avatar_filename:
        return url_for("static", filename=f"uploads/avatars/{user.avatar_filename}")
    return None


def save_avatar_file(file_storage):
    extension = Path(file_storage.filename).suffix.lower()
    if extension not in ALLOWED_AVATAR_EXTENSIONS:
        return None

    unique_name = f"{secrets.token_hex(12)}{extension}"
    target_path = AVATAR_UPLOAD_DIR / unique_name
    file_storage.save(target_path)
    return unique_name


def save_track_file(file_storage):
    extension = Path(file_storage.filename).suffix.lower()
    if extension not in ALLOWED_TRACK_EXTENSIONS:
        return None

    unique_name = f"{secrets.token_hex(12)}{extension}"
    target_path = TRACK_UPLOAD_DIR / unique_name
    file_storage.save(target_path)
    return unique_name


def serialize_track(track):
    return {
        "id": track.id,
        "title": track.title,
        "artist": track.user.username if track.user else "",
        "url": url_for("static", filename=f"uploads/tracks/{track.filename}"),
        "profile_url": url_for("account_by_username", username=track.user.username) if track.user else "#",
    }


def get_profile_context(profile_user, viewer=None, avatar_form=None, track_form=None):
    own_tracks = [serialize_track(track) for track in profile_user.tracks]
    return {
        "avatar_form": avatar_form or AvatarForm(),
        "track_form": track_form or TrackUploadForm(),
        "profile_user": profile_user,
        "avatar_url": build_avatar_url(profile_user),
        "followers_count": len(profile_user.followers),
        "uploaded_tracks_count": len(profile_user.tracks),
        "own_tracks": own_tracks,
        "liked_tracks": [],
        "is_own_profile": viewer is not None and viewer.id == profile_user.id,
        "is_following": viewer is not None and viewer.id != profile_user.id and viewer.is_following(profile_user),
    }


@app.context_processor
def inject_user():
    current_user = get_current_user()
    return {
        "current_user": current_user,
        "current_user_avatar_url": build_avatar_url(current_user),
    }


@app.route("/")
def index():
    db_sess = db_session.create_session()
    try:
        latest_tracks = (
            db_sess.query(Track)
            .order_by(Track.created_at.desc())
            .limit(6)
            .all()
        )
        popular_tracks = [serialize_track(track) for track in latest_tracks]
    finally:
        db_sess.close()
    return render_template("index.html", popular_tracks=popular_tracks)


@app.route("/cookan")
def cookan():
    return render_template("cookan.html")


@app.route("/cookan.png")
def cookan_image():
    return send_from_directory(BASE_DIR, "cookan.png")


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            existing_user = db_sess.query(User).filter(
                (User.username == form.username.data) | (User.email == form.email.data)
            ).first()
            if existing_user:
                flash("Пользователь с таким именем или email уже существует.", "danger")
            else:
                user = User(
                    username=form.username.data,
                    email=form.email.data,
                )
                user.set_password(form.password.data)
                db_sess.add(user)
                db_sess.commit()
                flash("Регистрация прошла успешно. Теперь можно войти.", "success")
                return redirect(url_for("login"))
        finally:
            db_sess.close()
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.email == form.email.data).first()
            if user and user.check_password(form.password.data):
                session["user_id"] = user.id
                flash("Вы успешно вошли в аккаунт.", "success")
                return redirect(url_for("account"))
            flash("Неверный email или пароль.", "danger")
        finally:
            db_sess.close()
    return render_template("login.html", form=form)


@app.route("/account", methods=["GET", "POST"])
def account():
    current_user = get_current_user()
    if not current_user:
        flash("Сначала войдите в аккаунт.", "warning")
        return redirect(url_for("login"))
    return redirect(url_for("account_by_username", username=current_user.username))


@app.route("/account/<username>", methods=["GET", "POST"])
def account_by_username(username):
    viewer = get_current_user()
    db_sess = db_session.create_session()
    try:
        profile_user = db_sess.query(User).filter(User.username == username).first()
        if not profile_user:
            flash("Пользователь не найден.", "warning")
            return redirect(url_for("index"))

        avatar_form = AvatarForm()
        track_form = TrackUploadForm()
        is_own_profile = viewer is not None and viewer.id == profile_user.id

        if request.method == "POST":
            if not viewer:
                flash("Сначала войдите в аккаунт.", "warning")
                return redirect(url_for("login"))

            action = request.form.get("action")

            if action == "toggle_follow" and viewer.id != profile_user.id:
                viewer_db = db_sess.get(User, viewer.id)
                profile_db = db_sess.get(User, profile_user.id)
                if viewer_db.is_following(profile_db):
                    viewer_db.following = [user for user in viewer_db.following if user.id != profile_db.id]
                    flash("Вы отписались от пользователя.", "info")
                else:
                    viewer_db.following.append(profile_db)
                    flash("Вы подписались на пользователя.", "success")
                db_sess.commit()
                return redirect(url_for("account_by_username", username=profile_user.username))

            if action == "update_avatar" and is_own_profile:
                if avatar_form.validate_on_submit():
                    if not avatar_form.avatar.data or not avatar_form.avatar.data.filename:
                        flash("Выберите изображение для аватарки.", "warning")
                    else:
                        ensure_upload_directories()
                        avatar_filename = save_avatar_file(avatar_form.avatar.data)
                        if not avatar_filename:
                            flash("Поддерживаются только изображения jpg, png, gif и webp.", "danger")
                        else:
                            profile_db = db_sess.get(User, profile_user.id)
                            old_avatar = profile_db.avatar_filename
                            profile_db.avatar_filename = avatar_filename
                            db_sess.commit()

                            if old_avatar:
                                old_path = AVATAR_UPLOAD_DIR / old_avatar
                                if old_path.exists():
                                    old_path.unlink()

                            flash("Аватарка обновлена.", "success")
                            return redirect(url_for("account_by_username", username=profile_user.username))
                else:
                    flash("Не удалось обновить аватарку.", "danger")

            if action == "upload_track" and is_own_profile:
                if track_form.validate_on_submit():
                    if not track_form.track_file.data or not track_form.track_file.data.filename:
                        flash("Выберите аудиофайл.", "warning")
                    else:
                        ensure_upload_directories()
                        track_filename = save_track_file(track_form.track_file.data)
                        if not track_filename:
                            flash("Поддерживаются только mp3, wav, ogg, flac и m4a.", "danger")
                        else:
                            profile_db = db_sess.get(User, profile_user.id)
                            track = Track(
                                title=track_form.title.data.strip(),
                                filename=track_filename,
                                user=profile_db,
                            )
                            db_sess.add(track)
                            db_sess.commit()
                            flash("Трек загружен.", "success")
                            return redirect(url_for("account_by_username", username=profile_user.username))
                else:
                    flash("Не удалось загрузить трек.", "danger")

        profile_user = db_sess.get(User, profile_user.id)
        viewer_db = db_sess.get(User, viewer.id) if viewer else None
        context = get_profile_context(profile_user, viewer_db, avatar_form, track_form)
        return render_template("account.html", **context)
    finally:
        db_sess.close()


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    db_sess = db_session.create_session()
    try:
        users = (
            db_sess.query(User)
            .filter(User.username.ilike(f"%{query}%"))
            .order_by(User.username.asc())
            .limit(5)
            .all()
        )
        tracks = (
            db_sess.query(Track)
            .filter(Track.title.ilike(f"%{query}%"))
            .order_by(Track.created_at.desc())
            .limit(5)
            .all()
        )

        user_payload = [
            {
                "type": "user",
                "label": user.username,
                "subtitle": "Аккаунт",
                "url": url_for("account_by_username", username=user.username),
                "avatar_url": build_avatar_url(user),
            }
            for user in users
        ]
        track_payload = [
            {
                "type": "track",
                "label": track.title,
                "subtitle": track.user.username if track.user else "Трек",
                "url": url_for("account_by_username", username=track.user.username) if track.user else "#",
                "audio_url": url_for("static", filename=f"uploads/tracks/{track.filename}"),
            }
            for track in tracks
        ]
        return jsonify((user_payload + track_payload)[:5])
    finally:
        db_sess.close()


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for("index"))


def main():
    ensure_upload_directories()
    app.run(port=8080)


if __name__ == "__main__":
    main()
 # meow
