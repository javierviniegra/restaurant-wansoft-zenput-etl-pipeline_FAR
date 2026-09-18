# PROJECT_CONTEXT_REPORT.md

Master continuity document. Generated/updated automatically at the close of major steps, on explicit request ("Generate project context report"), when the conversation gets very long, when consumed context exceeds ~70%, or when a new chat needs to be opened due to token limits. Always regenerated in full, never as an incremental patch.

Last generated: 2026-09-18, closing Step 24 and handing off into Step 25 (new sub-project kickoff). **Read this before anything else if you're picking this up fresh.**

---

# 0. Critical environment note — READ FIRST

**The project's working directory moved** (unchanged from prior reports, still true). OneDrive redirected the user's Desktop to the organization's OneDrive path around 2026-09-15. The old path (`C:\Users\JavierViniegra\Desktop\AnalisisRestaurantesBI\...`) is permanently empty.

**Current correct path:**
```
C:\Users\JavierViniegra\OneDrive - GRUPO FONDA ARGENTINA\Escritorio\AnalisisRestaurantesBI\Wansoft\Jupyter Notebooks\Python Files
```

The shell/harness's own default working directory still resets to the old (dead) path after every command — every command needs an explicit `cd` to the OneDrive path, or an absolute path. Session/tooling quirk, not a project issue.

