# Cockpit V3 — cycle de vie Swiper et collections progressives

Ce document décrit le contrat d'architecture introduit pour l'issue #108. Il
s'applique aux deux surfaces du Cockpit V3 : la démonstration (univers fictif,
piloté par `demo-data.json`) et le chemin live (renderer schématisé).

## Principe

Swiper n'est qu'un **moteur de navigation**. Il est initialisé **une seule
fois** par étage et n'est jamais détruit ni reconstruit entre deux collections.
La logique métier et la production du DOM vivent en dehors de Swiper.

```
CollectionProvider ─► CollectionController ─► Renderer ─► HTMLElement ─► Swiper
   (source items)       (cycle de vie)        (DOM pur)                 (navigation)
```

- **CollectionProvider** — la source d'une collection. Il émet les items
  **progressivement** (au fur et à mesure), même quand les données sont déjà en
  mémoire, pour exercer réellement le cycle placeholder → remplacement → append.
  Voir `v3/collection/collection_provider.js` (`streamArray`, `createArrayProvider`).
- **CollectionController** — possède **un** Swiper horizontal pour toute la durée
  de vie de l'étage. Voir `v3/collection/collection_controller.js`.
- **Renderer** — fonctions DOM pures, sans connaissance de Swiper. Voir
  `v3/collection/card_renderer.js`.
- **Swiper** — instance unique, alimentée par `appendSlide()`.

## Cycle de vie d'une collection

1. **Bootstrap (init unique).** Le wrapper est créé avec exactement deux slides :
   - une slide synthétique **`New` en prepend** (index 0), proposée uniquement
     pour les collections créables ;
   - une slide **placeholder**, première carte visible à l'ouverture.
2. **Premier item.** Le contenu du placeholder est **remplacé sur place** par la
   première fiche (aucune nouvelle slide).
3. **Items suivants.** Chaque item arrive **uniquement via `appendSlide()`**, au
   fil de son chargement.
4. **Settle.** Une fois tous les items émis, le contrôleur se positionne sur
   l'index voulu (par défaut la première fiche ; la slide `New` reste à sa
   gauche) et signale l'item actif une fois.

Aucune étape ne détruit Swiper, ne recrée le wrapper ni ne reconstruit les
slides. Changer de collection **réutilise l'instance** via `removeAllSlides()`
puis un nouveau bootstrap + streaming — jamais `destroy()`.

## Deux axes de la démonstration

La démo ajoute une navigation verticale par niveaux au-dessus de l'axe
horizontal des cartes sœurs. Voir `v3/collection/level_controller.js` :

- un Swiper **vertical** à trois slots stables (parent · courant · enfant),
  initialisé une fois ; les niveaux adjacents sont de simples aperçus statiques
  (pas de Swiper imbriqué, ce qui supprime définitivement le _jank_ des Swipers
  nichés) ;
- **un seul** `CollectionController` horizontal, hébergé dans le slot courant,
  re-`load()`é sur la nouvelle collection lors d'un changement de niveau.

Descendre / monter recycle le contenu des trois slots verticaux en place et
recentre par `slideTo(1, 0, false)`. Aucun `destroy()` de deck n'est réémis en
navigation.

## Chemin live

Le renderer live (`v2_app_schema.js`) détient déjà toute la fratrie
(`state.cards` + `snapshot().sibling_ids`). En V3, il **présente la collection
complète** à l'adaptateur `v3_swiper.js`, qui matérialise une slide par sœur via
le même `CollectionController`.

Invariant préservé : **une seule `.v2-card` interactive** à la fois (la slide
active). Les voisines sont des aperçus inertes `.v2-card-preview`, pour que
`#v2-stage .v2-card` continue de désigner la carte active ciblée par les autres
modules (`v2_actions.js`, `information_create.js`, `schema_editor.js`, …). Les
gestes horizontaux sont pilotés par Swiper ; le recognizer maison est désactivé
en V3 live.

## Config Swiper

La configuration reste **minimale** : on ne garde que les options qui diffèrent
des défauts Swiper et dont on a réellement besoin (`CollectionController`,
`BASE_OPTIONS`) :

- `touchReleaseOnEdges: true` — rendre le premier swipe / le relâchement aux bords (iOS) ;
- `roundLengths: true` — texte de carte net sur les slides transformées ;
- `noSwipingSelector` — les contrôles interactifs (boutons, champs) ne déclenchent pas de swipe.

Tout le reste s'appuie sur les défauts Swiper (`slidesPerView`, observers,
`resizeObserver`, `preventClicks`, `noSwiping`, `initialSlide`, vitesse…). La
**vitesse n'est pas surdéfinie**. Le Swiper imbriqué (horizontal, dans le deck
vertical) reçoit `nested: true`, conformément à l'API.

## Frontière

Ceci ne change que la mécanique de rendu et de navigation du Cockpit. Aucune
autorité de gouvernance, Evidence, approbation, autorisation de tâche ou vérité
serveur n'est affectée.

```text
slide chargée != état gouverné validé
projection != source de vérité
transition UI != autorisation
runtime success != Evidence
```
