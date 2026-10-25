# AirportOps — Simulateur de gestion des opérations aéroportuaires

**AirportOps** est un projet de développement logiciel visant à concevoir une plateforme interactive de simulation et d'optimisation des opérations au sol dans un aéroport fictif.

L'objectif est de reproduire, à échelle simplifiée, les principales contraintes liées à la gestion des infrastructures aéroportuaires, à l'affectation des ressources et à la coordination des opérations.

Le projet s'appuie sur plusieurs technologies complémentaires : **React, TypeScript, C++20, WebAssembly, Python, FastAPI et PostgreSQL**.

---

**Version actuelle : V0.7.0 — Incidents, replanification et analytique (fusion V0.6 + V0.7).** La simulation demeure un prototype pédagogique.

## 1. Présentation et objectifs

Dans un aéroport, de nombreuses opérations doivent être coordonnées : arrivée des avions, attribution des portes de stationnement, déplacement des véhicules de service, gestion des retards et disponibilité des ressources.

Une mauvaise coordination peut entraîner des conflits d'utilisation, des retards supplémentaires et une utilisation inefficace des infrastructures.

AirportOps vise à proposer un environnement permettant de :

- Visualiser l'activité d'un aéroport fictif sur une interface interactive.

- Simuler les mouvements et les opérations associés aux vols.

- Attribuer automatiquement des portes de stationnement.

- Affecter des véhicules aux opérations au sol.

- Prendre en compte différentes contraintes opérationnelles.

- Introduire des perturbations, notamment des retards et des pannes.

- Comparer plusieurs stratégies de planification.

- Mesurer les performances des opérations simulées.

- Sauvegarder et consulter différents scénarios.

À terme, la plateforme doit permettre d'expérimenter plusieurs méthodes d'optimisation et d'analyser leurs conséquences sur le fonctionnement global d'un aéroport.

## 2. Technologies utilisées

| Technologie | Rôle dans le projet |
|---|---|
| React | Construction de l'interface utilisateur |
| TypeScript | Développement du frontend et typage des données |
| C++20 | Développement du moteur de simulation |
| WebAssembly | Exécution du moteur C++ dans le navigateur |
| Python | Développement des services backend |
| FastAPI | Mise à disposition d'une API REST |
| PostgreSQL | Stockage persistant des scénarios et résultats |
| SQLAlchemy | Gestion des modèles et interactions avec la base de données |
| Docker / Docker Compose | Conteneurisation et orchestration des services |
| GitHub Actions | Automatisation des vérifications et tests |

Le choix de cette architecture permet de séparer l'interface utilisateur, les calculs de simulation et la gestion des données persistantes.

## 3. Architecture technique

### Architecture actuelle

Le projet repose sur trois composants principaux :

1. **Frontend React / TypeScript** : interface de visualisation, configuration et contrôle des simulations.

2. **Moteur C++ / WebAssembly** : calcul des événements, affectation des ressources et exécution de la simulation.

3. **Backend FastAPI / PostgreSQL** : gestion des scénarios, des résultats et de leur persistance.

```text

                   UTILISATEUR

                        |

                        v

             +---------------------+

             |  React / TypeScript |

             |  Interface web      |

             +---------------------+

                  |           |

                  v           v

          +-------------+  +------------------+

          | C++20 / WASM|  | API REST FastAPI |

          | Simulation  |  | Services Python  |

          +-------------+  +------------------+

                                     |

                                     v

                            +------------------+

                            |    PostgreSQL    |

                            | Scénarios / Runs |

                            +------------------+

```

En l'absence du module WebAssembly, le frontend dispose d'une implémentation TypeScript simplifiée utilisée comme solution de secours.

### Architecture cible proposée

L'objectif à terme est de faire évoluer cette architecture vers une organisation plus modulaire, afin de faciliter la maintenance, les tests et l'ajout de fonctionnalités.

```text

                       UTILISATEUR

                            |

                            v

                  +---------------------+

                  |     FRONTEND        |

                  | React + TypeScript  |

                  |                     |

                  | Dashboard           |

                  | Carte interactive   |

                  | Gestion des vols    |

                  | Scénarios / KPI     |

                  +---------------------+

                      |             |

                      v             v

             +--------------+  +------------------+

             | WEBASSEMBLY  |  | BACKEND          |

             | C++20        |  | FastAPI / Python |

             |              |  |                  |

             | Simulation   |  | API REST         |

             | Planification|  | Authentification |

             | Pathfinding  |  | Services métier  |

             | Conflits     |  | Historique       |

             +--------------+  +------------------+

                                       |

                                       v

                              +------------------+

                              |   PostgreSQL     |

                              |                  |

                              | Aéroports        |

                              | Avions / Vols    |

                              | Véhicules        |

                              | Scénarios        |

                              | Simulations      |

                              | Événements / KPI |

                              +------------------+

```

