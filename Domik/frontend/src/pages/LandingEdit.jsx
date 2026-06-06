import { useEffect, useMemo, useState } from 'react'
import AdminShell from '../components/AdminShell.jsx'
import { api } from '../api.js'

const ORDER = [
  'hero.title', 'hero.subtitle', 'hero.cta',
  'about.title', 'about.text',
  'rooms.title', 'rooms.text',
  'amenities.title', 'amenities.items',
  'gallery.title',
  'location.title', 'location.address', 'location.note',
  'contacts.title', 'contacts.owner_name', 'contacts.owner_role',
  'contacts.phone', 'contacts.vk', 'contacts.vk_personal', 'contacts.owner_photo',
  'media.settings',
  'footer.note',
]

const HINTS = {
  'amenities.items': 'Список через точку с запятой: Wi-Fi;Парковка;Кондиционер',
  'contacts.phone': 'Формат: +7 918 212-96-01',
  'contacts.vk': 'Ссылка на группу VK',
  'contacts.owner_photo': 'Путь к фото руководителя. Для замены лучше используйте вкладку «Одиночные фото».',
  'media.settings': 'JSON с порядком альбомов, порядком фото, номерами и одиночными фото. Лучше редактировать через вкладки ниже.',
}

function parseSettings(raw, manifest) {
  const baseAlbums = manifest?.albums || []
  let settings = {}
  try { settings = raw ? JSON.parse(raw) : {} } catch { settings = {} }
  const customAlbums = settings.customAlbums || []
  const allIds = [...baseAlbums.map(a => a.id), ...customAlbums.map(a => a.id)]
  return {
    albumOrder: settings.albumOrder?.length ? settings.albumOrder.filter(id => allIds.includes(id)).concat(allIds.filter(id => !settings.albumOrder.includes(id))) : allIds,
    albums: settings.albums || {},
    customAlbums,
    singleImages: settings.singleImages || {},
  }
}

function stringifySettings(settings) {
  return JSON.stringify(settings, null, 2)
}

function moveItem(arr, from, to) {
  const copy = [...arr]
  if (to < 0 || to >= copy.length) return copy
  const [item] = copy.splice(from, 1)
  copy.splice(to, 0, item)
  return copy
}

function slugify(s) {
  const map = { а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ё: 'e', ж: 'zh', з: 'z', и: 'i', й: 'y', к: 'k', л: 'l', м: 'm', н: 'n', о: 'o', п: 'p', р: 'r', с: 's', т: 't', у: 'u', ф: 'f', х: 'h', ц: 'c', ч: 'ch', ш: 'sh', щ: 'sch', ы: 'y', э: 'e', ю: 'yu', я: 'ya' }
  return String(s || 'room').toLowerCase().split('').map(ch => map[ch] || ch).join('').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'room'
}

function buildAlbum(album, cfg = {}) {
  const deleted = new Set(cfg.deletedPhotos || [])
  const basePhotos = (album.photos || []).concat(cfg.addedPhotos || []).filter(p => !deleted.has(p))
  const photos = cfg.photoOrder?.length
    ? cfg.photoOrder.filter(p => basePhotos.includes(p)).concat(basePhotos.filter(p => !cfg.photoOrder.includes(p)))
    : basePhotos
  return { ...album, photos, cover: cfg.cover || album.cover || photos[0] }
}

