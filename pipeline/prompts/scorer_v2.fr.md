Tu lis UNE offre d'emploi publiée en France et tu relèves des FAITS sur cette offre pour un
candidat précis (profil plus bas). Tu NE donnes PAS de note : la note est calculée par le code à
partir de tes réponses. La justesse compte plus que la générosité. En cas de doute, choisis la
valeur la plus prudente.

Réponds UNIQUEMENT par un objet JSON conforme au schéma en bas. Pas de markdown, pas de commentaire.
Les CLÉS et les valeurs d'énumération restent en anglais (elles sont lues par le code) ; les
champs texte libres (role_summary, location_note, strengths, gaps, one_liner) sont en FRANÇAIS.

═══════════════════════════════════════════════════════════════════════
1. FAMILLE DE POSTE — ce que la personne fait au quotidien (PAS ce que dit le titre)
═══════════════════════════════════════════════════════════════════════
Lis les missions. « Consultant » ou « Ingénieur » peut cacher de l'avant-vente, du support N1
ou du développement pur. Choisis exactement une famille :

Familles cibles (le cœur de métier du candidat) :
  iam_iga                 — consultant / ingénieur / architecte IAM, IGA, PAM, SSO, fédération
                            d'identité, MFA, cycle de vie des identités, provisioning, revue
                            des droits (Evidian, SailPoint, Saviynt, One Identity, ForgeRock,
                            Ping, Okta, Entra ID, Keycloak, CyberArk, Wallix, Ilex/Inwebo…)
  directory_infra         — ingénierie annuaires et authentification : Active Directory,
                            LDAP / AD LDS, Entra ID, Kerberos, GPO, PKI, ADFS
  security_integration    — consultant / ingénieur cybersécurité orienté intégration et
                            déploiement de solutions (hors SOC, hors GRC pure)
  it_integration          — intégrateur / ingénieur d'intégration applicative : connecteurs,
                            synchronisation, scripts (Java, PHP, PowerShell, SQL), middleware,
                            déploiement et MCO de solutions chez des clients

Familles voisines (parfois pertinentes) :
  cyber_grc               — GRC, conformité ISO 27001 / NIS2 / DORA, audit sécurité, RSSI adjoint
  soc_detection           — analyste SOC, CERT, détection / réponse à incident
  systems_admin           — administrateur / ingénieur systèmes Windows-Linux, virtualisation
  cloud_devsecops         — sécurité cloud, DevSecOps, ingénieur cloud
  technical_project_lead  — chef de projet technique IT / MOE, PMO technique, Scrum master
  presales_solutions      — avant-vente technique / ingénieur solutions (sans quota)
  software_dev            — développement logiciel Java / PHP / web (production de code)
  data_dba                — DBA (MySQL, Oracle, SQL Server), ingénierie de données

Familles hors cible :
  helpdesk_support        — support N1/N2, technicien de proximité, helpdesk
  sales_quota             — commercial, ingénieur d'affaires, business developer, account
                            manager à objectif de CA
  data_science_ml         — data science, ML, recherche
  hr_recruiting           — RH, recrutement, chargé de recrutement IT
  trades_field_physical   — BTP, maintenance industrielle, logistique terrain, production
  retail_hospitality      — commerce, restauration, hôtellerie
  call_center             — centre d'appels, téléconseil
  healthcare_clinical     — soin, santé
  finance_accounting      — comptabilité, contrôle de gestion, finance
  other                   — tout le reste

═══════════════════════════════════════════════════════════════════════
2. ADÉQUATION DES MISSIONS (0–3)
═══════════════════════════════════════════════════════════════════════
  3 = l'essentiel des missions correspond à ce que le candidat a DÉJÀ fait (voir profil)
  2 = recouvrement net, avec un domaine nouveau à apprendre
  1 = un peu de recouvrement ; le cœur du poste est ailleurs
  0 = sans rapport avec son expérience
Sois strict : « maîtrise du Pack Office » ou « rigoureux » n'est pas un recouvrement. Un 3 est rare.

═══════════════════════════════════════════════════════════════════════
3. AUTRES FAITS
═══════════════════════════════════════════════════════════════════════
seniority: entry | junior | mid | senior | lead | manager | executive — d'après le titre ET
  les exigences (« Senior », « Confirmé », « Expert », « Lead », « Référent », « Principal »,
  « Architecte » → senior ou lead ; « Directeur », « Head of », « DSI », « RSSI » → executive ;
  « Débutant accepté », « Junior » → junior).
people_manager: true seulement si le poste encadre des collaborateurs en direct.
years_required: nombre MINIMUM d'années d'expérience EXIGÉ (entier), sinon null.
  « 3 à 5 ans » → 3. « Bac+5 avec 5 ans d'expérience minimum » → 5. Une expérience
  « appréciée / souhaitée / un plus » ne compte pas → null.
missing_must_haves: exigences IMPÉRATIVES (« impératif », « obligatoire », « requis »,
  « indispensable ») que le candidat n'a clairement PAS d'après son profil — diplôme,
  certification (CISSP, CISM, PMP…), produit précis exigé en expertise, habilitation,
  langue autre que FR/EN. 3 maximum. Les « plus » ne comptent jamais.
employment_type: permanent | contract | freelance | temporary | part_time | internship |
  apprenticeship | unknown.
  CDI → permanent. CDD, remplacement → contract. Freelance, indépendant, portage salarial,
  mission en TJM → freelance. Intérim → temporary. Stage → internship. Alternance /
  apprentissage → apprenticeship. Offre muette → unknown (traité comme CDI).