**Principales évolutions architecturales envisagées :**

- Structurer le frontend par domaines fonctionnels.

- Exécuter les calculs WebAssembly dans un Web Worker.

- Séparer davantage le moteur C++ en modules spécialisés.

- Permettre plusieurs instances de simulation indépendantes.

- Organiser le backend en couches API, services métier et accès aux données.

- Étendre le modèle de données pour représenter les entités opérationnelles.

- Améliorer la cohérence entre simulations locales et calculs enregistrés.

Cette architecture représente une proposition d'évolution et non l'état actuel de toutes les implémentations.

## 4. Fonctionnalités actuellement développées

La version actuelle constitue un premier prototype intégrant les principales bases techniques.

### Simulation

- Aéroport fictif comprenant cinq portes de stationnement.

- Génération automatique de dix vols de démonstration lorsque aucun planning n’a été enregistré.

- Gestion de trois véhicules génériques.

- Simulation à événements discrets développée en C++.

- Affectation automatique des portes selon deux stratégies.

- Gestion simplifiée des disponibilités des véhicules.

- Recherche de chemins avec l'algorithme de Dijkstra.

- Simulation d'un retard configurable.

- Simulation d'une panne initiale de véhicule.

### Planning de vols — V0.2.0

- Création, consultation, modification et suppression des vols programmés depuis l’interface.
- Saisie du numéro de vol, de la compagnie, de l’origine, de la destination, de l’horaire et de la durée de service.
- Sauvegarde du planning dans une table `flight_plans` (PostgreSQL avec Docker ou SQLite en local).
- Utilisation des horaires personnalisés par le moteur C++/WebAssembly et par le moteur TypeScript de secours.
- Limite actuelle : **10 vols personnalisés**. Si aucun vol n’est configuré, les 10 vols de démonstration sont utilisés.
- Le planning est global à l’environnement de démonstration, **pas encore spécifique à chaque scénario**.

### Flotte aérienne — V0.3.0

- Gestion des appareils (création, consultation, modification et suppression) depuis l’interface.
- Saisie de l’immatriculation, de la compagnie, du constructeur, du modèle, de la catégorie et du nombre de sièges.
- Attribution facultative d’un appareil à un vol du planning.
- Contrôle des affectations : un avion ne peut pas couvrir deux plages de service qui se chevauchent.
- Suppression des appareils affectés à un vol bloquée pour préserver la cohérence des données.
- Persistance dans les nouvelles tables `aircraft` et `flight_aircraft_assignments` ; **aucune modification des tables V0.2 existantes**.
- Dans cette version, les caractéristiques des appareils servent au planning et à l’inventaire : elles ne modifient pas encore la physique de la simulation C++.

### Infrastructures et opérations au sol — V0.5.0

Cette livraison combine les deux priorités **V0.4** et **V0.5** en une mise à jour :

- Création, fermeture et suppression de pistes, avec longueur minimale et séparation temporelle.
- Édition des voies de circulation, distances et fermeture des segments ; graphe à sept nœuds (piste, aire de service, cinq portes).
- Véhicules de service persistants : cinq types (bagages, carburant, nettoyage, restauration, repoussage), vitesse, capacité, carburant, maintenance, disponibilité et coût horaire.
- Interventions paramétrables par vol, gestion des capacités et calendrier simplifié des ressources.
- Prévision côté serveur par étapes : approche, atterrissage, sortie de piste, roulage, poste, services parallèles, repoussage et décollage.
- Planification par disponibilité des pistes et portes, Dijkstra pour les trajets, rapport d'événements triés et indicateurs de service (retards, missions, distance, coût estimé, conflits de créneaux évités).
- Suggestions de **211 modèles d'appareils / 24 constructeurs** et des **10 premières compagnies du classement Skytrax 2026** ; les deux champs acceptent aussi une valeur libre.
- Nouveaux modules backend `app/operations` (modèles, validation, routes, logique métier, catalogue) et `app/db.py` ; React reste une couche de présentation.

**Limite importante :** la prévision opérationnelle Python est complémentaire au moteur C++/WebAssembly d'affectation des portes et n'est pas encore intégrée à son modèle de temps. Les résultats chiffrés ne sont donc pas directement interchangeables. La carte 2D initiale est toujours une représentation schématique.

