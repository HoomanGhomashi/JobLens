"""
JobLens Agent — Modèles de données
====================================
Dataclasses Python correspondant aux tables SQL Server.

Règles métier rappelées ici :
  • IsActiveOpportunity est RECALCULÉ à l'exécution, jamais lu depuis la DB
    comme source de vérité finale. La méthode `is_currently_active()` incarne
    cette règle.
  • AgeAtDiscoveryDays = info historique uniquement.
  • PublishedAt = None si inconnue. JAMAIS inventée.
  • Status (Job) ≠ IsActiveOpportunity — deux concepts distincts.
  • JuniorHiringSignal = signal actuel / HiringHistorySignal = pattern historique.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# =============================================================================
# Enums
# =============================================================================


class CompanyStatus(str, Enum):
    ACTIVE_RELEVANT = "ACTIVE_RELEVANT"
    MONITOR = "MONITOR"
    POTENTIALLY_RELEVANT = "POTENTIALLY_RELEVANT"
    LOW_PRIORITY = "LOW_PRIORITY"
    NOT_RELEVANT = "NOT_RELEVANT"


class HiringSignal(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class FrenchLanguageSignal(str, Enum):
    YES = "YES"
    MIXED = "MIXED"
    ENGLISH_ONLY = "ENGLISH_ONLY"
    UNKNOWN = "UNKNOWN"


class ContractType(str, Enum):
    CDI = "CDI"
    CDD = "CDD"
    ALTERNANCE = "Alternance"
    STAGE = "Stage"
    FREELANCE = "Freelance"
    INCONNU = "Inconnu"

    @property
    def can_be_active_opportunity(self) -> bool:
        """Seuls CDI et CDD peuvent satisfaire le HARD FILTER IsActiveOpportunity."""
        return self in (ContractType.CDI, ContractType.CDD)


class JobStatus(str, Enum):
    """État réel de l'offre sur la plateforme source."""
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class MatchResult(str, Enum):
    MATCH = "MATCH"
    BORDERLINE = "BORDERLINE"
    REJECT = "REJECT"
    UNKNOWN = "UNKNOWN"


class SearchType(str, Enum):
    FULL_DISCOVERY = "FULL_DISCOVERY"
    MONITORING_ONLY = "MONITORING_ONLY"
    MONITORING_PLUS_NEW = "MONITORING_PLUS_NEW"
    FULL_DISCOVERY_REFRESH = "FULL_DISCOVERY_REFRESH"


