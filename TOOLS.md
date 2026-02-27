## Custom Skills - Recruitment Pipeline

### 1. CV_Extractor (parsing.py)
- **Action** : Extrait le texte brut du PDF et le convertit en entités JSON (Compétences, Expériences).
- **Commande** : `py skills/parsing.py "data/CV français - Aramis Sandoz.pdf"`
- **Output** : Crée `data/cv_parsed.json`.

### 2. Match_Scorer (scoring.py)
- **Action** : Compare les infos cruciales du CV avec une description de poste trouvée sur le web.
- **Commande** : `py skills/scoring.py "data/cv_parsed.json" "data/temp_job_desc.json"`
- **Output** : Retourne un pourcentage de similarité et un résumé des points forts.