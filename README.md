# Desk Bourse — données de marché

Chaque matin de semaine (vers 6h15, heure de Paris), un robot GitHub lance `fetch.py` :

1. il récupère les cours historiques des valeurs de `symbols.json` avec **OpenBB** (fournisseur gratuit yfinance, sans clé) ;
2. il ajoute les chiffres clés (PER, rendement, capitalisation), l'objectif et l'avis des analystes et les dernières actus de chaque valeur, plus l'indice peur et avidité crypto (alternative.me) ;
3. il calcule le RSI 14 jours, les moyennes mobiles 20/50/200 jours, les supports/résistances (plus bas / plus haut 20 séances), les plus bas/hauts sur 52 semaines, la volatilité et la tendance ;
4. il enregistre tout dans [`data/marche.json`](data/marche.json).

La mise à jour automatique de **Mon Desk Bourse** lit ce fichier pour remplir les cours, les courbes et les décisions.

- Suivre une nouvelle valeur : ajouter une ligne dans `symbols.json` (code Yahoo Finance dans `ticker`).
- Lancer à la main : onglet **Actions** › *Données Desk Bourse* › **Run workflow**.

Données publiques de marché, fournies sans garantie. Pas un conseil en investissement.
