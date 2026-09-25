"""
JobLens Agent — Couche d'accès base de données (SQL Server / pyodbc)
======================================================================
Opérations CRUD, déduplication Jobs/Companies, logique SearchHistory.

Conventions :
  • Toutes les méthodes publiques prennent/retournent des dataclasses de models.py
  • Pas de logique métier ici — seulement persistence et requêtes
  • IsActiveOpportunity est RECALCULÉ en base via une expression SQL,
    jamais lu comme source de vérité depuis Python (cohérence garantie)
  • Les JSON arrays (technologies, queries, etc.) sont sérialisés/désérialisés
    automatiquement
"""

from __future__ import annotations

import json
import logging
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, Optional

import pyodbc

from models import (
    Company,
    CompanyStatus,
    CoverageState,
    FrenchLanguageSignal,
    HiringSignal,
    Job,
    JobSource,
    JobSourceEntry,
    JobStatus,
    ContractType,
    MatchResult,
    SearchDecision,
    SearchRecord,
    SearchType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

ACTIVE_OPPORTUNITY_MAX_DAYS = 20

# Seuils pour décider du type de recherche à partir du SearchHistory
FULL_DISCOVERY_REFRESH_DAYS = 90   # relance complète après 90 jours
MONITORING_PLUS_NEW_DAYS = 30      # monitoring + nouvelles entreprises après 30 jours


# =============================================================================
# DatabaseManager
# =============================================================================


class DatabaseManager:
    """
    Point d'entrée unique pour toutes les opérations SQL Server.

    Usage :
        db = DatabaseManager(connection_string)
        with db.connection() as conn:
            company = db.upsert_company(conn, company_data)
    """

    def __init__(self, connection_string: str) -> None:
        self._conn_str = connection_string

    @contextmanager
    def connection(self) -> Generator[pyodbc.Connection, None, None]:
        """Gestionnaire de contexte : connexion SQL Server avec autocommit désactivé."""
        conn = pyodbc.connect(self._conn_str, autocommit=False)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # =========================================================================
    # Companies
    # =========================================================================

    def upsert_company(self, conn: pyodbc.Connection, company: Company) -> Company:
        """
        Insère ou met à jour une entreprise.

        Stratégie de déduplication (dans l'ordre) :
          1. domain (UNIQUE) — le plus fiable
          2. normalized_name + city — fallback si pas de domain

        Retourne la Company avec son Id renseigné.
        """
        company.normalize()
        cursor = conn.cursor()

        existing_id = self._find_existing_company(cursor, company)

        if existing_id is not None:
            company.id = existing_id
            self._update_company(cursor, company)
            logger.debug("Company updated: id=%d name=%s", existing_id, company.name)
        else:
            company.id = self._insert_company(cursor, company)
            logger.debug("Company inserted: id=%d name=%s", company.id, company.name)

        return company

    def _find_existing_company(
        self, cursor: pyodbc.Cursor, company: Company
    ) -> Optional[int]:
        # 1. Par domain
        if company.domain:
            cursor.execute(
                "SELECT Id FROM research.Companies WHERE Domain = ?", company.domain
            )
            row = cursor.fetchone()
            if row:
                return row[0]

        # 2. Par normalized_name + city
        if company.normalized_name and company.city:
            cursor.execute(
                """
                SELECT Id FROM research.Companies
                WHERE NormalizedName = ? AND City = ?
                """,
                company.normalized_name,
                company.city,
            )
            row = cursor.fetchone()
            if row:
                return row[0]

        return None

    def _insert_company(self, cursor: pyodbc.Cursor, company: Company) -> int:
        cursor.execute(
            """
            INSERT INTO research.Companies (
                Name, NormalizedName, Domain, Website, CareersUrl,
                City, Department, Country,
                CompanyType, Sector,
                TechnologiesObserved, DeveloperRolesObserved,
                JuniorHiringSignal, HiringHistorySignal, FrenchLanguageSignal,
                AcceptsSpontaneous,
                Status, RelevanceReason, SourceUrls, Notes,
                FirstDiscoveredAt, LastResearchedAt, LastJobCheckAt, LastRelevantVacancyAt,
                CreatedAt, UpdatedAt
            ) VALUES (
                ?,?,?,?,?,
                ?,?,?,
                ?,?,
                ?,?,
                ?,?,?,
                ?,
                ?,?,?,?,
                ?,?,?,?,
                GETUTCDATE(), GETUTCDATE()
            );
            SELECT SCOPE_IDENTITY();
            """,
            company.name,
            company.normalized_name,
            company.domain,
            company.website,
            company.careers_url,
            company.city,
            company.department,
            company.country,
            company.company_type,
            company.sector,
            _json_dumps(company.technologies_observed),
            _json_dumps(company.developer_roles_observed),
            company.junior_hiring_signal.value,
            company.hiring_history_signal.value,
            company.french_language_signal.value,
            _bool_to_bit(company.accepts_spontaneous),
            company.status.value,
            company.relevance_reason,
            _json_dumps(company.source_urls),
            company.notes,
            _utc_now(),
            None,
            None,
            None,
        )
        row = cursor.fetchone()
        return int(row[0])

    def _update_company(self, cursor: pyodbc.Cursor, company: Company) -> None:
        """
        Mise à jour sélective : on ne régresse jamais un signal.
        Ex. HiringHistorySignal = HIGH ne repasse pas à UNKNOWN.
        """
        cursor.execute(
            """
            UPDATE research.Companies SET
                Name                   = ?,
                NormalizedName         = ?,
                Domain                 = COALESCE(Domain, ?),
                Website                = COALESCE(?, Website),
                CareersUrl             = COALESCE(?, CareersUrl),
                City                   = COALESCE(?, City),
                Department             = COALESCE(?, Department),
                CompanyType            = COALESCE(?, CompanyType),
                Sector                 = COALESCE(?, Sector),
                TechnologiesObserved   = ?,
                DeveloperRolesObserved = ?,
                -- Ne pas régresser les signaux (HIGH/MEDIUM ne repassent pas à UNKNOWN)
                JuniorHiringSignal     = CASE
                    WHEN JuniorHiringSignal = 'HIGH' THEN JuniorHiringSignal
                    WHEN ? = 'HIGH' THEN ?
                    WHEN JuniorHiringSignal = 'MEDIUM' THEN JuniorHiringSignal
                    WHEN ? = 'MEDIUM' THEN ?
                    ELSE COALESCE(?, JuniorHiringSignal)
                END,
                HiringHistorySignal    = CASE
                    WHEN HiringHistorySignal = 'HIGH' THEN HiringHistorySignal
                    WHEN ? = 'HIGH' THEN ?
                    WHEN HiringHistorySignal = 'MEDIUM' THEN HiringHistorySignal
                    WHEN ? = 'MEDIUM' THEN ?
                    ELSE COALESCE(?, HiringHistorySignal)
                END,
                FrenchLanguageSignal   = COALESCE(?, FrenchLanguageSignal),
                AcceptsSpontaneous     = COALESCE(?, AcceptsSpontaneous),
                Status                 = ?,
                RelevanceReason        = COALESCE(?, RelevanceReason),
                Notes                  = COALESCE(?, Notes),
                LastResearchedAt       = GETUTCDATE(),
                UpdatedAt              = GETUTCDATE()
            WHERE Id = ?
            """,
            # Name, NormalizedName
            company.name,
            company.normalized_name,
            # Domain, Website, CareersUrl, City, Department
            company.domain,
            company.website,
            company.careers_url,
            company.city,
            company.department,
            # CompanyType, Sector
            company.company_type,
            company.sector,
            # Technologies, Roles
            _json_dumps(company.technologies_observed),
            _json_dumps(company.developer_roles_observed),
            # JuniorHiringSignal (6 params pour le CASE)
            company.junior_hiring_signal.value,
            company.junior_hiring_signal.value,
            company.junior_hiring_signal.value,
            company.junior_hiring_signal.value,
            company.junior_hiring_signal.value,
            # HiringHistorySignal (6 params pour le CASE)
            company.hiring_history_signal.value,
            company.hiring_history_signal.value,
            company.hiring_history_signal.value,
            company.hiring_history_signal.value,
            company.hiring_history_signal.value,
            # FrenchLanguageSignal, AcceptsSpontaneous
            company.french_language_signal.value,
            _bool_to_bit(company.accepts_spontaneous),
            # Status, RelevanceReason, Notes
            company.status.value,
            company.relevance_reason,
            company.notes,
            # WHERE
            company.id,
        )

    def mark_company_relevant_vacancy(
        self, conn: pyodbc.Connection, company_id: int
    ) -> None:
        """Met à jour LastRelevantVacancyAt quand une offre pertinente est trouvée."""
        conn.cursor().execute(
            """
            UPDATE research.Companies
            SET LastRelevantVacancyAt = GETUTCDATE(), UpdatedAt = GETUTCDATE()
            WHERE Id = ?
            """,
            company_id,
        )

    def get_companies_for_monitoring(
        self, conn: pyodbc.Connection, department: str
    ) -> list[Company]:
        """Retourne les entreprises à surveiller pour un département donné."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT Id, Name, NormalizedName, Domain, Website, CareersUrl,
                   City, Department, Country, CompanyType, Sector,
                   TechnologiesObserved, DeveloperRolesObserved,
                   JuniorHiringSignal, HiringHistorySignal, FrenchLanguageSignal,
                   AcceptsSpontaneous, Status, RelevanceReason,
                   SourceUrls, Notes,
                   FirstDiscoveredAt, LastResearchedAt, LastJobCheckAt,
                   LastRelevantVacancyAt, CreatedAt, UpdatedAt
            FROM research.Companies
            WHERE Department = ?
              AND Status NOT IN ('NOT_RELEVANT')
            ORDER BY
                CASE HiringHistorySignal
                    WHEN 'HIGH' THEN 1
                    WHEN 'MEDIUM' THEN 2
                    WHEN 'LOW' THEN 3
                    ELSE 4
                END,
                LastJobCheckAt ASC
            """,
            department,
        )
        return [_row_to_company(row) for row in cursor.fetchall()]

    # =========================================================================
    # Jobs + JobSources
    # =========================================================================

    def upsert_job(self, conn: pyodbc.Connection, job: Job) -> Job:
        """
        Insère ou met à jour une offre logique et ses sources.

        Déduplication :
          1. Pour chaque source dans job.sources :
             - Si SourceJobId connu → cherche dans JobSources
             - Sinon → cherche par titre + entreprise + contrat (fuzzy)
          2. Si doublon trouvé → met à jour le Job existant + ajoute la source
          3. Sinon → insère le nouveau Job + sa source

        Retourne le Job avec Id renseigné.
        """
        cursor = conn.cursor()

        # Tentative de déduplication
        existing_job_id = self._find_existing_job(cursor, job)

        if existing_job_id is not None:
            job.id = existing_job_id
            self._update_job(cursor, job)
            logger.debug("Job updated: id=%d title=%s", existing_job_id, job.title)
        else:
            job.id = self._insert_job(cursor, job)
            logger.debug("Job inserted: id=%d title=%s", job.id, job.title)

        # Upsert des sources
        for source_entry in job.sources:
            source_entry.job_id = job.id
            self._upsert_job_source(cursor, source_entry)

        # Recalcul IsActiveOpportunity
        self._refresh_is_active_opportunity(cursor, job.id)

        return job

    def _find_existing_job(
        self, cursor: pyodbc.Cursor, job: Job
    ) -> Optional[int]:
        # 1. Par SourceJobId de chaque source
        for src in job.sources:
            if src.source_job_id and src.source.value:
                cursor.execute(
                    """
                    SELECT j.Id FROM research.Jobs j
                    JOIN research.JobSources s ON s.JobId = j.Id
                    WHERE s.Source = ? AND s.SourceJobId = ?
                    """,
                    src.source.value,
                    src.source_job_id,
                )
                row = cursor.fetchone()
                if row:
                    return row[0]

        # 2. Par URL source
        for src in job.sources:
            if src.source_url:
                cursor.execute(
                    """
                    SELECT j.Id FROM research.Jobs j
                    JOIN research.JobSources s ON s.JobId = j.Id
                    WHERE s.SourceUrl = ?
                    """,
                    src.source_url,
                )
                row = cursor.fetchone()
                if row:
                    return row[0]

        # 3. Fuzzy : même entreprise + titre normalisé similaire + même contrat
        if job.company_id and job.title and job.contract_type:
            normalized_title = _normalize_text(job.title)
            cursor.execute(
                """
                SELECT Id FROM research.Jobs
                WHERE CompanyId = ?
                  AND ContractType = ?
                  AND FirstDiscoveredAt >= DATEADD(day, -30, GETUTCDATE())
                  AND LOWER(Title) LIKE ?
                """,
                job.company_id,
                job.contract_type.value,
                f"%{normalized_title[:30]}%",
            )
            row = cursor.fetchone()
            if row:
                return row[0]

        return None

    def _insert_job(self, cursor: pyodbc.Cursor, job: Job) -> int:
        cursor.execute(
            """
            INSERT INTO research.Jobs (
                CompanyId, Title, City, Country,
                PublishedAt, PublishedAtRaw, AgeAtDiscoveryDays,
                ContractType,
                ExperienceRaw, ExperienceMinYears, ExperienceMaxYears,
                Technologies, LanguageRequirement,
                Description, SalaryRaw,
                MatchResult, MatchReason,
                Status, IsActiveOpportunity,
                FirstDiscoveredAt, LastSeenAt
            ) VALUES (
                ?,?,?,?,
                ?,?,?,
                ?,
                ?,?,?,
                ?,?,
                ?,?,
                ?,?,
                ?,0,
                GETUTCDATE(), GETUTCDATE()
            );
            SELECT SCOPE_IDENTITY();
            """,
            job.company_id,
            job.title,
            job.city,
            job.country,
            job.published_at,
            job.published_at_raw,
            job.age_at_discovery_days,
            job.contract_type.value,
            job.experience_raw,
            job.experience_min_years,
            job.experience_max_years,
            _json_dumps(job.technologies),
            job.language_requirement,
            job.description,
            job.salary_raw,
            job.match_result.value,
            job.match_reason,
            job.status.value,
        )
        row = cursor.fetchone()
        return int(row[0])

    def _update_job(self, cursor: pyodbc.Cursor, job: Job) -> None:
        cursor.execute(
            """
            UPDATE research.Jobs SET
                Title               = COALESCE(?, Title),
                PublishedAt         = COALESCE(?, PublishedAt),
                PublishedAtRaw      = COALESCE(?, PublishedAtRaw),
                ContractType        = CASE WHEN ? != 'Inconnu' THEN ? ELSE ContractType END,
                ExperienceRaw       = COALESCE(?, ExperienceRaw),
                ExperienceMinYears  = COALESCE(?, ExperienceMinYears),
                ExperienceMaxYears  = COALESCE(?, ExperienceMaxYears),
                Technologies        = COALESCE(?, Technologies),
                Description         = COALESCE(?, Description),
                MatchResult         = CASE WHEN ? != 'UNKNOWN' THEN ? ELSE MatchResult END,
                MatchReason         = COALESCE(?, MatchReason),
                Status              = ?,
                LastSeenAt          = GETUTCDATE()
            WHERE Id = ?
            """,
            job.title,
            job.published_at,
            job.published_at_raw,
            job.contract_type.value, job.contract_type.value,
            job.experience_raw,
            job.experience_min_years,
            job.experience_max_years,
            _json_dumps(job.technologies) if job.technologies else None,
            job.description,
            job.match_result.value, job.match_result.value,
            job.match_reason,
            job.status.value,
            job.id,
        )

    def _upsert_job_source(
        self, cursor: pyodbc.Cursor, source: JobSourceEntry
    ) -> None:
        # Vérifie si la source existe déjà
        if source.source_job_id:
            cursor.execute(
                "SELECT Id FROM research.JobSources WHERE Source = ? AND SourceJobId = ?",
                source.source.value,
                source.source_job_id,
            )
        elif source.source_url:
            cursor.execute(
                "SELECT Id FROM research.JobSources WHERE SourceUrl = ?",
                source.source_url,
            )
        else:
            return  # pas assez d'info pour identifier la source

        row = cursor.fetchone()
        if row:
            cursor.execute(
                """
                UPDATE research.JobSources SET
                    UrlVerified = CASE WHEN ? = 1 THEN 1 ELSE UrlVerified END,
                    UrlReliable = CASE WHEN ? = 1 THEN 1 ELSE UrlReliable END,
                    PageTitle   = COALESCE(?, PageTitle),
                    LastSeenAt  = GETUTCDATE(),
                    VerifiedAt  = CASE WHEN ? = 1 THEN GETUTCDATE() ELSE VerifiedAt END
                WHERE Id = ?
                """,
                _bool_to_bit(source.url_verified),
                _bool_to_bit(source.url_reliable),
                source.page_title,
                _bool_to_bit(source.url_verified),
                row[0],
            )
        else:
            cursor.execute(
                """
                INSERT INTO research.JobSources (
                    JobId, Source, SourceJobId, SourceUrl,
                    UrlVerified, UrlReliable,
                    PageTitle, PageContent,
                    DiscoveredAt, LastSeenAt, VerifiedAt
                ) VALUES (
                    ?,?,?,?,
                    ?,?,
                    ?,?,
                    GETUTCDATE(), GETUTCDATE(), ?
                )
                """,
                source.job_id,
                source.source.value,
                source.source_job_id,
                source.source_url,
                _bool_to_bit(source.url_verified),
                _bool_to_bit(source.url_reliable),
                source.page_title,
                source.page_content,
                _utc_now() if source.url_verified else None,
            )

    def _refresh_is_active_opportunity(
        self, cursor: pyodbc.Cursor, job_id: int
    ) -> None:
        """
        Recalcule IsActiveOpportunity en base à partir des HARD FILTERS.

        Règle SQL :
          ContractType IN ('CDI','CDD')
          AND PublishedAt IS NOT NULL
          AND DATEDIFF(day, PublishedAt, GETUTCDATE()) <= 20
          AND EXISTS (
              SELECT 1 FROM JobSources
              WHERE JobId = Jobs.Id AND UrlVerified = 1 AND UrlReliable = 1
          )
        """
        cursor.execute(
            """
            UPDATE research.Jobs SET
                IsActiveOpportunity = CASE
                    WHEN ContractType IN ('CDI', 'CDD')
                     AND PublishedAt IS NOT NULL
                     AND DATEDIFF(day, PublishedAt, GETUTCDATE()) <= ?
                     AND EXISTS (
                         SELECT 1 FROM research.JobSources
                         WHERE JobId = Jobs.Id
                           AND UrlVerified = 1
                           AND UrlReliable = 1
                     )
                    THEN 1
                    ELSE 0
                END
            WHERE Id = ?
            """,
            ACTIVE_OPPORTUNITY_MAX_DAYS,
            job_id,
        )

    def refresh_all_active_opportunities(self, conn: pyodbc.Connection) -> int:
        """
        Recalcule IsActiveOpportunity pour TOUS les jobs.
        À appeler au début de chaque run d'agent pour invalider les offres > 20 jours.
        Retourne le nombre de jobs mis à jour.
        """
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE research.Jobs SET
                IsActiveOpportunity = CASE
                    WHEN ContractType IN ('CDI', 'CDD')
                     AND PublishedAt IS NOT NULL
                     AND DATEDIFF(day, PublishedAt, GETUTCDATE()) <= ?
                     AND EXISTS (
                         SELECT 1 FROM research.JobSources
                         WHERE JobId = Jobs.Id
                           AND UrlVerified = 1
                           AND UrlReliable = 1
                     )
                    THEN 1
                    ELSE 0
                END
            """,
            ACTIVE_OPPORTUNITY_MAX_DAYS,
        )
        return cursor.rowcount

    def get_active_opportunities(self, conn: pyodbc.Connection) -> list[Job]:
        """Retourne les offres satisfaisant tous les HARD FILTERS actuellement."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT j.Id, j.CompanyId, j.Title, j.City, j.Country,
                   j.PublishedAt, j.PublishedAtRaw, j.AgeAtDiscoveryDays,
                   j.ContractType, j.ExperienceRaw, j.ExperienceMinYears, j.ExperienceMaxYears,
                   j.Technologies, j.LanguageRequirement,
                   j.Description, j.SalaryRaw,
                   j.MatchResult, j.MatchReason,
                   j.Status, j.IsActiveOpportunity,
                   j.FirstDiscoveredAt, j.LastSeenAt, j.ClosedAt
            FROM research.Jobs j
            WHERE j.IsActiveOpportunity = 1
              AND DATEDIFF(day, j.PublishedAt, GETUTCDATE()) <= ?
            ORDER BY j.PublishedAt DESC
            """,
            ACTIVE_OPPORTUNITY_MAX_DAYS,
        )
        jobs = []
        for row in cursor.fetchall():
            job = _row_to_job(row)
            job.sources = self._get_job_sources(cursor, job.id)
            jobs.append(job)
        return jobs

    def _get_job_sources(
        self, cursor: pyodbc.Cursor, job_id: int
    ) -> list[JobSourceEntry]:
        cursor.execute(
            """
            SELECT Id, JobId, Source, SourceJobId, SourceUrl,
                   UrlVerified, UrlReliable, PageTitle,
                   DiscoveredAt, LastSeenAt, VerifiedAt
            FROM research.JobSources
            WHERE JobId = ?
            """,
            job_id,
        )
        return [_row_to_job_source(row) for row in cursor.fetchall()]

    # =========================================================================
    # SearchHistory + Décision de recherche
    # =========================================================================

    def record_search(
        self, conn: pyodbc.Connection, record: SearchRecord
    ) -> SearchRecord:
        """Enregistre un run de recherche dans l'historique."""
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO research.SearchHistory (
                Geography, City, Department,
                SearchType, QueriesUsed, SourcesChecked,
                ApifyRunId,
                CompaniesFound, NewCompanies, DuplicatesFound,
                JobsFound, NewJobs,
                CoverageState, Notes,
                SearchedAt
            ) VALUES (
                ?,?,?,
                ?,?,?,
                ?,
                ?,?,?,
                ?,?,
                ?,?,
                GETUTCDATE()
            );
            SELECT SCOPE_IDENTITY();
            """,
            record.geography,
            record.city,
            record.department,
            record.search_type.value,
            _json_dumps(record.queries_used),
            _json_dumps(record.sources_checked),
            record.apify_run_id,
            record.companies_found,
            record.new_companies,
            record.duplicates_found,
            record.jobs_found,
            record.new_jobs,
            record.coverage_state.value,
            record.notes,
        )
        row = cursor.fetchone()
        record.id = int(row[0])
        return record

    def decide_search_strategy(
        self, conn: pyodbc.Connection, city: str, department: str
    ) -> SearchDecision:
        """
        Analyse le SearchHistory pour une ville et retourne la stratégie optimale.

        Logique de décision :
          • Aucun historique → FULL_DISCOVERY
          • Dernier run PARTIAL ou FAILED → relance FULL_DISCOVERY prioritaire
          • Dernière recherche < MONITORING_PLUS_NEW_DAYS jours + COMPLETE
              → MONITORING_ONLY
          • Dernière recherche entre MONITORING_PLUS_NEW_DAYS et
              FULL_DISCOVERY_REFRESH_DAYS + COMPLETE
              → MONITORING_PLUS_NEW
          • Dernière recherche > FULL_DISCOVERY_REFRESH_DAYS + COMPLETE
              → FULL_DISCOVERY_REFRESH
        """
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT TOP 1
                SearchType, QueriesUsed, SourcesChecked,
                CoverageState, SearchedAt,
                DATEDIFF(day, SearchedAt, GETUTCDATE()) AS DaysSince
            FROM research.SearchHistory
            WHERE City = ? AND Department = ?
            ORDER BY SearchedAt DESC
            """,
            city,
            department,
        )
        row = cursor.fetchone()

        if row is None:
            return SearchDecision(
                geography=f"{city}, {department}",
                city=city,
                search_type=SearchType.FULL_DISCOVERY,
                reason="Aucun historique — première exploration",
            )

        last_search_type = SearchType(row[0])
        queries_used: list[str] = json.loads(row[1] or "[]")
        sources_checked: list[str] = json.loads(row[2] or "[]")
        coverage_state = CoverageState(row[3])
        searched_at: datetime = row[4]
        days_since: int = row[5]

        # Relance prioritaire si la dernière recherche a échoué ou est partielle
        if coverage_state in (CoverageState.PARTIAL, CoverageState.FAILED):
            return SearchDecision(
                geography=f"{city}, {department}",
                city=city,
                search_type=SearchType.FULL_DISCOVERY,
                reason=f"Dernier run {coverage_state.value} ({days_since} j) — relance prioritaire",
                suggested_queries=_suggest_complementary_queries(queries_used),
                suggested_sources=_suggest_complementary_sources(sources_checked),
                last_search_at=searched_at,
                last_coverage_state=coverage_state,
                days_since_last_search=days_since,
            )

        # Recherche récente + complète
        if days_since <= MONITORING_PLUS_NEW_DAYS:
            return SearchDecision(
                geography=f"{city}, {department}",
                city=city,
                search_type=SearchType.MONITORING_ONLY,
                reason=f"Exploration récente et complète ({days_since} j) — monitoring des entreprises connues",
                last_search_at=searched_at,
                last_coverage_state=coverage_state,
                days_since_last_search=days_since,
            )

        if days_since <= FULL_DISCOVERY_REFRESH_DAYS:
            return SearchDecision(
                geography=f"{city}, {department}",
                city=city,
                search_type=SearchType.MONITORING_PLUS_NEW,
                reason=f"Exploration datée de {days_since} j — monitoring + nouvelles entreprises",
                suggested_queries=_suggest_complementary_queries(queries_used),
                suggested_sources=_suggest_complementary_sources(sources_checked),
                last_search_at=searched_at,
                last_coverage_state=coverage_state,
                days_since_last_search=days_since,
            )

        return SearchDecision(
            geography=f"{city}, {department}",
            city=city,
            search_type=SearchType.FULL_DISCOVERY_REFRESH,
            reason=f"Exploration ancienne ({days_since} j > {FULL_DISCOVERY_REFRESH_DAYS}) — refresh complet",
            last_search_at=searched_at,
            last_coverage_state=coverage_state,
            days_since_last_search=days_since,
        )

    def get_covered_cities(
        self, conn: pyodbc.Connection, department: str
    ) -> list[dict]:
        """
        Retourne les villes déjà couvertes pour un département,
        avec la date et l'état de la dernière recherche.
        """
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                City,
                MAX(SearchedAt) AS LastSearchAt,
                MAX(CASE WHEN CoverageState = 'COMPLETE' THEN 1 ELSE 0 END) AS HasComplete,
                COUNT(*) AS SearchCount
            FROM research.SearchHistory
            WHERE Department = ?
            GROUP BY City
            ORDER BY LastSearchAt DESC
            """,
            department,
        )
        return [
            {
                "city": row[0],
                "last_search_at": row[1],
                "has_complete": bool(row[2]),
                "search_count": row[3],
            }
            for row in cursor.fetchall()
        ]


# =============================================================================
# Helpers privés
# =============================================================================


def _json_dumps(value: list | None) -> Optional[str]:
    if not value:
        return None
    return json.dumps(value, ensure_ascii=False)


def _bool_to_bit(value: Optional[bool]) -> Optional[int]:
    if value is None:
        return None
    return 1 if value else 0


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_text(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return nfkd.encode("ascii", "ignore").decode("ascii").lower().strip()


def _suggest_complementary_queries(used: list[str]) -> list[str]:
    """Propose des queries complémentaires à celles déjà utilisées."""
    all_templates = [
        "développeur C# .NET {city}",
        "développeur backend .NET {city}",
        "full stack React .NET {city}",
        "développeur TypeScript {city}",
        "software engineer C# {city}",
        "developer .NET junior {city}",
    ]
    used_lower = {q.lower() for q in used}
    return [t for t in all_templates if t.lower() not in used_lower]


def _suggest_complementary_sources(used: list[str]) -> list[str]:
    all_sources = ["linkedin", "indeed", "wttj", "france_travail", "company"]
    return [s for s in all_sources if s not in used]


# =============================================================================
# Mappers row → dataclass
# =============================================================================


def _row_to_company(row) -> Company:
    return Company(
        id=row[0],
        name=row[1],
        normalized_name=row[2],
        domain=row[3],
        website=row[4],
        careers_url=row[5],
        city=row[6],
        department=row[7],
        country=row[8] or "France",
        company_type=row[9],
        sector=row[10],
        technologies_observed=json.loads(row[11] or "[]"),
        developer_roles_observed=json.loads(row[12] or "[]"),
        junior_hiring_signal=HiringSignal(row[13] or "UNKNOWN"),
        hiring_history_signal=HiringSignal(row[14] or "UNKNOWN"),
        french_language_signal=FrenchLanguageSignal(row[15] or "UNKNOWN"),
        accepts_spontaneous=bool(row[16]) if row[16] is not None else None,
        status=CompanyStatus(row[17] or "MONITOR"),
        relevance_reason=row[18],
        source_urls=json.loads(row[19] or "[]"),
        notes=row[20],
        first_discovered_at=row[21],
        last_researched_at=row[22],
        last_job_check_at=row[23],
        last_relevant_vacancy_at=row[24],
        created_at=row[25],
        updated_at=row[26],
    )


def _row_to_job(row) -> Job:
    return Job(
        id=row[0],
        company_id=row[1],
        title=row[2],
        city=row[3],
        country=row[4] or "France",
        published_at=row[5],
        published_at_raw=row[6],
        age_at_discovery_days=row[7],
        contract_type=ContractType(row[8] or "Inconnu"),
        experience_raw=row[9],
        experience_min_years=row[10],
        experience_max_years=row[11],
        technologies=json.loads(row[12] or "[]"),
        language_requirement=row[13],
        description=row[14],
        salary_raw=row[15],
        match_result=MatchResult(row[16] or "UNKNOWN"),
        match_reason=row[17],
        status=JobStatus(row[18] or "UNKNOWN"),
        is_active_opportunity=bool(row[19]),
        first_discovered_at=row[20],
        last_seen_at=row[21],
        closed_at=row[22],
    )


def _row_to_job_source(row) -> JobSourceEntry:
    return JobSourceEntry(
        id=row[0],
        job_id=row[1],
        source=JobSource(row[2] or "other"),
        source_job_id=row[3],
        source_url=row[4],
        url_verified=bool(row[5]),
        url_reliable=bool(row[6]),
        page_title=row[7],
        discovered_at=row[8],
        last_seen_at=row[9],
        verified_at=row[10],
    )
