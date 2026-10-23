# AirportOps — Plan de livraison (V0.5.0)

## Versions livrées

- **V0.1** : prototype React + C++20/WASM + FastAPI/PostgreSQL ; portes, véhicules et vols de démonstration.
- **V0.2** : planning CRUD des vols (10 vols maximum) et horaires personnalisés dans le moteur C++ et le secours TypeScript.
- **V0.2.1** : corrections TypeScript, CI, messages utilisateurs et suppression des scénarios.
- **V0.3** : catalogue de flotte CRUD, immatriculations, affectation avion-vol, blocage des créneaux qui se chevauchent.
- **V0.5 (fusion V0.4 + V0.5)** :
  - CRUD des pistes (longueur, fermeture, séparation des mouvements).
  - Gestion des voies de circulation bidirectionnelles entre 7 points (piste, aire de service, cinq postes) et visualisation du graphe.
  - Gestion persistante des véhicules de service avec vitesse, capacité, carburant, maintenance, disponibilité et coût horaire.
  - Création et suppression d'interventions par vol (bagages, carburant, nettoyage, restauration, repoussage).
  - Prévision opérationnelle Python : approche, atterrissage, libération de piste, roulage, stationnement, services, repoussage et décollage.
  - Ordonnancement simple des pistes, portes et véhicules, itinéraires Dijkstra, indicateurs et chronologie synchronisée sur l'heure simulée.
  - Catalogue de **211 suggestions** d'appareils de **24 constructeurs**, saisie libre toujours possible. Top 10 Skytrax 2026 pour les compagnies, saisie libre toujours possible.

## Limites connues

- Le moteur local C++/WebAssembly pour l'affectation des portes et le nouveau calcul opérationnel Python sont **deux modèles complémentaires non encore unifiés** ; ils peuvent générer des horaires et KPI différents.
- La carte SVG initiale montre encore un véhicule illustratif ; les opérations détaillées apparaissent dans le tableau et la chronologie, pas par animation continue des positions.
- Le modèle Python réserve des créneaux de piste et de véhicule ; il ne simule pas le contrôle aérien réel, les séparations par catégorie de sillage, les collisions en temps réel ni les deadlocks.
- Les changements d'état d'un véhicule (panne en cours de service, carburant consommé) ne sont **pas** enregistrés dans la base après une prévision, qui est volontairement sans effet de bord.
- Le catalogue civil fourni est vaste mais **non exhaustif** : les avions historiques, militaires et futures variantes mondiales se comptent par milliers. Saisie libre et mises à jour du catalogue nécessaires.
- Les 10 vols personnalisables et les cinq portes actuelles restent des limitations du moteur C++ de base.
- `Base.metadata.create_all` ajoute seulement les nouvelles tables ; les migrations contrôlées Alembic restent à réaliser pour les futures modifications de schéma.
- Les API ne disposent pas encore d’authentification. Le périmètre de sécurité actuel est limité à un environnement local de démonstration.

## Prochaines étapes

- **V0.6** : perturbations en cours de simulation, conflits de circulation et réordonnancement dynamique multi-ressources.
- **V0.7** : heuristiques d'optimisation supplémentaires, coûts et reporting historique avancé.
- **V0.8** : architecture sécurisée, authentification, rôles, migrations formelles.
- **V0.9** : tests E2E Playwright, compilation et test WebAssembly dans CI, validation Docker complète.
- **V1.0** : version consolidée et stabilité du périmètre convenu.
- **V1.1 à V1.4+** : améliorer, intégrer et faire converger progressivement les fonctionnalités explorées dans les archives de référence précédentes ; elles ne sont pas toutes présentes dans le dépôt progressif.

