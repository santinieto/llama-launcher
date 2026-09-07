# Release Process

Guía de ramas, versionado y flujo de entrega para `llama-launcher`.

Relacionado con [#4](https://github.com/santinieto/llama-launcher/issues/4).

---

## 1. Tipos de rama

| Tipo | Uso | Ejemplo |
|------|-----|---------|
| `feature/` | Nueva funcionalidad (GUI, skill, integración) | `feature/3__skill-create-github-task` |
| `enhancement/` | Mejora sobre algo existente (perf, UX) | `enhancement/2__mostrar-comando` |
| `bugfix/` | Corrección no urgente en desarrollo | `bugfix/1__unificar-model-yaml` |
| `hotfix/` | Fix crítico en `main`/producción (crash/OOM) | `hotfix/5__fix-oom-35b` |
| `docs/` | Solo documentación | `docs/4__release-process` |
| `chore/` | Mantenimiento (build, deps, gitignore) | `chore/6__actualizar-pyside` |

> `bugfix` vs `hotfix`: `hotfix` nace de `main` y se taguea `vX.Y.Z+1` inmediato; `bugfix` es rama normal que entra por PR a `main`.

---

## 2. Convención de nombre

```text
<tipo>/<numero>__<slug>
```

* `tipo`: uno de la tabla anterior.
* `numero`: ID del issue GitHub (`#1`..`#4`). Sin issue → usar `0` (solo para `chore/docs` menores).
* `__`: doble guión bajo separador (obligatorio).
* `slug`: título en `kebab-case`, sin acentos, `a-z0-9-`, máx 50 chars.

**Válidos:**
```text
feature/3__skill-create-github-task
docs/4__release-process
enhancement/2__mostrar-comando-final
bugfix/1__unificar-model-yaml-base
hotfix/12__fix-oom-qwen35b
```

**Inválidos:**
```text
feature/skill-nueva        # falta numero__
Feature/3__Skill           # mayúsculas
docs/4_release-process     # falta /
```

La codificación permite trazabilidad `rama ↔ issue` y `git log --oneline` legible.

---

## 3. Flujo de trabajo

### 3.1 Crear rama

```powershell
git checkout main
git pull origin main
git checkout -b <tipo>/<numero>__<slug>
# ej: git checkout -b docs/4__release-process
```

### 3.2 Commits

* Mensaje imperativo, corto: `feat:`, `fix:`, `docs:`, `chore:`
* Referenciar issue: `fixes #4` o `related to #2`

```text
docs: documenta release process (fixes #4)
feat: skill create-github-task con validación (fixes #3)
```

### 3.3 Push

```powershell
git push -u origin <tipo>/<numero>__<slug>
```

### 3.4 Pull Request

* Base: `main` ← Compare: tu rama
* Título: mismo que issue (`Unificar model.yaml base...`)
* Body: checklist de criterios del issue + `Closes #<numero>`
* Requerir 1 review (si hay branch protection)

En GitHub:

```powershell
# con gh (si está instalado)
gh pr create --title "docs: release process" --body "Closes #4" --base main
# o crear PR manual en github.com
```

### 3.5 Merge

* **Squash and merge** (recomendado) → 1 commit limpio en `main`
* Borrar rama tras merge (GitHub lo ofrece)

### 3.6 Tag / Release (opcional)

Para cambios user-facing:

```powershell
git checkout main
git pull origin main
git tag -a v0.2.0 -m "v0.2.0: variantes + MTP + release docs"
git push origin v0.2.0
# GitHub → Releases → Draft new release from tag
```

Versionado `SemVer`:
* `MAJOR`: breaking change
* `MINOR`: feature/enhancement
* `PATCH`: bugfix/hotfix/docs

---

## 4. Branch protection (recomendado)

En `Settings → Branches → Add rule` para `main`:

* ☑ Require pull request before merging (1 approval)
* ☑ Require status checks (si hay CI)
* ☑ Do not allow bypassing

Evita `git push origin main` directo.

---

## 5. Ejemplos por issue actual

| Issue | Rama correcta | Comando |
|-------|---------------|---------|
| #1 Unificar model.yaml | `bugfix/1__unificar-model-yaml` o `docs/1__...` | `git checkout -b bugfix/1__unificar-model-yaml` |
| #2 Mostrar comando final | `enhancement/2__mostrar-comando-final` | `git checkout -b enhancement/2__mostrar-comando-final` |
| #3 Skill github tasks | `feature/3__skill-create-github-task` | `git checkout -b feature/3__skill-create-github-task` |
| #4 Release process | `docs/4__release-process` | `git checkout -b docs/4__release-process` |

---

## 6. Checklist para PR

Copiar en descripción del PR:

```markdown
- [ ] Rama sigue `<tipo>/<numero>__<slug>`
- [ ] Commit(s) referencian issue (`fixes #N`)
- [ ] `README.md` actualizado si es feature/docs
- [ ] `.gitignore` respeta binarios pesados (*.gguf, llama.cpp/*.dll)
- [ ] Test manual: `python -m app.main` inicia y lista modelos
- [ ] No incluye `*.gguf`, `logs/`, `dist/build/` ni `.cache/`
```

---

## 7. Referencias

* Issues: https://github.com/santinieto/llama-launcher/issues
* Código relevante: `app/core/model_manager.py:91` (agrupación YAML), `app/core/command_builder.py:44`, `README.md:1`
