# WhoWas API

WhoWas est un moteur de questions biographiques explicable. Il transforme une question
en plan de recherche, résout les personnes dans Wikidata, effectue si nécessaire un
calcul ou une comparaison, puis renvoie une réponse sourcée.

## Fonctionnalités V4

- questions libres et plus de 25 familles de propriétés biographiques ;
- actions `lookup`, `count`, `summary`, `age`, `duration`, `compare` et `verify` ;
- âge et durée de vie calculés à partir de dates structurées ;
- comparaison de deux personnalités ;
- détection des homonymes avec choix explicite dans l'interface ;
- conversation courte grâce au contexte conservé dans le navigateur ;
- recherche dynamique de propriétés non codées à l'avance ;
- résumé Wikipédia, portrait Wikimedia Commons et source de chaque réponse ;
- prise en compte des rangs et des dates de fin pour les valeurs actuelles ;
- cache TTL, retries exponentiels, limite de concurrence et circuit breaker ;
- limitation de débit, CSP, en-têtes de sécurité et rendu sans injection HTML ;
- logs JSON, request ID, métriques Prometheus et healthchecks Kubernetes ;
- 47 tests, couverture supérieure à 85 %, Ruff, mypy et CI multi-version ;
- image Docker non-root avec healthcheck et scan Trivy.

## Exemples V4

```text
Qui est Marie Curie ?
Quel âge a Margot Robbie ?
À quel âge est morte Marie Curie ?
Combien de temps Albert Einstein a-t-il vécu ?
Qui est le plus âgé entre Messi et Ronaldo ?
Marie Curie et Albert Einstein ont-ils la même nationalité ?
Qui a reçu le plus de distinctions entre Nelson Mandela et Barack Obama ?
Margot Robbie est-elle australienne ?
Quel est le conjoint actuel de Margot Robbie ?
Quelle est la couleur des yeux de David Bowie ?
```

## Exemples de questions

| Intention | Exemple | Wikidata |
|---|---|---|
| Date de naissance | Quand est née cette personne ? | P569 |
| Lieu de naissance | Où est née cette personne ? | P19 |
| Date de décès | Quand est-elle décédée ? | P570 |
| Nationalité | Quelle est sa nationalité ? | P27 |
| Profession | Quel était son métier ? | P106 |
| Études | Où a-t-elle étudié ? | P69 |
| Conjoint | Avec qui était-elle mariée ? | P26 |
| Enfants | Qui sont ses enfants ? | P40 |
| Distinctions | Quels prix a-t-elle reçus ? | P166 |
| Fonctions | Quelles fonctions a-t-elle occupées ? | P39 |
| Famille | Qui est la mère de Beyoncé ? | P25 |
| Employeur | Pour qui travaille cette personne ? | P108 |
| Résidence | Où habite cette personne ? | P551 |
| Religion | Quelle est sa religion ? | P140 |
| Parti politique | À quel parti appartient-elle ? | P102 |
| Langues | Quelles langues parle-t-elle ? | P1412 |
| Œuvres principales | Quelles sont ses œuvres connues ? | P800 |
| Domaine | Quel est son domaine de spécialité ? | P101 |
| Taille | Combien mesure cette personne ? | P2048 |
| Cause du décès | Quelle est la cause de sa mort ? | P509 |
| Question libre | Quelle est la couleur des yeux de David Bowie ? | détection automatique |

## Lancer le projet

### Windows PowerShell

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --reload
```

`Set-ExecutionPolicy -Scope Process` ne modifie que la fenêtre PowerShell actuelle.

### Linux et macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --reload
```

Ouvrez ensuite <http://localhost:8000>. Swagger est disponible sur
<http://localhost:8000/docs>.

## Docker

```bash
docker build -t whowas-api .
docker run --rm -p 8000:8000 whowas-api
```

Pour lancer l'application avec Prometheus et Grafana, définissez d'abord un mot de passe local pour Grafana :

```powershell
$env:GRAFANA_ADMIN_PASSWORD = "choisissez-un-mot-de-passe-local"
docker compose up --build
```

Sous Linux ou macOS :

```bash
GRAFANA_ADMIN_PASSWORD="choisissez-un-mot-de-passe-local" docker compose up --build
```

- WhoWas : <http://localhost:8000>
- Prometheus : <http://localhost:9090>
- Grafana : <http://localhost:3000> (utilisateur `admin` par défaut et mot de passe défini ci-dessus)

## Exemple d'appel

```bash
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Où est née Marie Curie ?"
  }'
```

## Architecture

```text
Question → plan d'action → résolution des personnes → cache/API
         → données et qualificateurs → calcul/comparaison
         → réponse + confiance + preuve + source
```

## Exploitation et observabilité

| Endpoint | Utilité |
|---|---|
| `/health/live` | vérifie que le processus répond |
| `/health/ready` | expose l'état du circuit breaker et du cache |
| `/metrics` | métriques au format Prometheus |
| `/people/search?q=...` | recherche et désambiguïsation d'une personne |
| `/intents` | règles structurées disponibles |
| `/docs` | documentation OpenAPI interactive |

Les logs HTTP sont produits en JSON avec un `request_id`, le statut et la durée.

## Qualité

```bash
ruff check .
ruff format --check .
mypy app
pytest --cov=app --cov-fail-under=85
```

## Limites de cette version

- la première question doit contenir le nom de la personnalité ;
- les intentions reposent sur des règles et formulations françaises ;
- les réponses dépendent de la complétude de Wikidata ;
- aucun modèle d'intelligence artificielle n'est utilisé.

La découverte automatique dépend des propriétés et libellés présents dans Wikidata. Une
question ambiguë peut donc demander une reformulation. Ces limites rendent la V4 testable
et explicable.

## Licence

MIT
