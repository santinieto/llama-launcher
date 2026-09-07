---
name: create-github-task
description: "Crea tareas/issues en GitHub para llama-launcher con formato Titulo, Contexto, Problematica, Posible solucion y Criterios de aceptacion. Use ONLY when user says crea tarea github, crea issue, nueva tarea github, github task, crear tarea, o pide plantilla de issue."
---

# Create GitHub Task — Skill para issues estructurados

Skill para crear tareas en `santinieto/llama-launcher` con estructura consistente.

Debe generar issues con **5 secciones obligatorias** y crearlos vía API de GitHub.

---

## Campos obligatorios

1. **Titulo** — resumen imperativo, corto (<80 chars). Ej: `Mostrar comando final de llama-server en UI/logs`
2. **Contexto** — dónde está el problema, archivos/líneas, estado actual. Referenciar `file:line` cuando sea posible (`app/core/command_builder.py:44`, `README.md:1`, `docs/RELEASE_PROCESS.md:1`).
3. **Problematica** — qué falla o qué falta, impacto.
4. **Posible solucion** — enfoque sugerido, archivos a tocar, alternativas consideradas.
5. **Criterios de aceptacion** — checklist ` - [ ] ` verificable.

Si falta alguno, **pedir al usuario** el campo faltante antes de crear el issue. No inventar.

---

## Flujo

### 1. Validar

- Comprobar que los 5 campos no están vacíos.
- Titulo en imperativo, sin punto final.
- Contexto incluye referencia a archivos reales (verificar con `read`/`grep` si es necesario).

### 2. Generar markdown (plantilla)

```markdown
## Contexto
<contexto con referencias file:line>

## Problematica
<que falla, impacto>

## Posible solucion
<enfoque, archivos, usar docs/RELEASE_PROCESS.md para rama>

## Criterios de aceptacion
- [ ] <criterio 1>
- [ ] <criterio 2>
- [ ] Documentado en README/docs si aplica
```

### 3. Crear issue vía API

Obtener token del credential helper (mismo que usa `git push`):

```powershell
$cred = "protocol=https`nhost=github.com`n`n" | git credential fill
# extrae username/password (password = token gho_...)
```

Crear con `Invoke-RestMethod`:

```powershell
$token = ($cred | Select-String "password=(.*)").Matches.Groups[1].Value
$headers = @{ "Authorization" = "Bearer $token"; "Accept" = "application/vnd.github+json" }
$body = @{
  title = "<Titulo>"
  body = "<markdown generado>"
  labels = @("enhancement") # o bug/docs según posible solucion
} | ConvertTo-Json -Depth 4 -Compress

Invoke-RestMethod -Uri "https://api.github.com/repos/santinieto/llama-launcher/issues" -Method Post -Headers $headers -Body $body -ContentType "application/json"
```

Retornar `html_url` y `number`. No asignar `fixes` automático — usar `related to #N` por defecto (ver `AGENTS.md:12`).

### 4. Labels sugeridas

| Contexto | Labels |
|----------|--------|
| bug/crash/OOM | `bug` |
| nueva funcionalidad | `enhancement` |
| docs/README/RELEASE_PROCESS | `documentation` |
| mejora UX/perf | `enhancement` |
| duplicado | `duplicate` |

Si no existe el label, crear sin labels y actualizar luego vía PATCH.

---

## Ejemplo

**Usuario:** `crea tarea: mostrar comando final en UI`

**Skill genera:**

- Titulo: `Mostrar comando final de llama-server en UI/logs`
- Contexto: `CommandBuilder.build app/core/command_builder.py:44 construye args pero main_window.py:410 solo loguea [System] Lanzando...`
- Problematica: `No se puede depurar ni reproducir comando manualmente`
- Posible solucion: `Mostrar [CMD] en LogViewer app/gui/log_viewer.py:1 + botón Copiar en ModelCard`
- Criterios: `- [ ] UI muestra comando completo`, `- [ ] Copiable`, `- [ ] Por variante`

Luego ejecuta POST y retorna `https://github.com/santinieto/llama-launcher/issues/2`.

---

## Reglas

- Respetar `AGENTS.md:12` (no auto-merge, PR queda `open`, no `fixes` sin aprobación).
- Rama para implementar: `<tipo>/<numero>__<slug>` según `docs/RELEASE_PROCESS.md:15` (ej: `enhancement/2__mostrar-comando-final`).
- No crear tareas sin los 5 campos.
- Verificar archivos con `read` antes de referenciarlos.
- Ser conciso y factual.

