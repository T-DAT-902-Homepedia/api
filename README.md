# Homepedia API

API HTTP Homepedia (FastAPI). Pour l'instant, seul un healthcheck est exposé —
les endpoints data (choroplèthe prix/m²) reviendront une fois le backend de
données choisi (PostGIS ou BigQuery).

## Endpoints

```
GET /healthz
```

## Lancer en local

```bash
uv sync
uv run uvicorn app.main:app --reload
# Doc interactive : http://localhost:8000/docs
```

## En conteneur

Config via variables `API_*` (voir `app/config.py`).

Le conteneur écoute sur `$PORT` (défaut 8000) — Cloud Run injecte `PORT=8080`.

## CI / Release

Workflow unique `.github/workflows/ci.yml` :

- **CI** (PR + push `main`) : `ruff format --check`, `ruff check`,
  `pytest --cov` puis analyse SonarCloud (couverture incluse).
  Prérequis : projet SonarCloud créé (Automatic Analysis désactivée) et secret
  repo `SONAR_TOKEN`.
- **Release** (job `release`, uniquement sur push `main` après lint + tests
  verts, trunk-based) : la version SemVer est calculée depuis les **conventional commits** (`fix:` →
  patch, `feat:` → minor, `BREAKING CHANGE` → major ; rien à releaser → pas de
  tag). L'image est buildée et publiée sur
  `ghcr.io/t-dat-902-homepedia/api:<version>` (+ `latest`), scannée par Trivy,
  accompagnée d'un SBOM CycloneDX attaché à la release GitHub, puis signée et
  attestée avec cosign (keyless OIDC).

Vérifier une image :

```bash
cosign verify ghcr.io/t-dat-902-homepedia/api:<version> \
  --certificate-identity-regexp 'github.com/T-DAT-902-Homepedia/api' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

## Déploiement GCP (Cloud Run)

Déploiement automatique via GitHub Actions (`.github/workflows/cd.yml`),
déclenché après chaque run **réussi** du workflow CI / Release sur `main`
(ou manuellement via `workflow_dispatch`) : build de l'image, push vers
Artifact Registry, déploiement Cloud Run. Auth sans clé via Workload Identity
Federation (WIF).

### Prérequis one-shot (gcloud)

```bash
PROJECT_ID=<projet>          # ex. homepedia-prod
REGION=<région>              # ex. europe-west1
REPO=homepedia               # repo Artifact Registry
GITHUB_REPO=<org>/<repo>     # ex. monorg/T-DAT-902-Homepedia

gcloud config set project "$PROJECT_ID"

# 1. APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  iamcredentials.googleapis.com

# 2. Repo d'images
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker --location="$REGION"

# 3. Service account de déploiement
gcloud iam service-accounts create github-deployer
SA="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
for role in roles/run.admin roles/artifactregistry.writer \
            roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA" --role="$role"
done

# 4. Workload Identity Federation (GitHub OIDC)
gcloud iam workload-identity-pools create github --location=global
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global --workload-identity-pool=github \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository == '$GITHUB_REPO'"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
gcloud iam service-accounts add-iam-policy-binding "$SA" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/attribute.repository/${GITHUB_REPO}"
```

### Configuration côté GitHub

Variables (`Settings → Secrets and variables → Actions → Variables`) :

| Variable | Exemple |
|---|---|
| `GCP_PROJECT_ID` | `homepedia-prod` |
| `GCP_REGION` | `europe-west1` |
| `GAR_REPOSITORY` | `homepedia` |
| `API_CORS_ORIGINS` | `["https://homepedia.example.com"]` |

Secrets :

| Secret | Valeur |
|---|---|
| `WIF_PROVIDER` | `projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github/providers/github-provider` |
| `WIF_SERVICE_ACCOUNT` | `github-deployer@<projet>.iam.gserviceaccount.com` |

### Note backend de données

Quand le backend (PostGIS ou BigQuery) sera branché, ajouter le secret de
connexion dans Secret Manager et le référencer dans `cd.yml`
(`secrets:` de l'étape deploy-cloudrun) — le pipeline reste identique.
