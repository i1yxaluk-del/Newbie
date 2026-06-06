from sqlalchemy.orm import Session

from ..config import settings
from ..models import LandingContent, User
from ..security import hash_password

DEFAULT_CONTENT = {
    "hero.title": "Гостевой дом «АЛиНА»",
    "hero.subtitle": "Приглашаем Вас отдохнуть в посёлке Кучугуры: песчаный берег, ласковое тёплое море, тихий двор, бассейн и 5 комфортных номеров с удобствами.",
    "hero.cta": "Забронировать отдых",
    "about.title": "Отдых у тёплого Азовского моря",
    "about.text": (
        "Приглашаем Вас отдохнуть в посёлке Кучугуры в гостевом доме «АЛиНА». "
        "До песчаного пляжа около 400 метров — примерно 10 минут спокойной прогулки. "
        "Рядом нет шумных заведений, зато рядом магазины, столовые, кафе, рынок, аптека, банкомат, парки и аттракционы."
    ),
    "rooms.title": "5 комфортных номеров",
    "rooms.text": "Номера с удобствами: душ/туалет, телевизор, кондиционер или сплит-система. Возле каждого номера — своя обеденная зона.",
    "amenities.title": "Что есть для гостей",
    "amenities.items": (
        "400 м до пляжа;Песчаный берег;Автостоянка;Бассейн;Интернет в номерах;"
        "Телевизоры;Детская площадка;Беседка с мангалом;Можно с детьми любого возраста;"
        "Гладильная доска и утюг;Общая кухня;Стирка платно;Прокат коляски платно;Трансфер;"
        "Грязевой лечебный вулкан рядом;Минеральные источники рядом"
    ),
    "gallery.title": "Фото гостевого дома",
    "location.title": "Кучугуры, Азовское море",
    "location.address": "пос. Кучугуры, Краснодарский край, 400 м от пляжа",
    "location.note": "Песчаный берег, ласковое тёплое море, рядом грязевой лечебный вулкан и минеральные источники.",
    "contacts.title": "Связаться и забронировать",
    "contacts.owner_name": "Лукьянченко Александр Викторович",
    "contacts.owner_role": "Александр, руководитель гостевого дома",
    "contacts.phone": "+7 918 212-96-01",
    "contacts.vk": "https://vk.com/gostevoy_domalina",
    "contacts.vk_personal": "https://vk.ru/id135593764",
    "contacts.owner_photo": "/media/owner/01.png",
    "media.settings": "{}",
    "footer.note": "© Гостевой дом «Алина». Кучугуры, Азовское море.",
}


def seed_admin(db: Session) -> None:
    if db.query(User).count() == 0:
        u = User(
            email=settings.ADMIN_EMAIL,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            is_admin=True,
        )
        db.add(u)
        db.commit()


def seed_content(db: Session) -> None:
    existing = {c.key for c in db.query(LandingContent).all()}
    for k, v in DEFAULT_CONTENT.items():
        if k not in existing:
            db.add(LandingContent(key=k, value=v))
    db.commit()


def run_seed(db: Session) -> None:
    seed_admin(db)
    seed_content(db)
