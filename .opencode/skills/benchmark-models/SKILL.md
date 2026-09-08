---
name: benchmark-models
description: "Ejecuta benchmarks de inteligencia para modelos GGUF disponibles en el repositorio. Evalua razonamiento, conocimiento, matematicas, programacion y creatividad con tests en ingles. Genera reportes comparativos. Use ONLY when user says benchmark, evalua modelo, compara modelos, test inteligencia, bench, o genera reporte inteligencia."
---

# Benchmark Models — Evaluador de Inteligencia de Modelos

Skill para ejecutar benchmarks de inteligencia general sobre modelos GGUF disponibles en `models/`.

Evalua capacidades cognitivas del modelo en 6 categorias con preguntas desafiantes en ingles y genera un reporte de inteligencia con puntuacion comparativa.

Las preguntas estan diseñadas para modelos de 7-8B parametros — son desafiantes pero no imposibles. Tests de dificultad media-alta cubriendo razonamiento multi-paso, conocimiento cientifico, algebra, algoritmos, y creatividad.

**Nota**: Las preguntas son en inglés porque el evaluador verifica respuestas en inglés. El modelo debe responder en inglés para obtener una evaluacion precisa.


---

# 1. Objetivo

Permitir al usuario:
- Evaluar la inteligencia de modelos locales
- Comparar variantes del mismo modelo (Q4_K_M vs Q5_K_M, etc.)
- Obtener metricas objetivas por categoria
- Generar reportes para decidir que modelo usar segun el caso de uso

---

# 2. Categorias de Benchmark

## 2.1 Razonamiento Logico (25%)

Preguntas que evaluan capacidad de deduccion multi-paso, razonamiento algebraico, y resolucion de problemas complejos.

```yaml
- id: logic_1
  prompt: "A father is currently 4 times as old as his son. In 20 years, the father will be twice as old as his son. How old is the son now? Show your work."
  eval:
    pass: "Son is 10 years old + algebraic reasoning (4x+20=2(x+20))"
    partial: "Correct age without full reasoning"
    fail: "Incorrect age or no reasoning"

- id: logic_2
  prompt: "In a room, there are 3 boxes. Box A contains only apples. Box B contains only oranges. Box C contains a mix of apples and oranges. All boxes are labeled incorrectly. You can pick one fruit from one box without looking. What is the minimum number of picks needed to correctly label all boxes, and which box do you pick from?"
  eval:
    pass: "1 pick from Box C (mixed) + correct reasoning about labels"
    partial: "Correct box identified but incomplete reasoning"
    fail: "Incorrect strategy or wrong box"

- id: logic_3
  prompt: "Five people finished a race. Alice finished before Bob but after Carol. Dave finished before Eve but after Bob. Carol did not finish first. Who finished first? Explain your reasoning."
  eval:
    pass: "Correct ordering with explanation of contradictions"
    partial: "Partial ordering without complete reasoning"
    fail: "Incorrect ordering or no explanation"

- id: logic_4
  prompt: "A sequence follows this rule: each term after the first is obtained by multiplying the previous term by 2 and then subtracting 3. If the first term is 5, what is the fourth term? Show each step."
  eval:
    pass: "19 with all steps shown (5->7->11->19)"
    partial: "Correct answer without showing all steps"
    fail: "Incorrect answer"

- id: logic_5
  prompt: "If all mathematicians are logical thinkers, and some logical thinkers are poets, which of the following must be true? (a) Some mathematicians are poets. (b) Some poets are logical thinkers. (c) All poets are mathematicians. (d) No mathematicians are poets. Explain your answer."
  eval:
    pass: "(b) Some poets are logical thinkers + syllogism reasoning"
    partial: "Correct answer without explanation"
    fail: "Incorrect answer or no reasoning"
```

## 2.2 Conocimiento General (20%)

Preguntas de ciencia, tecnologia, fisica, y biologia que requieren conocimiento profundo y conceptual.

