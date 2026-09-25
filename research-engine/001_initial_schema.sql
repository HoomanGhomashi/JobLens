-- =============================================================================
-- JobLens — Migration 001 : Schéma initial
-- =============================================================================
-- Tables : Companies, Jobs, JobSources, SearchHistory
--
-- Règles métier importantes :
--   • IsActiveOpportunity = CDI/CDD + (GETUTCDATE() - PublishedAt) <= 20 jours
--                          + au moins une URL vérifiée dans JobSources
--   • IsActiveOpportunity est RECALCULÉ à chaque exécution, jamais stocké de
--     manière permanente — la colonne BIT sert de cache entre deux passages.
--   • AgeAtDiscoveryDays = information historique uniquement (au moment de la
--     découverte). NE PAS utiliser pour déterminer IsActiveOpportunity.
--   • PublishedAt = NULL si inconnue. Jamais inventée, jamais estimée.
--     Si PublishedAt IS NULL → IsActiveOpportunity = 0 sans exception.
--   • Status (Jobs) = état réel de l'offre : ACTIVE / CLOSED / EXPIRED / UNKNOWN
--     IsActiveOpportunity = filtre runtime : l'offre satisfait-elle tous les
--     HARD FILTERS en ce moment ?
--     Exemple valide : Status = ACTIVE, IsActiveOpportunity = 0
--     (offre toujours publiée mais > 20 jours — normal)
-- =============================================================================

