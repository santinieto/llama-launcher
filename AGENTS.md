# Instrucciones para agentes

Este archivo es cargado automáticamente por opencode (ver `opencode.json: instructions`).

## Idioma
- Responder en español salvo que el usuario pida otro idioma.
- Ser conciso y factual, sin superlativos innecesarios.

## Proyecto
- `llama-launcher` — gestor local para `llama.cpp` (PySide6, YAML, GGUF).
- Ver `docs/RELEASE_PROCESS.md` para flujo de ramas y versionado.
- Ver `README.md` para arquitectura real (per-variante YAML, MTP auto-detect, backend por modelo).

## Regla crítica — No merge automático

**Nunca hacer merge automático ni cerrar issues sin aprobación explícita del usuario.**

- Crear rama con `git checkout -b <tipo>/<numero>__<slug>` y `git push -u origin <rama>`.
- Abrir PR con `gh` o API, pero dejarlo **open** para review del usuario.
- En commits/PR body usar `related to #N` o `refs #N`, **no** `fixes #N` / `Closes #N` / `Fixes` a menos que el usuario lo pida explícito.
- No usar `gh pr merge` / `git merge` a `main` sin `usuario aprueba merge`.
- No borrar rama remota sin permiso.
- Si el usuario dice “pushea”, solo hace `push`, no `merge`.

## Convención de ramas

Template: `<tipo>/<numero>__<slug>` (doble `__`). Tipos: `feature/`, `enhancement/`, `bugfix/`, `hotfix/`, `docs/`, `chore/` (ver `docs/RELEASE_PROCESS.md:1`).

Ejemplos válidos: `feature/3__skill-create-github-task`, `docs/4__release-process`, `docs/0__instrucciones-agentes`.

## Commits

- Mensaje imperativo, referenciar issue como `related to #N` por defecto.
- No incluir `.gguf`, `llama.cpp/*.dll`, `logs/`, `dist/build/`, `.cache/` (ver `.gitignore`).

## Tras cambiar config de opencode

Recordar al usuario: `quit y restart opencode` para recargar `opencode.json` / `AGENTS.md` / skills.

