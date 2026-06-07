import { useEffect, useMemo, useState } from 'react'
import { api } from '../api.js'

const FALLBACK = {
  'hero.title': 'Гостевой дом «АЛиНА»',
  'hero.subtitle': 'Приглашаем Вас отдохнуть в посёлке Кучугуры: песчаный берег, ласковое тёплое море, тихий двор, бассейн и 5 комфортных номеров с удобствами.',
  'hero.cta': 'Забронировать отдых',
  'about.title': 'Отдых у тёплого Азовского моря',
  'about.text': 'Приглашаем Вас отдохнуть в посёлке Кучугуры в гостевом доме «АЛиНА». До песчаного пляжа около 400 метров — примерно 10 минут спокойной прогулки.',
  'rooms.title': '5 комфортных номеров',
  'rooms.text': 'Номера с удобствами: душ/туалет, телевизор, кондиционер или сплит-система. Возле каждого номера — своя обеденная зона.',
  'amenities.title': 'Что есть для гостей',
  'amenities.items': '400 м до пляжа;Песчаный берег;Автостоянка;Бассейн;Интернет в номерах;Телевизоры;Детская площадка;Беседка с мангалом;Можно с детьми любого возраста;Общая кухня;Трансфер',
  'gallery.title': 'Фото гостевого дома',
  'location.title': 'Кучугуры, Азовское море',
  'location.address': 'ул. Рабочая, 38, Кучугуры, Краснодарский край',
  'location.note': 'Песчаный берег, ласковое тёплое море, рядом грязевой лечебный вулкан и минеральные источники.',
  'contacts.title': 'Связаться и забронировать',
  'contacts.owner_name': 'Лукьянченко Александр Викторович',
  'contacts.owner_role': 'Александр, руководитель гостевого дома',
  'contacts.phone': '+7 918 212-96-01',
  'contacts.vk': 'https://vk.com/gostevoy_domalina',
  'contacts.vk_personal': 'https://vk.ru/id135593764',
  'contacts.owner_photo': '/media/owner/01.png',
  'media.settings': '{}',
  'footer.note': '© Гостевой дом «Алина». Кучугуры, Азовское море.',
}

const FEATURED_ALBUMS = [
  { label: 'Побережье', title: 'Тёплый берег', ids: ['beach'] },
  { label: 'Дом', title: 'Гостевой дом', ids: ['guest-house'] },
  { label: 'Номер', title: 'Номера', ids: ['room-2', 'room-3-4-1', 'room-3-4-2', 'room-two-room-4', 'room-one-room-4'] },
  { label: 'Двор', title: 'Двор и отдых', ids: ['yard'] },
  { label: 'Летняя атмосфера', title: 'Летняя атмосфера', ids: ['summer'] },
  { label: 'Кухня', title: 'Кухня', ids: ['kitchen'] },
]

function safeParse(raw) {
  if (!raw) return {}
  const trimmed = String(raw).trim()
  if (!trimmed || trimmed === 'undefined' || trimmed === 'null') return {}
  try { const parsed = JSON.parse(trimmed); return (parsed && typeof parsed === 'object') ? parsed : {} } catch { return {} }
}

