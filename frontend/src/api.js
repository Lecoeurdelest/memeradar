const API = import.meta.env.VITE_API || 'http://localhost:8000'

export const LANGUAGES = {
  en: '🇺🇸 English',
  es: '🇪🇸 Español',
  fr: '🇫🇷 Français',
  ja: '🇯🇵 日本語',
  pt: '🇧🇷 Português',
  vi: '🇻🇳 Tiếng Việt',
}

export const UPLOAD_STRINGS = {
  en: {
    headerExact: 'This image is already in the index',
    headerLikely: 'Looks like an existing meme — did you mean one of these?',
    headerAsk: 'Did you mean one of these memes?',
    youUploaded: 'You uploaded',
    bestScore: 'best score',
    pickMatch: 'This is the one',
    noMatches: 'No similar memes found — this looks new.',
    close: 'Close',
    addAsNew: "No, this is a new meme — add it to the index",
    pickImage: 'Please choose an image file.',
    uploadFailed: 'Upload failed',
    ingestFailed: 'Ingest failed',
    addedOk: 'Meme added to the index.',
  },
  es: {
    headerExact: 'Esta imagen ya está en el índice',
    headerLikely: 'Se parece a un meme existente — ¿te refieres a uno de estos?',
    headerAsk: '¿Te refieres a uno de estos memes?',
    youUploaded: 'Has subido',
    bestScore: 'mejor puntuación',
    pickMatch: 'Es este',
    noMatches: 'No se encontraron memes similares — parece nuevo.',
    close: 'Cerrar',
    addAsNew: 'No, es un meme nuevo — añadirlo al índice',
    pickImage: 'Por favor elige un archivo de imagen.',
    uploadFailed: 'Error al subir',
    ingestFailed: 'Error al indexar',
    addedOk: 'Meme añadido al índice.',
  },
  fr: {
    headerExact: "Cette image est déjà dans l'index",
    headerLikely: "Ressemble à un mème existant — vouliez-vous dire l'un de ceux-ci ?",
    headerAsk: "Vouliez-vous dire l'un de ces mèmes ?",
    youUploaded: 'Vous avez téléversé',
    bestScore: 'meilleur score',
    pickMatch: "C'est celui-ci",
    noMatches: 'Aucun mème similaire trouvé — il semble nouveau.',
    close: 'Fermer',
    addAsNew: "Non, c'est un nouveau mème — l'ajouter à l'index",
    pickImage: "Veuillez choisir un fichier image.",
    uploadFailed: 'Échec du téléversement',
    ingestFailed: "Échec de l'indexation",
    addedOk: "Mème ajouté à l'index.",
  },
  ja: {
    headerExact: 'この画像はすでにインデックスに存在します',
    headerLikely: '既存のミームと似ています — このいずれかのことですか?',
    headerAsk: 'このミームのいずれかのことですか?',
    youUploaded: 'アップロードした画像',
    bestScore: '最高スコア',
    pickMatch: 'これです',
    noMatches: '類似のミームは見つかりませんでした — 新しいようです。',
    close: '閉じる',
    addAsNew: 'いいえ、新しいミームです — インデックスに追加',
    pickImage: '画像ファイルを選んでください。',
    uploadFailed: 'アップロードに失敗しました',
    ingestFailed: 'インデックス登録に失敗しました',
    addedOk: 'ミームをインデックスに追加しました。',
  },
  pt: {
    headerExact: 'Esta imagem já está no índice',
    headerLikely: 'Parece um meme existente — você quis dizer um destes?',
    headerAsk: 'Você quis dizer um destes memes?',
    youUploaded: 'Você enviou',
    bestScore: 'melhor pontuação',
    pickMatch: 'É este',
    noMatches: 'Nenhum meme similar encontrado — parece novo.',
    close: 'Fechar',
    addAsNew: 'Não, é um meme novo — adicione ao índice',
    pickImage: 'Por favor escolha um arquivo de imagem.',
    uploadFailed: 'Falha no envio',
    ingestFailed: 'Falha ao indexar',
    addedOk: 'Meme adicionado ao índice.',
  },
  vi: {
    headerExact: 'Ảnh này đã có trong hệ thống',
    headerLikely: 'Trông giống meme có sẵn — có phải ý bạn là một trong những meme này không?',
    headerAsk: 'Có phải ý bạn là một trong những meme này không?',
    youUploaded: 'Bạn vừa upload',
    bestScore: 'best score',
    pickMatch: 'Đây là ý tôi',
    noMatches: 'Không tìm thấy meme tương tự — có vẻ đây là meme mới.',
    close: 'Đóng',
    addAsNew: 'Không, đây là meme mới — thêm vào hệ thống',
    pickImage: 'Vui lòng chọn một file ảnh.',
    uploadFailed: 'Upload thất bại',
    ingestFailed: 'Thêm vào hệ thống thất bại',
    addedOk: 'Đã thêm meme vào hệ thống.',
  },
}

