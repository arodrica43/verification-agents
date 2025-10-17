# Big Data Match Game (Angular 18, no backend)

**Install**
```bash
npm i -g @angular/cli
npm i
```

**Run locally**
```bash
npm start
```

**Build for GitHub Pages**
1. The build outputs to `docs/` with base-href `/big-data-match-game/`.
2. Build:
```bash
npm run build:prod
```
3. Commit & push.
4. GitHub → Settings → Pages → Source: *Deploy from Branch*, Branch: `main`, Folder: `/docs`.
5. Open: `https://<your-user>.github.io/big-data-match-game/`.

**Features**
- Tech → Use Case (drag & drop, single best)
- Use Case → Tech (multi-select with F1 scoring)
- Difficulty filters, timer, shuffle, Answer Key
- Import/Export JSON and in-app editor (localStorage)

**Customize**
- Click **Edit Data** in the app to change the deck.
- Or edit `src/app/data.ts` and rebuild.