**New this session:** a sibling project folder now exists at `...\AnalisisRestaurantesBI\Reportes\Analisis Ejecutivos\` (note: NOT inside the Wansoft repo — a separate directory one level up). This is where the new monthly/weekly executive-report PDFs live, and where the new Django web app (Step 25, see Section 13) will be scaffolded. It is currently **not a git repository** — that needs to be decided/set up when Step 25 starts (mirror `ControlPresupuestos_AP`'s own repo, or a new one — open question, see Section 10).

---

# 1. Executive Summary

**Overall project goal (unchanged):** build a unified analytical layer in MySQL that integrates Wansoft, Odoo, and Zenput, hiding from the end user which system originates each piece of data. Steps 1-23 (prior reports) built and validated Sales/Purchases/Inventory/Costs for that layer.

**This session's focus was different in kind from prior steps:** not pipeline/ETL debugging, but building a **presentation layer** on top of the already-validated data — branded executive PDF reports, one per branch per month, plus the discovery (through live iteration with the user) of the actual COGS-sourcing business rule that should govern them. This produced a reusable, corrected business rule that is *stricter and simpler* than what Step 23 had landed on, and now supersedes it (see Section 5).

**Big outcomes this session:**
- Diagnosed and explained (not "fixed", because it wasn't a bug) why Puebla's `getallordenesbyday_new_venta`/`_new_detalleventa` ticket-detail tables only covered a 4-day window in August: two independent Wansoft-side extraction scripts (`extractAllOrdersByDay.py`, 10-day rolling window; `getGlobalCashClosing.py`, 31-day rolling window) with different onboarding dates for Puebla — not a data bug on our side. This gap closed on its own mid-session as the user's own scheduled jobs kept running (observed live: Puebla's ticket-table coverage grew from 4 days -> full August between two messages in this same chat).
- Found the real Odoo source for a validated COGS %: Odoo's own "Reportes Analíticos" screen, reproduced exactly via `account.move.line` filtered to account codes `501.xx`, `parent_state='posted'`, **no `move_type` filter** — verified pixel-for-pixel against the user's own screenshot. Critical technical finding: `account.account.code` only resolves correctly when the XML-RPC call passes `context={'allowed_company_ids': [company_id]}` — without it, `code` comes back `False` for every account (multi-company chart-of-accounts quirk, cost several failed queries to find).
- **User gave a new, simpler, explicit Costs-routing rule that supersedes Step 23's 3-way split**: if a branch is on Odoo (`COMPANY_SOURCE == "odoo"`), its main "Costo de Productos Vendidos" figure comes from Odoo (cuenta 501); if not, from Wansoft (`costeomensual`). Merma, Cortesias, Cancelaciones/Anulaciones always come from Wansoft regardless (same principle as Step 23's Cortesias/Cancelaciones override, now stated as one clean rule instead of a per-branch exception table). See Section 5 for the full reasoning and why this replaces `COSTS_ODOO_SOURCE_COMPANIES`.
- **Also discovered and applied: cost percentages must be computed against venta NETA (sin IVA), not venta bruta** — explicit user correction; moved Puebla's August COGS% from 33.3% (bruta) to 38.65% (neta), landing exactly on the user's own ~38% PowerBI benchmark. This was the detail that made the whole exercise converge.
- Built a reusable branded-PDF generator (`analysis/puebla_scorecard/build_executive_pdf_all.py`) covering **all 19 branches**, 1-2 pages each, reusing the exact Fonda Argentina visual template (logo/frame/watermark) extracted directly from an existing branded report (`Reportes/Análisis Carnes/.../analisis_impactoCarne.pdf`) rather than redesigned from scratch.
- Cross-checked one metric (CPV % of venta neta) across all 19 branches after generating them, specifically to catch outliers before delivering — found Metepec at 10.34% vs. everyone else's 29-41% band. Surfaced it rather than silently smoothing it over; user confirmed the root cause is operational (Metepec, a franchise, doesn't reliably upload purchases or manage inventory) — not a bug, not to be re-investigated (see Section 9, bug-log-adjacent "confirmed not a bug" entries, and `project_metepec_franchise_data_gap` memory).
- New folder convention, user-created and now wired into the generator: `Reportes/Analisis Ejecutivos/docs/Mensuales/<year>/<Spanish month name>/`, auto-created if missing.
- **Session pivots into a new sub-project at the end**: user wants a Django web app (structured like `ControlPresupuestos_AP`) living in `Reportes/Analisis Ejecutivos/`, with scheduled email delivery (monthly day-4, weekly Tuesdays), an in-browser dashboard (no PDF required to analyze), on-demand report generation for any week/month/year, and week-over-week / year-over-week (and month-over-month / year-over-year, conditional on branch history) comparisons with trend arrows. This is **Step 25**, not started yet beyond requirements-gathering — see Section 13.

**Current block:** none on Steps 1-24 (all delivered, no open bugs). Step 25 is a fresh scaffold, requirements gathered but no code written yet.

---

# 2. Session 2026-09-18 — Full recap

## 2.1 Puebla single-branch exercise (started as a continuation of Step 23/24 boundary)

User asked for a manual scorecard-style analysis (Ventas + Costos, Wansoft + Odoo-live) for Puebla, August + September, modeled after a real weekly scorecard format they use. This iterated through several corrections before landing on the validated methodology — each correction is preserved here because the *reasoning*, not just the final number, is what generalizes:

1. **Meseros / mix Alimentos-Bebidas / Consumo Salón initially looked wrong** because `getallordenesbyday_new_venta`/`_new_detalleventa` only had a 4-day window (Aug 28-31) for Puebla. Diagnosed via `legacy/wansoft/automaticos/extractAllOrdersByDay.py` (10-day rolling window, Puebla added late to its branch list) vs. `legacy/wansoft/descargarCostoWansoft/getGlobalCashClosing.py` (31-day rolling window, Puebla added earlier) — two independent extraction jobs, not the same pipeline. User declined a manual backfill ("ya estás tomando un total de venta exacto y en cada ticket viene el tipo de orden" — the estimate-from-ratio approach was good enough). **The gap then closed on its own mid-session** as the user's real scheduled jobs kept running in the background — by the time of the multi-branch batch (Section 2.3), Puebla and Acoxpa had full-month ticket coverage; the other 5 Odoo-migrated branches still had partial (28-31 ago) coverage.
2. **COGS via Odoo purchase orders (the Step 23 approach) undercounted real cost** — `analytics_purchase_order_lines`-based estimates landed at 33-35%, and even after correctly re-including two vendors that had been wrongly auto-flagged as "internal" (El Bodegón de Fito, Las Empanadas de María Eva — same finding as Step 23's Section 2.2 internal-vendor bug, recurring in a new context), still only reached ~43% with no department-level filtering possible (product-department mapping is almost entirely null for Puebla in Odoo).
3. **User redirected to the real source**: Odoo Accounting's own "Reportes Analíticos" screen, filtered to accounts starting with `501`. Replicated exactly via live XML-RPC (see Section 1's technical finding on `allowed_company_ids`). This produced Puebla's real COGS breakdown by category (Carnes, Frutas y Verduras, Con Alcohol, etc.) — verified against the user's screenshot line-by-line, exact match.
4. **User then gave the venta-neta correction** (Section 1) — the detail that reconciled the Odoo-based COGS% with the user's own ~38% benchmark.
5. **User then asked for Merma/Consumo Salón specifically from Wansoft** (cierre diario + `getallordenesbyday_new_venta` filtered to `TipoOrden='Restaurant'` and Mesero not an app-channel placeholder) — confirmed Puebla has no literal "AppsLlevar" Mesero value, only "Aplicaciones - Fonda Argentina", and confirmed it only ever appears under `TipoOrden='eCommerce'`, never `'Restaurant'`, so the extra Mesero filter is a no-op safety net, not a real exclusion.

Result: a full Ventas+Costos scorecard for Puebla, delivered first as a chat table, then as an Excel workbook (`Scorecard_Puebla_Ago_Sep_2026.xlsx`), then as a branded 2-page executive PDF (see 2.2).

## 2.2 Branded PDF template — extracted, not redesigned

User provided an existing branded report (`Reportes/Análisis Carnes/Resultados/analisis_impactoCarne.pdf`) as the style reference and asked to reuse its look exactly. Rather than re-implementing the Fonda Argentina brand from scratch, extracted the **actual background image** (logo badge + rounded-corner frame + watermark silhouette, all one JPEG) directly from the reference PDF via `pymupdf`/`fitz`'s `page.get_images()` + `extract_image(xref)`, and reused it as a full-bleed page background in a new `reportlab`-based generator. Brand teal sampled directly from the image: `#10564E`. This is now the standing template for all executive PDFs — see `feedback_executive_report_standard_format` memory.