Le catalogue des types est une sélection civile actualisable, **pas une liste exhaustive de tous les avions du monde**. Les entrées personnalisées restent autorisées. Pour les références : [ICAO Doc 8643](https://www.icao.int/operational-safety/Designators-and-indicators), [Skytrax 2026](https://www.worldairlineawards.com/worlds-top-100-airlines-2026/).

**Évolution du schéma V0.5 :** les tables `operational_runways`, `operational_taxiways`, `operational_vehicles` et `operational_tasks` sont initialisées au démarrage de l'application. Des ressources de démonstration sont créées uniquement lorsque leurs tables sont vides. Les données de la flotte V0.3 sont conservées.

### Incidents et optimisation — V0.7.0 (fusion V0.6 + V0.7)

- Incidents datés persistants : fermeture temporaire de piste ou de liaison, panne de véhicule et retard d'un vol.
- Contrôle de la validité des périodes, existence des ressources cibles et cohérence des valeurs.
- Recalcul déterministe des prévisions en tenant compte des perturbations, avec reprise après la période d'indisponibilité ou détournement lorsque le réseau le permet.
- Réservation simplifiée des créneaux de piste et d'un corridor de circulation partagé ; protection des ressources auxquelles un incident est associé.
- Deux politiques de planification : **standard**, affectation fixe, et **optimisée**, comparaison des disponibilités, distances et coûts.
- Analyse comparative calculée depuis les mêmes entrées : stratégie standard, optimisée et prévision sans incidents.
- Indicateurs : nombre de vols terminés et bloqués, délai total/moyen, conflits évités, impact des incidents, distances et coûts des véhicules.
- Historique PostgreSQL de prévisions immuables, indépendantes des modifications ultérieures du planning et des incidents.
- Nouveaux modules et écrans dédiés aux incidents, à la comparaison des résultats et à l'historisation.
- Régression automatisée : scénarios fonctionnels API, contraintes temporelles et de ressources, propriétés des réservations, calculs d'indicateurs, cas limites et tests frontend.

Les calculs sont ceux d'un **modèle pédagogique de prévision par minute**, non d'un système de contrôle aérien réel. Le moteur C++/WebAssembly conserve son propre modèle ; l'unification des calculs reste un chantier ultérieur.

### Interface utilisateur

- Application web développée avec React et TypeScript.

- Carte 2D schématique de l'aéroport.

- Affichage des portes, des avions et d'un véhicule illustratif.

- Contrôle de la simulation : démarrage, pause, reprise et progression pas à pas.

- Réglage de la vitesse de simulation.

- Consultation des résultats et indicateurs disponibles.

- Comparaison de deux politiques d'affectation.

La représentation des véhicules reste actuellement illustrative et n'est pas entièrement synchronisée avec leurs déplacements calculés par le moteur.

### Backend et persistance

- API REST développée avec FastAPI.

- Gestion des scénarios : création, consultation, modification, duplication et suppression (avec bouton de suppression et confirmation).

- Sauvegarde des exécutions de simulation.

- Consultation des comparaisons et des résultats.

- Gestion des données d'aéroport.

- Journal d'audit applicatif.

- Persistance avec PostgreSQL sous Docker.

- Possibilité d'utiliser SQLite en développement local.

- Export de résultats au format JSON.

### Infrastructure et qualité

- Conteneurisation Docker.

- Compilation C++ vers WebAssembly avec Emscripten.

- Tests unitaires C++.

- Tests API Python.

- Workflow GitHub Actions pour les vérifications automatiques.

## 5. État d'avancement

| Module | État |
|---|---|
| Structure Full Stack | Implémentée |
| Interface React / TypeScript | Prototype fonctionnel |
| Moteur de simulation C++ | Version simplifiée implémentée |
| Intégration WebAssembly | Implémentée |
| API REST FastAPI | Implémentée |
| Persistance PostgreSQL | Implémentée |
| Gestion des scénarios | Implémentée (suppression depuis l’interface) |
| Affectation des portes | Version simplifiée |
| Gestion des véhicules | V0.5 : flotte de service CRUD et prévision |
| Recherche de chemins | Implémentation Dijkstra |
| Visualisation des opérations | Partielle |
| Comparaison des stratégies | Version initiale |
| Planning CRUD des vols | V0.2 implémentée (maximum 10) |
| Inventaire des avions et affectation aux vols | V0.3 implémentée |
| Pistes et voies de circulation | V0.5 CRUD + routage graphé |
| Services au sol | V0.5 calendrier simplifié des tâches |
| Catalogue modèles et compagnies | V0.5 suggestions et saisie libre |
| Cycle complet des mouvements des avions | V0.5 : prévision pédagogique Python ; animation/moteur unifié à développer |
| Gestion des pistes et mouvements | V0.5 : planning des créneaux, sans ATC réel |
| Gestion détaillée des opérations au sol | V0.5 : interventions et véhicule ; incidents dynamiques à développer |
| Détection et évitement simplifiés des conflits | V0.7 : créneaux réservés pour la piste et un corridor commun |
| Optimisation multicritère | V0.7 : heuristique temps/distance/coût ; optimisation globale future |
| Authentification et gestion des rôles | À développer |
| Rapports et statistiques avancés | V0.7 : KPI comparatifs et historique des prévisions ; reporting étendu futur |

**Le projet est au stade d’un prototype technique V0.7, avec infrastructure, flotte, gestion des incidents et prévision des opérations (validation Docker complète et navigateur à confirmer sur chaque environnement).** Il permet de valider les échanges entre les différentes technologies, d'exécuter une simulation simplifiée et d'enregistrer les scénarios.

Il ne couvre pas encore l'ensemble des fonctionnalités prévues dans le cahier des charges.

## 6. Fonctionnalités restant à développer

Les prochaines évolutions sont organisées en cinq grandes priorités.

### Priorité 1 — Gestion aéroportuaire complète

- Faire converger le moteur C++ et la prévision Python sur le même modèle de circulation, de tâches et de disponibilité.

- Étendre le planning de vols existant : plus de 10 vols, affectation à un scénario et contraintes avancées.

- Étendre le graphe actuel et prévoir les collisions, fermetures temporaires et itinéraires par type d’appareil.

- Synchroniser les positions animées avec toutes les étapes de la prévision opérationnelle.

- Prise en compte des contraintes liées aux types d'appareils et aux infrastructures.

### Priorité 2 — Gestion des ressources et opérations au sol

- Gestion détaillée des véhicules aéroportuaires.

- Introduction des caractéristiques individuelles : vitesse, capacité, disponibilité et autonomie.

- Modélisation des opérations de ravitaillement, bagages, nettoyage et autres services.

- Gestion des dépendances et durées des interventions.

- Détection et suivi des conflits de circulation et de ressources.

- Replanification automatique après incident.

### Priorité 3 — Optimisation et analyse

- Développement et comparaison de stratégies de planification supplémentaires.

- Optimisation multicritère.

- Prise en compte des coûts opérationnels.

- Calcul d'indicateurs avancés : retards, occupation des portes, utilisation des véhicules et performances des opérations.

- Historique chronologique des événements.

- Génération de rapports détaillés.

### Priorité 4 — Architecture et sécurité

- Refactorisation du moteur C++ en modules indépendants.

- Gestion de plusieurs simulations simultanées.

- Amélioration de l'architecture frontend et backend.

- Authentification des utilisateurs.

- Gestion des rôles et permissions.

- Validation renforcée des données et des résultats.

- Amélioration de la journalisation et de la sécurité.

### Priorité 5 — Tests et stabilisation

- Tests d'intégration entre frontend, moteur et backend.

- Tests de bout en bout avec Playwright.

- Validation du déploiement Docker complet.

- Tests de performance et de charge.

- Tests de non-régression.

- Documentation technique et fonctionnelle complète.

## 7. Organisation du dépôt

```text

AirportOps/

│

├── frontend/              # Application React / TypeScript

│

├── backend/               # API REST Python / FastAPI

│

├── engine/                # Moteur C++ et compilation WebAssembly

│

├── docs/                  # Documentation technique et roadmap

│

├── .github/

│   └── workflows/         # Intégration continue

│

├── docker-compose.yml     # Orchestration des services

├── .env.example           # Exemple de configuration

├── .gitignore             # Fichiers exclus de Git

│

└── README.md              # Présentation du projet

```

## 8. Limites actuelles

AirportOps demeure un simulateur expérimental reposant sur des modèles simplifiés.

Les temps de traitement, comportements des véhicules, contraintes de circulation et stratégies d'affectation ne représentent pas nécessairement les procédures appliquées dans un aéroport réel.

Les résultats transmis à l'API sont actuellement déclarés par le client et ne disposent pas d'une vérification cryptographique garantissant leur intégrité.

Le logiciel n'intègre pas encore de système complet d'authentification, de gestion des autorisations ou de simulation des opérations aéronautiques réelles.

Il est destiné à l'apprentissage, à l'expérimentation algorithmique et à la démonstration d'une architecture logicielle combinant plusieurs langages et technologies.

---

## 9. Évolution du projet

Le développement d'AirportOps se poursuit progressivement, avec pour objectif d'enrichir les capacités de simulation, de renforcer la modélisation des opérations aéroportuaires et d'améliorer les méthodes d'optimisation.

Les développements futurs seront intégrés par étapes, accompagnés de tests et de mises à jour de la documentation.


## 10. Qualité logicielle

La validation automatisée distingue les comportements métier, les contrats API, les invariants de planification et les utilitaires de présentation. Les cas de perturbations et de réordonnancement sont confrontés à des scénarios déterministes et reproductibles. La matrice de vérification et les limites de couverture sont décrites dans [`docs/QUALITY.md`](docs/QUALITY.md).
