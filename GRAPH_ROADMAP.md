# Explore as a similarity graph

Explore and Browse currently do the same thing twice: both are grids of anime
cards, and only Explore's filters tell them apart.

The split: **Browse finds by criteria** (search plus the filters moved over
from Explore). **Explore discovers by similarity** — a graph where anime are
nodes and edges are how close their plots are in embedding space.

That also surfaces the most interesting thing in the project. 2,500 titles have
384-dimension embeddings that power semantic search invisibly; nothing in the
UI shows them.

---

## Measured first, 2026-11-24

Numbers taken against the live catalogue, so next session does not re-derive
them.

**Nearest neighbours are cheap.** The HNSW index does the work:

| | |
|---|---|
| k-NN for one anime | 74 ms |
| whole graph, 2,500 × top-8 | **944 ms** — 20,000 edges, one query |

So the edge set is a precompute, not an architectural problem.

**The rating bands are well shaped at the top and badly shaped in the middle:**

| layer | titles | |
|---|---|---|
| 10 – 8.5 | **125** | the opening view |
| 8.5 – 7.5 | 900 | too many to render at once |
| 7.5 – 6.5 | 1099 | too many to render at once |
| 6.5 – 5.0 | 341 | |
| below 5.0 | 35 | |

**Franchises dominate layer 1.** Of those 125 titles, only **73 are distinct
works** — 42% are sequels and side stories:

```
9x Gintama · 8x Attack on Titan · 6x Kizumonogatari · 4x BLEACH · 4x HAIKYU!!
```

**And the franchise data is already fetched and thrown away.** `anime.json`
carries 3,351 relation edges over 1,623 titles — SEQUEL 1164, SIDE_STORY 1042,
PREQUEL 848, SPIN_OFF 297 — and `related_anime` has **0 rows**. Ingest creates
the table and never writes to it. Connected components over those edges give
1,613 franchises, the largest holding 27 titles.

**The top tier is not internally connected.** Of the 1,000 nearest-neighbour
edges leaving the 8.5+ tier, only **171 land back inside it** — 17%. Drawing
only edges between tier members gives scattered dots, not a map. Computing the
edges *within the sample* instead gives 125 nodes, 500 edges, every node
connected, average degree 4.

**Renderer sizes**, same author, same API, drop-in swap:

| | |
|---|---|
| `react-force-graph-2d` | 1.6 MB |
| `react-force-graph-3d` | 13.6 MB (bundles three.js) |

The bundle is already 654 KB raw / 215 KB gzipped, so both must be lazy-loaded
on the route.

---

## How it behaves

The graph always shows **100-150 nodes**. Which 100-150 changes as you move.

```
open Explore   a sample of the full graph, picked by rating: the 8.5+ tier,
               collapsed to ~73 franchise nodes
click a node   detail panel: description and its 3-5 true nearest, which are
               usually NOT in the tier
click one      the graph re-centres on it and redraws ~120 nodes around it,
               with no rating restriction at all
2D ⇄ 3D        same data, same props
```

Rating is **the entry point, not a filter**. It answers "where do I start" and
then stops applying. Navigation is panning a map, not descending tiers.

### Why the opening sample needs its own edges

Taking the top tier and drawing only the edges between its members does not
work. Measured: of the 1,000 nearest-neighbour edges leaving the 8.5+ tier,
**only 171 land back inside it** — 17%. Most of what a great anime is closest
to is not itself great. Render that and you get scattered dots.

The fix is to compute the opening view's edges **within the sample**: each node
links to its nearest few among the nodes on screen. Measured on the 125:

```
125 nodes · 500 edges · every node connected · average degree 4
```

Those edges are "nearest among what you can see", which is the honest thing for
an overview. The *true* nearest neighbours appear in the detail panel when you
click a node — and clicking one of those is what re-centres the graph.

### Ship the whole graph, compute neighbourhoods in the browser

The entire graph is smaller than what Explore downloads today:

| | |
|---|---|
| 2,500 nodes (id, title, cover, rating, year, franchise) | ~337 kB |
| ~20,000 edges | ~300 kB |
| **total, gzipped** | **~200 kB** |
| what Explore ships today | 2 MB raw, ~680 kB gzipped |

So one request loads everything, and re-centring is a breadth-first walk in
memory — instant, no network, no endpoint per click. With k=8, a walk reaches
~8 nodes at depth 1, ~64 at depth 2 and ~500 at depth 3, so a budget of 120
lands naturally between depths 2 and 3.

This removes most of the API surface this feature looked like it needed.

## The work, in order

### 1. Load the relations that already exist

`ingest_anime.py` parses `relations` from `anime.json` and drops them. Write
them to `related_anime`, then compute connected components and store a
`franchise_id` on `anime`.

Also fixes `/api/anime/{id}/related`, which returns nothing today — and which
is shadowed by a duplicate route in `anime.py` (see ROADMAP.md).

### 2. Precompute the neighbour table

One query builds all 20,000 edges in under a second, so this belongs in
`ingest_anime.py` beside the vector index:

```sql
CREATE TABLE anime_neighbours (
  anime_id int, neighbour_id int, similarity real, rank smallint,
  PRIMARY KEY (anime_id, neighbour_id)
);
```

Top 8 per title. Rebuilt whenever embeddings change, which the idempotent
ingest already tracks.

### 3. One endpoint

```
GET /api/graph        all nodes and edges, franchise ids included
```

Cacheable, rebuilt only when ingest changes embeddings. Everything else —
the opening sample, re-centring, expansion — happens in the browser against
the data it already has. The detail panel reuses `GET /api/anime/{id}`.

### 4. Frontend, 2D first

`react-force-graph-2d`, lazy-loaded. Prove the interaction is actually fun
before paying for three.js.

### 5. Then 3D and the switch

Same data and props. Bands become z-planes. Lazy-load each renderer separately
so only the selected one downloads.

### 6. Move the filters to Browse

Rating, genre, year and studio move out of Explore. Browse already has the
search box, so it becomes the find-by-criteria surface and Explore becomes pure
discovery.

---

## Still open

**What exactly does a re-centre keep?** Dropping all 120 nodes and drawing a
fresh set is disorienting; keeping the clicked node and its path in place costs
layout stability but preserves the sense of having travelled. Worth trying both
— it is the difference between a map and a slideshow.

**How far should the walk go before it stops being related?** A budget of 120
reaches past depth 2, where similarity to the centre is already weak. A
distance cutoff may matter more than a node count.

**Render performance is entirely untested.** Every number above is database or
package size. Nothing has put a node on screen. 73 nodes should be trivial; the
question is what happens after a few expansions, especially in 3D on a phone.

**Mobile.** The app only just started fitting a phone. A force graph fights
page scroll for touch gestures and wants big tap targets. The low node count
helps; the detail panel probably wants to be a bottom sheet. 2D may be the only
sensible mobile mode.

**Does collapsing hide too much?** Attack on Titan becomes one node. Someone
looking for a specific season has to expand. Browse's search covers that case,
but it is worth watching.

---

## Done when

- Explore opens on a readable graph and no longer looks like Browse
- A node reaches its 3-5 nearest, and a franchise expands in place
- Re-centring stays under ~150 nodes however far you travel
- Nothing below 8.5 is unreachable: any node is a few clicks from the opening tier
- `scripts/mobile-check.mjs` still passes on Explore
- The Explore route's bundle is lazy, so Chat and Browse do not pay for it