class CoverageState(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class JobSource(str, Enum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    WTTJ = "wttj"
    FRANCE_TRAVAIL = "france_travail"
    COMPANY = "company"
    OTHER = "other"


# =============================================================================
# Company
# =============================================================================


@dataclass
class Company:
    """
    Entreprise découverte et monitorée.
    Persiste indéfiniment, même sans offre active.
    """
    # Clé
    id: Optional[int] = None

    # Identité
    name: str = ""
    normalized_name: Optional[str] = None      # lower, sans accents — pour dedup
    domain: Optional[str] = None               # ex. "accenture.com" (UNIQUE)
    website: Optional[str] = None
    careers_url: Optional[str] = None

    # Localisation
    city: Optional[str] = None
    department: Optional[str] = None           # ex. "Rhône", "69"
    country: str = "France"

    # Profil
    company_type: Optional[str] = None         # PME|ETI|Grande entreprise|Startup|ESN|Éditeur
    sector: Optional[str] = None

    # Données observées
    technologies_observed: list[str] = field(default_factory=list)
    developer_roles_observed: list[str] = field(default_factory=list)

    # Signaux de recrutement
    junior_hiring_signal: HiringSignal = HiringSignal.UNKNOWN
    hiring_history_signal: HiringSignal = HiringSignal.UNKNOWN
    french_language_signal: FrenchLanguageSignal = FrenchLanguageSignal.UNKNOWN

    # Candidature
    accepts_spontaneous: Optional[bool] = None

    # Pertinence
    status: CompanyStatus = CompanyStatus.MONITOR
    relevance_reason: Optional[str] = None
    source_urls: list[str] = field(default_factory=list)
    notes: Optional[str] = None

    # Horodatages
    first_discovered_at: Optional[datetime] = None
    last_researched_at: Optional[datetime] = None
    last_job_check_at: Optional[datetime] = None
    last_relevant_vacancy_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def normalize(self) -> None:
        """Calcule NormalizedName pour la déduplication."""
        import unicodedata
        if self.name:
            nfkd = unicodedata.normalize("NFKD", self.name)
            ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
            self.normalized_name = ascii_name.lower().strip()


# =============================================================================
# Job (offre logique — dédupliquée inter-sources)
# =============================================================================


@dataclass
class Job:
    """
    Offre d'emploi logique.
    Un même poste sur LinkedIn + Indeed + site entreprise = 1 seul Job
    avec plusieurs JobSourceEntry dans `sources`.

    IMPORTANT — IsActiveOpportunity :
      Ne jamais utiliser la valeur stockée comme source de vérité finale.
      Appeler `is_currently_active()` à chaque exécution de l'agent.
    """
    # Clé
    id: Optional[int] = None
    company_id: Optional[int] = None

    # Description
    title: Optional[str] = None
    city: Optional[str] = None
    country: str = "France"

    # Date de publication
    # published_at  : datetime réel extrait. None si inconnu. JAMAIS inventé.
    # published_at_raw : chaîne brute ("il y a 3 jours", "01/09/2026", "Hier")
    # age_at_discovery_days : âge au moment de la DÉCOUVERTE — historique uniquement
    published_at: Optional[datetime] = None
    published_at_raw: Optional[str] = None
    age_at_discovery_days: Optional[int] = None

    # Contrat
    contract_type: ContractType = ContractType.INCONNU

    # Expérience — extraite du texte, jamais inventée
    experience_raw: Optional[str] = None
    experience_min_years: Optional[int] = None
    experience_max_years: Optional[int] = None

    # Compétences
    technologies: list[str] = field(default_factory=list)
    language_requirement: Optional[str] = None    # FR|EN|FR+EN|Inconnu

    # Contenu
    description: Optional[str] = None
    salary_raw: Optional[str] = None

    # Évaluation
    match_result: MatchResult = MatchResult.UNKNOWN
    match_reason: Optional[str] = None

    # État
    # status              = état réel de l'offre sur la plateforme source
    # is_active_opportunity = cache runtime, recalculé à chaque passage
    status: JobStatus = JobStatus.UNKNOWN
    is_active_opportunity: bool = False       # cache — voir is_currently_active()

    # Horodatages
    first_discovered_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    # Sources (non persisté directement dans Jobs — dans JobSources)
    sources: list[JobSourceEntry] = field(default_factory=list)

    def is_currently_active(self, reference_dt: Optional[datetime] = None) -> bool:
        """
        HARD FILTERS pour IsActiveOpportunity — recalcul à chaque exécution.

        Conditions TOUTES requises :
          1. ContractType IN (CDI, CDD)
          2. PublishedAt IS NOT NULL
          3. (reference_dt - PublishedAt) <= 20 jours
          4. Au moins une source avec UrlVerified=True ET UrlReliable=True

        Si PublishedAt est inconnu → False sans exception (jamais estimé).
        """
        if not self.contract_type.can_be_active_opportunity:
            return False

        if self.published_at is None:
            return False

        ref = reference_dt or datetime.now(timezone.utc)
        # S'assurer que les deux datetime sont tz-aware pour la comparaison
        pub = self.published_at
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)

        age_days = (ref - pub).days
        if age_days > 20:
            return False

        has_verified_url = any(
            s.url_verified and s.url_reliable
            for s in self.sources
        )
        return has_verified_url

    @property
    def best_source_url(self) -> Optional[str]:
        """Retourne la meilleure URL vérifiée disponible."""
        # Priorité : URL vérifiée + fiable, site entreprise en premier
        for src in self.sources:
            if src.url_verified and src.url_reliable and src.source == JobSource.COMPANY:
                return src.source_url
        for src in self.sources:
            if src.url_verified and src.url_reliable:
                return src.source_url
        # Fallback : première URL disponible
        for src in self.sources:
            if src.source_url:
                return src.source_url
        return None


# =============================================================================
# JobSourceEntry (une URL par source)
# =============================================================================


@dataclass
class JobSourceEntry:
    """
    Une URL source pour un Job logique.

    Responsabilités :
      • Apify     : récupère l'URL candidate + contenu de la page
      • Claude    : valide sémantiquement (url_verified, url_reliable)

    Ne jamais reconstruire ou inventer une URL.
    Ne jamais utiliser comme URL finale :
      - page de résultats Google/LinkedIn/Indeed
      - homepage d'entreprise (si une URL directe existe)
      - URL générée/reconstituée
    """
    id: Optional[int] = None
    job_id: Optional[int] = None

    source: JobSource = JobSource.OTHER
    source_job_id: Optional[str] = None       # ID interne de la source (ex. ID LinkedIn)
    source_url: Optional[str] = None          # URL directe vers la page de détail

    # Validation par Claude
    # url_verified : Claude a confirmé que la page est bien une page de détail d'offre
    # url_reliable : l'URL est stable, accessible, non expirée
    url_verified: bool = False
    url_reliable: bool = False

    # Données brutes retournées par Apify
    page_title: Optional[str] = None
    page_content: Optional[str] = None

    # Horodatages
    discovered_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None    # quand Claude a validé


# =============================================================================
# SearchRecord (historique des recherches)
# =============================================================================


@dataclass
class SearchRecord:
    """
    Enregistrement d'une recherche dans l'historique.

    Utilisé par l'agent AVANT chaque run pour décider :
      • Quelle stratégie adopter (FULL_DISCOVERY / MONITORING_ONLY / etc.)
      • Quelles villes ont déjà été explorées et quand
      • Quelles queries ont été utilisées
      • Si une relance est nécessaire (PARTIAL/FAILED = relance prioritaire)
    """
    id: Optional[int] = None

    geography: Optional[str] = None           # ex. "Rhône", "Lyon"
    city: Optional[str] = None
    department: Optional[str] = None          # ex. "69"

    search_type: SearchType = SearchType.FULL_DISCOVERY
    queries_used: list[str] = field(default_factory=list)
    sources_checked: list[str] = field(default_factory=list)

    apify_run_id: Optional[str] = None

    companies_found: int = 0
    new_companies: int = 0
    duplicates_found: int = 0
    jobs_found: int = 0
    new_jobs: int = 0

    coverage_state: CoverageState = CoverageState.PARTIAL
    notes: Optional[str] = None
    searched_at: Optional[datetime] = None


# =============================================================================
# SearchDecision (résultat de l'analyse SearchHistory)
# =============================================================================


@dataclass
class SearchDecision:
    """
    Décision prise par l'agent après analyse du SearchHistory.
    Détermine comment procéder pour une zone géographique donnée.
    """
    geography: str
    city: Optional[str]

    search_type: SearchType
    reason: str

    # Queries à lancer (nouvelles ou supplémentaires)
    suggested_queries: list[str] = field(default_factory=list)
    suggested_sources: list[str] = field(default_factory=list)

    # Context
    last_search_at: Optional[datetime] = None
    last_coverage_state: Optional[CoverageState] = None
    days_since_last_search: Optional[int] = None
