# Shortlist — adaptation au marché français

Cette variante fait tourner le pipeline sur des **sites et offres d'emploi français**, avec
des règles adaptées (CDI/CDD/freelance, départements, mentions H/F, ESN, documents en français).
La configuration canadienne d'origine (`config/search.yaml`) reste intacte et fonctionne toujours.

## Mise en route

```bash
cd pipeline
cp -r profile.example.fr profile          # puis adapter candidate.md, resume.tex, cover_letter.tex
cp .env.example .env                      # puis renseigner les clés
echo "AUTOJOB_CONFIG=./config/search.fr.yaml" >> .env
./venv/bin/autojob doctor
./venv/bin/autojob sources test francetravail apec wttj   # vérifier chaque source FR
./venv/bin/autojob run --dry-run --max-jobs 20            # essai à blanc
./venv/bin/autojob run
```

Clés à mettre dans `.env` :

| Variable | Source | Obtention |
|---|---|---|
| `FRANCETRAVAIL_CLIENT_ID` / `FRANCETRAVAIL_CLIENT_SECRET` | France Travail | francetravail.io → créer une application → API « Offres d'emploi v2 » (gratuit) |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | Adzuna France | developer.adzuna.com (même clé que pour le Canada) |
| `SERPER_API_KEY` | HelloWork, Free-Work, Cadremploi, Meteojob… via Google | serper.dev |
| `LLM_API_KEY` | notation + documents | inchangé |

APEC, Welcome to the Jungle, LinkedIn/Indeed (jobspy) et Workable ne demandent pas de clé.

Pour la génération des PDF, installer `texlive-lang-french` (sinon les gabarits compilent sans
la typographie française, grâce à un `\IfFileExists`).

## Sources actives (`config/search.fr.yaml`)

| Source | Type | Couverture |
|---|---|---|
| `francetravail` (**nouvelle**) | API officielle OAuth2 | Toutes les offres France Travail + partenaires ; passe Villeurbanne + 40 km et passe télétravail |
| `apec` | JSON public | Offres cadres ; contrat / télétravail / lieux désormais configurables |
| `wttj` | Index Algolia public | Welcome to the Jungle : bureaux Lyon/Villeurbanne + full remote France |
| `adzuna` | API | `country: FR`, salaires en EUR, passes Lyon (rayon) + France |
| `boards` | jobspy | LinkedIn + Indeed France (Lyon, puis France en télétravail) |
| `serper` | Google | Annonces individuelles HelloWork, Free-Work, Cadremploi, Meteojob, Lever/Greenhouse/Ashby/SmartRecruiters, Teamtailor, Welcome Kit |
| `workable_search` | JSON public | PME européennes sur Workable (Lyon + France remote) |

Les sources propres au Canada (Job Bank, GC Jobs, BC Public Service, Eluta, Workday canadiens…)
sont désactivées dans la config FR.

## Ce qui a changé dans le code

| Fichier | Changement |
|---|---|
| `autojob/sources/francetravail.py` | Nouvelle source (jeton OAuth2 mis en cache, pagination 150, passes commune/département/région) |
| `autojob/sources/apec.py` | `contrats`, `teletravail`, `lieux` configurables ; lieu et contrat réels dans l'offre |
| `autojob/sources/adzuna.py` | Devise selon le pays ; la passe « France » n'envoie plus de rayon |
| `autojob/sources/serper.py` | Reconnaît les URL d'offres des job boards français ; nettoie leurs suffixes de titre |
| `autojob/prefilter.py` | `home_markers` / `local_markers` configurables ; **règle 1b** : rejet des offres sur site/hybrides hors `local_departements` (lit « (92) », « 75008 », « Paris 08 - 75 ») ; une offre hybride dans une ville exclue est rejetée |
| `autojob/normalize.py` | Dédoublonnage insensible aux mentions H/F, F/H/X, écriture inclusive (·e, (e)) et aux accents ; suffixes SAS/SARL/SASU/EURL |
| `autojob/scorer.py` | Familles, signaux, contrats exclus, séniorité et années éliminatoires lisibles depuis `scoring.v2` ; type d'employeur `esn` et `editor` |
| `autojob/settings.py` | `profile.language` ; `prompts/<nom>.fr.md` prioritaire si la langue est `fr` ; secrets France Travail |
| `autojob/notify.py` | Digest Telegram en français, dates JJ/MM/AAAA |
| `autojob/docs.py` | Date française dans la lettre ; section « Profil » reconnue dans le CV ; **correctif** : les `{{CHAMPS}}` présents dans les commentaires LaTeX ne sont plus remplacés (le bloc `{{BULLETS}}` cassait la compilation, y compris en anglais) |
| `autojob/cli.py` | Découverte d'entreprises : verbes français (« recrute », « ouvre »…) |
| `prompts/*.fr.md` | Notation, CV et lettre de motivation en français |
| `profile.example.fr/` | Profil, CV (A4) et lettre de motivation français |
| `tests/test_france.py` | 12 tests sur l'ensemble de l'adaptation |

## Régler pour un autre profil

1. `queries` et les `title_keywords` de chaque source.
2. `prefilter.location` : `local_markers`, `local_departements`, `deny_cities`.
3. `scoring.v2` : familles cibles/voisines/exclues, poids, `not_permanent` (retirer `freelance` pour les missions).
4. `prompts/scorer_v2.fr.md` section 1 si les familles changent (les identifiants doivent correspondre).

## Limites connues

- La lecture des offres n'a été testée que hors ligne, sur des exemples de réponses API. Au premier
  lancement, vérifier dans les logs que chaque source renvoie des offres.
- APEC et WTTJ utilisent des points d'accès non documentés : ils peuvent changer ou être bloqués (DataDome).
- HelloWork, Free-Work, Cadremploi et Meteojob ne passent que par Serper (pas d'API publique).
- Le tableau de bord (Next.js) reste en anglais.