-- =============================================================================
-- Schema
-- =============================================================================
-- Toutes les tables du Research Engine vivent sous le schéma "research",
-- séparé du schéma "app" (futur, propriété d'EF Core / ASP.NET Core).
-- =============================================================================

CREATE SCHEMA research;
GO

-- ---------------------------------------------------------------------------
-- 1. Companies
-- ---------------------------------------------------------------------------
-- Une entreprise reste dans la base même sans aucune offre active.
-- Elle est monitorée indéfiniment une fois découverte.
-- ---------------------------------------------------------------------------
CREATE TABLE research.Companies
(
    Id                     INT IDENTITY (1,1) PRIMARY KEY,

    -- Identité
    Name                   NVARCHAR(200) NOT NULL,
    NormalizedName         NVARCHAR(200),                    -- lower, sans accents, pour dedup
    Domain                 NVARCHAR(200),                    -- ex. "accenture.com" (UNIQUE, nullable)
    Website                NVARCHAR(500),
    CareersUrl             NVARCHAR(500),

    -- Localisation
    City                   NVARCHAR(100),
    Department             NVARCHAR(50),                     -- ex. "Rhône", "69"
    Country                NVARCHAR(50) DEFAULT 'France',

    -- Profil
    CompanyType            NVARCHAR(100),                    -- PME|ETI|Grande entreprise|Startup|ESN|Éditeur
    Sector                 NVARCHAR(200),

    -- Données observées (JSON arrays sérialisés)
    TechnologiesObserved   NVARCHAR(MAX),                    -- ex. ["C#","React","Azure"]
    DeveloperRolesObserved NVARCHAR(MAX),                    -- ex. ["Développeur .NET","Lead Dev"]

    -- Signaux de recrutement
    -- JuniorHiringSignal  : signal ACTUEL — l'entreprise cherche-t-elle des juniors en ce moment ?
    -- HiringHistorySignal : signal HISTORIQUE — l'entreprise a-t-elle une culture de recrutement
    --                       de développeurs, observée sur la durée ?
    JuniorHiringSignal     NVARCHAR(20)  DEFAULT 'UNKNOWN',  -- HIGH|MEDIUM|LOW|UNKNOWN
    HiringHistorySignal    NVARCHAR(20)  DEFAULT 'UNKNOWN',  -- HIGH|MEDIUM|LOW|UNKNOWN
    FrenchLanguageSignal   NVARCHAR(20)  DEFAULT 'UNKNOWN',  -- YES|MIXED|ENGLISH_ONLY|UNKNOWN

    -- Contexte candidature
    AcceptsSpontaneous     BIT,                              -- NULL = inconnu

    -- Pertinence pour le candidat
    Status                 NVARCHAR(50)  DEFAULT 'MONITOR',
    -- ACTIVE_RELEVANT     : offre pertinente actuellement
    -- MONITOR             : à surveiller, pas d'offre en ce moment
    -- POTENTIALLY_RELEVANT: peu d'info, à re-vérifier
    -- LOW_PRIORITY        : peu probable d'avoir des juniors
    -- NOT_RELEVANT        : exclue (ex. uniquement senior, hors scope)

    RelevanceReason        NVARCHAR(MAX),                    -- justification texte de Claude
    SourceUrls             NVARCHAR(MAX),                    -- JSON array des URLs sources de découverte
    Notes                  NVARCHAR(MAX),

    -- Horodatages
    FirstDiscoveredAt      DATETIME2,
    LastResearchedAt       DATETIME2,                        -- dernière analyse générale
    LastJobCheckAt         DATETIME2,                        -- dernier contrôle des offres
    LastRelevantVacancyAt  DATETIME2,                        -- dernière offre pertinente observée
    CreatedAt              DATETIME2     DEFAULT GETUTCDATE(),
    UpdatedAt              DATETIME2     DEFAULT GETUTCDATE()
);

-- ---------------------------------------------------------------------------
-- 2. Jobs (offres logiques — dédupliquées inter-sources)
-- ---------------------------------------------------------------------------
-- Un même poste publié sur LinkedIn + Indeed + site entreprise = 1 seul Job
-- avec plusieurs entrées dans JobSources.
-- ---------------------------------------------------------------------------
CREATE TABLE research.Jobs
(
    Id                  INT IDENTITY (1,1) PRIMARY KEY,
    CompanyId           INT REFERENCES research.Companies (Id) ON DELETE SET NULL,

    -- Description du poste
    Title               NVARCHAR(200),
    City                NVARCHAR(100),
    Country             NVARCHAR(50)  DEFAULT 'France',

    -- Date de publication
    -- PublishedAt  = date réelle extraite. NULL si inconnue. JAMAIS inventée.
    -- PublishedAtRaw = chaîne brute telle qu'elle apparaît dans l'annonce
    --                  ex. "il y a 3 jours", "Publiée le 01/09/2026", "Hier"
    -- AgeAtDiscoveryDays = âge au moment de la DÉCOUVERTE (information historique).
    --                      NE PAS utiliser pour IsActiveOpportunity.
    PublishedAt         DATETIME2,
    PublishedAtRaw      NVARCHAR(100),
    AgeAtDiscoveryDays  INT,                                 -- historique uniquement

    -- Contrat
    -- ContractType = valeur normalisée ; seuls CDI et CDD peuvent mener à IsActiveOpportunity = 1
    ContractType        NVARCHAR(50),                        -- CDI|CDD|Alternance|Stage|Freelance|Inconnu

    -- Expérience
    -- ExperienceRaw = extrait du texte de l'annonce, JAMAIS inventé
    ExperienceRaw       NVARCHAR(200),
    ExperienceMinYears  INT,
    ExperienceMaxYears  INT,

    -- Compétences
    Technologies        NVARCHAR(MAX),                       -- JSON array extrait de l'annonce
    LanguageRequirement NVARCHAR(100),                       -- FR|EN|FR+EN|Inconnu

    -- Contenu
    Description         NVARCHAR(MAX),
    SalaryRaw           NVARCHAR(200),

    -- Évaluation par Claude
    MatchResult         NVARCHAR(20)  DEFAULT 'UNKNOWN',     -- MATCH|BORDERLINE|REJECT|UNKNOWN
    MatchReason         NVARCHAR(MAX),

    -- État de l'offre
    -- Status         = état réel de l'offre sur la plateforme source
    -- IsActiveOpportunity = cache runtime — recalculé à chaque passage de l'agent
    --   Conditions : ContractType IN (CDI, CDD)
    --                AND PublishedAt IS NOT NULL
    --                AND DATEDIFF(day, PublishedAt, GETUTCDATE()) <= 20
    --                AND EXISTS (SELECT 1 FROM JobSources WHERE JobId = Jobs.Id
    --                            AND UrlVerified = 1 AND UrlReliable = 1)
    Status              NVARCHAR(20)  DEFAULT 'UNKNOWN',     -- ACTIVE|CLOSED|EXPIRED|UNKNOWN
    IsActiveOpportunity BIT           DEFAULT 0,             -- recalculé à chaque run

    -- Horodatages
    FirstDiscoveredAt   DATETIME2     DEFAULT GETUTCDATE(),
    LastSeenAt          DATETIME2,
    ClosedAt            DATETIME2
);

-- ---------------------------------------------------------------------------
-- 3. JobSources (URLs par source pour chaque offre logique)
-- ---------------------------------------------------------------------------
-- Apify récupère l'URL candidate et le contenu de la page.
-- Claude valide sémantiquement si c'est bien une page de détail d'offre.
-- Une URL n'est jamais reconstruite ni inventée.
-- ---------------------------------------------------------------------------
CREATE TABLE research.JobSources
(
    Id          INT IDENTITY (1,1) PRIMARY KEY,
    JobId       INT REFERENCES research.Jobs (Id) ON DELETE CASCADE NOT NULL,

    -- Source
    Source      NVARCHAR(100),
    -- linkedin | indeed | wttj | france_travail | company | other

    -- Identifiant interne de la source (ex. ID LinkedIn de l'offre)
    SourceJobId NVARCHAR(200),

    -- URL directe vers la page de l'offre
    -- Jamais une page de résultats, jamais une homepage, jamais une URL reconstruite.
    SourceUrl   NVARCHAR(1000),

    -- Validation par Claude
    -- UrlVerified : Claude a analysé le contenu fourni par Apify et confirmé
    --              que la page est bien une page de détail d'offre d'emploi.
    -- UrlReliable : l'URL est stable et directement accessible (pas redirigée,
    --              pas derrière un paywall, pas expirée au moment de la vérification).
    UrlVerified  BIT            DEFAULT 0,
    UrlReliable  BIT            DEFAULT 0,

    -- Données récupérées par Apify (avant validation Claude)
    PageTitle    NVARCHAR(500),
    PageContent  NVARCHAR(MAX),                              -- contenu brut retourné par Apify

    -- Horodatages
    DiscoveredAt DATETIME2      DEFAULT GETUTCDATE(),
    LastSeenAt   DATETIME2,
    VerifiedAt   DATETIME2                                   -- quand Claude a validé l'URL
);

-- ---------------------------------------------------------------------------
-- 4. SearchHistory
-- ---------------------------------------------------------------------------
-- Journalise chaque recherche et permet à l'agent de décider intelligemment
-- du type de prochaine recherche (FULL_DISCOVERY / MONITORING_ONLY / etc.)
--
-- Avant chaque run, l'agent consulte cette table pour savoir :
--   • quelles villes ont été explorées et quand
--   • quelles queries ont déjà été utilisées
--   • quelles sources ont été vérifiées
--   • si la dernière recherche était COMPLETE, PARTIAL ou FAILED
--   • si une relance est nécessaire (PARTIAL/FAILED peuvent partir plus tôt)
-- ---------------------------------------------------------------------------
CREATE TABLE research.SearchHistory
(
    Id              INT IDENTITY (1,1) PRIMARY KEY,

    -- Périmètre géographique
    Geography       NVARCHAR(100),                           -- ex. "Rhône", "Lyon", "Villeurbanne"
    City            NVARCHAR(100),
    Department      NVARCHAR(50),                            -- ex. "69"

    -- Type de recherche effectuée
    SearchType      NVARCHAR(50),
    -- FULL_DISCOVERY       : exploration complète d'une zone nouvelle
    -- MONITORING_ONLY      : vérification des entreprises déjà connues
    -- MONITORING_PLUS_NEW  : monitoring + recherche de nouvelles entreprises
    -- FULL_DISCOVERY_REFRESH : re-exploration complète d'une zone déjà couverte

    -- Détails de l'exécution (JSON arrays)
    QueriesUsed     NVARCHAR(MAX),                           -- JSON : ["C# Lyon", ".NET Rhône", ...]
    SourcesChecked  NVARCHAR(MAX),                           -- JSON : ["linkedin","indeed","wttj"]

    -- Référence Apify
    ApifyRunId      NVARCHAR(100),

    -- Résultats
    CompaniesFound  INT           DEFAULT 0,
    NewCompanies    INT           DEFAULT 0,
    DuplicatesFound INT           DEFAULT 0,
    JobsFound       INT           DEFAULT 0,
    NewJobs         INT           DEFAULT 0,

    -- Qualité de la recherche
    CoverageState   NVARCHAR(20),
    -- COMPLETE : recherche terminée avec succès, couverture satisfaisante
    -- PARTIAL  : interrompue ou couverture insuffisante — relance prioritaire
    -- FAILED   : erreur technique — relance dès que possible

    Notes           NVARCHAR(MAX),
    SearchedAt      DATETIME2     DEFAULT GETUTCDATE()
);

-- =============================================================================
-- Index
-- =============================================================================

-- Companies
CREATE UNIQUE INDEX UX_Companies_Domain
    ON research.Companies (Domain)
    WHERE Domain IS NOT NULL;

CREATE INDEX IX_Companies_Status
    ON research.Companies (Status);

CREATE INDEX IX_Companies_City
    ON research.Companies (City);

CREATE INDEX IX_Companies_Department
    ON research.Companies (Department);

CREATE INDEX IX_Companies_LastJobCheckAt
    ON research.Companies (LastJobCheckAt);

CREATE INDEX IX_Companies_HiringSignals
    ON research.Companies (JuniorHiringSignal, HiringHistorySignal);

-- Jobs
CREATE INDEX IX_Jobs_CompanyId
    ON research.Jobs (CompanyId);

CREATE INDEX IX_Jobs_IsActiveOpportunity
    ON research.Jobs (IsActiveOpportunity)
    WHERE IsActiveOpportunity = 1;

CREATE INDEX IX_Jobs_PublishedAt
    ON research.Jobs (PublishedAt);

CREATE INDEX IX_Jobs_ContractType
    ON research.Jobs (ContractType);

CREATE INDEX IX_Jobs_MatchResult
    ON research.Jobs (MatchResult);

CREATE INDEX IX_Jobs_Status
    ON research.Jobs (Status);

-- JobSources
CREATE UNIQUE INDEX UX_JobSources_SourceJobId
    ON research.JobSources (Source, SourceJobId)
    WHERE SourceJobId IS NOT NULL;

CREATE INDEX IX_JobSources_JobId
    ON research.JobSources (JobId);

CREATE INDEX IX_JobSources_UrlVerified
    ON research.JobSources (UrlVerified, UrlReliable);

-- SearchHistory
CREATE INDEX IX_SearchHistory_Geography
    ON research.SearchHistory (Geography, SearchType, SearchedAt DESC);

CREATE INDEX IX_SearchHistory_City
    ON research.SearchHistory (City, SearchedAt DESC);

CREATE INDEX IX_SearchHistory_CoverageState
    ON research.SearchHistory (CoverageState, SearchedAt DESC);

-- =============================================================================
-- FIN DE MIGRATION
-- =============================================================================
