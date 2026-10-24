# CropLink Web — cinematic 3D landing page

A standalone React + Vite site that lives next to `croplink-mobile/` and the FastAPI backend.
It does **not** modify the backend, the Expo app, or any API contract.

## Run

```bash
cd croplink-web
npm install
npm run dev        # http://localhost:5173
npm run build      # production bundle in dist/
npm run preview
```

Optional: copy `.env.example` to `.env` to point at a different backend (`VITE_API_URL`).
Default is the Render URL already used by the mobile app. Production hosting needs an SPA
fallback for `/login` and `/register` (`public/_redirects` for Netlify and `vercel.json` are included).

## Stack
React 18 · Vite · plain JavaScript (matches the existing project) · **direct Three.js** (no R3F, no Spline,
no external 3D assets) · GSAP + ScrollTrigger · Lucide · hand-written CSS.

## Structure
```
src/
  scene/        createAgriculturalScene.js  (the island, lights, clouds, particles, camera rig)
                terrain.js                  (procedural terraced height-field, strata, crop scatter)
                bridge.js                   (scroll/pointer state shared with the DOM)
  components/   Navbar, HeroSection, FloatingMarketCards, AgriculturalScene (lazy canvas host),
                ProblemSection, ProductShowcase, MarketIntelligence, HowItWorks,
                VisionSection, FinalCTA, Footer, Logo, Sparkline, SampleBadge
  pages/        LandingPage, AuthPage (/login, /register → real backend)
  api/auth.js   POST /auth/login, POST /auth/register
  data/sample.js  clearly-labelled demonstration data
```

## How the 3D works
* One fixed full-viewport canvas behind the page. The hero and Vision sections are transparent; the cream /
  green sections are opaque and cover it. Rendering pauses whenever neither is on screen.
* Scroll: ScrollTrigger writes two progress values (hero→exit, arrival→vision) into `bridge`; the scene blends
  three camera/island compositions from them and damps toward the result.
* Pointer: damped camera + island parallax; DOM cards use `--mx/--my` CSS variables.
* Crops: a single `InstancedMesh` (~1.8k plants desktop, ~0.5k mobile) with wind sway in the vertex shader.
* Mobile (<960px or coarse pointer): stacked composition, fewer plants/clouds/particles, 512px shadow map,
  no MSAA, DPR capped at 1.5. The scene is never hidden.
* Three.js is code-split and loaded after the hero copy renders. No WebGL / context loss → CSS fallback island.
  `prefers-reduced-motion` → no idle motion, parallax, or scroll choreography.

## Honesty notes
* Anonymous visitors cannot call `/prices/today` or `/forecast` (they require login), so every price, trend,
  profit and recommendation on the page is **sample data**, badged as such. Nothing is presented as live.
* The backend's forecaster and grader are trained on synthetic data (see root README), so no accuracy or
  impact statistics appear anywhere.
* The web app has no farmer/buyer dashboard. After login/register the auth page says so and points users to the mobile app.
* The project contains no contact details or social links, so the footer shows none.
