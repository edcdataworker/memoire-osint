# Revue humaine et évaluation des 42 articles

Le parcours de revue utilise les 42 textes réservés au test et leurs propositions IA figées. Le modèle, le train et le dev restent identiques. Les prédictions sont masquées pendant la lecture pour réduire l’ancrage sur les sorties du modèle ; les propositions IA restent une source possible d’ancrage.

Codex a examiné les 42 textes et corrigé les brouillons. Son attestation IA, les décisions, les empreintes et les annotations restent dans `Codex_prelecture_attestation_42.json` sur le volume chiffré. Cela atteste une prélecture par IA uniquement : au dernier contrôle, 0 article sur 42 porte une attestation humaine. L’interface présente les propositions corrigées pour la lecture et la validation personnelle.

## Réaliser la revue

1. Monter le volume chiffré MemoireOSINT, puis ouvrir `Lancer_revue_humaine.command` depuis le dossier du bloc 4. L’environnement Python local doit être installé selon le README.
2. Ouvrir [la revue locale](http://127.0.0.1:8767). Saisir son nom de relecteur, lire les conventions, puis le texte intégral de chaque article.
3. Corriger les noms, les labels et les frontières dans les champs. Ajouter les mentions absentes en sélectionnant le passage et son label ; le parcours reste utilisable au clavier avec les positions Unicode.
4. Justifier les ambiguïtés dans la note. Un article sans mention doit aussi être relu et attesté. Les navires/systèmes nommés relèvent de WEAPON, les unités/flottes/districts/bases nommés de MIL_UNIT, et les branches/ministères/alliances militaires de MIL_ORG. Les institutions civiles et noms de personnes sont exclus du schéma.
5. Enregistrer un brouillon pour reprendre plus tard, ou cocher la déclaration de lecture complète puis attester cet article. Toute sauvegarde de brouillon retire l’attestation précédente. Le serveur horodate la décision et conserve l’identité du relecteur.
6. Une fois les 42 articles attestés, cliquer sur « Évaluer les 42 articles relus ». Le calcul vérifie l’empreinte du texte, le manifeste test et l’absence de groupes d’apprentissage/développement. Il produit précision, rappel, F1, résultats par label et erreurs à correspondance exacte.

Le serveur refuse les requêtes d’écriture sans origine locale et jeton de session. La présence de ces mécanismes et des déclarations ne prouve pas, à elle seule, la réalité d’une lecture : l’auteur des attestations doit avoir effectué cette lecture. Aucun nom ni aucune attestation n’est rempli automatiquement sur les textes réels.

## Où les décisions sont conservées

Les fichiers sont dans `/Volumes/MemoireOSINT/B4/Revue_humaine_42` : `progression.json`, `reference_humaine.jsonl`, puis `evaluation_humaine.json` après revue complète. Ils restent privés, avec permissions restrictives. Une référence modifiée nécessite un nouveau dossier de progression. Le lanceur contrôle la présence du volume chiffré et refuse un remplacement en clair.

Le résultat humain ne remplace pas silencieusement le diagnostic IA. Il identifie la référence, le modèle, les déclarations et leur date. Ne pas publier le nom du relecteur avec les textes sans qualification du destinataire et des droits d’usage. Appliquer la procédure D01 du bloc 1 si un article doit être retiré de cette progression.

## Interprétation et suite

Les 18 articles initiaux ont un biais de sélection ; les 24 autres sont stratifiés par longueur et l’ensemble n’est pas pondéré. Une revue humaine rend la référence mieux justifiée, mais ne transforme pas ces 42 textes en estimation de qualité du corpus entier. Une seconde adjudication et un échantillon représentatif seraient nécessaires pour renforcer la portée des résultats.

Ne pas utiliser les corrections de ce test pour entraîner un candidat ensuite évalué sur les mêmes textes. Si elles servent à construire ou régler de nouvelles règles, constituer un autre test indépendant pour mesurer l’amélioration. Les données train/dev doivent avoir leur propre revue avant promotion de production ; les garde-fous de promotion du projet restent distincts des critères scolaires.

Le cours AI Deployment p. 24 demande une relecture humaine d’un échantillon. Une proposition ou une vérification automatique de Codex est une assistance ; cette étape est accomplie seulement après lecture par une personne identifiée.

## État de livraison

Interface, sauvegarde, contrôle de provenance et évaluation testés sur articles fictifs. Les 42 articles réels ne sont pas attestés par les tests. Le fichier `Preuves/Revue_humaine/Verification_interface.json` distingue les parcours synthétiques de l’affichage réel en lecture seule. Les résultats des tests ne sont pas des mesures de qualité NER réelle.
