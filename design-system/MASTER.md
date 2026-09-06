# Episteme design direction

UI/UX Pro Max was consulted using `learning progress dashboard minimal`, then the narrower `developer analytics dashboard`. The first result matched children's educational apps, so it was rejected. The second returned Data-Dense Dashboard with readable hierarchy, explicit status and keyboard-accessible controls; its marketing-page pattern was not applicable.

Applied direction: a calm personal learning workspace, forest-green progress panel, warm-white surfaces, restrained sage accents, Poppins bundled locally, consistent Lucide icons, visible keyboard focus, semantic progress element, reduced motion and mobile layout. The forest palette and Poppins are project-specific editorial choices, not claimed database recommendations. Starter values come only from the backend. Never use invented completion percentages, streaks or activity.

Tokens live in src/style.css. Source checks and their limitations must remain visible in milestone details. Missing connections, loading and errors must have explicit states. A webhook secret alone does not mean GitHub delivery is active.

The sidebar now uses the generated celestial emblem plus episteme wordmark in src/assets/episteme-light.png. Dashboard body and control typography use locally bundled Poppins at the user's request.
