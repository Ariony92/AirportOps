# AirportOps — Plan de livraison (V0.9.0)

## Versions livrées

| Version | Périmètre |
|---|---|
| V0.1.0 | Prototype C++ / WASM, interface React, API FastAPI et persistance |
| V0.2.0 | Planning CRUD des vols ; durée et horaire personnalisés |
| V0.2.1 | Correctifs TypeScript, CI et gestion des scénarios |
| V0.3.0 | Flotte aérienne, immatriculations et affectations |
| V0.5.0 | Fusion 0.4 et 0.5 : pistes, taxiways, véhicules et opérations au sol |
| V0.7.0 | Fusion 0.6 et 0.7 : incidents datés, stratégies, coûts, historique et KPI |
| V0.7.1 | Correctif du typage `taxi_conflicts_avoided` et cohérence des métadonnées SemVer |
| **V0.9.0** | Fusion V0.8 et V0.9 : navigation multipage, moteur métier Python unique, scénarios paramétrés déterministes, accès sans compte, migration initiale, préparation CI étendue |

## Architecture cible et état

- Calcul métier opérationnel : **backend Python**, API de lecture de l'historique et des positions clés horodatées.
- Frontend : **pages par domaine**, formulaires, événements d'interface et rendu SVG de la chronologie.
- Backend : modèles ORM, schémas d'entrées/sorties, routeurs, services et éléments de persistance séparés ; les opérations historiques conservent encore des adaptations CRUD dans leur routeur.
- C++ / WASM : ancien moteur expérimental retiré du code actif ; les règles métier sont centralisées en Python.
- Accès : utilisation libre sans création de compte ; séparation des données des visiteurs et protections contre les abus encore à implémenter pour un déploiement public multi-utilisateur.
- Migration : révision initiale Alembic. Basculement des données existantes à vérifier par environnement.
- Qualité : tests automatisés backend et frontend, vérification des versions, tests de bout en bout Playwright et validation Docker dans GitHub Actions.


## Limitations identifiées

- Animation et graphe schématiques ; pas de routage géométrique continu ni de simulation sub-minute.
- Les écritures dans les données partagées ne sont pas encore isolées par visiteur ; les quotas et limites de requêtes ne sont pas implémentés sur toutes les routes.
- Les composants de gestion historiques restent relativement grands et certains routeurs contiennent du CRUD ; décomposition plus fine en sous-domaines à poursuivre.
- L’exécution des scénarios applique `delay`, `breakdown` et `seed` à un vol et véhicule déterministes ; ces scénarios ne disposent pas encore de ressources ou plannings totalement indépendants.
- Le modèle opérationnel ne garantit pas d'optimum global ni une sécurité d'exploitation aéronautique réelle.

## Évolutions suivantes

- Optimisation de l’algorithme Python et tests de performance sur des charges représentatives, sans réintroduire un second moteur métier.
- Représentation géométrique de tout le réseau de circulation, itinéraires segmentés et déplacement précis de plusieurs véhicules concurrents.
- Accès public robuste sans compte : sessions anonymes à durée limitée, isolation des données par session, plafonds de consommation, limitation des requêtes, nettoyage des anciennes données et HTTPS.
- Migrations évolutives successives, vérification de la transition des bases existantes, sauvegardes et restauration testées.
- Architecture frontend plus granulaire, composants et hooks réutilisables, tests visuels et accessibilité renforcée.
- Scénarios indépendants avec planification, ressources et incidents spécifiques à chacun.