First version built at `analysis/puebla_scorecard/build_executive_pdf.py` (Puebla only, Odoo-cost). User approved the format after one round of content-outline review (asked to see the planned content before generating — this stepwise-approval pattern, not silent scaffolding, applied throughout the session).

## 2.3 Generalized to all 19 branches — and the real Costs-routing rule emerged

User asked for the same exercise for "las empresas que ya están en Odoo," which surfaced Step 23's 3-way Costs split (`COSTS_ODOO_SOURCE_COMPANIES = {"Puebla", "CentroMyJ"}`, Wansoft `costeomensual` for the other 5 migrated branches) — applied it first (`build_executive_pdf_multi.py`, 6 new branches + Puebla). Validated Acoxpa's Wansoft-sourced CPV at 34.88% of venta neta — matching the user's own PowerBI benchmark for that branch.

**Then the user gave a new, simpler rule that overrides Step 23's split** (their exact words): "si ya está en Odoo, la empresa debería de traer los costos de Odoo[;] si no está en Odoo ... traerlos de Wansoft[, salvo] los valores que vienen del cierre diario como mermas, cortesías, descuentos que vienen de Wansoft siempre al igual que la venta." Rebuilt as `build_executive_pdf_all.py` covering **all 19 `COMPANY_SOURCE` branches** (7 Odoo + 12 Wansoft), applying:
- Costo de Productos Vendidos: Odoo cuenta 501 if `COMPANY_SOURCE=="odoo"`, else `costeomensual.CostoDeProductosVendidos`.
- Merma: **always** `costeomensual.CostoDeMerma` (no cierre-diario equivalent exists).
- Cortesías / Cancelaciones / Anulaciones: **always** `getglobalcashclosing` (cierre diario), at sale-price valuation, kept as a separate "Ajustes de Venta" block rather than summed into Costo Total (mixing sale-price and ingredient-cost valuations in one total would be methodologically wrong — flagged to the user, not silently done).

This is now the standing rule, documented in `feedback_executive_report_standard_format` memory (which also records the superseded v1 per-branch split, kept for context on *why* it existed).

Two real edge cases handled while building the 19-branch batch:
- **Metepec and Versalles have zero rows** in `getallordenesbyday_new_venta` for any period — not a coverage gap, a total absence (different failure mode than the 4-day-window gap in 2.1). Made ticket-detail resolution tolerant of zero matches (render N/D) instead of raising.
- **Viaducto vs. Taquería Viaducto** are two distinct branches that both match a naive `LIKE '%Viaducto%'` — needed exact-match resolution for these two specifically.

Company-name resolution across 4 different naming schemes (`COMPANY_SOURCE` keys, `getglobalcashclosing.subsidiary_name`, `getallordenesbyday_new_venta.Sucursal`, Odoo `res.company.name`) required a per-branch lookup table — none of the schemes match each other directly (e.g. "Metepec" ~ Wansoft subsidiary "Tollocan"). See the `COMPANIES` list in `build_executive_pdf_all.py`.

**Post-build cross-check caught a real anomaly**: CPV% across all 19 branches clusters at 29-41% except Metepec at 10.34%. Flagged to the user (not silently delivered). User confirmed: known, accepted, operational root cause ("Metepec no sube compras y no maneja bien su inventario ... que sea el número que es") — do not re-investigate or attempt to correct in future runs (now in `project_metepec_franchise_data_gap` memory).

## 2.4 Folder convention + PDF filing