function mergeMediaSettings(manifest, rawSettings) {
  const albums = Array.isArray(manifest?.albums) ? manifest.albums : []
  const settings = safeParse(rawSettings)
  const customAlbums = Array.isArray(settings.customAlbums) ? settings.customAlbums : []
  const allAlbums = [...albums, ...customAlbums]
  const albumOrder = Array.isArray(settings.albumOrder) ? settings.albumOrder : []
  const albumSettings = (settings.albums && typeof settings.albums === 'object') ? settings.albums : {}
  return [...allAlbums]
    .map(album => {
      const cfg = albumSettings[album.id] || {}
      const deleted = new Set(cfg.deletedPhotos || [])
      const basePhotos = (album.photos || []).concat(cfg.addedPhotos || []).filter(p => !deleted.has(p))
      const photos = cfg.photoOrder?.length
        ? cfg.photoOrder.filter(p => basePhotos.includes(p)).concat(basePhotos.filter(p => !cfg.photoOrder.includes(p)))
        : basePhotos
      return { ...album, photos, cover: cfg.cover || album.cover || photos[0], hidden: !!cfg.hidden, chips: cfg.chips && cfg.chips.length ? cfg.chips : album.chips, title: cfg.title || album.title, description: cfg.description || album.description }
    })
    .filter(a => !a.hidden && (a.photos.length || a.cover))
    .sort((a, b) => {
      const ai = albumOrder.indexOf(a.id)
      const bi = albumOrder.indexOf(b.id)
      return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
    })
}

