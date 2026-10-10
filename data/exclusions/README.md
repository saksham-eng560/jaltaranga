# Published Hydrological & Geospatial Exclusions

In low-lying floodplain digital elevation models (DEMs), satellite radar and optical DSMs (such as Copernicus GLO-30) capture elevations of bridge decks, elevated transit viaducts, and overhead civil structures rather than ground level. In addition, certain engineered civil assets possess localized waterproof flood-protection barriers (such as sealed floodwalls or pump-drained basements).

This directory documents **published exclusion polygons** where raw surface elevation or water intersection must not trigger false "road impassable" or "building flooded" flags.

## Documented Exclusions

| Exclusion ID | Feature Name | Type | Rationale |
|---|---|---|---|
| `excl_metro_red_viaduct` | Delhi Metro Red Line Viaduct (Kashmere Gate – Shastri Park) | Elevated Rail | Elevated concrete viaduct 12–15 m above Yamuna bed. Operates continuously during river flooding. |
| `excl_metro_blue_viaduct` | Delhi Metro Blue Line Viaduct (Indraprastha – Yamuna Bank) | Elevated Rail | Pier-supported elevated viaduct crossing Yamuna. Bridge deck elevation is >215 m MSL. |
| `excl_barapullah_elevated` | Barapullah Elevated Corridor (Phase 1–3) | Elevated Expressway | Elevated arterial corridor bridging the Yamuna khadar; piers resist inundation. |
| `excl_geeta_colony_flyover` | Geeta Colony Flyover High-Deck Ramps | Elevated Highway | Grade-separated ramps passing over Ring Road and marginal bund. |
| `excl_signature_approach` | Signature Bridge Northern Approach Viaduct | Elevated Viaduct | Elevated cable-stayed bridge approach structure 8–10 m above floodplain ground level. |
| `excl_who_bund_revetment` | WHO Building / Drain 12 Engineered Floodwall | Embanked Floodwall | Army/NDRF engineered sheet-pile sandbag bund and revetment preventing river ingress into Central Delhi. |

## Data Format
Each feature is published as a GeoJSON Feature with properties:
- `exclusion_id`: Unique identifier
- `name`: Human-readable name
- `type`: `elevated_transit` | `elevated_highway` | `engineered_barrier`
- `deck_elevation_m`: Effective clearance / deck elevation above ground
- `rationale`: Engineering documentation
