import { useEffect, useMemo, useRef, useState } from 'react'
import AdminShell from '../components/AdminShell.jsx'
import { api } from '../api.js'

const TEXT_GROUPS = [
  { id: 'hero', title: 'Первый экран (Hero)', fields: [
    { key: 'hero.title', label: 'Заголовок', type: 'text' },
    { key: 'hero.subtitle', label: 'Подзаголовок', type: 'textarea' },
    { key: 'hero.cta', label: 'Текст кнопки', type: 'text' },
  ]},
  { id: 'about', title: 'О гостевом доме', fields: [
    { key: 'about.title', label: 'Заголовок', type: 'text' },
    { key: 'about.text', label: 'Текст', type: 'textarea' },
  ]},
  { id: 'rooms-text', title: 'Блок «Номера»', fields: [
    { key: 'rooms.title', label: 'Заголовок', type: 'text' },
    { key: 'rooms.text', label: 'Описание', type: 'textarea' },
  ]},
  { id: 'amenities', title: 'Удобства', fields: [
    { key: 'amenities.title', label: 'Заголовок', type: 'text' },
    { key: 'amenities.items', label: 'Список удобств (по одному в строке)', type: 'list' },
  ]},
  { id: 'gallery-text', title: 'Галерея', fields: [
    { key: 'gallery.title', label: 'Заголовок', type: 'text' },
  ]},
  { id: 'location', title: 'Расположение', fields: [
    { key: 'location.title', label: 'Заголовок', type: 'text' },
    { key: 'location.address', label: 'Адрес', type: 'text' },
    { key: 'location.note', label: 'Подпись', type: 'textarea' },
  ]},
  { id: 'contacts', title: 'Контакты', fields: [
    { key: 'contacts.title', label: 'Заголовок блока', type: 'text' },
    { key: 'contacts.owner_name', label: 'Имя руководителя', type: 'text' },
    { key: 'contacts.owner_role', label: 'Подпись/должность', type: 'text' },
    { key: 'contacts.phone', label: 'Телефон', type: 'text' },
    { key: 'contacts.vk', label: 'Группа VK', type: 'text' },
    { key: 'contacts.vk_personal', label: 'Личный профиль VK', type: 'text' },
  ]},
  { id: 'footer', title: 'Подвал', fields: [
    { key: 'footer.note', label: 'Текст подвала', type: 'text' },
  ]},
  { id: 'bookings', title: 'Режим бронирования', fields: [
    { key: 'bookings.closed_message', label: 'Сообщение при закрытом приёме заявок', type: 'textarea' },
  ]},
]

const SINGLE_IMAGES = [
  { key: 'hero', title: 'Фон первого экрана', hint: 'Большое фото на главном экране сайта.' },
  { key: 'about1', title: 'Фото «О доме» — левое', hint: 'Фото гостевого дома в блоке «О доме» (верхнее).' },
  { key: 'about2', title: 'Фото «О доме» — правое', hint: 'Фото двора в блоке «О доме» (нижнее).' },
  { key: 'owner', title: 'Аватар руководителя', hint: 'Квадратное фото в блоке контактов.' },
  { key: 'location', title: 'Фото в блоке локации', hint: 'Фон карточки «где мы находимся».' },
]

function safeParse(raw) {
  if (!raw) return {}
  const trimmed = String(raw).trim()
  if (!trimmed || trimmed === 'undefined' || trimmed === 'null') return {}
  try { const parsed = JSON.parse(trimmed); return (parsed && typeof parsed === 'object') ? parsed : {} } catch { return {} }
}

function parseSettings(raw, manifest) {
  const baseAlbums = manifest?.albums || []
  const s = safeParse(raw)
  const customAlbums = Array.isArray(s.customAlbums) ? s.customAlbums : []
  const allIds = [...baseAlbums.map(a => a.id), ...customAlbums.map(a => a.id)]
  const order = Array.isArray(s.albumOrder) && s.albumOrder.length
    ? s.albumOrder.filter(id => allIds.includes(id)).concat(allIds.filter(id => !s.albumOrder.includes(id)))
    : allIds
  return {
    albumOrder: order,
    albums: s.albums && typeof s.albums === 'object' ? s.albums : {},
    customAlbums,
    singleImages: s.singleImages && typeof s.singleImages === 'object' ? s.singleImages : {},
  }
}