User created `Reportes/Analisis Ejecutivos/docs/Mensuales/<year>/<Spanish month name>/` by hand and asked that future monthly reports be generated directly into that structure, creating year/month folders as needed. Updated `build_executive_pdf_all.py`: `OUT_DIR` is now computed from two constants at the top of the file (`ANIO`, `MES_NUM`) instead of being hardcoded, and the output filename suffix is derived the same way (was previously hardcoded to `_Agosto_2026` regardless of the configured month — fixed as part of this same change, would have silently mislabeled any future month's files otherwise).

## 2.5 Session pivots to a new sub-project: Análisis Ejecutivos web app (Step 25 kickoff)

User asked to build a Django web app, structured and conventioned the same way as `ControlPresupuestos_AP`, living in `Reportes/Analisis Ejecutivos/`. Before scaffolding, reviewed `ControlPresupuestos_AP`'s actual conventions (not assumed):
- Django `>=4.2,<5.0` (capped — dev/prod MariaDB is 10.4.32, Django 5.0+ needs MariaDB 10.5+), `mysqlclient`, `python-dotenv`, `openpyxl`, `matplotlib`, `xhtml2pdf` (their PDF approach — HTML/CSS-to-PDF, different from this session's `reportlab` approach; open question for Step 25, see Section 10).
- `.env`-driven settings with a `_DEV` suffix pattern for dev/prod DB switching (`PRESUPUESTOS_DB_HOST_DEV` vs. `PRESUPUESTOS_DB_HOST`).
- Scheduling is **Windows Task Scheduler calling standalone Django-context scripts** (`scripts/scheduler.py`, `django.setup()` then direct ORM calls) — not Celery, not an in-process scheduler daemon. Dedicated `logs/scheduler.log` via its own logger, separate from `logs/django.log`.
- Production: Waitress (WSGI) + WhiteNoise (static files) on a dedicated app VM (`SVR-HIKCENTER`), reached only through an existing Apache reverse proxy (`187.251.203.223:8088`) under a URL-path prefix (`/presupuestos_ap/`) — never the app VM's own address directly. `deploy/PRODUCTION_SETUP.md` + `deploy/update.ps1` document the one-time setup and routine update flow.

User's functional requirements for Step 25 (gathered via `AskUserQuestion`, answer was a full paragraph, not a single option — captured verbatim in Section 13's handoff prompt so nothing gets lost/paraphrased-away):
- Scheduled auto-send: monthly on day 4, weekly on Tuesdays, to per-branch-assigned email recipients.
- In-browser analysis without needing a generated PDF (a real dashboard, not just a file server).
- On-demand generation for any chosen week, month, or year.
- Weeks are Monday-Sunday; months are calendar/Gregorian.
- **Weekly reports**: compare vs. previous week AND vs. the same numeric week of the prior year, with a trend-arrow column (grow/shrink/flat) in the same table.
- **Monthly reports**: same comparison treatment, but only for branches that actually have prior-year (or prior-month-of-prior-year) history — most branches don't (see the whole "sin comparación año anterior" pattern that ran through Section 2's single-branch and multi-branch work; this is not new information, just now a hard requirement to implement conditionally per branch).
- Possibly one additional chart per comparison axis (vs. prior period, vs. prior year).

No code written for Step 25 yet — this report closes here specifically so that buildout starts in a fresh chat with a clean context budget, per the project's own standing convention for major steps (see Section 12's Permanent Rule, and prior reports' own practice of one step per session when the step is large).

---

# 3. Detailed Status by Domain (delta from Step 23 report only — domains not touched this session are omitted, see prior report for Sales/Purchases/Inventory full status)

