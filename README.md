# WhoWas API

WhoWas est un moteur de questions biographiques. L'utilisateur écrit directement une
question contenant le nom d'une personnalité et reçoit une réponse simple à partir des
propriétés structurées de Wikidata.

## Fonctionnalités V2

- détection du nom de la personnalité dans la question ;
- recherche automatique de la personne dans Wikidata ;
- reconnaissance de 10 intentions par règles explicables ;
- récupération en temps réel des propriétés Wikidata ;
- résolution en français des entités liées ;
- réponse simple avec preuve et lien source ;
- interface web et documentation OpenAPI ;
- tests, Docker et intégration continue GitHub Actions.

## Intentions reconnues

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
Question contenant le nom de la personne
            ↓
 Détection de l'intention et du nom
            ↓
 Recherche de la personne dans Wikidata
            ↓
 Propriété Wikidata correspondante
            ↓
 Récupération et résolution des données
            ↓
  Réponse simple + preuve + source
```

## Limites de cette version

- la question doit contenir le nom de la personnalité ;
- les intentions reposent sur des règles et formulations françaises ;
- les réponses dépendent de la complétude de Wikidata ;
- aucun modèle d'intelligence artificielle n'est utilisé.

Ces limites sont volontaires : elles rendent le comportement de la V2 prévisible,
testable et explicable.

## Licence

MIT