```yaml
- id: knowledge_1
  prompt: "What is the difference between nuclear fission and nuclear fusion in terms of energy output, fuel requirements, and practical applications today? Which process currently generates commercial electricity?"
  eval:
    pass: "Correct comparison + fission for commercial electricity"
    partial: "Partial comparison or missing practical application"
    fail: "Confused or incorrect"

- id: knowledge_2
  prompt: "Explain the difference between TCP and UDP protocols. In what scenarios would you choose UDP over TCP despite its lack of reliability guarantees?"
  eval:
    pass: "Correct protocol differences + valid UDP use cases (streaming, gaming, VoIP)"
    partial: "Correct protocol differences but weak use cases"
    fail: "Confused or incorrect"

- id: knowledge_3
  prompt: "What is the Heisenberg Uncertainty Principle? Why does it not apply to macroscopic objects in everyday life, and what fundamental limit does it impose on measurement?"
  eval:
    pass: "Correct principle + explanation of macroscopic vs quantum + measurement limit"
    partial: "Correct principle but incomplete explanation"
    fail: "Incorrect or confused"

- id: knowledge_4
  prompt: "Describe the difference between supervised, unsupervised, and reinforcement learning with one concrete example for each. What makes semi-supervised learning useful?"
  eval:
    pass: "Correct descriptions + examples for all three + semi-supervised explanation"
    partial: "Correct descriptions but missing examples"
    fail: "Confused or incomplete"

- id: knowledge_5
  prompt: "What are the primary differences between mitosis and meiosis? How many daughter cells does each produce, and what is the ploidy of each? Why is meiosis essential for sexual reproduction?"
  eval:
    pass: "Correct differences + daughter cell counts + ploidy + reproduction explanation"
    partial: "Correct differences but missing ploidy or reproduction"
    fail: "Confused or incorrect"
```

## 2.3 Comprension Lectora (15%)

Capacidad de extraer informacion de textos cientificos complejos, inferir significados, y analizar argumentos.

```yaml
- id: reading_1
  prompt: "Read this passage: 'The Industrial Revolution, beginning in Britain in the late 18th century, fundamentally transformed manufacturing processes. While it increased productivity dramatically, it also led to significant social upheaval, including urbanization, child labor, and environmental degradation. The shift from agrarian economies to industrial ones created new class structures and altered family dynamics.' Based on this passage, what can we infer about the relationship between economic development and social welfare during this period?"
  eval:
    pass: "Nuanced inference about tradeoffs between productivity and social costs"
    partial: "Basic inference without nuance"
    fail: "No inference or incorrect"

- id: reading_2
  prompt: "Read this passage: 'Quantum computing leverages quantum mechanical phenomena such as superposition and entanglement to perform computations. Unlike classical bits that exist in states 0 or 1, qubits can exist in a superposition of both states simultaneously. This property theoretically allows quantum computers to solve certain problems exponentially faster than classical computers.' What are the two main quantum phenomena described, and what practical advantage do they theoretically provide?"
  eval:
    pass: "Superposition and entanglement + exponential speedup for certain problems"
    partial: "Correct phenomena but missing exponential advantage"
    fail: "Incorrect or confused"

- id: reading_3
  prompt: "Read this passage: 'The Marshall Plan, officially the European Recovery Program, was an American initiative passed in 1948 to provide foreign aid to Western Europe. The United States transferred over $12 billion (equivalent to approximately $130 billion in 2023) in economic recovery programs to help rebuild war-torn regions, remove trade barriers, modernize industry, and prevent the spread of communism.' What was the primary strategic objective of the Marshall Plan, and what was its secondary humanitarian goal?"
  eval:
    pass: "Strategic: prevent communism spread + Humanitarian: rebuild war-torn regions"
    partial: "One objective correct"
    fail: "Incorrect or missing objectives"

- id: reading_4
  prompt: "Read this passage: 'CRISPR-Cas9 is a revolutionary genome editing technology that allows scientists to precisely alter DNA sequences. The system uses a guide RNA to locate the target DNA sequence and the Cas9 enzyme to make a double-strand break. The cell's natural repair mechanisms then either disable a gene or insert new genetic material.' What are the three main components of the CRISPR-Cas9 system, and what is the critical limitation that researchers still face with this technology?"
  eval:
    pass: "guide RNA + Cas9 enzyme + repair mechanism + off-target effects limitation"
    partial: "Correct components but missing limitation"
    fail: "Incorrect or incomplete"

- id: reading_5
  prompt: "Read this passage: 'The concept of dark matter was first proposed by Swiss astronomer Fritz Zwicky in 1933 when he observed that galaxies in the Coma Cluster were moving faster than expected based on visible mass alone. Current estimates suggest that dark matter constitutes approximately 27% of the universe's mass-energy content, while ordinary matter makes up only about 5%.' What evidence initially led to the dark matter hypothesis, and why is it called 'dark' matter?"
  eval:
    pass: "Galaxy rotation anomaly + does not emit/reflect light"
    partial: "One part correct"
    fail: "Incorrect or confused"
```

## 2.4 Matematicas (20%)

Operaciones, algebra, geometria avanzada, combinatoria, y razonamiento cuantitativo.

