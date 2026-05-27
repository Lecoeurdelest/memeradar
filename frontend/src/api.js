const API = import.meta.env.VITE_API || 'http://localhost:8000'

export async function searchMemes({ q, k = 24, visualWeight = 0.35, ironyWeight = 0.65, template = null }) {
  const params = new URLSearchParams({
    q,
    k: String(k),
    visual_weight: String(visualWeight),
    irony_weight: String(ironyWeight),
  })
  if (template) params.set('template', template)

  const res = await fetch(`${API}/search?${params}`)
  if (!res.ok) throw new Error(`search failed: ${res.status}`)
  return res.json()
}