export default function LandingEdit() {
  const [data, setData] = useState({})
  const [manifest, setManifest] = useState({ albums: [] })
  const [active, setActive] = useState(ORDER[0])
  const [mode, setMode] = useState('texts')
  const [saved, setSaved] = useState(false)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.getContent().then(setData).catch(e => setErr(String(e.message || e)))
    fetch('/media-manifest.json').then(r => r.json()).then(setManifest).catch(e => setErr(String(e.message || e)))
  }, [])

  function set(k, v) { setData(d => ({ ...d, [k]: v })); setSaved(false) }

  async function save(customData = data) {
    setBusy(true); setErr(''); setSaved(false)
    try {
      const items = Object.entries(customData).map(([key, value]) => ({ key, value: String(value ?? '') }))
      await api.updateContent(items)
      setSaved(true)
    } catch (e) {
      setErr(String(e.message || e))
    } finally { setBusy(false) }
  }

  const settings = useMemo(() => parseSettings(data['media.settings'], manifest), [data, manifest])
  const allAlbums = useMemo(() => [...(manifest.albums || []), ...settings.customAlbums], [manifest, settings.customAlbums])
  const albumsById = useMemo(() => Object.fromEntries(allAlbums.map(a => [a.id, a])), [allAlbums])
  const keys = Array.from(new Set([...ORDER, ...Object.keys(data)]))

  function updateSettings(nextSettings, autosave = false) {
    const nextData = { ...data, 'media.settings': stringifySettings(nextSettings) }
    setData(nextData)
    setSaved(false)
    if (autosave) save(nextData)
  }

  function patchAlbum(id, patch) {
    updateSettings({ ...settings, albums: { ...settings.albums, [id]: { ...(settings.albums[id] || {}), ...patch } } })
  }

  function moveAlbum(id, dir) {
    const idx = settings.albumOrder.indexOf(id)
    updateSettings({ ...settings, albumOrder: moveItem(settings.albumOrder, idx, idx + dir) })
  }

  function toggleHidden(id) {
    patchAlbum(id, { hidden: !(settings.albums[id]?.hidden) })
  }

  function setCover(id, photo) {
    patchAlbum(id, { cover: photo })
  }

  function movePhoto(id, photo, dir) {
    const album = buildAlbum(albumsById[id], settings.albums[id])
    const idx = album.photos.indexOf(photo)
    patchAlbum(id, { photoOrder: moveItem(album.photos, idx, idx + dir) })
  }

  async function uploadAlbumPhoto(id, file) {
    if (!file) return
    setBusy(true); setErr('')
    try {
      const r = await api.uploadFile(file, id)
      const cfg = settings.albums[id] || {}
      const addedPhotos = [...(cfg.addedPhotos || []), r.url]
      const photoOrder = [...(cfg.photoOrder || buildAlbum(albumsById[id], cfg).photos), r.url]
      patchAlbum(id, { addedPhotos, photoOrder, cover: cfg.cover || r.url })
    } catch (e) { setErr(String(e.message || e)) } finally { setBusy(false) }
  }

  async function removePhoto(id, photo) {
    if (!confirm('Удалить фото из альбома?')) return
    const cfg = settings.albums[id] || {}
    const addedPhotos = (cfg.addedPhotos || []).filter(p => p !== photo)
    const deletedPhotos = photo.startsWith('/uploads/') ? (cfg.deletedPhotos || []) : [...(cfg.deletedPhotos || []), photo]
    const photoOrder = buildAlbum(albumsById[id], cfg).photos.filter(p => p !== photo)
    const cover = cfg.cover === photo ? photoOrder[0] : cfg.cover
    try { if (photo.startsWith('/uploads/')) await api.deleteUpload(photo) } catch {}
    patchAlbum(id, { addedPhotos, deletedPhotos, photoOrder, cover })
  }

  function addRoom() {
    const title = prompt('Название номера', 'Новый номер')
    if (!title) return
    const id = `custom-room-${slugify(title)}-${Date.now().toString(36)}`
    const album = { id, title, category: 'rooms', description: 'Номер с удобствами.', cover: '', photos: [], custom: true }
    updateSettings({ ...settings, customAlbums: [...settings.customAlbums, album], albumOrder: [...settings.albumOrder, id] })
  }

  function updateRoom(id, patch) {
    updateSettings({ ...settings, customAlbums: settings.customAlbums.map(a => a.id === id ? { ...a, ...patch } : a) })
  }

  function deleteRoom(id) {
    if (!confirm('Удалить номер? Фото, загруженные в этот номер, также будут убраны из настроек.')) return
    updateSettings({
      ...settings,
      customAlbums: settings.customAlbums.filter(a => a.id !== id),
      albumOrder: settings.albumOrder.filter(x => x !== id),
      albums: Object.fromEntries(Object.entries(settings.albums).filter(([key]) => key !== id)),
    })
  }

  async function uploadSingle(key, file) {
    if (!file) return
    setBusy(true); setErr('')
    try {
      const r = await api.uploadFile(file, `single-${key}`)
      updateSettings({ ...settings, singleImages: { ...settings.singleImages, [key]: r.url } })
    } catch (e) { setErr(String(e.message || e)) } finally { setBusy(false) }
  }

  function clearSingle(key) {
    updateSettings({ ...settings, singleImages: { ...settings.singleImages, [key]: '' } })
  }

  const orderedAlbums = settings.albumOrder.map(id => albumsById[id]).filter(Boolean)
  const roomAlbums = orderedAlbums.filter(a => a.category === 'rooms')

  return (
    <AdminShell>
      <h2>Landing-edit</h2>
      <p className="form__hint">Редактируйте тексты, номера, альбомы, фото и одиночные изображения.</p>

      {err && <div className="form__error">{err}</div>}
      {saved && <div className="form__success">Сохранено</div>}

      <div className="editor-tabs">
        <button className={mode === 'texts' ? 'active' : ''} onClick={() => setMode('texts')} type="button">Тексты</button>
        <button className={mode === 'rooms' ? 'active' : ''} onClick={() => setMode('rooms')} type="button">Номера</button>
        <button className={mode === 'media' ? 'active' : ''} onClick={() => setMode('media')} type="button">Фото и альбомы</button>
        <button className={mode === 'single' ? 'active' : ''} onClick={() => setMode('single')} type="button">Одиночные фото</button>
      </div>

      {mode === 'texts' && (
        <div className="editor__grid">
          <div className="editor__list">
            {keys.map(k => <button key={k} className={active === k ? 'active' : ''} onClick={() => setActive(k)}>{k}</button>)}
          </div>
          <div className="editor__pane">
            <label style={{ fontSize: 13, color: '#777' }}>Ключ</label>
            <div style={{ fontWeight: 600, marginBottom: 10 }}>{active}</div>
            {HINTS[active] && <p className="form__hint">{HINTS[active]}</p>}
            <textarea value={data[active] || ''} onChange={e => set(active, e.target.value)} />
            <div className="editor__bar">
              <button className="btn btn--primary" disabled={busy} onClick={() => save()}>{busy ? 'Сохраняем...' : 'Сохранить'}</button>
              <a className="btn btn--ghost" href="/" target="_blank" rel="noreferrer">Открыть сайт</a>
            </div>
          </div>
        </div>
      )}

      {mode === 'rooms' && (
        <div className="media-editor">
          <div className="editor__bar"><button className="btn btn--primary" onClick={addRoom} type="button">Добавить номер</button></div>
          {roomAlbums.map(album => {
            const custom = settings.customAlbums.find(a => a.id === album.id)
            const built = buildAlbum(album, settings.albums[album.id])
            return (
              <section className="media-album" key={album.id}>
                <div className="media-album__top">
                  <div>
                    <h3>{built.title}</h3>
                    <p className="form__hint">{built.photos.length} фото · id: {album.id}</p>
                  </div>
                  <div className="media-actions">
                    <label className="upload-btn">Загрузить фото<input type="file" accept="image/*" onChange={e => uploadAlbumPhoto(album.id, e.target.files?.[0])} /></label>
                    {custom && <button onClick={() => deleteRoom(album.id)} type="button">Удалить номер</button>}
                  </div>
                </div>
                {custom && <div className="room-edit-fields">
                  <label>Название<input value={custom.title} onChange={e => updateRoom(album.id, { title: e.target.value })} /></label>
                  <label>Описание<textarea value={custom.description} onChange={e => updateRoom(album.id, { description: e.target.value })} /></label>
                </div>}
                <PhotoGrid album={built} onCover={setCover} onMove={movePhoto} onRemove={removePhoto} />
              </section>
            )
          })}
          <div className="editor__bar"><button className="btn btn--primary" disabled={busy} onClick={() => save()}>{busy ? 'Сохраняем...' : 'Сохранить номера'}</button></div>
        </div>
      )}

      {mode === 'media' && (
        <div className="media-editor">
          <div className="form__hint">Главное фото отмечено рамкой. Можно загружать/удалять фото и менять порядок альбомов.</div>
          {orderedAlbums.map((album, albumIndex) => {
            const built = buildAlbum(album, settings.albums[album.id])
            const cfg = settings.albums[album.id] || {}
            return (
              <section className="media-album" key={album.id}>
                <div className="media-album__top">
                  <div><h3>{built.title}</h3><p className="form__hint">{built.description} · {built.photos.length} фото · id: {album.id}</p></div>
                  <div className="media-actions">
                    <button onClick={() => moveAlbum(album.id, -1)} disabled={albumIndex === 0} type="button">Альбом ↑</button>
                    <button onClick={() => moveAlbum(album.id, 1)} disabled={albumIndex === orderedAlbums.length - 1} type="button">Альбом ↓</button>
                    <button onClick={() => toggleHidden(album.id)} type="button">{cfg.hidden ? 'Показать' : 'Скрыть'}</button>
                    <label className="upload-btn">Загрузить фото<input type="file" accept="image/*" onChange={e => uploadAlbumPhoto(album.id, e.target.files?.[0])} /></label>
                  </div>
                </div>
                <PhotoGrid album={built} onCover={setCover} onMove={movePhoto} onRemove={removePhoto} />
              </section>
            )
          })}
          <div className="editor__bar"><button className="btn btn--primary" disabled={busy} onClick={() => save()}>{busy ? 'Сохраняем...' : 'Сохранить фото'}</button></div>
        </div>
      )}

      {mode === 'single' && (
        <div className="media-editor">
          <SingleImage title="Фон первого экрана" name="hero" value={settings.singleImages.hero} onUpload={uploadSingle} onClear={clearSingle} />
          <SingleImage title="Аватар руководителя" name="owner" value={settings.singleImages.owner} onUpload={uploadSingle} onClear={clearSingle} />
          <SingleImage title="Фото в блоке локации" name="location" value={settings.singleImages.location} onUpload={uploadSingle} onClear={clearSingle} />
          <div className="editor__bar"><button className="btn btn--primary" disabled={busy} onClick={() => save()}>{busy ? 'Сохраняем...' : 'Сохранить одиночные фото'}</button></div>
        </div>
      )}
    </AdminShell>
  )
}