```yaml
- id: math_1
  prompt: "A cylindrical tank has a radius of 7 meters and a height of 10 meters. It is being filled with water at a rate of 3 cubic meters per minute. How long will it take to fill the tank to 80% of its capacity? (Use pi = 3.14159). Show your solution."
  eval:
    pass: "Correct calculation (~410 minutes) + proper formula"
    partial: "Correct formula but arithmetic error"
    fail: "Incorrect or no work shown"

- id: math_2
  prompt: "A company offers two payment plans for a sales position: Plan A gives a base salary of $3000 plus 5% commission on sales. Plan B gives a base salary of $2000 plus 8% commission on sales. At what sales amount do both plans pay the same? What is that payment amount? For sales above this amount, which plan is better?"
  eval:
    pass: "x=$33,333 + payment=$4,667 + Plan A better above"
    partial: "Correct breakeven point but incomplete analysis"
    fail: "Incorrect or no comparison"

- id: math_3
  prompt: "In a standard deck of 52 cards, what is the probability of drawing exactly 2 aces when drawing 5 cards without replacement? Show the combinatorial calculation. Express your answer as a fraction and as a percentage."
  eval:
    pass: "C(4,2)*C(48,3)/C(52,5) + correct fraction (~3.99%)"
    partial: "Correct setup but arithmetic error"
    fail: "Incorrect or no combinatorial work"

- id: math_4
  prompt: "Solve the following system of equations for x and y: 3x + 2y = 17 and 5x - 4y = 1. Verify your answer by substituting back into both equations."
  eval:
    pass: "x=3, y=4 + verification by substitution"
    partial: "Correct answer without verification"
    fail: "Incorrect answer"

- id: math_5
  prompt: "A ball is thrown upward from a height of 50 meters with an initial velocity of 20 m/s. Using the formula h(t) = -4.9t^2 + 20t + 50, at what time does the ball hit the ground? How high does it go above the initial launch point?"
  eval:
    pass: "t≈5.83s + max height = 70.4m (20.4m above launch)"
    partial: "Correct time but missing max height"
    fail: "Incorrect or no quadratic solution"
```

## 2.5 Programacion (15%)

Estructuras de datos avanzadas, algoritmos, concurrencia, SQL complejo, y arquitectura de software.

```yaml
- id: code_1
  prompt: "Implement a Python class called LRUCache with a fixed capacity that supports get(key) and put(key, value) operations in O(1) time complexity. Use an appropriate data structure combination and explain your design choices."
  eval:
    pass: "LRUCache class + O(1) + dict + doubly linked list explanation"
    partial: "Working cache but missing O(1) or explanation"
    fail: "Incorrect or non-functional"

- id: code_2
  prompt: "Write a Python function that takes a list of integers and returns all unique triplets that sum to zero. The solution must not contain duplicate triplets. What is the time complexity of your approach? For example: given nums = [-1,0,1,2,-1,-4], the solution is [[-1,-1,2],[-1,0,1]]."
  eval:
    pass: "Working solution + O(n^2) or O(n^2 log n) complexity"
    partial: "Correct approach but has duplicates"
    fail: "Incorrect solution"

- id: code_3
  prompt: "Explain the difference between a race condition and a deadlock in concurrent programming. Provide a concrete code example of each and describe how you would prevent them."
  eval:
    pass: "Correct definitions + code examples + prevention strategies"
    partial: "Correct definitions but no examples"
    fail: "Confused or incorrect"

- id: code_4
  prompt: "Write a SQL query that finds customers who have placed orders in the last 30 days AND have a total order value exceeding $1000, but who have never placed an order in the 'Electronics' category. Assume tables: customers(id, name), orders(id, customer_id, total, order_date, category)."
  eval:
    pass: "Correct JOIN + subquery + date filter + NOT EXISTS"
    partial: "Correct logic but syntax error"
    fail: "Incorrect query"

- id: code_5
  prompt: "Implement a binary search tree in Python with insert, delete, and find operations. Include an in-order traversal method that returns sorted values. What is the worst-case time complexity for each operation and why?"
  eval:
    pass: "Working BST + O(log n) average / O(n) worst case explanation"
    partial: "Working BST but missing complexity analysis"
    fail: "Incorrect or non-functional"
```

## 2.6 Creatividad (5%)

Capacidad de generar ideas originales, escritura creativa con temas profundos, y resolucion de problemas con restricciones.

