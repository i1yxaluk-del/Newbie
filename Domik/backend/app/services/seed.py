from sqlalchemy.orm import Session

from ..config import settings
from ..models import LandingContent, User
from ..security import hash_password

DEFAULT_CONTENT = {
    "hero.title": "Гостевой дом «Алина» на Азовском море",
    "hero.subtitle": "Тёплое море, домашний уют и тишина у самого берега",
    "hero.cta": "Забронировать",
    "about.title": "О нас",
    "about.text": (
        "«Алина» — уютный гостевой дом в нескольких минутах ходьбы от Азовского моря. "
        "Мы создаём для вас атмосферу настоящего летнего отдыха: чистые тёплые номера, "
        "уютный двор, домашняя кухня и гостеприимный хозяин."
    ),
    "rooms.title": "Номера",
    "rooms.text": "Стандартные и семейные номера с удобствами, кондиционером и Wi-Fi.",
    "amenities.title": "Удобства",
    "amenities.items": (
        "Wi-Fi;Парковка;Кондиционер;Двор и зона отдыха;Мангал;Кухня;"
        "Бельё и полотенца;Доступ к морю"
    ),
    "gallery.title": "Галерея",
    "location.title": "Где мы находимся",
    "location.address": "Краснодарский край, побережье Азовского моря",
    "location.note": "Точный адрес и схему проезда вышлем после подтверждения брони.",
    "contacts.title": "Контакты",
    "contacts.owner_name": "Лукьянченко Александр Викторович",
    "contacts.owner_role": "Хозяин гостевого дома",
    "contacts.phone": "+7 918 212-96-01",
    "contacts.vk": "https://vk.ru/gostevoy_domalina",
    "contacts.vk_personal": "https://vk.ru/id135593764",
    "contacts.owner_photo": "https://vk.ru/photo135593764_457241091",
    "footer.note": "© Гостевой дом «Алина». Азовское море. Сделано с теплом.",
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
