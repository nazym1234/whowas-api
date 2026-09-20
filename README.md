# WhoWas API

WhoWas est une première version d'un moteur de questions biographiques. L'utilisateur
sélectionne une personnalité, pose une question en français et reçoit une réponse simple
à partir des propriétés structurées de Wikidata.

## Fonctionnalités V1

- sélection parmi 10 personnalités ;
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

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
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
    "person_qid": "Q7186",
    "question": "Où est née cette personne ?"
  }'
```

## Architecture

```text
Question + personne sélectionnée
            ↓
    Détection de l'intention
            ↓
 Propriété Wikidata correspondante
            ↓
 Récupération et résolution des données
            ↓
  Réponse simple + preuve + source
```

## Limites de cette version

- la personne doit être choisie dans la liste proposée ;
- les intentions reposent sur des règles et formulations françaises ;
- les réponses dépendent de la complétude de Wikidata ;
- aucun modèle d'intelligence artificielle n'est utilisé.

Ces limites sont volontaires : elles rendent le comportement de la V1 prévisible,
testable et explicable.

## Licence

MIT