### Costs
**Routing rule changed** (supersedes Step 23's `COSTS_ODOO_SOURCE_COMPANIES`, see Section 5). The old 3-way split is now dead code / historical reasoning only — `core/config/companies.py`'s `COSTS_ODOO_SOURCE_COMPANIES` and `is_company_wansoft_source_for_costs()` were **not edited this session** (this session's work lives in the standalone `analysis/puebla_scorecard/` reporting scripts, not in the core ETL/pipeline code) — if the core pipeline's own Costs consumers are ever pointed at this new rule, that dict needs to be revisited or removed. Flagging explicitly so it isn't missed: **the core pipeline (`core/config/companies.py`) and the new executive-report generator (`analysis/puebla_scorecard/build_executive_pdf_all.py`) currently implement two DIFFERENT Costs-routing rules side by side** — the pipeline still has the old per-branch 3-way split, the reports use the new simpler if-Odoo-then-Odoo rule. This was a deliberate scope choice this session (the user's new rule was given specifically in the context of the executive reports), not an oversight, but it means the two are now out of sync and someone will eventually need to decide whether `core/config/companies.py` should be updated to match.

### Executive Reporting (new domain, did not exist before this session)
Fully built for August 2026, all 19 branches, validated. Lives entirely outside the core ETL pipeline, in `analysis/puebla_scorecard/`:
- `build_executive_pdf_all.py` — the generator (current standard, supersedes `build_executive_pdf.py` and `build_executive_pdf_multi.py`, both kept on disk as historical/reference, not deleted).
- `build_cost_chart.py`, `logo_extract_0.jpeg` — chart and branded-background assets.
- Output: `Reportes/Analisis Ejecutivos/docs/Mensuales/2026/Agosto/*.pdf` (19 files).

---

# 4. Architectural Decisions Made (this session)

| Decision | Rationale | Impact |
|---|---|---|
| Reuse the brand's actual background image (extracted from an existing PDF) instead of rebuilding the visual identity in code | Pixel-exact match to the user's existing reports, zero design guesswork, verified directly against a real reference | `analysis/puebla_scorecard/logo_extract_0.jpeg`, all executive PDFs |
| Cost percentages computed against venta NETA (sin IVA), never venta bruta | Explicit user correction; matches how the business actually calculates cost ratios; reconciled the Odoo-COGS finding with the user's own benchmark | All executive-report percentage calculations |
| Costs routing: Odoo if `COMPANY_SOURCE=="odoo"`, else Wansoft; Merma/Cortesías/Cancelaciones always Wansoft | User's explicit, simpler replacement for Step 23's 3-way split — applies uniformly, no more per-branch exception table to maintain | `build_executive_pdf_all.py`; **not yet propagated to `core/config/companies.py`**, see Section 3 |
| Cortesías/Cancelaciones/Anulaciones shown as a separate "Ajustes de Venta" block, not summed into Costo Total | They're valued at sale price, not ingredient cost — summing would mix valuation bases incorrectly. Surfaced to the user as a methodology point, not silently done | `build_executive_pdf_all.py` |
| `account.account.code` XML-RPC calls must pass `context={'allowed_company_ids': [id]}` | Without it, `code` returns `False` for every account in this multi-company Odoo instance — cost real debugging time to discover | `analysis/puebla_scorecard/build_executive_pdf_all.py`, any future Odoo `account.account` query |
| Ticket-detail company-name resolution needs a hardcoded per-branch lookup, not a generic `LIKE` pattern | 4 different naming schemes across `COMPANY_SOURCE`/Wansoft/Odoo don't share a common substring reliably (Metepec/Tollocan, Viaducto/Taquería Viaducto collision) | `COMPANIES` list in `build_executive_pdf_all.py` |
| `OUT_DIR` and output filenames derived from two constants (`ANIO`, `MES_NUM`) instead of hardcoded strings | The first version hardcoded "Agosto_2026" in the output filename regardless of the configured month — would have silently mislabeled every future month's PDFs | `build_executive_pdf_all.py` |
| Metepec's anomalous 10.34% CPV is presented as-is, permanently, no correction attempted | User-confirmed operational root cause (franchise doesn't reliably report purchases/inventory), not a data bug | Documented in `project_metepec_franchise_data_gap` memory, binding on all future executive reports |

---

# 5. Business Rules Implemented / Reinforced (this session)

