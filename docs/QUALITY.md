# AirportOps — Validation technique (V0.7.0)

## Stratégie de validation

La couverture porte en priorité sur les comportements susceptibles d'affecter la cohérence d'une prévision, la persistance des données et les décisions d'affectation. Les tests sont reproductibles et ne dépendent pas de données réelles d'aéroport.

| Domaine | Scénarios couverts | Critère de validité |
|---|---|---|
| Compatibilité | Création et gestion des scénarios, vols, avions et infrastructures | Les API et traitements hérités restent fonctionnels |
| Contraintes de pistes | Arrivées rapprochées, départs concurrents, séparation temporelle | Aucune réservation chevauchante avec l'écart requis |
| Circulation | Dijkstra, segment fermé hors itinéraire, segment bloquant et itinéraire de détour | Le coût du détour est pris en compte ; une fermeture sans effet ne retarde pas les vols |
| Incidents | Fenêtres temporelles, incidents désactivés, pannes successives, retard de vol | Les contraintes temporelles affectent les phases concernées |
| Ressources | Véhicules indisponibles, sous-capacité, carburant insuffisant, maintenance | Les interventions restent compatibles avec les disponibilités simulées |
| Stratégies | Planification standard contre optimisée sur données identiques | Écarts de délais/coûts cohérents et mesurables |
| Prévisions | Déterminisme, absence de mutation des données sources | Même entrée = même résultat, sans modifier l'état métier |
| API REST | CRUD, validation 404/409/422, protection des références | Aucun objet incohérent après refus de transaction |
| Historique | Instantané enregistré puis désactivation de l'incident | Le résultat historisé reste inchangé |
| Utilitaires frontend | Écarts, signes, arrondis, référence sans retard | Les bénéfices et régressions sont affichés sans inversion |
| C++/TypeScript | Régressions des horaires personnalisés et stratégies du moteur existant | Les comportements antérieurs sont préservés |

## Périmètre de la CI

Le workflow GitHub Actions compile et teste le moteur C++, exécute la suite pytest et compile le frontend avec TypeScript/Vite avant d'exécuter les tests Node.js. Les tests backend utilisent SQLite isolée pour valider les contrats API et le calcul métier ; le déploiement Docker/PostgreSQL complet demeure une vérification d'intégration distincte.

## Limites de validation

- L'ordonnancement des voies de circulation reste basé sur un corridor agrégé et une granularité à la minute.
- Le modèle de prévision Python reste distinct de l'exécution C++/WebAssembly.
- Les comportements visuels du navigateur ne sont pas encore couverts par des tests E2E Playwright.
- L'exécution PostgreSQL réelle, les migrations Alembic et les tests de charge multi-utilisateur ne font pas partie de la suite automatisée actuelle.
- Les heuristiques d'affectation ne garantissent pas un optimum global ; les indicateurs permettent de mesurer les gains ou régressions sur chaque scénario.