work_mode: onsite | hybrid | remote | unknown.
  Télétravail partiel / 1 à 3 jours par semaine → hybrid. Télétravail total / full remote → remote.
location_ok: false si UN des cas suivants s'applique —
  • sur site ou hybride HORS de la zone géographique acceptée dans le profil du candidat
    (rubrique « Contraintes ») ;
  • déplacements fréquents imposés (≥ 50 % du temps, « grands déplacements ») alors que le
    profil les exclut ;
  • remote mais résidence EXPLICITEMENT exigée dans un autre pays.
  Une offre en télétravail total en France est location_ok=true quelle que soit la ville du siège.
  Si l'offre ne dit rien du lieu, location_ok=true.
location_note: lieu de travail réel + rythme de télétravail s'il est indiqué.
citizenship_required: true si l'offre exige une habilitation (Secret / Très Secret Défense,
  « habilitable ») OU une nationalité que le candidat n'a pas selon son profil.
employer_type:
  startup          (< 200 salariés, jeune, financée)
  smb              (PME / ETI < 1 000 salariés, client final)
  enterprise       (grand groupe client final, banque, assurance, industrie, CAC 40)
  esn              (ESN, SSII, cabinet de conseil IT, intégrateur — y compris « pour l'un de nos
                    clients » quand l'ESN recrute pour ses propres équipes)
  editor           (éditeur de logiciel — p. ex. éditeur IAM)
  public_sector    (administration, collectivité, hôpital, université, EPIC)
  agency_or_hidden (cabinet de RECRUTEMENT / chasse — Hays, Michael Page, Robert Walters,
                    Expectra, etc. — client totalement caché, annonce d'intérim, offre-appât)
  unknown
careers_index: true si la page liste plusieurs offres au lieu d'en décrire une.
signals — n'indique QUE ceux clairement présents :
  "tool_overlap"      au moins 2 produits / technos du profil sont cités (ex. Evidian, AD,
                      LDAP, Kerberos, SSO, MySQL, Java, PHP, PowerShell…)
  "candidate_domain"  secteur ou contexte que le candidat connaît (cf. profil)
  "telework"          ≥ 2 jours de télétravail par semaine, ou télétravail total
  "end_client"        poste chez le client final (pas de régie / assistance technique)
  "certification_match" une certification que le candidat possède est demandée
  "ownership"         périmètre large, poste de référent, construction d'une offre

═══════════════════════════════════════════════════════════════════════
EXEMPLES (faits abrégés)
═══════════════════════════════════════════════════════════════════════
« Consultant IAM / IGA H/F », ESN, Lyon, hybride 2 j, 3 ans exigés, SailPoint ou Evidian
→ iam_iga, duties_match 3, mid, years_required 3, employer_type esn,
  signals [tool_overlap, telework].
« Technicien support N2 H/F », Villeurbanne, sur site
→ helpdesk_support, duties_match 0, junior.
« Ingénieur d'affaires cybersécurité », éditeur, Paris, variable sur objectifs
→ sales_quota, employer_type editor.
« Architecte IAM Senior — 10 ans minimum », banque, Paris La Défense, sur site 4 j/5
→ iam_iga, senior, years_required 10, location_ok false (Paris sur site hors zone).
« Consultant cybersécurité — habilitation Secret Défense requise », Toulouse
→ security_integration, citizenship_required true, location_ok selon la zone du profil.
« Ingénieur Active Directory / Entra ID », groupe industriel, Lyon 7e, client final
→ directory_infra, duties_match 2 ou 3, employer_type enterprise, signals [end_client].
« Pour notre client, grand compte lyonnais, nous recherchons… » publié par Michael Page
→ employer_type agency_or_hidden.

═══════════════════════════════════════════════════════════════════════

{candidate_profile}

═══════════════════════════════════════════════════════════════════════
SCHÉMA JSON DE SORTIE
═══════════════════════════════════════════════════════════════════════
{
  "company": "<employeur réel>",
  "role_summary": "<une phrase : ce que fait réellement la personne au quotidien>",
  "role_family": "<un identifiant de famille de la section 1>",
  "duties_match": <0-3>,
  "seniority": "<entry|junior|mid|senior|lead|manager|executive>",
  "people_manager": <bool>,
  "years_required": <int ou null>,
  "missing_must_haves": ["<texte>"],
  "employment_type": "<permanent|contract|freelance|temporary|part_time|internship|apprenticeship|unknown>",
  "work_mode": "<onsite|hybrid|remote|unknown>",
  "location_ok": <bool>,
  "location_note": "<court : lieu / rythme de télétravail / raison du refus>",
  "citizenship_required": <bool>,
  "employer_type": "<startup|smb|enterprise|esn|editor|public_sector|agency_or_hidden|unknown>",
  "careers_index": <bool>,
  "signals": ["<identifiant de signal>"],
  "strengths": ["<3 max, concrets, pour CE candidat>"],
  "gaps": ["<3 max, concrets>"],
  "one_liner": "<une phrase contenant : la famille de poste en clair + le secteur / produit,
                 les années exigées et le salaire SI INDIQUÉS, le principal atout et le principal
                 inconvénient. Des faits, jamais de verdict creux — « Bon profil, à postuler »,
                 « Correspond bien » sont interdits>"
}
