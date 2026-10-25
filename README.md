# AirportOps — Simulateur des opérations aéroportuaires

**Version actuelle : V0.9.0 — Refonte de l'architecture et de l'expérience opérationnelle (fusion V0.8 + V0.9).**

AirportOps est un prototype pédagogique de planification et de visualisation des opérations d'un aéroport fictif. Il permet de gérer des vols et des avions, les pistes, les voies de circulation, les véhicules, leurs tâches, des incidents temporels et des historiques de prévisions.

## Architecture

| Domaine | Responsabilité |
|---|---|
| Frontend React / TypeScript | Navigation, formulaires, affichage des données API, chronologie, interpolation graphique des positions entre des images clés datées |
| Backend FastAPI / Python | Règles métier, état opérationnel, graphe et itinéraires, conflits de créneaux, affectation des ressources, calculs de prévision, historiques, données d'animation |
| SQLAlchemy / PostgreSQL | Entités persistantes, audits, incidents et historiques |
| Alembic | Historique versionné des modifications de schéma |
| Moteur de calcul | **Python uniquement** ; l’ancien prototype C++/WASM a été retiré de la distribution active pour éviter deux sources de vérité |

Le frontend n'exécute plus le moteur TypeScript de simulation. La carte présente les images clés temporelles produites par `GET /api/operations/playback`, construites à partir de la même prévision Python que les KPI et le journal des événements. L'interpolation entre coordonnées est un effet d'affichage, sans choix de route, de créneau ou de véhicule dans React.

La granularité métier est actuellement d'une minute. Les déplacements entre positions restent schématiques et les véhicules ne sont pas modélisés en 3D, ni suivis par GPS.

### Organisation de l'application

- **Simulation** : carte, lecture/pause, vitesse, navigation temporelle, KPI et événements contextualisés.
- **Vols & flotte** : planning et gestion des appareils, affectation avion–vol.
- **Infrastructures** : pistes, taxiways, véhicules et opérations au sol.
- **Incidents & KPI** : fermetures, pannes, retards, comparaison de stratégies et historique des prévisions.
- **Scénarios** : scénarios enregistrés et exécutions calculées par le serveur.

Le code React est organisé autour de `pages/`, `features/` et `shared/`. Le backend sépare les modèles, les contrats d'API, les routeurs, des services métiers et les accès aux données. Le domaine opérationnel est regroupé sous `app/operations/`.

## Fonctionnalités disponibles

Le calcul opérationnel utilise un graphe de sept nœuds et Dijkstra, des créneaux réservés pour les pistes et un corridor partagé, une affectation simplifiée des ressources, les indisponibilités datées, ainsi que les stratégies standard et optimisée. Les résultats incluent retards, conflits évités, distances, utilisation des véhicules et estimation des coûts. Les prévisions persistées conservent des instantanés immuables. La création de nouveaux résultats depuis des métriques calculées par le navigateur a été retirée ; les anciens enregistrements demeurent consultables.

La V0.9 intègre une API de lecture des images clés horodatées, l'organisation en cinq espaces de navigation, le retrait des simulations métier TypeScript et C++/WASM redondantes, une première migration Alembic, et de nouveaux tests d'intégration et de navigateur. Les scénarios exécutés côté serveur appliquent aussi leurs paramètres enregistrés de façon déterministe.

### Accès public sans compte

AirportOps est destiné à être utilisé gratuitement et sans inscription ni connexion. Les routes de l'API ne requièrent aucun identifiant utilisateur. Les données saisies (vols, scénarios, ressources et incidents) sont enregistrées dans la base du serveur ; elles ne sont donc pas nécessairement isolées entre visiteurs dans cette version.

**Limitation importante :** le prototype ne dispose pas encore d'une isolation des scénarios par session anonyme ni d'une limitation systématique du trafic. Il n'est pas adapté à une exposition publique multi-utilisateur en écriture sans ces protections. La validation des entrées et la politique CORS ne constituent ni une autorisation ni une défense suffisante contre les abus.

### Schéma et migrations

Les modèles sont définis sous `backend/app/models.py`, et `backend/app/operations/models.py`. La première migration formelle figure dans `backend/migrations/versions/0001_initial.py`. Le mode local historique conserve `create_all` pour les bases de démonstration déjà existantes. Le mode `AIRPORTOPS_SCHEMA_MODE=alembic` suppose un schéma déjà migré avant le démarrage de l'API ; il n'effectue pas automatiquement de modifications non contrôlées de la base.

L'état d'un volume PostgreSQL existant ne doit pas être recréé arbitrairement. Les migrations initiales sont destinées à une base neuve. Pour une base existante déjà conforme, un marquage de révision (stamp) requiert d'abord la vérification de son schéma et une sauvegarde. Le mécanisme Alembic n'est pas une procédure de migration de données automatiques depuis des versions incompatibles.

## Limites de simulation

- Modèle pédagogique : aucune certification ATC, prédiction réelle de trajectoire ou garantie d'absence de collisions géométriques.
- Cinq portes et au plus dix vols dans le domaine historique du planning ; réseau de circulation statique limité.
- Une prévision est recalculée depuis un état figé ; les événements incidents ne modifient pas en continu une simulation déjà en cours.
- Les paramètres `delay`, `breakdown` et `seed` s’appliquent uniquement aux exécutions explicitement générées depuis un scénario. La valeur `delay` décale un seul vol choisi selon la graine ; `breakdown` programme une panne du véhicule choisi pendant les 240 premières minutes simulées. Le planning courant et les incidents globaux constituent encore une base partagée.
- Les positions graphiques représentent un plan schématique avec interpolation ; les trajectoires par segment et animations de véhicules détaillées sont des axes de développement ultérieur.
- Le moteur unique de calcul métier est Python ; les animations restent des projections schématiques et non des mesures en temps réel.
- Accès sans compte ; les scénarios et ressources sont encore partagés entre visiteurs, en attente d’une séparation des données par session anonyme et de contrôles anti-abus pour une publication ouverte.

## Qualité

L'intégration continue sépare les tests Python et API, la compilation frontend TypeScript/Vite, les vérifications de cohérence SemVer et les validations E2E et Docker définies dans `.github/workflows/ci.yml`. La couverture et ses limitations sont récapitulées dans [`docs/QUALITY.md`](docs/QUALITY.md). Les versions fonctionnelles antérieures sont résumées dans [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Références techniques

- [React : décomposition par composants](https://react.dev/learn/thinking-in-react)
- [React : règles des composants purs](https://react.dev/reference/rules)
- [FastAPI : organisation des applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Alembic : migrations](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Playwright : tests de bout en bout](https://playwright.dev/docs/intro)
