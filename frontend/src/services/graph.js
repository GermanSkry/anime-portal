/**
 * The similarity graph, loaded once and walked in memory.
 *
 * The whole thing is ~236 KB gzipped — less than the catalogue Explore used to
 * download — so re-centring on a click costs nothing and needs no request.
 */
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/** How many nodes a re-centred view aims for. */
export const BUDGET = 120

export async function fetchGraph() {
  const res = await fetch(`${API_BASE}/api/graph`)
  if (!res.ok) throw new Error(`graph unavailable (${res.status})`)
  const data = await res.json()

  // adjacency, strongest edge first, so a walk takes the closest titles
  const adj = new Map()
  for (const { a, b, w } of data.edges) {
    if (!adj.has(a)) adj.set(a, [])
    if (!adj.has(b)) adj.set(b, [])
    adj.get(a).push({ id: b, w })
    adj.get(b).push({ id: a, w })
  }
  for (const list of adj.values()) list.sort((x, y) => y.w - x.w)

  return {
    nodes: new Map(data.nodes.map(n => [n.id, n])),
    adj,
    seed: data.seed,
  }
}

/**
 * A node's true nearest, which are usually outside whatever is on screen.
 *
 * Sequels are dropped: a plot embedding puts Kaguya season 2 next to Kaguya
 * seasons 1 and 3, which the viewer can already see is the same show. The
 * franchise is on the map in its own colour; this list is for what else to
 * watch. Only 8 neighbours are stored per node, so a long franchise can
 * return fewer than `count`.
 */
export function nearest(graph, id, count = 5) {
  const ownFranchise = graph.nodes.get(id)?.franchise
  const seen = new Set()
  return (graph.adj.get(id) || [])
    .filter(n => !seen.has(n.id) && seen.add(n.id))
    .map(n => ({ ...graph.nodes.get(n.id), similarity: n.w }))
    .filter(n => n.id !== undefined && n.franchise !== ownFranchise)
    .slice(0, count)
}

/**
 * The neighbourhood around one node, breadth-first until the budget is spent.
 * With 8 edges a node, that reaches ~8 at depth 1 and ~64 at depth 2, so a
 * budget of 120 lands between depths 2 and 3.
 */
export function neighbourhood(graph, centreId, budget = BUDGET) {
  const depth = new Map([[centreId, 0]])
  const order = [centreId]
  for (let i = 0; i < order.length && order.length < budget; i++) {
    const cur = order[i]
    for (const { id } of graph.adj.get(cur) || []) {
      if (depth.has(id)) continue
      depth.set(id, depth.get(cur) + 1)
      order.push(id)
      if (order.length >= budget) break
    }
  }

  const included = new Set(order)
  const links = []
  for (const a of included) {
    for (const { id: b, w } of graph.adj.get(a) || []) {
      if (a < b && included.has(b)) links.push({ source: a, target: b, w })
    }
  }
  return {
    nodes: order.map(id => ({ ...graph.nodes.get(id), depth: depth.get(id) })),
    links,
  }
}

/** The opening view: one node per franchise above the rating line. */
export function seedView(graph) {
  const ids = new Set(graph.seed.ids)
  const links = graph.seed.edges
    .filter(e => ids.has(e.a) && ids.has(e.b))
    .map(e => ({ source: e.a, target: e.b, w: e.w }))
  return {
    nodes: graph.seed.ids.map(id => ({ ...graph.nodes.get(id), depth: 0 })),
    links,
  }
}