function stringifySettings(s) { return JSON.stringify(s, null, 2) }

function moveItem(arr, from, to) {
  if (to < 0 || to >= arr.length) return arr
  const copy = [...arr]
  const [item] = copy.splice(from, 1)
  copy.splice(to, 0, item)
  return copy
}

function slugify(s) {
  const map = { а:'a',б:'b',в:'v',г:'g',д:'d',е:'e',ё:'e',ж:'zh',з:'z',и:'i',й:'y',к:'k',л:'l',м:'m',н:'n',о:'o',п:'p',р:'r',с:'s',т:'t',у:'u',ф:'f',х:'h',ц:'c',ч:'ch',ш:'sh',щ:'sch',ы:'y',э:'e',ю:'yu',я:'ya' }
  return String(s || 'room').toLowerCase().split('').map(ch => map[ch] || ch).join('').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'room'
}

function buildAlbum(album, cfg = {}) {
  const deleted = new Set(cfg.deletedPhotos || [])
  const base = (album.photos || []).concat(cfg.addedPhotos || []).filter(p => !deleted.has(p))
  const photos = cfg.photoOrder?.length
    ? cfg.photoOrder.filter(p => base.includes(p)).concat(base.filter(p => !cfg.photoOrder.includes(p)))
    : base
  return { ...album, photos, cover: cfg.cover || album.cover || photos[0], title: cfg.title || album.title, description: cfg.description || album.description }
}

