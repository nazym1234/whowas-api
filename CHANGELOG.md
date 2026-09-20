# Changelog

## 4.2.2

- Reconnaissance des questions de décès formulées au pluriel.
- Distinction entre demande de date et vérification « morts ou pas ».
- Réponse séparée pour chaque membre du dernier groupe conversationnel.

## 4.2.1

- Compréhension des continuations elliptiques comme « et en quelle année ? ».
- Conservation de la dernière question et de la dernière propriété dans le contexte.
- Suppression systématique d'une question en attente après un échec côté interface.

## 4.2.0

- Mémoire conversationnelle structurée sur les 20 derniers tours.
- Suivi distinct du sujet principal et du dernier groupe de personnes mentionné.
- Résolution des pronoms singuliers et pluriels ainsi que de « premier » et « deuxième ».
- Réponses groupées, notamment pour l'âge des enfants ou d'autres personnes liées.

## 4.1.0

- Nouvelle interface applicative avec navigation latérale et conversation continue.
- Ajout d'un annuaire de recherche de personnalités et d'un historique détaillé.
- Ajout du mode « Qui est-ce ? » avec sessions, questions et classement des réponses.
- Interface mobile adaptée et nouveaux tests du moteur de devinette.

## 4.0.0

- moteur d'actions : recherche, comptage, résumé, âge, durée, comparaison et vérification ;
- résolution de plusieurs personnes et désambiguïsation des homonymes ;
- contexte conversationnel local et portraits Wikimedia Commons ;
- sélection dynamique d'une propriété réellement disponible sur l'entité ;
- prise en compte des rangs et qualificateurs temporels ;
- cache TTL, retries, backoff, circuit breaker et limitation de concurrence ;
- métriques Prometheus, logs JSON, request IDs et healthchecks ;
- CSP, en-têtes de sécurité, rate limiting et rendu DOM sûr ;
- CI Python 3.11 à 3.13, Ruff, mypy, couverture et scan Trivy ;
- environnement Docker Compose avec Prometheus et Grafana.