- **Costs routing for executive reports (NEW, supersedes Step 23's 3-way split for this domain)**: Odoo cuenta 501 if the branch is Odoo-sourced (`COMPANY_SOURCE=="odoo"`), Wansoft `costeomensual` otherwise. Merma/Cortesías/Cancelaciones/Anulaciones **always** Wansoft, regardless — same "Sales-and-Sales-adjacent-values-are-always-Wansoft" principle Step 23 established for Cortesías/Cancelaciones specifically, now generalized and simplified into one rule instead of a lookup table.
- **Cost percentages are always computed against venta neta (sin IVA)**, never venta bruta — applies to every cost line, every branch, every report.
- **Sale-price-valued figures (Cortesías/Cancelaciones/Anulaciones) never get summed into a cost total** — different valuation basis than ingredient cost; shown adjacently, not combined.
- **Metepec's Costs numbers are accepted as-is, permanently** — same standing principle Step 23 already established for Metepec's Inventory numbers (`project_metepec_franchise_data_gap`), now explicitly extended to Costs by the user this session.
- **A branch only gets a year-over-year comparison if it actually has prior-year (or prior-same-period) data** — stated as a hard requirement for Step 25, but consistent with everything already observed this session and in Step 23/24 about which branches have real history (Puebla, CentroMyJ, and the 5 migrated-in-2026-06 branches largely don't).

---

# 6. Technical Conventions (new this session)

- **Extracting a branded background from an existing PDF**: `pymupdf` (`import fitz` still works but is deprecated in favor of `import pymupdf`), `doc[page_num].get_images(full=True)` to list embedded images, `doc.extract_image(xref)` to pull the raw bytes — much more reliable than screenshotting and cropping.
- **Rendering a PDF page to inspect it visually**: `page.get_pixmap(dpi=130-150).save(path)`, then `Read` the resulting PNG — used throughout this session to visually QA every generated report page before delivering.
- **`reportlab` for branded, precisely-laid-out PDFs**: full-page background image via `canvas.drawImage`, custom bold-lead-in bullet wrapping (a mixed-bold/regular-font word-wrap helper was needed — reportlab has no built-in rich-text-in-a-flow primitive at this level of control), manual table drawing (`draw_kpi_table` helper) rather than `reportlab.platypus` — chosen for exact pixel control over spacing/alternating-row-color/header-bar styling matching the brand reference.
- **Vertical-space budgeting on a fixed-size branded page is real and easy to get wrong**: hit an actual content/footer overlap bug when adding a 4th KPI block without re-budgeting row heights and inter-section gaps — fixed by tightening row height (16.5->15.2pt), bullet leading, and collapsing a 3-row table into a single text line where the content was simple enough. Worth padding estimates generously on any future page-1-must-fit-exactly report.
- **Odoo XML-RPC company-scoped fields**: any field that Odoo computes per-company-in-context (chart-of-accounts `code` was this session's example) needs `context={'allowed_company_ids': [company_id]}` passed explicitly in the `execute_kw` call — easy to miss since the call succeeds and returns data, just with the company-scoped field silently `False`/empty instead of erroring.
- **MySQL client string encoding in this environment**: printing/interpolating accented Spanish strings (á, é, í, ó, ú, ñ) directly into an f-string SQL query source can mangle them in a way that breaks exact-match queries; using bound parameters (`cursor.execute(query, (param,))`) instead of string interpolation avoids the issue since the bytes travel through the connector's own encoding path rather than being re-encoded by print/terminal display. Also true of the `Edit` tool's string matching against already-written source containing accented characters — safer to anchor edits on the ASCII-only portions of a line when the accented portion isn't unique enough to need including.

---

# 7. Git State

**Wansoft repo** (`...\Wansoft\Jupyter Notebooks\Python Files`): branch `main`. This session's new files (`analysis/puebla_scorecard/*`) have **not yet been committed** as of this report — see Section 10, needs an explicit commit this session or first thing in the next one. Prior state was up to date with `origin/main` through `5e18b79` (Step 23); nothing from Steps 1-23 changed this session.

**Análisis Ejecutivos folder** (`...\Reportes\Analisis Ejecutivos\`): **not a git repository at all yet.** This is new territory for Step 25 — needs a decision (new repo vs. folder-only, see Section 10) before the Django scaffold starts.

---

# 8. Important Historical Context — Bug Log Additions (do not re-investigate)

Continuing the numbering from prior reports (last entry was #23, Step 23).

| # | Item | Where | Status |
|---|---|---|---|
| 24 | Executive-PDF output filename hardcoded `_Agosto_2026` regardless of configured month | `analysis/puebla_scorecard/build_executive_pdf_all.py` | **Fixed 2026-09-18**, before it ever shipped a wrong filename |
| 25 | Metepec CPV anomaly (10.34% vs. 29-41% band) | `costeomensual` for Metepec/Tollocan | **Confirmed NOT a bug** — operational (franchise doesn't reliably report purchases/inventory), user-confirmed 2026-09-18, do not re-investigate |
| 26 | Puebla ticket-detail table 4-day-window gap (recurrence of the Step 23-adjacent rolling-window pattern, different branch/table than Step 22's Sales gap) | `getallordenesbyday_new_venta`/`_new_detalleventa`, `extractAllOrdersByDay.py`'s 10-day window vs. `getGlobalCashClosing.py`'s 31-day window | **Confirmed NOT a bug** — two independent extraction jobs, different onboarding dates; resolved itself as the real scheduled jobs kept running through the session |

**Also confirmed NOT bugs this round (non-numbered, methodology findings rather than data issues):**
- Purchase-order-based COGS estimates (Step 23's original approach for pure-Odoo branches) genuinely undercount real cost vs. the Odoo accounting (`account.move.line`) ground truth — not a bug in the purchase-order data, just the wrong table for this specific question. `account.move.line` on cuenta 501 is the validated source going forward.
- Two vendors (El Bodegón de Fito, Las Empanadas de María Eva) auto-flagged `is_internal_vendor=True` in `analytics_purchase_order_lines` for Puebla — same class of issue as Step 23's Section 2.2 internal-vendor bug, but this session's fix was scoped to the reporting layer's own treatment of them (include as real spend, per user decision), not a pipeline-level fix to the `is_internal_vendor` classification itself. **Open question for whoever picks up the core pipeline next**: should `analytics_purchase_order_lines`'s own internal-vendor classification be corrected for these two vendors specifically, the way Step 23 corrected the company-vs-vendor logic? Not done this session, scope was the report only.

---

# 9. User Decisions (explicit, don't lose track of these)

- **Confirmed (2026-09-18):** Costs routing for executive reports is "Odoo if the branch is Odoo, Wansoft if not, except Merma/Cortesías/Cancelaciones which are always Wansoft" — supersedes Step 23's 3-way split for this domain. Given after being shown the numeric tradeoff (floor/ceiling/best-estimate scenarios for two ambiguously-classified vendors).
- **Confirmed (2026-09-18):** cost percentages use venta neta (sin IVA), not venta bruta.
- **Confirmed (2026-09-18):** El Bodegón de Fito and Las Empanadas de María Eva are real third-party food suppliers for Puebla, not internal/related-party entities to exclude — include both as real materia-prima spend.
- **Confirmed (2026-09-18):** Metepec's Costs numbers (and, by extension, all its numbers) are accepted as-is — do not re-investigate the low CPV%, it's a known franchise data-reliability issue, not a pipeline bug.
- **Confirmed (2026-09-18):** monthly reports go in `Reportes/Analisis Ejecutivos/docs/Mensuales/<year>/<Spanish month name>/`, auto-created if missing.
- **Confirmed (2026-09-18):** Step 25 (Análisis Ejecutivos web app) should be built "the same way" as `ControlPresupuestos_AP` was — same collaborative, step-by-step, approval-gated working style, same technical conventions (Django, `.env`-driven dev/prod, Windows Task Scheduler for automation, Waitress+WhiteNoise for prod) unless a specific reason to deviate comes up.
- **Open, not yet decided:** whether Step 25 keeps `reportlab` (this session's proven approach) or switches to `xhtml2pdf` (`ControlPresupuestos_AP`'s own convention) for any PDF export the web app offers. Worth raising explicitly at the start of Step 25 rather than assuming either way.
- **Open, not yet decided:** whether `core/config/companies.py`'s `COSTS_ODOO_SOURCE_COMPANIES` (the old 3-way split, still live in the core pipeline) should be updated to match the new simpler rule, left alone since it serves a different consumer, or deprecated entirely. Not addressed this session — flagged, not resolved.

---

# 10. Open Items / Immediate Next Actions

- **This session's new files are uncommitted.** Before ending this chat: commit `analysis/puebla_scorecard/*` (generator scripts, extracted brand assets, this report) to the Wansoft repo with an English commit message (see `feedback_github_content_english_only` memory). The generated PDFs themselves (`docs/Mensuales/...` under Análisis Ejecutivos) live in a **different, currently non-git folder** — decide in Step 25 whether that folder becomes its own repo (likely, to mirror `ControlPresupuestos_AP`) before committing anything there.
- **Decide Análisis Ejecutivos' repo strategy** before scaffolding Django: new standalone repo (matching `ControlPresupuestos_AP`'s own structure exactly), or something else. Not asked yet.
- **Reconcile the two now-divergent Costs-routing implementations** (`core/config/companies.py`'s 3-way split vs. the executive report's simpler if-Odoo rule) at some point — not urgent, but will confuse a future session if left unexplained. This report is that explanation, for now.
- **Step 25 functional spec is gathered but unrefined** — the user's answer (Section 2.5) is a real spec, but hasn't been turned into a numbered implementation roadmap yet (the FONDA-BI-style step-by-step-with-approval pattern the user prefers for big builds, per `feedback_fonda_bi_approval_workflow` memory, which explicitly is the working style to reuse here too). That roadmapping is the actual first task of Step 25, before any Django code.

---

# 11. Consolidated Backlog (carried forward from Step 23, unchanged unless noted)

- Inventory valuation for pure-Odoo branches (Puebla, CentroMyJ) — still not built, still blocks a true (non-approximated) COGS for them at the pipeline level. **Note:** this session's executive reports sidestep this by using Odoo's accounting (`account.move.line`) directly instead of inventory valuation — a different, now-validated path to the same COGS number, but the underlying inventory-valuation gap for other pipeline uses is still open.
- Decide when to turn off production's duplicate Wansoft Purchases/Inventory loading (5 branches) — unchanged, still deferred.
- Check whether Antenas/Tepeyac/Oceania/La Esquina Coyoacán/CentroMyJ have the same dev-only Aug 1-27 Sales gap Acoxpa/Puebla had — unchanged, still not checked (though this session observed all 5 of these branches' ticket-detail tables had only a 28-31 ago window when the executive reports were built, which is *consistent with* an unhealed gap, but wasn't specifically re-diagnosed this session the way Section 2.1 diagnosed Puebla's).
- Weekly product-mapping job first-real-Sunday-run — unchanged, still not observed.
- **New from this session**: build Step 25 (Análisis Ejecutivos web app) — now the active priority.

---

# 12. Next Steps — HANDOFF PROMPT

**Paste this as the first message when resuming in a new chat:**

```
Continúo el proyecto FONDA. Este chat es específicamente para el Paso 25:
Análisis Ejecutivos - Proyecto Web (Django), estructurado y trabajado igual
que ControlPresupuestos_AP.

Lee primero C:\Users\JavierViniegra\OneDrive - GRUPO FONDA ARGENTINA\
Escritorio\AnalisisRestaurantesBI\Wansoft\Jupyter Notebooks\Python Files\
PROJECT_CONTEXT_REPORT.md completo -- especialmente la Sección 0 (rutas),
la Sección 2.5 y 9-10 (qué se pidió exactamente para este proyecto web y
qué sigue abierto).

Contexto rápido: ya existen 19 reportes ejecutivos PDF mensuales (agosto
2026, todas las sucursales) generados por
analysis/puebla_scorecard/build_executive_pdf_all.py, guardados en
Reportes/Analisis Ejecutivos/docs/Mensuales/2026/Agosto/. La regla de
costos ya validada: Odoo (cuenta 501) si la sucursal ya está en Odoo,
Wansoft (costeomensual) si no, salvo Merma/Cortesías/Cancelaciones que
siempre son Wansoft. Los % de costo siempre se calculan sobre venta neta.

Lo que pediste para el proyecto web (textual, para no perder nada):
- Envío automático por correo: mensual el día 4, semanal los martes, a
  correos asignados por sucursal.
- Poder analizar la información en la misma web sin necesidad de generar
  el PDF (dashboard real, no solo un servidor de archivos).
- Poder forzar la generación de un resumen ejecutivo de la semana, mes o
  año que yo elija.
- Semanas de lunes a domingo; meses del calendario gregoriano.
- Reportes semanales: comparativo contra la semana anterior Y contra la
  misma semana numérica del año anterior, con columna de flechas
  (crece/decrece/se mantiene) en la misma tabla.
- Reportes mensuales: mismo comparativo, pero solo para las sucursales
  que sí tengan mes del año anterior o mes del mismo año anterior (la
  mayoría no tiene, como ya vimos en Puebla/CentroMyJ/etc.).
- Posiblemente una gráfica extra por eje de comparación (vs. periodo
  anterior, vs. mismo periodo año anterior).

Primer paso real de este chat: NO escribir código Django todavía.
Primero armar el roadmap paso a paso (igual que FONDA BI) y validarlo
conmigo antes de tocar nada -- incluye resolver las preguntas abiertas
de la Sección 9-10 del reporte (reportlab vs xhtml2pdf, repo nuevo o no
para esta carpeta, etc.).
```

**Suggested title for the new chat**: `FONDA (Análisis Ejecutivos): Paso 25: Proyecto Web Django — roadmap y arranque`

**Also, before opening that new chat**: commit this session's uncommitted work in the Wansoft repo (Section 10) — do not leave `analysis/puebla_scorecard/*` and this report uncommitted across the chat boundary.

---

# Permanent Rule

Regenerate this document in full (never as patches) when: the user explicitly asks, a major step closes, the conversation gets very long, context exceeds ~70%, or a new chat needs to be opened due to token limits. In that last case, also generate:
1. The handoff prompt (Section 12, first code block, if applicable).
2. The suggested title for the new chat, in the format **`FONDA (short project): Paso N[-M]: <short description>`** (same style as the user's own session list). `FONDA` is a fixed prefix; `(short project)` identifies which project — note this now varies per sub-project under the same user (e.g. "Wansoft" for the ETL/pipeline work, "Análisis Ejecutivos" for this new web app) even though both ultimately serve Grupo Fonda Argentina. Use `N` = the major step/block number in progress (continues a single running count across the user's FONDA projects, per their own session-list convention — confirm the next number from the most recent title if unsure), `-M` = sub-part suffix if the step spans multiple consecutive sessions/chats.

**Note on language:** this document, all commit messages, and all documentation pushed to GitHub in this project must be written in English — even though the working conversation with the user is in Spanish. See project memory `feedback_github_content_english_only` for the full rule.