export function resolveImageUrl(url) {
  if (!url) return ''
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  if (url.startsWith('/')) return `${API}${url}`
  return url
}

export async function searchMemes({ q, k = 24, visualWeight = 0.35, ironyWeight = 0.65, template = null, lang = 'en' }) {
  const params = new URLSearchParams({
    q,
    k: String(k),
    visual_weight: String(visualWeight),
    irony_weight: String(ironyWeight),
    lang,
  })
  if (template) params.set('template', template)

  const res = await fetch(`${API}/search?${params}`)
  if (!res.ok) throw new Error(`search failed: ${res.status}`)
  return res.json()
}

export async function uploadCheck(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API}/upload/check`, { method: 'POST', body: form })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || `upload check failed: ${res.status}`)
  }
  return res.json()
}

export async function uploadIngest({ imageSha256, title }) {
  const res = await fetch(`${API}/upload/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_sha256: imageSha256, title: title || null }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || `upload ingest failed: ${res.status}`)
  }
  return res.json()
}

export async function randomMemes({ k = 24, lang = 'en' } = {}) {
  const params = new URLSearchParams({ k: String(k), lang })
  const res = await fetch(`${API}/random?${params}`)
  if (!res.ok) throw new Error(`random failed: ${res.status}`)
  return res.json()
}

export const NULL_LINEAGE_CACHE = { template: null, variants: [] }

export const MUTATION_DEFAULT_MIN_MEMBERS = 5

export async function fetchMutations({ trendingOnly = false } = {}) {
  const params = new URLSearchParams({ trending_only: String(trendingOnly) })
  const res = await fetch(`${API}/mutations?${params}`)
  if (!res.ok) throw new Error(`mutations failed: ${res.status}`)
  return res.json()
}

export function buildMutationIndex(response) {
  const templates = Array.isArray(response?.templates) ? response.templates : []
  const byTemplate = new Map()
  for (const entry of templates) {
    if (entry && typeof entry.template === 'string') byTemplate.set(entry.template, entry)
  }
  return {
    byTemplate,
    threshold: typeof response?.threshold === 'number' ? response.threshold : null,
    minMembers: typeof response?.min_members === 'number' ? response.min_members : MUTATION_DEFAULT_MIN_MEMBERS,
    ok: Array.isArray(response?.templates),
  }
}

function normalizeLineageCache(hit) {
  const raw = hit?.lineage_cache ?? hit?.lineage ?? null
  return {
    template: raw?.template ?? hit?.template ?? null,
    variants: Array.isArray(raw?.variants) ? raw.variants : [],
  }
}

export function toMutationRadarModel(hit, index) {
  const lineageCache = normalizeLineageCache(hit)
  const minMembers = index?.minMembers ?? MUTATION_DEFAULT_MIN_MEMBERS
  const telemetry = index?.byTemplate?.get(lineageCache.template) ?? null
  const memberCount = telemetry && typeof telemetry.member_count === 'number' ? telemetry.member_count : null
  const velocity = telemetry && typeof telemetry.velocity === 'number' ? telemetry.velocity : null
  const accumulatingBaseline = telemetry
    ? Boolean(telemetry.accumulating_baseline) || (memberCount !== null && memberCount < minMembers)
    : false
  const trendingFromHit = typeof hit?.trending_mutation === 'boolean' ? hit.trending_mutation : null
  const trendingFromTemplate = telemetry ? Boolean(telemetry.trending_mutation) : false
  const templateDriftScore = typeof hit?.template_drift_score === 'number' ? hit.template_drift_score : null
  return {
    template: lineageCache.template,
    variants: lineageCache.variants,
    templateDriftScore,
    trendingMutation: trendingFromHit ?? trendingFromTemplate,
    velocity,
    memberCount,
    minMembers,
    threshold: index?.threshold ?? null,
    accumulatingBaseline,
    hasTelemetry: Boolean(telemetry),
  }
}