```yaml
- id: creative_1
  prompt: "Write a short story (100-200 words) where the main character discovers that their reflection in a mirror has been living a different life than they have. The story should have an unexpected twist ending and convey a philosophical theme about identity."
  eval:
    pass: "Story within word count + twist ending + philosophical theme"
    partial: "Story with theme but no twist"
    fail: "Too short, no theme, or generic"

- id: creative_2
  prompt: "Design a hypothetical app that helps people overcome procrastination using behavioral psychology principles. Describe the core features, the psychological mechanisms it leverages, and why each feature would be effective."
  eval:
    pass: "App design + specific psychology principles (e.g., commitment device, variable reward) + effectiveness explanation"
    partial: "App concept but vague psychology"
    fail: "Generic or no psychology connection"

- id: creative_3
  prompt: "Write a Python one-liner (or as few lines as possible) that generates the first 20 Fibonacci numbers using recursion with memoization. The code must be clean, efficient, and well-documented with comments explaining how it works."
  eval:
    pass: "Clean recursive Fibonacci + memoization + correct output + comments"
    partial: "Working code but missing comments or memoization"
    fail: "Incorrect or non-recursive"
```

---

# 3. Scoring

## Puntuacion por Categoria

Cada pregunta se evalua:
- ✅ Pass = 1 punto
- ⚠️ Partial = 0.5 puntos
- ❌ Fail = 0 puntos

### Pesos por Categoria

| Categoria | Peso | Preguntas | Maximo |
|-----------|------|-----------|--------|
| Razonamiento Logico | 25% | 5 | 5 |
| Conocimiento General | 20% | 5 | 5 |
| Comprension Lectora | 15% | 5 | 5 |
| Matematicas | 20% | 5 | 5 |
| Programacion | 15% | 5 | 5 |
| Creatividad | 5% | 3 | 3 |

### Puntuacion General

```text
Score General = (Logico * 0.25) + (Conocimiento * 0.20) + (Comprension * 0.15) +
                (Matematicas * 0.20) + (Programacion * 0.15) + (Creatividad * 0.05)
```

Normalizado a escala 0-100.

### Clasificacion

| Score | Nivel |
|-------|-------|
| 90-100 | 🟢 Excelente |
| 75-89 | 🟢 Bueno |
| 60-74 | 🟠 Aceptable |
| 45-59 | 🟠 Basico |
| <45 | 🔴 Degradado |

**Nota**: Los tests estan diseñados para ser desafiantes pero realistas para un modelo de 7-8B parametros. Un score de 60-70/100 es esperable y no indica que el modelo este "roto" — refleja la dificultad de las preguntas, no la calidad del modelo.

---

# 4. Flujo de Ejecucion

## 4.1 Detectar modelos disponibles

```powershell
Get-ChildItem D:\llama.cpp\models -Directory | Where-Object {
    Test-Path "$($_.FullName)\model.yaml"
} | Select-Object Name
```

## 4.2 Seleccionar modelos a evaluar

Preguntar al usuario:
1. ¿Evaluar todos los modelos o seleccion especifica?
2. ¿Que variantes? (todas o una especifica)

## 4.3 Verificar modelo activo

```powershell
Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'" |
    Select-Object ProcessId, CommandLine |
    Format-List
```

Si no hay modelo activo, pedir al usuario que lance uno primero.

## 4.4 Ejecutar benchmarks

Para cada modelo/variante seleccionado:

1. Verificar que el servidor llama-server esta activo en el puerto correspondiente
2. Ejecutar el script `benchmarks/run_benchmark.py` (Python 3) que llama a la API
3. El script contiene 28 preguntas en inglés en 6 categorias
4. Cada pregunta se envia via API con temperature=0.7 y max_tokens=500
5. Capturar respuestas + metricas (tok/s)
6. Evaluar respuestas con los criterios del script
7. Calcular score por categoria

### Script de ejecucion

El script `benchmarks/run_benchmark.py` ya contiene todos los prompts en inglés, la funcion de evaluacion, y la generacion del reporte JSON. Para ejecutar:

```powershell
python benchmarks/run_benchmark.py
```

### API Template

```python
import urllib.request, json
body = json.dumps({"model": "<alias>", "messages": [{"role": "user", "content": "<prompt>"}], "temperature": 0.7, "max_tokens": 500, "stream": False}).encode()
req = urllib.request.Request("http://127.0.0.1:<port>/v1/chat/completions", data=body, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=120)
data = json.loads(resp.read())
response = data["choices"][0]["message"]["content"]
tok_s = data.get("timings", {}).get("predicted_per_second", 0)
```

## 4.5 Generar reporte

Ver seccion 5.

---

# 5. Formato de Reporte

## 5.1 Reporte Individual

