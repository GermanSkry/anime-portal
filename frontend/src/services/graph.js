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

  // Only franchises with more than one title are worth a colour: a singleton
  // has no group to reveal, and colouring it adds noise with no information.
  const franchiseSize = new Map()
  for (const n of data.nodes) {
    franchiseSize.set(n.franchise, (franchiseSize.get(n.franchise) || 0) + 1)
  }

  return {
    nodes: new Map(data.nodes.map(n => [n.id, n])),
    adj,
    seed: data.seed,
    franchiseSize,
  }
}

/** A node's true nearest, which are usually outside whatever is on screen. */
export function nearest(graph, id, count = 5) {
  const seen = new Set()
  return (graph.adj.get(id) || [])
    .filter(n => !seen.has(n.id) && seen.add(n.id))
    .slice(0, count)
    .map(n => ({ ...graph.nodes.get(n.id), similarity: n.w }))
    .filter(n => n.id !== undefined)
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
    links: markCrossFranchise(graph, order, links),
  }
}

/**
 * Mark, for every node, its strongest drawn link that leaves its franchise.
 *
 * Within a franchise everything resembles everything, so those edges say
 * little. The strongest edge going somewhere else is the jump worth taking.
 *
 * It works over the links actually drawn rather than global adjacency, so the
 * mark means the same thing in the opening view — whose edges are computed
 * within the sample — as it does after travelling.
 */
export function markCrossFranchise(graph, ids, links) {
  const franchiseOf = id => graph.nodes.get(id)?.franchise
  const best = new Map()
  for (const l of links) {
    const { source: a, target: b, w = 0 } = l
    if (franchiseOf(a) === franchiseOf(b)) continue
    for (const end of [a, b]) {
      if (!best.has(end) || best.get(end).w < w) best.set(end, { w, link: l })
    }
  }
  const marked = new Set([...best.values()].map(v => v.link))
  return links.map(l => ({ ...l, cross: marked.has(l) }))
}

/** The opening view: one node per franchise above the rating line. */
export function seedView(graph) {
  const ids = new Set(graph.seed.ids)
  const links = graph.seed.edges
    .filter(e => ids.has(e.a) && ids.has(e.b))
    .map(e => ({ source: e.a, target: e.b, w: e.w }))
  return {
    nodes: graph.seed.ids.map(id => ({ ...graph.nodes.get(id), depth: 0 })),
    links: markCrossFranchise(graph, graph.seed.ids, links),
  }
}
