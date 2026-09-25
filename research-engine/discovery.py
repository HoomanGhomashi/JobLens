"""
JobLens Agent — Discovery (Company Discovery par zone géographique)
====================================================================
Responsabilité : découvrir des entreprises tech dans une ville via Apify.

Ce module NE décide PAS :
  • si une entreprise est bonne pour le candidat
  • si une offre est un match
  • si l'expérience demandée correspond au profil
  • quel score attribuer

Il produit une liste de CompanyCandidate prête à être analysée par Claude
(dans analysis.py, appelé par agent.py).

Flux :
  SearchHistory → décision stratégie
  → build_queries
  → call_apify_one_query (une query = un run Apify)
  → extract_candidates (heuristiques légères, sans LLM)
  → deduplicate_candidates (comparaison base de données)
  → DiscoveryRunResult (avec new_candidates pour Claude)
  → record_search (SearchHistory)
"""

from __future__ import annotations

import logging
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import pyodbc
from apify_client import ApifyClient

from database import DatabaseManager
from models import (
    Company,
    CompanyStatus,
    CoverageState,
    HiringSignal,
    SearchDecision,
    SearchRecord,
    SearchType,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Constantes
# =============================================================================

# Acteur Apify utilisé
APIFY_ACTOR_ID = "apify/rag-web-browser"

# Paramètres d'appel par défaut
APIFY_MAX_RESULTS = 5          # pages scrappées par query
APIFY_TIMEOUT_SECS = 40        # timeout total (Google + scraping)
APIFY_MAX_RETRIES = 2          # retries internes (gérés par l'acteur)
APIFY_PAUSE_BETWEEN_QUERIES = 2  # secondes entre deux runs Apify

# Délai minimum (jours) avant de re-analyser complètement une entreprise connue
REFRESH_FULL_ANALYSIS_AFTER_DAYS = 90
REFRESH_PARTIAL_AFTER_DAYS = 30

# =============================================================================
# Domaines agrégateurs / annuaires — filtrés avant envoi à Claude
# =============================================================================

AGGREGATOR_DOMAINS = frozenset({
    # Annuaires et agrégateurs
    "pagesjaunes.fr", "societe.com", "kompass.com", "manageo.fr",
    "infogreffe.fr", "verif.com", "pappers.fr", "bilan-gratuit.fr",
    "sirene.fr", "annuaire-mairie.fr", "annuaires.mairie.fr",
    "corporama.com", "datainfogreffe.fr", "firmenprofil.de",
    # Jobboards / agrégateurs d'offres
    "apec.fr", "monster.fr", "cadremploi.fr", "meteojob.com",
    "jobteaser.com", "talent.io", "choosemycompany.com",
    "hellowork.com", "letudiant.fr", "regionsjob.com",
    # Réseaux sociaux / moteurs (pages de résultats)
    "google.com", "google.fr", "bing.com", "yahoo.com",
    "twitter.com", "x.com", "facebook.com", "instagram.com",
    # Wikipedia et encyclopédies
    "wikipedia.org", "wikimedia.org",
    # Presse généraliste
    "lefigaro.fr", "lemonde.fr", "liberation.fr", "20minutes.fr",
    "bfmtv.com", "francetvinfo.fr",
})

# Patterns d'URL indiquant une page de résultats (pas une page d'entreprise)
RESULT_PAGE_PATTERNS = [
    r"linkedin\.com/(jobs|search|pub/dir|company-beta)",
    r"indeed\.com/(emplois|jobs|viewjob|q-|l-)",
    r"welcometothejungle\.com/(fr/jobs|jobs)",
    r"france\.travail\.gouv\.fr/offres/recherche",
    r"google\.(fr|com)/search",
    r"/search\?",
    r"/recherche\?",
    r"/emplois\?",
    r"/jobs\?",
    r"/offres\?",
    r"pagesjaunes\.fr/pros",
]

# =============================================================================
# Templates de queries par angle de recherche
# =============================================================================

QUERY_TEMPLATES: dict[str, list[str]] = {
    "tech_companies": [
        "entreprises informatique logiciel {city}",
        "éditeur logiciel {city}",
        "société tech {city}",
        "entreprise numérique {city}",
        "solutions informatiques {city} {dept}",
        "développement logiciel {city}",
    ],
    "esn_services": [
        "ESN {city}",
        "SSII informatique {city}",
        "société services informatiques {city}",
        "cabinet conseil IT {city}",
        "prestataire développement logiciel {city}",
        "bureau d'études informatique {city}",
    ],
    "startup_saas": [
        "startup tech {city}",
        "SaaS {city} Rhône",
        "scale-up tech {city}",
        "éditeur SaaS {city}",
    ],
    "job_angle": [
        "développeur C# .NET {city} emploi",
        "développeur web React TypeScript {city}",
        "poste développeur logiciel {city}",
        "offre emploi développeur informatique {city}",
    ],
}

# Ordre des angles selon la stratégie
ANGLES_BY_STRATEGY: dict[SearchType, list[str]] = {
    SearchType.FULL_DISCOVERY: [
        "tech_companies", "esn_services", "startup_saas", "job_angle"
    ],
    SearchType.FULL_DISCOVERY_REFRESH: [
        "tech_companies", "esn_services", "startup_saas", "job_angle"
    ],
    SearchType.MONITORING_PLUS_NEW: [
        "startup_saas", "job_angle", "tech_companies"  # angles plus susceptibles de révéler du nouveau
    ],
    SearchType.MONITORING_ONLY: [],  # pas de queries Apify, monitoring direct
}

# Villes du Rhône (69) — explorées progressivement par priorité
RHONE_CITIES: list[dict] = [
    # Tier 1 — zone urbaine Lyon
    {"city": "Lyon", "department": "69", "priority": 1},
    {"city": "Villeurbanne", "department": "69", "priority": 1},
    {"city": "Bron", "department": "69", "priority": 1},
    {"city": "Vénissieux", "department": "69", "priority": 1},
    {"city": "Saint-Priest", "department": "69", "priority": 1},
    # Tier 2 — proche banlieue
    {"city": "Caluire-et-Cuire", "department": "69", "priority": 2},
    {"city": "Écully", "department": "69", "priority": 2},
    {"city": "Dardilly", "department": "69", "priority": 2},
    {"city": "Tassin-la-Demi-Lune", "department": "69", "priority": 2},
    {"city": "Décines-Charpieu", "department": "69", "priority": 2},
    {"city": "Meyzieu", "department": "69", "priority": 2},
    {"city": "Genas", "department": "69", "priority": 2},
    {"city": "Corbas", "department": "69", "priority": 2},
    {"city": "Chassieu", "department": "69", "priority": 2},
    {"city": "Rillieux-la-Pape", "department": "69", "priority": 2},
    # Tier 3 — villes plus petites / périphérie
    {"city": "Brignais", "department": "69", "priority": 3},
    {"city": "Mions", "department": "69", "priority": 3},
    {"city": "Saint-Genis-Laval", "department": "69", "priority": 3},
    {"city": "Givors", "department": "69", "priority": 3},
    {"city": "Oullins", "department": "69", "priority": 3},
    {"city": "Pierre-Bénite", "department": "69", "priority": 3},
    {"city": "Craponne", "department": "69", "priority": 3},
    {"city": "Mornant", "department": "69", "priority": 3},
    # Tier 4 — hors Grand Lyon
    {"city": "Villefranche-sur-Saône", "department": "69", "priority": 4},
    {"city": "Tarare", "department": "69", "priority": 4},
    {"city": "L'Arbresle", "department": "69", "priority": 4},
    {"city": "Gleizé", "department": "69", "priority": 4},
    {"city": "Lentilly", "department": "69", "priority": 4},
    {"city": "Belleville-en-Beaujolais", "department": "69", "priority": 4},
]


# =============================================================================
# Dataclasses intermédiaires (staging — non persistées telles quelles)
# =============================================================================


@dataclass
class RawApifyResult:
    """
    Item brut retourné par l'acteur apify/rag-web-browser.
    Conservé pour audit, non modifié après construction.

    Champs mappés depuis la réponse réelle de l'acteur :
      url              ← item["url"]
      page_title       ← item["title"] ou item["metadata"]["title"]
      page_description ← item["description"] ou item["metadata"]["description"]
      page_content_markdown ← item["markdown"]
      serp_position    ← item["searchResult"]["position"]
      http_status      ← item["crawl"]["httpStatusCode"]
      loaded_url       ← item["crawl"]["loadedUrl"]
      language_code    ← item["metadata"]["languageCode"]
      raw_json         ← dump complet pour audit
    """
    url: str
    page_title: str
    page_description: Optional[str]
    page_content_markdown: Optional[str]
    serp_position: Optional[int]
    http_status: Optional[int]
    loaded_url: Optional[str]
    language_code: Optional[str]
    raw_json: dict


@dataclass
class CompanyCandidate:
    """
    Résultat intermédiaire après extraction et déduplication, avant envoi à Claude.
    Contient les données brutes Apify + inférences légères (heuristiques Python).

    Les champs `guessed_*` sont des heuristiques sans LLM.
    Claude (dans analysis.py) fera l'analyse définitive.
    """
    # Source brute
    source_url: str
    page_title: str
    page_description: Optional[str]
    page_content_markdown: Optional[str]

    # Inférences légères (heuristiques Python, sans LLM)
    guessed_name: Optional[str]
    guessed_domain: Optional[str]
    guessed_city: Optional[str]
    detected_language: Optional[str]

    # Contexte de découverte
    discovery_query: str
    city: str
    department: str
    apify_run_id: str
    serp_position: Optional[int]

    # État après déduplication
    is_known_company: bool = False
    known_company_id: Optional[int] = None
    needs_full_analysis: bool = True    # entreprise inconnue → analyse complète Claude
    needs_partial_refresh: bool = False  # entreprise connue mais données anciennes


@dataclass
class DiscoveryRunResult:
    """
    Résultat complet d'un run de discovery sur une ville.
    Retourné à agent.py pour orchestration de la suite (analysis.py).
    """
    city: str
    department: str
    search_type: SearchType
    apify_run_id: Optional[str]             # ID du premier run Apify (ou None si FAILED avant appel)

    queries_executed: list[str]
    raw_results: list[RawApifyResult]       # bruts, conservés pour audit
    candidates: list[CompanyCandidate]      # tous les candidats extraits (après filtre URL)
    new_candidates: list[CompanyCandidate]  # inconnus → à envoyer à Claude (full analysis)
    known_to_refresh: list[CompanyCandidate] # connus mais données anciennes → Claude partial

    companies_found_total: int = 0
    new_companies: int = 0
    duplicates_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    coverage_state: CoverageState = CoverageState.PARTIAL
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


# =============================================================================
# Point d'entrée principal
# =============================================================================


def run_city_discovery(
    city: str,
    department: str,
    apify_client: ApifyClient,
    db: DatabaseManager,
    conn: pyodbc.Connection,
    max_results_per_query: int = APIFY_MAX_RESULTS,
) -> DiscoveryRunResult:
    """
    Lance la discovery pour une ville.

    1. Consulte SearchHistory → décide de la stratégie
    2. Construit les queries adaptées à la stratégie
    3. Lance un run Apify par query
    4. Extrait et déduplique les candidats
    5. Enregistre dans SearchHistory
    6. Retourne DiscoveryRunResult (new_candidates prêts pour analysis.py)

    Cette fonction ne fait pas d'analyse Claude.
    Elle ne modifie pas la table Companies (c'est analysis.py qui le fait).
    """
    started_at = datetime.now(timezone.utc)
    logger.info("=== Discovery démarrée : %s (%s) ===", city, department)

    # Étape 1 — décision stratégique
    strategy = db.decide_search_strategy(conn, city, department)
    logger.info(
        "Stratégie : %s — %s", strategy.search_type.value, strategy.reason
    )

    result = DiscoveryRunResult(
        city=city,
        department=department,
        search_type=strategy.search_type,
        apify_run_id=None,
        queries_executed=[],
        raw_results=[],
        candidates=[],
        new_candidates=[],
        known_to_refresh=[],
        started_at=started_at,
    )

    # MONITORING_ONLY → pas de queries Apify, on sort immédiatement
    # (le monitoring des career pages est géré dans monitoring.py)
    if strategy.search_type == SearchType.MONITORING_ONLY:
        logger.info("MONITORING_ONLY — aucune requête Apify pour %s", city)
        result.coverage_state = CoverageState.COMPLETE
        result.finished_at = datetime.now(timezone.utc)
        _record_search(db, conn, result, strategy)
        return result

    # Étape 2 — construction des queries
    queries_already_used = strategy.suggested_queries  # remplacé ci-dessous si MONITORING_PLUS_NEW
    # On recharge les queries réellement utilisées depuis l'historique
    queries_already_used = _get_queries_already_used(conn, city, department)

    queries = build_queries(
        city=city,
        department=department,
        search_type=strategy.search_type,
        queries_already_used=queries_already_used,
    )

    if not queries:
        logger.warning("Aucune query générée pour %s — toutes déjà utilisées", city)
        result.coverage_state = CoverageState.COMPLETE
        result.finished_at = datetime.now(timezone.utc)
        _record_search(db, conn, result, strategy)
        return result

    logger.info("%d queries à exécuter pour %s", len(queries), city)

    # Étape 3 — exécution séquentielle des runs Apify
    all_raw: list[RawApifyResult] = []
    successful_queries: list[str] = []
    failed_queries: list[str] = []
    first_run_id: Optional[str] = None

    for i, query in enumerate(queries):
        logger.info("[%d/%d] Query : %r", i + 1, len(queries), query)
        try:
            run_id, raw_items = call_apify_one_query(
                query=query,
                apify_client=apify_client,
                max_results=max_results_per_query,
                use_browser=False,
            )
            if first_run_id is None:
                first_run_id = run_id
                result.apify_run_id = run_id

            all_raw.extend(raw_items)
            successful_queries.append(query)
            logger.info(
                "  → %d résultats bruts (run_id=%s)", len(raw_items), run_id
            )

        except Exception as exc:
            logger.error("  → Erreur Apify pour %r : %s", query, exc)
            failed_queries.append(query)
            result.errors.append(f"Query '{query}': {exc}")

        # Pause entre les runs pour éviter le rate limiting
        if i < len(queries) - 1:
            time.sleep(APIFY_PAUSE_BETWEEN_QUERIES)

    result.queries_executed = successful_queries
    result.raw_results = all_raw

    # Étape 4 — extraction des candidats depuis les résultats bruts
    all_candidates: list[CompanyCandidate] = []
    for raw in all_raw:
        candidate = _extract_candidate(raw, city, department)
        if candidate is not None:
            all_candidates.append(candidate)

    logger.info(
        "%d candidats extraits sur %d résultats bruts",
        len(all_candidates), len(all_raw)
    )

    # Étape 5 — déduplication intra-run (même domaine vu plusieurs fois)
    candidates_deduped = _dedup_intra_run(all_candidates)
    intra_run_dupes = len(all_candidates) - len(candidates_deduped)
    logger.info(
        "%d candidats après dédup intra-run (%d doublons intra-run ignorés)",
        len(candidates_deduped), intra_run_dupes
    )

    # Étape 6 — déduplication contre la base de données
    new_candidates, known_to_refresh, db_dupes = deduplicate_candidates(
        candidates=candidates_deduped,
        db=db,
        conn=conn,
    )
    result.duplicates_skipped = intra_run_dupes + db_dupes
    result.candidates = candidates_deduped
    result.new_candidates = new_candidates
    result.known_to_refresh = known_to_refresh
    result.companies_found_total = len(candidates_deduped)
    result.new_companies = len(new_candidates)

    logger.info(
        "Résumé %s : total=%d new=%d refresh=%d dupes_skipped=%d",
        city,
        result.companies_found_total,
        result.new_companies,
        len(known_to_refresh),
        result.duplicates_skipped,
    )

    # Étape 7 — détermination du coverage_state
    if not successful_queries:
        result.coverage_state = CoverageState.FAILED
    elif failed_queries:
        result.coverage_state = CoverageState.PARTIAL
    else:
        result.coverage_state = CoverageState.COMPLETE

    result.finished_at = datetime.now(timezone.utc)

    # Étape 8 — enregistrement dans SearchHistory
    _record_search(db, conn, result, strategy)

    logger.info(
        "=== Discovery terminée : %s — %s ===",
        city, result.coverage_state.value
    )
    return result


# =============================================================================
# Construction des queries
# =============================================================================


def build_queries(
    city: str,
    department: str,
    search_type: SearchType,
    queries_already_used: list[str],
    max_queries_per_angle: int = 2,
) -> list[str]:
    """
    Construit la liste de queries pour un run, selon la stratégie.

    FULL_DISCOVERY / FULL_DISCOVERY_REFRESH :
      → Sélectionne des templates dans chaque angle.
        Pour FULL_DISCOVERY : templates NON encore utilisés en priorité.
        Pour FULL_DISCOVERY_REFRESH : utilise TOUS les templates.

    MONITORING_PLUS_NEW :
      → Utilise uniquement les templates pas encore utilisés.

    MONITORING_ONLY :
      → Retourne [] (géré avant cet appel).
    """
    angles = ANGLES_BY_STRATEGY.get(search_type, [])
    used_lower = {q.lower() for q in queries_already_used}
    is_refresh = search_type == SearchType.FULL_DISCOVERY_REFRESH

    selected: list[str] = []

    for angle in angles:
        templates = QUERY_TEMPLATES.get(angle, [])
        angle_queries: list[str] = []

        for tmpl in templates:
            query = tmpl.format(city=city, dept=department)
            if is_refresh or query.lower() not in used_lower:
                angle_queries.append(query)
            if len(angle_queries) >= max_queries_per_angle:
                break

        selected.extend(angle_queries)

    return selected


# =============================================================================
# Appel Apify
# =============================================================================


def call_apify_one_query(
    query: str,
    apify_client: ApifyClient,
    max_results: int = APIFY_MAX_RESULTS,
    use_browser: bool = False,
) -> tuple[str, list[RawApifyResult]]:
    """
    Lance un run Apify pour une query et retourne (run_id, résultats).

    Utilise uniquement les champs réellement disponibles dans la réponse :
      url, title, description, markdown, metadata, searchResult, crawl

    Lève une exception en cas d'erreur Apify (gérée par l'appelant).
    """
    run_input = {
        "query": query,
        "maxResults": max_results,
        "outputFormats": ["markdown"],
        "scrapingTool": "browser-playwright" if use_browser else "raw-http",
        "requestTimeoutSecs": APIFY_TIMEOUT_SECS,
        "removeCookieWarnings": True,
    }

    run = apify_client.actor(APIFY_ACTOR_ID).call(run_input=run_input)
    run_id: str = run.get("id", "unknown")
    dataset_id: str = run["defaultDatasetId"]

    items_page = apify_client.dataset(dataset_id).list_items()
    raw_results: list[RawApifyResult] = []

    for item in (items_page.items or []):
        # Extraction des champs avec fallbacks selon la structure réelle de l'acteur
        metadata: dict = item.get("metadata") or {}
        search_result: dict = item.get("searchResult") or {}
        crawl: dict = item.get("crawl") or {}

        url: str = item.get("url") or crawl.get("loadedUrl") or ""
        if not url:
            continue  # item sans URL → ignoré

        raw = RawApifyResult(
            url=url,
            page_title=(
                item.get("title")
                or metadata.get("title")
                or search_result.get("title")
                or ""
            ),
            page_description=(
                item.get("description")
                or metadata.get("description")
                or search_result.get("description")
            ),
            page_content_markdown=item.get("markdown"),
            serp_position=search_result.get("position"),
            http_status=crawl.get("httpStatusCode"),
            loaded_url=crawl.get("loadedUrl"),
            language_code=metadata.get("languageCode"),
            raw_json=item,  # conservé intégralement pour audit
        )
        raw_results.append(raw)

    return run_id, raw_results


# =============================================================================
# Extraction d'un candidat depuis un résultat brut
# =============================================================================


def _extract_candidate(
    raw: RawApifyResult,
    city: str,
    department: str,
    discovery_query: str = "",
    apify_run_id: str = "",
) -> Optional[CompanyCandidate]:
    """
    Tente d'extraire un CompanyCandidate depuis un RawApifyResult.

    Retourne None si l'URL est un agrégateur, une page de résultats,
    ou si on n'a pas assez d'informations pour identifier une entreprise.

    Aucune logique LLM ici — uniquement des heuristiques Python.
    """
    url = raw.url or raw.loaded_url or ""
    if not url:
        return None

    # Filtre agrégateur / page de résultats
    if _is_aggregator_or_results_page(url):
        logger.debug("  Ignoré (agrégateur) : %s", url)
        return None

    # Filtre HTTP : on ne traite pas les pages en erreur
    if raw.http_status and raw.http_status >= 400:
        logger.debug("  Ignoré (HTTP %d) : %s", raw.http_status, url)
        return None

    domain = _extract_domain(url)
    guessed_name = _guess_company_name(raw.page_title, url)

    # Si on n'a ni nom ni domaine, on ne peut pas identifier l'entreprise
    if not guessed_name and not domain:
        return None

    return CompanyCandidate(
        source_url=url,
        page_title=raw.page_title,
        page_description=raw.page_description,
        page_content_markdown=raw.page_content_markdown,
        guessed_name=guessed_name,
        guessed_domain=domain,
        guessed_city=city,  # ville de recherche — Claude peut affiner
        detected_language=raw.language_code,
        discovery_query=discovery_query,
        city=city,
        department=department,
        apify_run_id=apify_run_id,
        serp_position=raw.serp_position,
    )


def extract_candidates(
    raw_results: list[RawApifyResult],
    query: str,
    city: str,
    department: str,
    apify_run_id: str,
) -> list[CompanyCandidate]:
    """
    Applique _extract_candidate sur une liste de RawApifyResult.
    Exposée publiquement pour les tests.
    """
    candidates = []
    for raw in raw_results:
        candidate = _extract_candidate(raw, city, department, query, apify_run_id)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


# =============================================================================
# Déduplication
# =============================================================================


def _dedup_intra_run(
    candidates: list[CompanyCandidate],
) -> list[CompanyCandidate]:
    """
    Déduplique les candidats du run actuel par domain.
    Si plusieurs résultats pointent vers le même domaine,
    on garde celui qui a le plus de contenu markdown.
    """
    seen_domains: dict[str, CompanyCandidate] = {}
    no_domain: list[CompanyCandidate] = []

    for c in candidates:
        if not c.guessed_domain:
            no_domain.append(c)
            continue

        if c.guessed_domain not in seen_domains:
            seen_domains[c.guessed_domain] = c
        else:
            # Garde le candidat avec le plus de contenu
            existing = seen_domains[c.guessed_domain]
            existing_len = len(existing.page_content_markdown or "")
            current_len = len(c.page_content_markdown or "")
            if current_len > existing_len:
                seen_domains[c.guessed_domain] = c

    return list(seen_domains.values()) + no_domain


def deduplicate_candidates(
    candidates: list[CompanyCandidate],
    db: DatabaseManager,
    conn: pyodbc.Connection,
) -> tuple[list[CompanyCandidate], list[CompanyCandidate], int]:
    """
    Compare les candidats contre la base de données.

    Retourne :
      (new_candidates, known_to_refresh, nb_db_dupes_skipped)

    Logique par candidat :
      1. Cherche par domain dans Companies
      2. Cherche par NormalizedName + City si pas de domain
      3. Si trouvé :
         - LastResearchedAt < 30 j → skip (données fraîches)
         - LastResearchedAt entre 30 et 90 j → partial refresh
         - LastResearchedAt > 90 j ou NULL → full analysis
      4. Si pas trouvé → full analysis
    """
    from datetime import timedelta
    import unicodedata

    new_candidates: list[CompanyCandidate] = []
    known_to_refresh: list[CompanyCandidate] = []
    db_dupes_skipped = 0

    now = datetime.now(timezone.utc)
    cursor = conn.cursor()

    for candidate in candidates:
        existing_id, last_researched = _find_in_db(cursor, candidate)

        if existing_id is None:
            # Entreprise inconnue → analyse complète Claude
            candidate.is_known_company = False
            candidate.needs_full_analysis = True
            new_candidates.append(candidate)
            continue

        # Entreprise connue
        candidate.is_known_company = True
        candidate.known_company_id = existing_id

        if last_researched is None:
            # Connue mais jamais vraiment analysée → full analysis
            candidate.needs_full_analysis = True
            known_to_refresh.append(candidate)
            continue

        # S'assurer que last_researched est tz-aware
        if last_researched.tzinfo is None:
            last_researched = last_researched.replace(tzinfo=timezone.utc)

        age_days = (now - last_researched).days

        if age_days < REFRESH_PARTIAL_AFTER_DAYS:
            # Données fraîches → skip
            logger.debug(
                "  Skip (données fraîches, %d j) : %s",
                age_days, candidate.guessed_domain
            )
            db_dupes_skipped += 1
            continue

        elif age_days < REFRESH_FULL_ANALYSIS_AFTER_DAYS:
            # Données un peu datées → refresh partiel
            candidate.needs_full_analysis = False
            candidate.needs_partial_refresh = True
            known_to_refresh.append(candidate)

        else:
            # Données trop anciennes → full analysis
            candidate.needs_full_analysis = True
            candidate.needs_partial_refresh = False
            known_to_refresh.append(candidate)

    return new_candidates, known_to_refresh, db_dupes_skipped


def _find_in_db(
    cursor: pyodbc.Cursor,
    candidate: CompanyCandidate,
) -> tuple[Optional[int], Optional[datetime]]:
    """
    Cherche l'entreprise dans la base.
    Retourne (company_id, last_researched_at) ou (None, None).
    """
    # 1. Par domain
    if candidate.guessed_domain:
        cursor.execute(
            "SELECT Id, LastResearchedAt FROM research.Companies WHERE Domain = ?",
            candidate.guessed_domain,
        )
        row = cursor.fetchone()
        if row:
            return row[0], row[1]

    # 2. Par NormalizedName + City
    if candidate.guessed_name and candidate.city:
        normalized = _normalize_text(candidate.guessed_name)
        cursor.execute(
            """
            SELECT Id, LastResearchedAt FROM research.Companies
            WHERE NormalizedName = ? AND City = ?
            """,
            normalized,
            candidate.city,
        )
        row = cursor.fetchone()
        if row:
            return row[0], row[1]

    return None, None


# =============================================================================
# Enregistrement dans SearchHistory
# =============================================================================


def _record_search(
    db: DatabaseManager,
    conn: pyodbc.Connection,
    result: DiscoveryRunResult,
    strategy: SearchDecision,
) -> None:
    """Enregistre le résultat du run dans SearchHistory."""
    record = SearchRecord(
        geography=f"{result.city}, {result.department}",
        city=result.city,
        department=result.department,
        search_type=result.search_type,
        queries_used=result.queries_executed,
        sources_checked=["apify/rag-web-browser"],
        apify_run_id=result.apify_run_id,
        companies_found=result.companies_found_total,
        new_companies=result.new_companies,
        duplicates_found=result.duplicates_skipped,
        jobs_found=0,      # jobs traités dans job_search.py
        new_jobs=0,
        coverage_state=result.coverage_state,
        notes=_build_search_notes(result),
    )
    try:
        db.record_search(conn, record)
        logger.debug("SearchHistory enregistré pour %s", result.city)
    except Exception as exc:
        # Ne pas faire échouer le run pour un problème d'historique
        logger.error("Échec enregistrement SearchHistory : %s", exc)


def _build_search_notes(result: DiscoveryRunResult) -> Optional[str]:
    """Construit les notes de résumé pour SearchHistory."""
    parts = []
    if result.errors:
        parts.append(f"Erreurs : {'; '.join(result.errors)}")
    if result.coverage_state == CoverageState.PARTIAL:
        parts.append(
            f"{len(result.queries_executed)}/{len(result.queries_executed) + len(result.errors)} "
            f"queries réussies"
        )
    return " | ".join(parts) if parts else None


# =============================================================================
# Utilitaires privés
# =============================================================================


def _is_aggregator_or_results_page(url: str) -> bool:
    """
    Retourne True si l'URL est un agrégateur, annuaire ou page de résultats.
    Ces URLs ne correspondent pas à une page d'entreprise directe.
    """
    parsed = urllib.parse.urlparse(url.lower())
    domain = parsed.netloc.lstrip("www.")

    # Vérification domaine agrégateur connu
    if domain in AGGREGATOR_DOMAINS:
        return True

    # Vérification pattern de page de résultats
    full_url_lower = url.lower()
    for pattern in RESULT_PAGE_PATTERNS:
        if re.search(pattern, full_url_lower):
            return True

    return False


def _extract_domain(url: str) -> Optional[str]:
    """
    Extrait le domaine depuis une URL.
    Exemples :
      "https://www.inova.fr/solutions" → "inova.fr"
      "https://linkedin.com/company/acme" → "linkedin.com"
    """
    if not url:
        return None
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        # Supprimer www. et port éventuel
        netloc = re.sub(r"^www\.", "", netloc)
        netloc = re.sub(r":\d+$", "", netloc)
        return netloc if netloc else None
    except Exception:
        return None


def _guess_company_name(title: str, url: str) -> Optional[str]:
    """
    Tente d'inférer le nom de l'entreprise depuis le titre de la page.

    Stratégie :
      1. Prend la partie avant le premier séparateur (|, -, –, :, »)
      2. Nettoie les suffixes courants ("Accueil", "Home", "Site officiel", etc.)
      3. Si le résultat est vide ou trop court → essaie le domaine

    Cette inférence est légère et peut être fausse.
    Claude (analysis.py) fera la validation définitive.
    """
    if not title:
        return _name_from_domain(url)

    # Sépare sur les délimiteurs courants
    for sep in [" | ", " - ", " – ", " — ", " : ", " » "]:
        if sep in title:
            candidate = title.split(sep)[0].strip()
            if len(candidate) >= 2:
                cleaned = _clean_company_name(candidate)
                if cleaned:
                    return cleaned

    # Si pas de séparateur, utilise le titre entier (nettoyé)
    cleaned = _clean_company_name(title)
    if cleaned and len(cleaned) >= 2:
        return cleaned

    # Fallback : domaine
    return _name_from_domain(url)


def _clean_company_name(name: str) -> Optional[str]:
    """Supprime les suffixes génériques courants d'un nom."""
    GENERIC_SUFFIXES = [
        "accueil", "home", "site officiel", "bienvenue", "welcome",
        "page d'accueil", "nos solutions", "solutions", "services",
        "à propos", "about us", "contact",
    ]
    cleaned = name.strip()
    cleaned_lower = cleaned.lower()

    for suffix in GENERIC_SUFFIXES:
        if cleaned_lower == suffix:
            return None  # le titre ENTIER est générique

    # Trop court ou trop long → peu fiable
    if len(cleaned) < 2 or len(cleaned) > 80:
        return None

    return cleaned


def _name_from_domain(url: str) -> Optional[str]:
    """Extrait un nom approximatif depuis le domaine."""
    domain = _extract_domain(url)
    if not domain:
        return None
    # Prend la partie avant le TLD (.fr, .com, .io, etc.)
    parts = domain.split(".")
    if len(parts) >= 2:
        name = parts[-2]  # ex. "inova" depuis "inova.fr"
        if len(name) >= 2:
            return name.capitalize()
    return None


def _normalize_text(text: str) -> str:
    """Normalise un texte pour la comparaison (lower, sans accents, strip)."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text)
    return nfkd.encode("ascii", "ignore").decode("ascii").lower().strip()


def _get_queries_already_used(
    conn: pyodbc.Connection,
    city: str,
    department: str,
) -> list[str]:
    """
    Récupère toutes les queries déjà utilisées pour une ville depuis SearchHistory.
    Utilisé pour éviter de relancer exactement les mêmes recherches.
    """
    import json
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT QueriesUsed
        FROM research.SearchHistory
        WHERE City = ? AND Department = ? AND CoverageState = 'COMPLETE'
        ORDER BY SearchedAt DESC
        """,
        city,
        department,
    )
    all_queries: list[str] = []
    for row in cursor.fetchall():
        try:
            queries = json.loads(row[0] or "[]")
            all_queries.extend(queries)
        except (json.JSONDecodeError, TypeError):
            pass
    return all_queries