function PhotoGrid({ album, onCover, onMove, onRemove }) {
  return <div className="media-photos">
    {album.photos.map((photo, photoIndex) => (
      <div key={photo}>
        <button className={'media-photo ' + (album.cover === photo ? 'cover' : '')} onClick={() => onCover(album.id, photo)} type="button">
          <img src={photo} alt={album.title} />
          <span>{album.cover === photo ? 'главная' : photoIndex + 1}</span>
        </button>
        <div className="media-actions" style={{ marginTop: 6 }}>
          <button onClick={() => onMove(album.id, photo, -1)} disabled={photoIndex === 0} type="button">↑</button>
          <button onClick={() => onMove(album.id, photo, 1)} disabled={photoIndex === album.photos.length - 1} type="button">↓</button>
          <button onClick={() => onRemove(album.id, photo)} type="button">Удалить</button>
        </div>
      </div>
    ))}
  </div>
}

function SingleImage({ title, name, value, onUpload, onClear }) {
  return <section className="media-album">
    <div className="media-album__top">
      <div><h3>{title}</h3><p className="form__hint">Ключ: {name}</p></div>
      <div className="media-actions">
        <label className="upload-btn">Заменить фото<input type="file" accept="image/*" onChange={e => onUpload(name, e.target.files?.[0])} /></label>
        {value && <button onClick={() => onClear(name)} type="button">Сбросить</button>}
      </div>
    </div>
    {value ? <img className="single-preview" src={value} alt={title} /> : <div className="form__hint">Используется фото по умолчанию.</div>}
  </section>
}
