# AirportOps — Validation technique (V0.9.0)

## Suites automatisées

| Domaine | Couverture |
|---|---|
| Règles métier | Prévision déterministe, détection de conflits, affectation véhicules, ruptures et retards |
| API / SQLite | Création, validation et suppression des ressources, incidents, historiques |
| API de lecture | Cohérence entre timeline, mouvements horodatés et KPI |
| Scénarios et comparaison | Calculs côté serveur, différences de KPI correctes, absence d’import de résultats non vérifiés |
| Accès public | API accessible sans connexion, génération de scénarios côté serveur et validation des entrées |
| Frontend | Compilateur TypeScript/Vite, utilitaires de présentation |
| Scénarios paramétrés | Retard, panne, graine reproductible, reproductibilité et absence de mutation du planning |
| Navigateur | Parcours des pages, lecture/pause et incidents avec Playwright/Chromium |
| Conteneurisation | Vérification Compose, démarrage API et base PostgreSQL en CI |
| Versionnement | Vérification SemVer entre frontend, backend, documentation et lock npm |

## Limites de couverture

Les tests locaux Python n'exécutent pas automatiquement l'interface Chromium ni les images Docker. Les tests E2E sont exécutés dans le job CI dédié avec des navigateurs téléchargés. Le moteur historique C++/WebAssembly a été retiré du code actif ; les prévisions sont calculées par le backend Python. L'API de lecture n'implique aucune simulation ATC certifiée. L'API publique n'isole pas encore les écritures de chaque visiteur, et les contrôles de débit restent à développer.

La granularité métier reste la minute et la carte applique une interpolation graphique entre les positions clés. Les données de carburant, coûts et disponibilité restent des approximations pédagogiques. La CI ne remplace pas une revue de sécurité externe ni la validation de compatibilité des migrations sur un volume PostgreSQL réel et préexistant.