```markdown
# Benchmark: <Modelo> <Variante>

**Fecha**: <YYYY-MM-DD HH:MM>
**Servidor**: llama-server en puerto <port>

## Resumen

| Categoria | Score | Nivel |
|-----------|-------|-------|
| Razonamiento Logico | X/5 | 🟢/🟠/🔴 |
| Conocimiento General | X/5 | 🟢/🟠/🔴 |
| Comprension Lectora | X/5 | 🟢/🟠/🔴 |
| Matematicas | X/5 | 🟢/🟠/🔴 |
| Programacion | X/5 | 🟢/🟠/🔴 |
| Creatividad | X/3 | 🟢/🟠/🔴 |
| **GENERAL** | **XX/100** | **🟢/🟠/🔴** |

## Detalle por Categoria

### Razonamiento Logico

| ID | Pregunta | Resultado | Score |
|----|----------|-----------|-------|
| logic_1 | Si todos los gatos... | ✅ | 1.0 |
| logic_2 | Encuentra el patron... | ⚠️ | 0.5 |
| ... | ... | ... | ... |

### Conocimiento General
[...detalle similar...]

## Fortalezas
- <categoria con mejor score>: <descripcion>
- <otra fortaleza>

## Debilidades
- <categoria con peor score>: <descripcion>
- <otra debilidad>

## Velocidad

| Metrica | Valor |
|---------|-------|
| Prompt tok/s | X |
| Generation tok/s | X |

## Recomendacion

<basado en el score y las categorias, recomendar para que casos de uso es ideal este modelo>
```

## 5.2 Reporte Comparativo (multiples modelos)

```markdown
# Comparativa de Modelos

**Fecha**: <YYYY-MM-DD HH:MM>

## Ranking General

| # | Modelo | Variante | Score | Nivel |
|---|--------|----------|-------|-------|
| 1 | <modelo> | <variante> | XX/100 | 🟢 |
| 2 | <modelo> | <variante> | XX/100 | 🟢 |
| 3 | <modelo> | <variante> | XX/100 | 🟠 |

## Comparativa por Categoria

| Categoria | <Modelo 1> | <Modelo 2> | <Modelo 3> |
|-----------|------------|------------|------------|
| Razonamiento | X/5 | X/5 | X/5 |
| Conocimiento | X/5 | X/5 | X/5 |
| Comprension | X/5 | X/5 | X/5 |
| Matematicas | X/5 | X/5 | X/5 |
| Programacion | X/5 | X/5 | X/5 |
| Creatividad | X/3 | X/3 | X/3 |

## Analisis

### Mejor para Razonamiento
<modelo> con <score> — <por que>

### Mejor para Conocimiento
<modelo> con <score> — <por que>

### Mejor para Codigo
<modelo> con <score> — <por que>

## Recomendaciones por Caso de Uso

| Caso de Uso | Modelo Recomendado | Razon |
|-------------|-------------------|-------|
| Asistente general | <modelo> | <score general mas alto> |
| Coding assistant | <modelo> | <mejor en programacion> |
| Investigacion | <modelo> | <mejor en conocimiento> |
| Razonamiento complejo | <modelo> | <mejor en logica> |

## Velocidad

| Modelo | Gen tok/s | Prompt tok/s |
|--------|-----------|--------------|
| <modelo 1> | X | X |
| <modelo 2> | X | X |
```

---

# 6. Exportar Resultados

Guardar en `benchmarks/`:

```yaml
# benchmarks/<modelo>_<variante>_<fecha>.yaml
model: <nombre_modelo>
variant: <variante>
date: <YYYY-MM-DD HH:MM>
scores:
  logic: X/5
  knowledge: X/5
  reading: X/5
  math: X/5
  code: X/5
  creativity: X/3
  general: XX/100
details:
  logic_1:
    score: 1.0
    response: "<respuesta truncada>"
  logic_2:
    score: 0.5
    response: "<respuesta truncada>"
speed:
  prompt_tok_s: X
  generation_tok_s: X
```

---

# 7. Reglas

- Ejecutar benchmarks solo con un modelo activo y funcionando
- No saltar categorias sin razon
- Evaluar consistentemente con los mismos criterios
- Guardar resultados para historial comparativo
- No inferir capacidades no evaluadas
- Ser objetivo en la evaluacion (no asumir que modelos grandes son mejores)
- Incluir metricas de velocidad en cada reporte
- Comparar solo modelos con proposito similar

---

# 8. Archivos

- **Skill**: `.opencode/skills/benchmark-models/SKILL.md`
- **Resultados**: `benchmarks/*.yaml`
- **Modelos**: `models/*/model.yaml`
- **Logs**: `logs/<modelo>/`