# =============================================================================
# Helpers pour orchestration externe (agent.py)
# =============================================================================


def get_rhone_cities_by_priority() -> list[dict]:
    """
    Retourne la liste des villes du Rhône triées par priorité.
    Utilisé par agent.py pour décider quelle ville explorer ensuite.
    """
    return sorted(RHONE_CITIES, key=lambda c: c["priority"])


def get_next_city_to_discover(
    db: DatabaseManager,
    conn: pyodbc.Connection,
    department: str = "69",
) -> Optional[dict]:
    """
    Retourne la prochaine ville à explorer en tenant compte du SearchHistory.

    Priorité :
      1. Villes sans historique (jamais explorées), par tier
      2. Villes avec dernière recherche PARTIAL ou FAILED
      3. Villes avec recherche COMPLETE la plus ancienne (si > MONITORING_PLUS_NEW_DAYS)
    """
    covered = {
        row["city"].lower(): row
        for row in db.get_covered_cities(conn, department)
    }

    cities_by_priority = get_rhone_cities_by_priority()

    # Passe 1 : villes jamais explorées
    for city_conf in cities_by_priority:
        if city_conf["city"].lower() not in covered:
            return city_conf

    # Passe 2 : villes en PARTIAL ou FAILED
    for city_conf in cities_by_priority:
        city_lower = city_conf["city"].lower()
        if city_lower in covered and not covered[city_lower]["has_complete"]:
            return city_conf

    # Passe 3 : ville avec la recherche COMPLETE la plus ancienne
    oldest = None
    oldest_date = None
    for city_conf in cities_by_priority:
        city_lower = city_conf["city"].lower()
        if city_lower in covered:
            last_at = covered[city_lower]["last_search_at"]
            if oldest_date is None or last_at < oldest_date:
                oldest_date = last_at
                oldest = city_conf

    return oldest
