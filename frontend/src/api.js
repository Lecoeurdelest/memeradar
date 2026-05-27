const API = import.meta.env.VITE_API ?? 'http://localhost:8000'

export async function searchMemes({ q, k = 24, visualWeight = 0.35, ironyWeight = 0.65, template = null }) {
  const url = new URL(`${API}/search`)
  url.searchParams.set('q', q)
  url.searchParams.set('k', String(k))
  url.searchParams.set('visual_weight', String(visualWeight))
  url.searchParams.set('irony_weight', String(ironyWeight))
  if (template) url.searchParams.set('template', template)

  const res = await fetch(url)
  if (!res.ok) throw new Error(`search failed: ${res.status}`)
  return res.json()
}
