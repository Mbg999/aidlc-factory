# AutoSkills — opt-in

Do you want AI-DLC to run AutoSkills (https://github.com/midudev/autoskills) to detect
recommended AI agent *skills* for this repository?

Choose one option:

A) Yes — Run AutoSkills in dry-run and propose skills (no installs)
B) Yes — Run AutoSkills and install recommended skills (non-interactive)
C) No  — Do not run AutoSkills for this workflow

[Answer]:

Notes:
- AutoSkills requires Node.js >= 22 to execute `npx autoskills`.
- When you choose A the workflow will only *propose* skills and will not modify files.
- When you choose B the workflow may install skill files and write `skills-lock.json`.
