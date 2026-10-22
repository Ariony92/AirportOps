# AirportOps — Statut technique et évolutions

## Réalisé

- C++ : simulation déterministe à événements, réseau de 11 nœuds, Dijkstra, deux politiques, panne initiale et retard, véhicule affecté, statistiques.
- WebAssembly : compilation Emscripten ES module ; build Docker dédié.
- React : affichage schématique, tableau des vols, contrôles de lecture, configuration, comparaison, sauvegarde, export JSON.
- FastAPI/PostgreSQL : CRUD scénarios, création d'aéroport, sauvegarde/lecture de runs, comparaison, journal d'audit, validation.
- Docker Compose et CI GitHub Actions.

## Reste à faire pour atteindre le cahier des charges complet

1. Faire avancer les véhicules sur les segments à chaque pas, contrôler les collisions et les deadlocks, remplacer le camion SVG illustratif par les positions du moteur.
2. Introduire des tâches de service typées, capacités, dépendances et interruptions/reprises après panne pendant l'exécution.
3. Charger des configurations aéroport et vols entièrement éditables depuis l'API jusque dans le moteur via un format versionné.
4. Mettre les simulations longues dans un Web Worker.
5. Ajouter gestion d'utilisateurs, sessions, autorisations RBAC et protections serveur adaptées à un déploiement public.
6. Ajouter migrations Alembic ; `create_all` est utilisé uniquement pour simplifier le prototype initial.
7. Fournir un vrai éditeur graphique d'aéroport et un Gantt des opérations.
8. Évaluer plusieurs heuristiques multicritères sur des jeux de données variés ; prouver les contraintes de sécurité logique.
9. Développer des tests d'intégration du WASM et des tests E2E du navigateur.
10. Ajouter sauvegarde d'un état instantané et replay complet à partir d'un journal d'événements.

Les résultats de ce prototype sont déterministes et utiles pour une démonstration, mais ne sont pas des prédictions opérationnelles réelles.
