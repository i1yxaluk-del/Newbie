import { useEffect, useMemo, useState } from 'react'
import { api } from '../api.js'

const FALLBACK = {
  'hero.title': 'Гостевой дом «Алина» на Азовском море',
  'hero.subtitle': 'Тёплое море, домашний уют и тишина у самого берега',
  'hero.cta': 'Забронировать',
  'about.title': 'О нас',
  'about.text': 'Уютный гостевой дом в шаге от моря.',
  'rooms.title': 'Номера',
  'rooms.text': 'Стандартные и семейные номера со всеми удобствами.',
  'amenities.title': 'Удобства',
  'amenities.items': 'Wi-Fi;Парковка;Кондиционер;Двор;Мангал;Кухня',
  'gallery.title': 'Галерея',
  'location.title': 'Где мы находимся',
  'location.address': 'Азовское море, Краснодарский край',
  'location.note': 'Адрес уточняем после подтверждения брони.',
  'contacts.title': 'Контакты',
  'contacts.owner_name': 'Лукьянченко Александр Викторович',
  'contacts.owner_role': 'Хозяин гостевого дома',
  'contacts.phone': '+7 918 212-96-01',
  'contacts.vk': 'https://vk.ru/gostevoy_domalina',
  'contacts.vk_personal': 'https://vk.ru/id135593764',
  'contacts.owner_photo': '',
  'footer.note': '© Гостевой дом «Алина».',
}