export default function LandingEdit() {
  const [data, setData] = useState(null)
  const [manifest, setManifest] = useState({ albums: [] })
  const [section, setSection] = useState('hero')
  const [openAlbums, setOpenAlbums] = useState({})
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [flash, setFlash] = useState('')
  const iframeRef = useRef(null)
  const reloadTimer = useRef(null)

  useEffect(() => {
    Promise.all([
      api.getContent().catch(() => ({})),
      fetch('/media-manifest.json').then(r => r.json()).catch(() => ({ albums: [] })),
    ]).then(([content, mf]) => {
      setData(content || {})
      setManifest(mf || { albums: [] })
    }).catch(e => setErr(String(e.message || e)))
  }, [])

  const settings = useMemo(() => parseSettings(data?.['media.settings'], manifest), [data, manifest])
  const allAlbums = useMemo(() => [...(manifest.albums || []), ...settings.customAlbums], [manifest, settings.customAlbums])
  const albumsById = useMemo(() => Object.fromEntries(allAlbums.map(a => [a.id, a])), [allAlbums])
  const orderedAlbums = settings.albumOrder.map(id => albumsById[id]).filter(Boolean)
  const roomAlbums = orderedAlbums.filter(a => a.category === 'rooms')
  const nonRoomAlbums = orderedAlbums.filter(a => a.category !== 'rooms')

  function reloadPreviewSoon() {
    clearTimeout(reloadTimer.current)
    reloadTimer.current = setTimeout(() => {
      try { iframeRef.current?.contentWindow?.location.reload() } catch {}
    }, 350)
  }

  function showFlash(msg) {
    setFlash(msg)
    setTimeout(() => setFlash(''), 1800)
  }

  function setText(key, value) {
    setData(d => ({ ...(d || {}), [key]: value }))
    setDirty(true)
  }

  function commitSettings(next) {
    setData(d => ({ ...(d || {}), 'media.settings': stringifySettings(next) }))
    setDirty(true)
    reloadPreviewSoon()
  }

  async function persistSettings(next) {
    setBusy(true); setErr('')
    try {
      const merged = { ...(data || {}), 'media.settings': stringifySettings(next) }
      const items = Object.entries(merged).map(([key, value]) => ({ key, value: String(value ?? '') }))
      await api.updateContent(items)
      setData(merged)
      setDirty(false)
      showFlash('Сохранено')
      reloadPreviewSoon()
    } catch (e) {
      setErr(String(e.message || e))
    } finally { setBusy(false) }
  }

  async function saveAll() {
    if (!data) return
    setBusy(true); setErr('')
    try {
      const items = Object.entries(data).map(([key, value]) => ({ key, value: String(value ?? '') }))
      await api.updateContent(items)
      setDirty(false)
      showFlash('Все изменения сохранены')
      reloadPreviewSoon()
    } catch (e) { setErr(String(e.message || e)) } finally { setBusy(false) }
  }

  function patchAlbumLocal(id, patch) {
    return { ...settings, albums: { ...settings.albums, [id]: { ...(settings.albums[id] || {}), ...patch } } }
  }

  function setCover(id, photo) {
    const next = patchAlbumLocal(id, { cover: photo })
    commitSettings(next)
    persistSettings(next)
  }

  function moveAlbum(id, dir) {
    const idx = settings.albumOrder.indexOf(id)
    const next = { ...settings, albumOrder: moveItem(settings.albumOrder, idx, idx + dir) }
    commitSettings(next)
    persistSettings(next)
  }

  function toggleHidden(id) {
    const next = patchAlbumLocal(id, { hidden: !(settings.albums[id]?.hidden) })
    commitSettings(next)
    persistSettings(next)
  }

  function movePhoto(id, photo, dir) {
    const album = buildAlbum(albumsById[id], settings.albums[id])
    const idx = album.photos.indexOf(photo)
    const next = patchAlbumLocal(id, { photoOrder: moveItem(album.photos, idx, idx + dir) })
    commitSettings(next)
    persistSettings(next)
  }

  async function uploadAlbumPhoto(id, file) {
    if (!file) return
    setBusy(true); setErr('')
    try {
      const r = await api.uploadFile(file, id)
      const cfg = settings.albums[id] || {}
      const album = buildAlbum(albumsById[id], cfg)
      const addedPhotos = [...(cfg.addedPhotos || []), r.url]
      const photoOrder = [...album.photos, r.url]
      const cover = cfg.cover || album.cover || r.url
      const next = patchAlbumLocal(id, { addedPhotos, photoOrder, cover })
      commitSettings(next)
      await persistSettings(next)
      showFlash('Фото загружено')
    } catch (e) { setErr(String(e.message || e)) } finally { setBusy(false) }
  }

  async function removePhoto(id, photo) {
    if (!confirm('Удалить фото из альбома?')) return
    const cfg = settings.albums[id] || {}
    const album = buildAlbum(albumsById[id], cfg)
    const addedPhotos = (cfg.addedPhotos || []).filter(p => p !== photo)
    const deletedPhotos = photo.startsWith('/uploads/')
      ? (cfg.deletedPhotos || [])
      : [...(cfg.deletedPhotos || []), photo]
    const photoOrder = album.photos.filter(p => p !== photo)
    const cover = cfg.cover === photo ? photoOrder[0] : cfg.cover
    try { if (photo.startsWith('/uploads/')) await api.deleteUpload(photo) } catch {}
    const next = patchAlbumLocal(id, { addedPhotos, deletedPhotos, photoOrder, cover })
    commitSettings(next)
    persistSettings(next)
  }

  function addRoom() {
    const title = prompt('Название номера', 'Новый номер')
    if (!title) return
    const id = `custom-room-${slugify(title)}-${Date.now().toString(36)}`
    const album = { id, title, category: 'rooms', description: 'Номер с удобствами.', cover: '', photos: [], custom: true }
    const next = {
      ...settings,
      customAlbums: [...settings.customAlbums, album],
      albumOrder: [...settings.albumOrder, id],
    }
    commitSettings(next)
    persistSettings(next)
  }

  function updateRoom(id, patch) {
    const next = {
      ...settings,
      customAlbums: settings.customAlbums.map(a => a.id === id ? { ...a, ...patch } : a),
    }
    commitSettings(next)
  }

  function updateAlbumChips(id, chipsStr) {
    const chips = chipsStr.split(';').map(s => s.trim()).filter(Boolean)
    const next = patchAlbumLocal(id, { chips })
    commitSettings(next)
    persistSettings(next)
  }

  function updateAlbumField(id, field, value) {
    const next = patchAlbumLocal(id, { [field]: value })
    commitSettings(next)
    persistSettings(next)
  }

  function deleteRoom(id) {
    if (!confirm('Удалить номер? Загруженные фото также будут отвязаны от него.')) return
    const next = {
      ...settings,
      customAlbums: settings.customAlbums.filter(a => a.id !== id),
      albumOrder: settings.albumOrder.filter(x => x !== id),
      albums: Object.fromEntries(Object.entries(settings.albums).filter(([key]) => key !== id)),
    }
    commitSettings(next)
    persistSettings(next)
  }

  async function uploadSingle(key, file) {
    if (!file) return
    setBusy(true); setErr('')
    try {
      const r = await api.uploadFile(file, `single-${key}`)
      const next = { ...settings, singleImages: { ...settings.singleImages, [key]: r.url } }
      commitSettings(next)
      await persistSettings(next)
      showFlash('Изображение заменено')
    } catch (e) { setErr(String(e.message || e)) } finally { setBusy(false) }
  }

  function toggleAlbumOpen(id) {
    setOpenAlbums(o => ({ ...o, [id]: !o[id] }))
  }

  function clearSingle(key) {
    const next = { ...settings, singleImages: { ...settings.singleImages, [key]: '' } }
    commitSettings(next)
    persistSettings(next)
  }

  const SECTIONS = [
    { id: 'hero', title: 'Hero', kind: 'text' },
    { id: 'about', title: 'О доме', kind: 'text' },
    { id: 'rooms-text', title: 'Блок «Номера»', kind: 'text' },
    { id: 'amenities', title: 'Удобства', kind: 'text' },
    { id: 'gallery-text', title: 'Галерея (тексты)', kind: 'text' },
    { id: 'location', title: 'Расположение', kind: 'text' },
    { id: 'contacts', title: 'Контакты', kind: 'text' },
    { id: 'footer', title: 'Подвал', kind: 'text' },
    { id: 'bookings', title: 'Режим бронирования', kind: 'text' },
    { id: 'rooms-media', title: 'Номера и фото', kind: 'rooms' },
    { id: 'media', title: 'Галерея и альбомы', kind: 'media' },
    { id: 'single', title: 'Одиночные фото', kind: 'single' },
  ]
  const active = SECTIONS.find(s => s.id === section) || SECTIONS[0]
  const textGroup = TEXT_GROUPS.find(g => g.id === active.id)

  return (
    <AdminShell>
      <div className="le-shell">
        <header className="le-topbar">
          <div>
            <h2 style={{ margin: 0 }}>Landing-edit</h2>
            <div className="le-status">{dirty ? '● Есть несохранённые правки' : 'Все правки сохранены'}</div>
          </div>
          <div className="le-actions">
            {flash && <span className="le-flash">{flash}</span>}
            <a className="btn btn--ghost" href="/" target="_blank" rel="noreferrer">Открыть сайт</a>
            <button className="btn btn--primary" onClick={saveAll} disabled={busy || !data}>{busy ? 'Сохраняем…' : 'Сохранить всё'}</button>
          </div>
        </header>

        {err && <div className="form__error">{err}</div>}

        <div className="le-grid">
          <nav className="le-nav">
            <div className="le-nav__group">Тексты</div>
            {SECTIONS.filter(s => s.kind === 'text').map(s => (
              <button key={s.id} className={'le-nav__item ' + (section === s.id ? 'active' : '')} onClick={() => setSection(s.id)} type="button">{s.title}</button>
            ))}
            <div className="le-nav__group">Фото и номера</div>
            {SECTIONS.filter(s => s.kind !== 'text').map(s => (
              <button key={s.id} className={'le-nav__item ' + (section === s.id ? 'active' : '')} onClick={() => setSection(s.id)} type="button">{s.title}</button>
            ))}
          </nav>

          <div className="le-pane">
            {!data && <div className="form__hint">Загружаем…</div>}

            {data && active.kind === 'text' && textGroup && (
              <div className="le-card">
                <div className="le-card__title">{textGroup.title}</div>
                {textGroup.fields.map(f => (
                  <div className="le-field" key={f.key}>
                    <label>{f.label}</label>
                    {f.type === 'textarea' && <textarea value={data[f.key] || ''} onChange={e => setText(f.key, e.target.value)} />}
                    {f.type === 'list' && (
                      <textarea
                        value={(data[f.key] || '').split(';').map(s => s.trim()).filter(Boolean).join('\n')}
                        onChange={e => setText(f.key, e.target.value.split('\n').map(s => s.trim()).filter(Boolean).join(';'))}
                      />
                    )}
                    {f.type === 'text' && <input value={data[f.key] || ''} onChange={e => setText(f.key, e.target.value)} />}
                  </div>
                ))}
                <div className="le-card__hint">Изменения применятся после нажатия «Сохранить всё» в верхней панели.</div>
              </div>
            )}

            {data && active.kind === 'rooms' && (
              <div>
                <div className="le-bar">
                  <button className="btn btn--primary" onClick={addRoom} type="button">+ Добавить номер</button>
                </div>
                {roomAlbums.length === 0 && <div className="le-card">Пока нет номеров. Нажмите «Добавить номер».</div>}
                {roomAlbums.map(album => {
                  const custom = settings.customAlbums.find(a => a.id === album.id)
                  const built = buildAlbum(album, settings.albums[album.id])
                  const open = !!openAlbums[album.id]
                  return (
                    <section className={'le-card le-accordion' + (open ? ' is-open' : '')} key={album.id}>
                      <button className="le-accordion__head" onClick={() => toggleAlbumOpen(album.id)} type="button">
                        <div>
                          <div className="le-card__title">{built.title || 'Без названия'}</div>
                          <div className="le-card__hint">{built.photos.length} фото · {open ? 'свернуть' : 'нажмите чтобы открыть'}</div>
                        </div>
                        <span className="le-accordion__chev">{open ? '▲' : '▼'}</span>
                      </button>
                      {open && (
                        <div className="le-accordion__body">
                          <div className="le-card__actions" style={{ marginBottom: 14 }}>
                            <label className="btn btn--primary">Загрузить фото<input className="le-hidden" type="file" accept="image/*" onChange={e => { uploadAlbumPhoto(album.id, e.target.files?.[0]); e.target.value = '' }} /></label>
                            {custom && <button className="btn btn--ghost" onClick={() => deleteRoom(album.id)} type="button">Удалить номер</button>}
                          </div>
                          <div className="le-grid-2">
                            <div className="le-field"><label>Название</label><input value={built.title} onChange={e => updateAlbumField(album.id, 'title', e.target.value)} /></div>
                            <div className="le-field"><label>Описание</label><textarea value={built.description} onChange={e => updateAlbumField(album.id, 'description', e.target.value)} /></div>
                          </div>
                          <div className="le-field"><label>Удобства (через ;)</label><input value={(built.chips || ['душ/туалет', 'ТВ', 'кондиционер']).join('; ')} onChange={e => updateAlbumChips(album.id, e.target.value)} /></div>
                          <PhotoGrid album={built} onCover={setCover} onMove={movePhoto} onRemove={removePhoto} />
                        </div>
                      )}
                    </section>
                  )
                })}
              </div>
            )}

            {data && active.kind === 'media' && (
              <div>
                <div className="le-card__hint" style={{ marginBottom: 12 }}>Нажмите на альбом, чтобы развернуть его и работать с фото.</div>
                {nonRoomAlbums.map((album, i) => {
                  const built = buildAlbum(album, settings.albums[album.id])
                  const cfg = settings.albums[album.id] || {}
                  const open = !!openAlbums[album.id]
                  return (
                    <section className={'le-card le-accordion' + (open ? ' is-open' : '')} key={album.id}>
                      <button className="le-accordion__head" onClick={() => toggleAlbumOpen(album.id)} type="button">
                        <div>
                          <div className="le-card__title">{built.title}</div>
                          <div className="le-card__hint">{built.photos.length} фото{cfg.hidden ? ' · скрыт' : ''} · {open ? 'свернуть' : 'нажмите чтобы открыть'}</div>
                        </div>
                        <span className="le-accordion__chev">{open ? '▲' : '▼'}</span>
                      </button>
                      {open && (
                        <div className="le-accordion__body">
                          <div className="le-card__actions" style={{ marginBottom: 14 }}>
                            <button className="btn btn--ghost" onClick={() => moveAlbum(album.id, -1)} disabled={i === 0} type="button">↑ выше</button>
                            <button className="btn btn--ghost" onClick={() => moveAlbum(album.id, 1)} disabled={i === nonRoomAlbums.length - 1} type="button">↓ ниже</button>
                            <button className="btn btn--ghost" onClick={() => toggleHidden(album.id)} type="button">{cfg.hidden ? 'Показать' : 'Скрыть'}</button>
                            <label className="btn btn--primary">Загрузить фото<input className="le-hidden" type="file" accept="image/*" onChange={e => { uploadAlbumPhoto(album.id, e.target.files?.[0]); e.target.value = '' }} /></label>
                          </div>
                          <PhotoGrid album={built} onCover={setCover} onMove={movePhoto} onRemove={removePhoto} />
                        </div>
                      )}
                    </section>
                  )
                })}
              </div>
            )}

            {data && active.kind === 'single' && (
              <div>
                <div className="le-card__hint" style={{ marginBottom: 12 }}>Эти изображения используются в одиночных слотах сайта. После загрузки сразу применяются.</div>
                {SINGLE_IMAGES.map(s => {
                  const value = (settings.singleImages && settings.singleImages[s.key]) || ''
                  return (
                    <section className="le-card" key={s.key}>
                      <div className="le-card__head">
                        <div>
                          <div className="le-card__title">{s.title}</div>
                          <div className="le-card__hint">{s.hint}</div>
                        </div>
                        <div className="le-card__actions">
                          <label className="btn btn--primary">{value ? 'Заменить фото' : 'Загрузить фото'}<input className="le-hidden" type="file" accept="image/*" onChange={e => { uploadSingle(s.key, e.target.files?.[0]); e.target.value = '' }} /></label>
                          {value && <button className="btn btn--ghost" onClick={() => clearSingle(s.key)} type="button">Сбросить</button>}
                        </div>
                      </div>
                      {value ? <img className="le-single-preview" src={value} alt={s.title} /> : <div className="le-card__hint">Сейчас используется фото по умолчанию.</div>}
                    </section>
                  )
                })}
              </div>
            )}
          </div>

          <aside className="le-preview">
            <div className="le-preview__bar">
              <span>Предпросмотр сайта</span>
              <div style={{ display: 'flex', gap: 6 }}>
                <a className="btn btn--ghost le-preview__reload" href="/" target="_blank" rel="noreferrer">В большом окне</a>
                <button className="btn btn--ghost le-preview__reload" onClick={() => iframeRef.current?.contentWindow?.location.reload()} type="button">Обновить</button>
              </div>
            </div>
            <div className="le-preview__viewport">
              <iframe ref={iframeRef} src="/" title="preview" className="le-preview__frame" />
            </div>
          </aside>
        </div>
      </div>
    </AdminShell>
  )
}

function PhotoGrid({ album, onCover, onMove, onRemove }) {
  if (!album.photos.length) return <div className="le-card__hint" style={{ marginTop: 8 }}>В этом альбоме пока нет фото. Загрузите первое.</div>
  return (
    <div className="le-photos">
      {album.photos.map((photo, i) => (
        <figure key={photo} className={'le-photo ' + (album.cover === photo ? 'is-cover' : '')}>
          <img src={photo} alt={album.title} onClick={() => onCover(album.id, photo)} />
          <figcaption>
            <button type="button" title="Сделать главной" onClick={() => onCover(album.id, photo)}>{album.cover === photo ? '★ главная' : 'Сделать главной'}</button>
            <button type="button" onClick={() => onMove(album.id, photo, -1)} disabled={i === 0}>↑</button>
            <button type="button" onClick={() => onMove(album.id, photo, 1)} disabled={i === album.photos.length - 1}>↓</button>
            <button type="button" className="danger" onClick={() => onRemove(album.id, photo)}>Удалить</button>
          </figcaption>
        </figure>
      ))}
    </div>
  )
}
