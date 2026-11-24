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

**Renderer sizes**, same author, same API, drop-in swap:

| | |
|---|---|
| `react-force-graph-2d` | 1.6 MB |
| `react-force-graph-3d` | 13.6 MB (bundles three.js) |

The bundle is already 654 KB raw / 215 KB gzipped, so both must be lazy-loaded
on the route.

---

## How it behaves

```
open Explore     layer 1 renders whole — 73 franchise nodes, rating 8.5+
click a node     description, and its 3-5 nearest by embedding
expand ⊕         a franchise node fans out its other entries
go deeper        the next band unlocks: expanding a node may now pull in
                 8.5-7.5 titles. The graph grows by what you touch, never
                 by a thousand at once
2D ⇄ 3D          same data; in 3D the unlocked bands are z-planes
```

Two rules keep it readable:

**Deeper layers unlock, they never dump.** 900 nodes on screen is a hairball
whatever the renderer. Depth changes which titles are *allowed in*, and
expansion brings them.

**One edge meaning: embedding similarity.** Genre, year and studio become
filters on which nodes appear, not edge types — if edges mean different things,
distance on screen means nothing. They are also already covered by Browse.

The layers are what make 3D worth 13.6 MB: a z-axis that means "rating tier" is
a real third dimension, rather than decoration.

---

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

### 3. Endpoints

| | |
|---|---|
| `GET /api/graph/layer?max_rating=&min_rating=&collapse=true` | nodes for a band, one per franchise |
| `GET /api/graph/neighbours/{id}?depth=` | a node's edges, limited to unlocked bands |
| `GET /api/anime/{id}/franchise` | the other entries behind a ⊕ |

The detail panel reuses `GET /api/anime/{id}`.

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

**Does unlocking a band seed anything visible?** Purely expansion-driven may
feel empty — nothing changes on screen until you click. The alternative is
dropping in the 20-30 best-connected titles from the new band. Start with
purely expansion-driven and see.

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
- Depth is reachable without ever rendering more than a few hundred nodes
- `scripts/mobile-check.mjs` still passes on Explore
- The Explore route's bundle is lazy, so Chat and Browse do not pay for it