export default function Landing() {
  const [c, setC] = useState(FALLBACK)
  const [manifest, setManifest] = useState({ albums: [] })
  const [activeAlbum, setActiveAlbum] = useState(null)
  const [calendar, setCalendar] = useState({ bookings_open: true, unavailable_dates: [], blocked_dates: [], occupied_dates: [] })
  const [form, setForm] = useState({ name: '', phone: '', email: '', guests: '', date_from: '', date_to: '', message: '' })
  const [sending, setSending] = useState(false)
  const [ok, setOk] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.getContent().then(d => setC({ ...FALLBACK, ...d })).catch(() => {})
    fetch('/media-manifest.json').then(r => r.json()).then(setManifest).catch(() => {})
    api.getCalendarPublic().then(setCalendar).catch(() => {})
  }, [])

  const albums = useMemo(() => mergeMediaSettings(manifest, c['media.settings']), [manifest, c])
  const mediaSettings = useMemo(() => safeParse(c['media.settings']), [c])
  const singles = mediaSettings.singleImages || {}
  const unavailable = useMemo(() => new Set(calendar.unavailable_dates || []), [calendar])
  const bookingsOpen = calendar.bookings_open !== false
  const closedMessage = c['bookings.closed_message'] || 'В настоящее время мы не принимаем гостей. Пожалуйста, попробуйте позже или свяжитесь по телефону.'

  function isRangeBlocked(from, to) {
    if (!from || !to) return false
    const a = new Date(from); const b = new Date(to)
    if (isNaN(a) || isNaN(b)) return false
    if (b < a) return false
    const cur = new Date(a)
    while (cur <= b) {
      const iso = cur.toISOString().slice(0, 10)
      if (unavailable.has(iso)) return true
      cur.setDate(cur.getDate() + 1)
    }
    return false
  }
  const rangeBlocked = isRangeBlocked(form.date_from, form.date_to)
  const roomAlbums = albums.filter(a => a.category === 'rooms')
  const guestHouse = albums.find(a => a.id === 'guest-house')
  const yard = albums.find(a => a.id === 'yard')
  const beach = albums.find(a => a.id === 'beach')
  const owner = albums.find(a => a.id === 'owner')
  const heroPhoto = singles.hero || guestHouse?.cover || albums[0]?.cover || '/media/guest-house/01.jpg'
  const ownerPhoto = singles.owner || c['contacts.owner_photo'] || owner?.cover
  const aboutPhoto1 = singles.about1 || guestHouse?.photos?.[1] || '/media/guest-house/02.jpg'
  const aboutPhoto2 = singles.about2 || yard?.cover || '/media/yard/01.jpg'
  const galleryPhotos = albums.flatMap(a => a.photos.slice(0, 3)).slice(0, 12)
  const featuredAlbums = FEATURED_ALBUMS.map(group => {
    const groupAlbums = group.ids.map(id => albums.find(a => a.id === id)).filter(Boolean)
    const photos = groupAlbums.flatMap(a => a.photos)
    return {
      ...group,
      albums: groupAlbums,
      photos,
      cover: groupAlbums[0]?.cover || photos[0],
      count: photos.length,
    }
  }).filter(group => group.cover)

  const amenities = useMemo(
    () => (c['amenities.items'] || '').split(';').map(s => s.trim()).filter(Boolean),
    [c]
  )

  async function submit(e) {
    e.preventDefault()
    if (!bookingsOpen) {
      setErr(closedMessage)
      return
    }
    if (rangeBlocked) {
      setErr('Выбранные даты недоступны. Пожалуйста, выберите другие.')
      return
    }
    setSending(true); setErr(''); setOk(false)
    try {
      await api.createLead({
        ...form,
        guests: form.guests ? Number(form.guests) : null,
        email: form.email || null,
      })
      setOk(true)
      setForm({ name: '', phone: '', email: '', guests: '', date_from: '', date_to: '', message: '' })
      api.getCalendarPublic().then(setCalendar).catch(() => {})
    } catch (e) {
      setErr((e && e.message) || ('Не удалось отправить заявку. Попробуйте позвонить: ' + c['contacts.phone']))
    } finally {
      setSending(false)
    }
  }

  const phoneHref = 'tel:' + (c['contacts.phone'] || '').replace(/[^+\d]/g, '')

  return (
    <>
      <header className="header header--glass">
        <div className="container header__inner">
          <a href="#top" className="brand">
            <div className="brand__mark">А</div>
            <div>
              <div className="brand__name">Гостевой дом «АЛиНА»</div>
              <div className="brand__subline">Кучугуры · Азовское море</div>
            </div>
          </a>
          <nav className="nav">
            <a href="#about">О доме</a>
            <a href="#rooms">Номера</a>
            <a href="#gallery">Фото</a>
            <a href="#contacts">Контакты</a>
            <a className="btn btn--primary" href="#book">{c['hero.cta']}</a>
          </nav>
        </div>
      </header>

      <main id="top">
        <section className="photo-hero" style={{ backgroundImage: `linear-gradient(180deg, rgba(22,24,22,.22), rgba(22,24,22,.62)), url("${heroPhoto}")` }}>
          <div className="container photo-hero__grid">
            <div>
              <div className="hero__eyebrow hero__eyebrow--light">400 м до пляжа · 10 минут пешком</div>
              <h1 className="photo-hero__title">{c['hero.title']}</h1>
              <p className="photo-hero__lead">{c['hero.subtitle']}</p>
              <div className="hero__cta">
                <a className="btn btn--primary" href="#book">{c['hero.cta']}</a>
                <a className="btn btn--light" href={phoneHref}>{c['contacts.phone']}</a>
              </div>
              {!bookingsOpen && <div className="hero__closed">{closedMessage} <a href={phoneHref}>{c['contacts.phone']}</a></div>}
            </div>
            <form className="booking-panel" onSubmit={submit}>
              <h3>Быстрая заявка</h3>
              {bookingsOpen ? (
                <p>Уточним свободные даты, стоимость и подходящий номер.</p>
              ) : (
                <div className="form__error">{closedMessage}<br /><a href={phoneHref}>{c['contacts.phone']}</a></div>
              )}
              {ok && <div className="form__success">Спасибо! Заявка отправлена. Мы скоро свяжемся.</div>}
              {err && bookingsOpen && <div className="form__error">{err}</div>}
              {rangeBlocked && bookingsOpen && <div className="form__error">Дата уже забронирована, пожалуйста, выберите другую дату.</div>}
              <fieldset disabled={!bookingsOpen} style={{ border: 0, padding: 0, margin: 0 }}>
                <div className="form__row">
                  <div><label>Заезд</label><input type="date" value={form.date_from} onChange={e => { setForm({ ...form, date_from: e.target.value }); setErr('') }} min={calendar.today} /></div>
                  <div><label>Выезд</label><input type="date" value={form.date_to} onChange={e => { setForm({ ...form, date_to: e.target.value }); setErr('') }} min={form.date_from || calendar.today} /></div>
                </div>
                <label>Ваше имя *</label>
                <input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
                <label>Телефон *</label>
                <input required value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} placeholder="+7..." />
                <button className="btn btn--primary" disabled={sending || !bookingsOpen || rangeBlocked} type="submit">{sending ? 'Отправляем...' : 'Отправить'}</button>
              </fieldset>
            </form>
          </div>
        </section>

        <section id="about" className="section">
          <div className="container premium-grid">
            <div>
              <span className="section-kicker">О гостевом доме</span>
              <h2>{c['about.title']}</h2>
              <p>{c['about.text']}</p>
              <div className="facts-row">
                <div><b>400 м</b><span>до пляжа</span></div>
                <div><b>5</b><span>номеров</span></div>
                <div><b>10 мин</b><span>пешком к морю</span></div>
              </div>
            </div>
            <div className="split-photos">
              <img src={aboutPhoto1} alt="Гостевой дом Алина" />
              <img src={aboutPhoto2} alt="Двор гостевого дома" />
            </div>
          </div>
        </section>

        <section id="rooms" className="section section--warm">
          <div className="container">
            <div className="section-headline">
              <span className="section-kicker">Номера</span>
              <h2>{c['rooms.title']}</h2>
              <p>{c['rooms.text']}</p>
            </div>
            <div className="room-grid">
              {roomAlbums.map(album => (
                <article className="room-card" key={album.id}>
                  <button className="room-card__image" onClick={() => setActiveAlbum(album)} type="button">
                    <img src={album.cover} alt={album.title} />
                    <span>{album.photos.length} фото</span>
                  </button>
                  <div className="room-card__body">
                    <h3>{album.title}</h3>
                    <p>{album.description}</p>
                    <div className="chips">{(album.chips || ['душ/туалет', 'ТВ', 'кондиционер']).map(c => <span key={c}>{c}</span>)}</div>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section">
          <div className="container">
            <div className="section-headline">
              <span className="section-kicker">Удобства</span>
              <h2>{c['amenities.title']}</h2>
            </div>
            <div className="amenity-grid">
              {amenities.map(a => <span key={a} className="amenity-card">{a}</span>)}
            </div>
          </div>
        </section>

        <section id="gallery" className="section section--tight">
          <div className="container">
            <div className="section-headline">
              <span className="section-kicker">Галерея</span>
              <h2>{c['gallery.title']}</h2>
              <p>Фотографии из ваших папок: гостевой дом, двор, кухня, номера, пляж и летняя атмосфера.</p>
            </div>
            <div className="featured-albums">
              {featuredAlbums.map(group => (
                <button key={group.title} onClick={() => setActiveAlbum(group.albums[0])} type="button">
                  <img src={group.cover} alt={group.title} />
                  <span className="featured-albums__label">{group.label}</span>
                  <span className="featured-albums__title">{group.title}</span>
                  <small>{group.count} фото</small>
                </button>
              ))}
            </div>
            <div className="masonry-gallery">
              {galleryPhotos.map((src, i) => <button key={src} onClick={() => setActiveAlbum(albums.find(a => a.photos.includes(src)))} type="button"><img src={src} alt={`Фото гостевого дома ${i + 1}`} /></button>)}
            </div>
          </div>
        </section>

        <section id="contacts" className="section contacts-premium">
          <div className="container contacts-premium__grid">
            <div>
              <span className="section-kicker">Контакты</span>
              <h2>{c['contacts.title']}</h2>
              <p>{c['location.note']}</p>
              <div className="owner owner--premium">
                {ownerPhoto ? <img className="owner__avatar" src={ownerPhoto} alt={c['contacts.owner_name']} /> : <div className="owner__avatar">АЛ</div>}
                <div>
                  <div className="owner__name">{c['contacts.owner_name']}</div>
                  <div className="owner__role">{c['contacts.owner_role']}</div>
                  <a className="owner__phone" href={phoneHref}>{c['contacts.phone']}</a>
                </div>
              </div>
              <div className="hero__cta">
                <a className="btn btn--primary" href={phoneHref}>Позвонить</a>
                <a className="btn btn--ghost" href={c['contacts.vk']} target="_blank" rel="noreferrer">Группа VK</a>
              </div>
            </div>
            <div className="location-card" style={{ backgroundImage: `linear-gradient(180deg, rgba(22,24,22,.04), rgba(22,24,22,.38)), url("${singles.location || beach?.cover || heroPhoto}")` }}>
              <div><b>{c['location.title']}</b><span>{c['location.address']}</span></div>
            </div>
          </div>
        </section>

        <section id="book" className="section">
          <div className="container" style={{ maxWidth: 760 }}>
            <div className="section-headline">
              <span className="section-kicker">Бронирование</span>
              <h2>Оставить заявку</h2>
              {bookingsOpen ? (
                <p>Свяжемся в ближайшее время, расскажем про свободные даты и условия.</p>
              ) : (
                <div className="form__error">
                  {closedMessage}<br />
                  <a href={phoneHref}>{c['contacts.phone']}</a>
                </div>
              )}
            </div>
            <form className="form" onSubmit={submit}>
              {ok && <div className="form__success">Спасибо! Заявка отправлена. Мы скоро свяжемся.</div>}
              {err && bookingsOpen && <div className="form__error">{err}</div>}
              {rangeBlocked && bookingsOpen && <div className="form__error">Дата уже забронирована, пожалуйста, выберите другую дату.</div>}
              <fieldset disabled={!bookingsOpen} style={{ border: 0, padding: 0, margin: 0 }}>
                <div className="form__row">
                  <div><label>Ваше имя *</label><input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
                  <div><label>Телефон *</label><input required value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} placeholder="+7..." /></div>
                </div>
                <div className="form__row">
                  <div><label>Email</label><input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></div>
                  <div><label>Гостей</label><input type="number" min="1" max="20" value={form.guests} onChange={e => setForm({ ...form, guests: e.target.value })} /></div>
                </div>
                <div className="form__row">
                  <div><label>Заезд</label><input type="date" value={form.date_from} onChange={e => { setForm({ ...form, date_from: e.target.value }); setErr('') }} min={calendar.today} /></div>
                  <div><label>Выезд</label><input type="date" value={form.date_to} onChange={e => { setForm({ ...form, date_to: e.target.value }); setErr('') }} min={form.date_from || calendar.today} /></div>
                </div>
                <label>Комментарий</label>
                <textarea value={form.message} onChange={e => setForm({ ...form, message: e.target.value })} placeholder="Пожелания, вопросы..." />
                <div style={{ marginTop: 16, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                  <button className="btn btn--primary" disabled={sending || !bookingsOpen || rangeBlocked} type="submit">{sending ? 'Отправляем...' : 'Отправить заявку'}</button>
                  <span className="form__hint">Заявка уйдёт на email и в Telegram после настройки SMTP и бота.</span>
                </div>
              </fieldset>
            </form>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="container footer__row">
          <div>{c['footer.note']}</div>
          <div><a href={phoneHref}>{c['contacts.phone']}</a> · <a href={c['contacts.vk']} target="_blank" rel="noreferrer">VK</a></div>
        </div>
      </footer>

      {activeAlbum && (
        <div className="lightbox" onClick={() => setActiveAlbum(null)}>
          <div className="lightbox__panel" onClick={e => e.stopPropagation()}>
            <button className="lightbox__close" onClick={() => setActiveAlbum(null)} type="button">Закрыть</button>
            <h3>{activeAlbum.title}</h3>
            <p>{activeAlbum.description}</p>
            <div className="lightbox__grid">
              {activeAlbum.photos.map(src => <img key={src} src={src} alt={activeAlbum.title} />)}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
