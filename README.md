# AirportOps — Simulateur de gestion des opérations aéroportuaires

**AirportOps** est un projet de développement logiciel visant à concevoir une plateforme interactive de simulation et d'optimisation des opérations au sol dans un aéroport fictif.

L'objectif est de reproduire, à échelle simplifiée, les principales contraintes liées à la gestion des infrastructures aéroportuaires, à l'affectation des ressources et à la coordination des opérations.

Le projet s'appuie sur plusieurs technologies complémentaires : **React, TypeScript, C++20, WebAssembly, Python, FastAPI et PostgreSQL**.

---

**Version actuelle : V0.2.0 — Planning de vols personnalisable.** La simulation demeure un prototype pédagogique.

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
| Gestion des véhicules | Partielle |
| Recherche de chemins | Implémentation Dijkstra |
| Visualisation des opérations | Partielle |
| Comparaison des stratégies | Version initiale |
| Planning CRUD des vols | V0.2 implémentée (maximum 10) |
| Gestion complète des avions et de leurs mouvements | À développer |
| Gestion des pistes et mouvements | À développer |
| Gestion détaillée des opérations au sol | À développer |
| Détection avancée des conflits | À développer |
| Optimisation multicritère | À développer |
| Authentification et gestion des rôles | À développer |
| Rapports et statistiques avancés | À développer |

**Le projet est actuellement au stade d’un prototype technique V0.2, avec un planning personnalisable (validation complète Docker et navigateur à confirmer sur chaque environnement).** Il permet de valider les échanges entre les différentes technologies, d'exécuter une simulation simplifiée et d'enregistrer les scénarios.

Il ne couvre pas encore l'ensemble des fonctionnalités prévues dans le cahier des charges.

## 6. Fonctionnalités restant à développer

Les prochaines évolutions sont organisées en cinq grandes priorités.

### Priorité 1 — Gestion aéroportuaire complète

- Gestion CRUD des avions et infrastructures ; améliorer la gestion des vols déjà amorcée en V0.2.

- Étendre le planning de vols existant : plus de 10 vols, affectation à un scénario et contraintes avancées.

- Gestion des pistes et voies de circulation.

- Simulation du cycle complet des avions : approche, atterrissage, roulage, stationnement, repoussage et décollage.

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

## 7. Installation et exécution

### Prérequis

Pour la méthode recommandée :

- Git

- Docker Desktop

- Moteur Docker Linux activé

- Connexion Internet pour télécharger les images et les dépendances nécessaires

### Cloner le projet

```bash

git clone https://github.com/Ariony92/AirportOps.git

cd AirportOps

```

### Configurer l'environnement

Copier le fichier `.env.example` vers `.env`, puis **remplacer la valeur d’exemple** de `POSTGRES_PASSWORD` par un mot de passe PostgreSQL de développement unique. Le fichier `.env` reste local et ne doit pas être publié sur GitHub.

Sous PowerShell :

```powershell

Copy-Item .env.example .env

notepad .env

```

Le fichier `.env` ne doit pas être versionné. Le fichier `.env.example` est public et ne doit contenir **aucun secret réel**.

**Important :** si PostgreSQL a déjà créé un volume, changer `POSTGRES_PASSWORD` dans `.env` ne modifie pas automatiquement le mot de passe de l’utilisateur existant. Modifiez le mot de passe côté PostgreSQL ou réinitialisez le volume uniquement si vous n’avez aucune donnée à conserver.

### Démarrer les services

```powershell

docker compose up --build

```

Une fois les services disponibles :
| Service | Adresse |
|---|---|
| Interface web | http://localhost:5173 |
| Documentation API | http://localhost:8000/docs |
| Santé de l'API | http://localhost:8000/health |

Le premier démarrage construit notamment le moteur WebAssembly et le frontend. Il peut nécessiter des téléchargements importants.

### Arrêter l'application

```powershell

docker compose down

```

Pour supprimer également les données persistantes de PostgreSQL :

```powershell

docker compose down -v

```

**Attention :** cette dernière commande supprime le volume de la base de données et les données qui y sont stockées.

## 8. Démarrage en développement local

### Backend — Python / FastAPI

Prérequis : Python 3.11 ou supérieur.

```bash

cd backend

python -m venv .venv

```

Activer l'environnement virtuel, installer les dépendances puis démarrer l'API :

```bash

pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000

```

Sans configuration PostgreSQL, le backend utilise une base SQLite locale.

### Frontend — React / TypeScript

Prérequis : Node.js 22 ou supérieur.

```bash

cd frontend

npm install

npm run dev

```

Si le module WebAssembly n'est pas disponible, le navigateur utilise le moteur TypeScript simplifié de secours.

### Moteur C++ / WebAssembly

La compilation manuelle nécessite Emscripten :

```bash

cd engine

bash build-wasm.sh

```

### Tests C++

```bash

cmake -S engine -B engine/build

cmake --build engine/build

ctest --test-dir engine/build --output-on-failure

```

### Tests du backend

Depuis le dossier `backend` :

```bash

python -m pytest -q

```

### Vérifications frontend et intégration continue

Depuis `frontend/` : `npm run build` et `npm test`. La configuration TypeScript utilise `vite/client` dans `frontend/tsconfig.json`, sans fichier `vite-env.d.ts` supplémentaire. Le workflow GitHub Actions lance les tests du moteur C++, les tests Python et la compilation du frontend.

## 9. Organisation du dépôt

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

## 10. Limites actuelles

AirportOps demeure un simulateur expérimental reposant sur des modèles simplifiés.

Les temps de traitement, comportements des véhicules, contraintes de circulation et stratégies d'affectation ne représentent pas nécessairement les procédures appliquées dans un aéroport réel.

Les résultats transmis à l'API sont actuellement déclarés par le client et ne disposent pas d'une vérification cryptographique garantissant leur intégrité.

Le logiciel n'intègre pas encore de système complet d'authentification, de gestion des autorisations ou de simulation des opérations aéronautiques réelles.

Il est destiné à l'apprentissage, à l'expérimentation algorithmique et à la démonstration d'une architecture logicielle combinant plusieurs langages et technologies.

---

## 11. Évolution du projet

Le développement d'AirportOps se poursuit progressivement, avec pour objectif d'enrichir les capacités de simulation, de renforcer la modélisation des opérations aéroportuaires et d'améliorer les méthodes d'optimisation.

Les développements futurs seront intégrés par étapes, accompagnés de tests et de mises à jour de la documentation.
