# HEARTBEAT.md - Veille Stratégique Active

## Routine Automatisée (Toutes les 6 heures)
- **Scanning Web** : Lancer une recherche via `web_search` sur les mots-clés : "Stage ML Ops 2026 Paris", "Stage Machine Learning Intern 2026", "Stage LLM Engineering 2 mois", "Stage AI Engineer 2026".
- **Scoring Invisible** : Pour chaque nouveau résultat, extraire la description et exécuter `skills/scoring.py` par rapport au profil d'Aramis.
- **Filtrage** : Ignorer systématiquement les offres dont la durée est supérieure à 3 mois ou dont le score de matching est inférieur à 70%.

## Notifications & Mémoire
- **Alerte Haute Priorité** : Si une offre dépasse 85% de matching, créer immédiatement une note dans `memory/alerts/` et préparer un brouillon de message de candidature.
- **Mise à jour Journalière** : Une fois par jour, compiler le nombre d'offres scannées dans `MEMORY.md` pour suivre l'évolution du marché.

## Maintenance Skill
- Vérifier que `data/cv_parsed.json` est toujours synchronisé avec la version PDF du CV.

# Répondre HEARTBEAT_OK si aucune action critique n'est requise.