export default function Landing() {
  const [c, setC] = useState(FALLBACK)
  const [form, setForm] = useState({ name: '', phone: '', email: '', guests: '', date_from: '', date_to: '', message: '' })
  const [sending, setSending] = useState(false)
  const [ok, setOk] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.getContent().then(d => setC({ ...FALLBACK, ...d })).catch(() => {})
  }, [])

  const amenities = useMemo(
    () => (c['amenities.items'] || '').split(';').map(s => s.trim()).filter(Boolean),
    [c]
  )

  async function submit(e) {
    e.preventDefault()
    setSending(true); setErr(''); setOk(false)
    try {
      const payload = {
        ...form,
        guests: form.guests ? Number(form.guests) : null,
        email: form.email || null,
      }
      await api.createLead(payload)
      setOk(true)
      setForm({ name: '', phone: '', email: '', guests: '', date_from: '', date_to: '', message: '' })
    } catch (e) {
      setErr('Не удалось отправить заявку. Попробуйте позвонить: ' + c['contacts.phone'])
    } finally {
      setSending(false)
    }
  }

  const phoneHref = 'tel:' + (c['contacts.phone'] || '').replace(/[^+\d]/g, '')

  return (
    <>
      <header className="header">
        <div className="container header__inner">
          <a href="#top" className="brand">
            <div className="brand__mark">A</div>
            <div>
              <div className="brand__name">Алина <span className="brand__sub">у моря</span></div>
            </div>
          </a>
          <nav className="nav">
            <a href="#about">О доме</a>
            <a href="#rooms">Номера</a>
            <a href="#gallery">Галерея</a>
            <a href="#contacts">Контакты</a>
            <a className="btn btn--primary" href="#book">{c['hero.cta']}</a>
          </nav>
        </div>
      </header>

      <main id="top">
        <section className="hero container">
          <div className="hero__grid">
            <div>
              <div className="hero__eyebrow">Азовское море · лето круглый год в сердце</div>
              <h1 className="hero__title">{c['hero.title']}</h1>
              <p className="hero__lead">{c['hero.subtitle']}</p>
              <div className="hero__cta">
                <a className="btn btn--primary" href="#book">{c['hero.cta']}</a>
                <a className="btn btn--ghost" href={phoneHref}>Позвонить</a>
              </div>
            </div>
            <div className="hero__art">
              <div className="hero__sun" />
              <div className="hero__wave" />
              <div className="hero__house" />
            </div>
          </div>
        </section>

        <section id="about" className="section">
          <div className="container grid-2">
            <div>
              <h2>{c['about.title']}</h2>
              <p>{c['about.text']}</p>
            </div>
            <div className="card">
              <h3>Почему у нас тепло</h3>
              <p>• Семейная атмосфера и встречаем как родных</p>
              <p>• Минуты пешком до тёплого моря</p>
              <p>• Чистые номера, бельё и полотенца включены</p>
              <p>• Двор с зоной отдыха и мангалом</p>
            </div>
          </div>
        </section>

        <section id="rooms" className="section section--tight">
          <div className="container">
            <h2>{c['rooms.title']}</h2>
            <p style={{ maxWidth: 720 }}>{c['rooms.text']}</p>
            <div className="grid-3" style={{ marginTop: 24 }}>
              <div className="card"><h3>Стандарт 2-местный</h3><p>Кондиционер, душ, Wi-Fi.</p></div>
              <div className="card"><h3>Семейный 3–4 места</h3><p>Просторный номер, удобства, балкон.</p></div>
              <div className="card"><h3>Большая семья</h3><p>Сдвоенный номер для компании или большой семьи.</p></div>
            </div>
          </div>
        </section>

        <section className="section section--tight">
          <div className="container">
            <h2>{c['amenities.title']}</h2>
            <div className="amenities">
              {amenities.map(a => <span key={a} className="amenity">{a}</span>)}
            </div>
          </div>
        </section>

        <section id="gallery" className="section section--tight">
          <div className="container">
            <h2>{c['gallery.title']}</h2>
            <div className="gallery">
              {Array.from({ length: 8 }).map((_, i) => <div key={i} className="gallery__cell" />)}
            </div>
            <p className="form__hint" style={{ marginTop: 14 }}>
              Фото из <a href={c['contacts.vk']} target="_blank" rel="noreferrer">группы ВКонтакте</a> будут добавлены через панель администратора.
            </p>
          </div>
        </section>

        <section id="contacts" className="section">
          <div className="container grid-2">
            <div className="card">
              <h2>{c['contacts.title']}</h2>
              <div className="owner" style={{ marginTop: 12 }}>
                <div className="owner__avatar">АЛ</div>
                <div>
                  <div className="owner__name">{c['contacts.owner_name']}</div>
                  <div className="owner__role">{c['contacts.owner_role']}</div>
                  <a className="owner__phone" href={phoneHref}>{c['contacts.phone']}</a>
                </div>
              </div>
              <p style={{ marginTop: 16 }}>
                ВКонтакте: <a href={c['contacts.vk']} target="_blank" rel="noreferrer">группа гостевого дома</a><br />
                Личная страница: <a href={c['contacts.vk_personal']} target="_blank" rel="noreferrer">{c['contacts.vk_personal']}</a>
              </p>
            </div>

            <div className="card">
              <h3>{c['location.title']}</h3>
              <p>{c['location.address']}</p>
              <p className="form__hint">{c['location.note']}</p>
            </div>
          </div>
        </section>

        <section id="book" className="section">
          <div className="container" style={{ maxWidth: 720 }}>
            <h2>Оставить заявку</h2>
            <p>Свяжемся в ближайшее время, расскажем про свободные даты и условия.</p>
            <form className="form" onSubmit={submit}>
              {ok && <div className="form__success">Спасибо! Заявка отправлена. Мы скоро свяжемся.</div>}
              {err && <div className="form__error">{err}</div>}
              <div className="form__row">
                <div>
                  <label>Ваше имя *</label>
                  <input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
                </div>
                <div>
                  <label>Телефон *</label>
                  <input required value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} placeholder="+7..." />
                </div>
              </div>
              <div className="form__row">
                <div>
                  <label>Email</label>
                  <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
                </div>
                <div>
                  <label>Гостей</label>
                  <input type="number" min="1" max="20" value={form.guests} onChange={e => setForm({ ...form, guests: e.target.value })} />
                </div>
              </div>
              <div className="form__row">
                <div>
                  <label>Заезд</label>
                  <input type="date" value={form.date_from} onChange={e => setForm({ ...form, date_from: e.target.value })} />
                </div>
                <div>
                  <label>Выезд</label>
                  <input type="date" value={form.date_to} onChange={e => setForm({ ...form, date_to: e.target.value })} />
                </div>
              </div>
              <label>Комментарий</label>
              <textarea value={form.message} onChange={e => setForm({ ...form, message: e.target.value })} placeholder="Пожелания, вопросы..." />
              <div style={{ marginTop: 16, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                <button className="btn btn--primary" disabled={sending} type="submit">
                  {sending ? 'Отправляем...' : 'Отправить заявку'}
                </button>
                <span className="form__hint">Нажимая «Отправить», вы соглашаетесь с обработкой персональных данных.</span>
              </div>
            </form>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="container footer__row">
          <div>{c['footer.note']}</div>
          <div>
            <a href={phoneHref}>{c['contacts.phone']}</a> · <a href={c['contacts.vk']} target="_blank" rel="noreferrer">VK</a> · <a href="/admin/login">Админ</a>
          </div>
        </div>
      </footer>
    </>
  )
}
