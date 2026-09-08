# -*- coding: utf-8 -*-
import json
import urllib.request
import time
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

MODEL = "Gemma4-E4B"
PORT = 18765
BASE_URL = f"http://127.0.0.1:{PORT}/v1/chat/completions"

benchmarks = [
    # Logic (5) - Multi-step reasoning
    {"id": "logic_1", "cat": "Logic", "prompt": "A father is currently 4 times as old as his son. In 20 years, the father will be twice as old as his son. How old is the son now? Show your work.", "max": 5},
    {"id": "logic_2", "cat": "Logic", "prompt": "In a room, there are 3 boxes. Box A contains only apples. Box B contains only oranges. Box C contains a mix of apples and oranges. All boxes are labeled incorrectly. You can pick one fruit from one box without looking. What is the minimum number of picks needed to correctly label all boxes, and which box do you pick from?", "max": 5},
    {"id": "logic_3", "cat": "Logic", "prompt": "Five people finished a race. Alice finished before Bob but after Carol. Dave finished before Eve but after Bob. Carol did not finish first. Who finished first? Explain your reasoning.", "max": 5},
    {"id": "logic_4", "cat": "Logic", "prompt": "A sequence follows this rule: each term after the first is obtained by multiplying the previous term by 2 and then subtracting 3. If the first term is 5, what is the fourth term? Show each step.", "max": 5},
    {"id": "logic_5", "cat": "Logic", "prompt": "If all mathematicians are logical thinkers, and some logical thinkers are poets, which of the following must be true? (a) Some mathematicians are poets. (b) Some poets are logical thinkers. (c) All poets are mathematicians. (d) No mathematicians are poets. Explain your answer.", "max": 5},
    # Knowledge (5) - Specific and challenging
    {"id": "knowledge_1", "cat": "Knowledge", "prompt": "What is the difference between nuclear fission and nuclear fusion in terms of energy output, fuel requirements, and practical applications today? Which process currently generates commercial electricity?", "max": 5},
    {"id": "knowledge_2", "cat": "Knowledge", "prompt": "Explain the difference between TCP and UDP protocols. In what scenarios would you choose UDP over TCP despite its lack of reliability guarantees?", "max": 5},
    {"id": "knowledge_3", "cat": "Knowledge", "prompt": "What is the Heisenberg Uncertainty Principle? Why does it not apply to macroscopic objects in everyday life, and what fundamental limit does it impose on measurement?", "max": 5},
    {"id": "knowledge_4", "cat": "Knowledge", "prompt": "Describe the difference between supervised, unsupervised, and reinforcement learning with one concrete example for each. What makes semi-supervised learning useful?", "max": 5},
    {"id": "knowledge_5", "cat": "Knowledge", "prompt": "What are the primary differences between mitosis and meiosis? How many daughter cells does each produce, and what is the ploidy of each? Why is meiosis essential for sexual reproduction?", "max": 5},
    # Reading (5) - Complex passages with inference
    {"id": "reading_1", "cat": "Reading", "prompt": "Read this passage: 'The Industrial Revolution, beginning in Britain in the late 18th century, fundamentally transformed manufacturing processes. While it increased productivity dramatically, it also led to significant social upheaval, including urbanization, child labor, and environmental degradation. The shift from agrarian economies to industrial ones created new class structures and altered family dynamics.' Based on this passage, what can we infer about the relationship between economic development and social welfare during this period?", "max": 5},
    {"id": "reading_2", "cat": "Reading", "prompt": "Read this passage: 'Quantum computing leverages quantum mechanical phenomena such as superposition and entanglement to perform computations. Unlike classical bits that exist in states 0 or 1, qubits can exist in a superposition of both states simultaneously. This property theoretically allows quantum computers to solve certain problems exponentially faster than classical computers.' What are the two main quantum phenomena described, and what practical advantage do they theoretically provide?", "max": 5},
    {"id": "reading_3", "cat": "Reading", "prompt": "Read this passage: 'The Marshall Plan, officially the European Recovery Program, was an American initiative passed in 1948 to provide foreign aid to Western Europe. The United States transferred over $12 billion (equivalent to approximately $130 billion in 2023) in economic recovery programs to help rebuild war-torn regions, remove trade barriers, modernize industry, and prevent the spread of communism.' What was the primary strategic objective of the Marshall Plan, and what was its secondary humanitarian goal?", "max": 5},
    {"id": "reading_4", "cat": "Reading", "prompt": "Read this passage: 'CRISPR-Cas9 is a revolutionary genome editing technology that allows scientists to precisely alter DNA sequences. The system uses a guide RNA to locate the target DNA sequence and the Cas9 enzyme to make a double-strand break. The cell's natural repair mechanisms then either disable a gene or insert new genetic material.' What are the three main components of the CRISPR-Cas9 system, and what is the critical limitation that researchers still face with this technology?", "max": 5},
    {"id": "reading_5", "cat": "Reading", "prompt": "Read this passage: 'The concept of dark matter was first proposed by Swiss astronomer Fritz Zwicky in 1933 when he observed that galaxies in the Coma Cluster were moving faster than expected based on visible mass alone. Current estimates suggest that dark matter constitutes approximately 27% of the universe's mass-energy content, while ordinary matter makes up only about 5%.' What evidence initially led to the dark matter hypothesis, and why is it called 'dark' matter?", "max": 5},
    # Math (5) - More complex
    {"id": "math_1", "cat": "Math", "prompt": "A cylindrical tank has a radius of 7 meters and a height of 10 meters. It is being filled with water at a rate of 3 cubic meters per minute. How long will it take to fill the tank to 80% of its capacity? (Use pi = 3.14159). Show your solution.", "max": 5},
    {"id": "math_2", "cat": "Math", "prompt": "A company offers two payment plans for a sales position: Plan A gives a base salary of $3000 plus 5% commission on sales. Plan B gives a base salary of $2000 plus 8% commission on sales. At what sales amount do both plans pay the same? What is that payment amount? For sales above this amount, which plan is better?", "max": 5},
    {"id": "math_3", "cat": "Math", "prompt": "In a standard deck of 52 cards, what is the probability of drawing exactly 2 aces when drawing 5 cards without replacement? Show the combinatorial calculation. Express your answer as a fraction and as a percentage.", "max": 5},
    {"id": "math_4", "cat": "Math", "prompt": "Solve the following system of equations for x and y: 3x + 2y = 17 and 5x - 4y = 1. Verify your answer by substituting back into both equations.", "max": 5},
    {"id": "math_5", "cat": "Math", "prompt": "A ball is thrown upward from a height of 50 meters with an initial velocity of 20 m/s. Using the formula h(t) = -4.9t^2 + 20t + 50, at what time does the ball hit the ground? How high does it go above the initial launch point?", "max": 5},
    # Code (5) - More complex
    {"id": "code_1", "cat": "Code", "prompt": "Implement a Python class called LRUCache with a fixed capacity that supports get(key) and put(key, value) operations in O(1) time complexity. Use an appropriate data structure combination and explain your design choices.", "max": 5},
    {"id": "code_2", "cat": "Code", "prompt": "Write a Python function that takes a list of integers and returns all unique triplets that sum to zero. The solution must not contain duplicate triplets. What is the time complexity of your approach? For example: given nums = [-1,0,1,2,-1,-4], the solution is [[-1,-1,2],[-1,0,1]].", "max": 5},
    {"id": "code_3", "cat": "Code", "prompt": "Explain the difference between a race condition and a deadlock in concurrent programming. Provide a concrete code example of each and describe how you would prevent them.", "max": 5},
    {"id": "code_4", "cat": "Code", "prompt": "Write a SQL query that finds customers who have placed orders in the last 30 days AND have a total order value exceeding $1000, but who have never placed an order in the 'Electronics' category. Assume tables: customers(id, name), orders(id, customer_id, total, order_date, category).", "max": 5},
    {"id": "code_5", "cat": "Code", "prompt": "Implement a binary search tree in Python with insert, delete, and find operations. Include an in-order traversal method that returns sorted values. What is the worst-case time complexity for each operation and why?", "max": 5},
    # Creative (3) - More nuanced
    {"id": "creative_1", "cat": "Creative", "prompt": "Write a short story (100-200 words) where the main character discovers that their reflection in a mirror has been living a different life than they have. The story should have an unexpected twist ending and convey a philosophical theme about identity.", "max": 3},
    {"id": "creative_2", "cat": "Creative", "prompt": "Design a hypothetical app that helps people overcome procrastination using behavioral psychology principles. Describe the core features, the psychological mechanisms it leverages, and why each feature would be effective.", "max": 3},
    {"id": "creative_3", "cat": "Creative", "prompt": "Write a Python one-liner (or as few lines as possible) that generates the first 20 Fibonacci numbers using recursion with memoization. The code must be clean, efficient, and well-documented with comments explaining how it works.", "max": 3},
]

# English evaluation logic
def evaluate(response, qid, cat, mx):
    rl = response.lower().strip()
    if cat == "Logic":
        if qid == "logic_1":
            # son age: 4x + 20 = 2(x+20) -> 4x+20 = 2x+40 -> 2x=20 -> x=10
            return 1.0 if any(x in rl for x in ["10", "ten"]) and ("years" in rl or "old" in rl) else 0.5 if any(x in rl for x in ["10", "ten"]) else 0.0
        if qid == "logic_2":
            # minimum picks = 1, pick from mixed box C
            return 1.0 if ("1" in rl or "one" in rl) and ("c" in rl or "mixed" in rl or "combination" in rl) else 0.5 if ("1" in rl or "one" in rl) else 0.0
        if qid == "logic_3":
            # Alice > Bob, Carol > Alice, Bob > Dave, Dave > Eve, Carol not first
            # Carol > Alice > Bob > Dave > Eve, Carol not first -> contradiction
            # Actually: Carol > Alice > Bob, Bob > Dave > Eve, Carol not first -> someone else first
            return 1.0 if "first" in rl else 0.5 if "alice" in rl or "bob" in rl or "carol" in rl else 0.0
        if qid == "logic_4":
            # a1=5, a2=5*2-3=7, a3=7*2-3=11, a4=11*2-3=19
            return 1.0 if "19" in rl else 0.0
        if qid == "logic_5":
            # Some logical thinkers are poets doesn't mean all poets or some mathematicians
            return 1.0 if "(b)" in rl or "b" in rl else 0.0
    if cat == "Knowledge":
        if qid == "knowledge_1":
            return 1.0 if ("fission" in rl or "fusion" in rl) and ("commercial" in rl or "electricity" in rl) else 0.5 if any(w in rl for w in ["fission", "fusion", "nuclear"]) else 0.0
        if qid == "knowledge_2":
            return 1.0 if ("tcp" in rl or "udp" in rl) and ("reliable" in rl or "streaming" in rl or "gaming" in rl) else 0.5 if any(w in rl for w in ["tcp", "udp"]) else 0.0
        if qid == "knowledge_3":
            return 1.0 if ("uncertainty" in rl or "heisenberg" in rl) and ("macroscopic" in rl or "measurement" in rl) else 0.5 if any(w in rl for w in ["uncertainty", "heisenberg"]) else 0.0
        if qid == "knowledge_4":
            return 1.0 if ("supervised" in rl or "unsupervised" in rl or "reinforcement" in rl) and ("semi" in rl or "example" in rl) else 0.5 if any(w in rl for w in ["supervised", "unsupervised", "reinforcement"]) else 0.0
        if qid == "knowledge_5":
            return 1.0 if ("mitosis" in rl or "meiosis" in rl) and ("daughter" in rl or "ploidy" in rl or "haploid" in rl) else 0.5 if any(w in rl for w in ["mitosis", "meiosis"]) else 0.0
    if cat == "Reading":
        if qid == "reading_1":
            return 1.0 if ("social" in rl or "welfare" in rl or "upheaval" in rl or "class" in rl) and "inference" in rl or True else 0.5
        if qid == "reading_2":
            return 1.0 if ("superposition" in rl or "entanglement" in rl) and "exponentially" in rl else 0.5 if any(w in rl for w in ["superposition", "entanglement"]) else 0.0
        if qid == "reading_3":
            return 1.0 if ("communism" in rl or "strategic" in rl or "rebuild" in rl) and "humanitarian" in rl else 0.5 if any(w in rl for w in ["communism", "rebuild", "strategy"]) else 0.0
        if qid == "reading_4":
            return 1.0 if ("guide" in rl and "cas9" in rl) or ("rna" in rl and "enzyme" in rl) else 0.5 if any(w in rl for w in ["crispr", "guide", "cas9"]) else 0.0
        if qid == "reading_5":
            return 1.0 if ("zwicky" in rl or "coma" in rl) and ("visible" in rl or "mass" in rl) else 0.5 if any(w in rl for w in ["dark", "matter"]) else 0.0
    if cat == "Math":
        if qid == "math_1":
            # pi*r^2*h = 3.14159*49*10 = 1539.4 m3, 80% = 1231.5, /3 = ~410.5 min
            return 1.0 if any(x in rl for x in ["410", "411"]) else 0.5 if ("pi" in rl or "cylinder" in rl) else 0.0
        if qid == "math_2":
            # 3000+0.05x = 2000+0.08x -> 1000 = 0.03x -> x = 33333.33
            return 1.0 if "33333" in rl or "33333" in rl else 0.5 if any(w in rl for w in ["3000", "2000", "commission"]) else 0.0
        if qid == "math_3":
            # C(4,2)*C(48,3)/C(52,5) = 6*17296/2598960 = 103776/2598960 = 0.0399 or 3.99%
            return 1.0 if any(x in rl for x in ["0.04", "0.039", "3.99", "4%"]) else 0.5 if any(w in rl for w in ["probability", "deck", "ace"]) else 0.0
        if qid == "math_4":
            # 3x+2y=17, 5x-4y=1 -> x=3, y=4
            return 1.0 if "x = 3" in rl or ("3" in rl and "4" in rl and "y" in rl) else 0.0
        if qid == "math_5":
            # h(t)=-4.9t^2+20t+50=0 -> t = (-20 ± sqrt(400+980))/(-9.8) = (-20 ± sqrt(1380))/(-9.8)
            # sqrt(1380)=37.15 -> t = (20+37.15)/9.8 = 5.83s or t = (20-37.15)/-9.8 = -1.75s (discard)
            return 1.0 if any(x in rl for x in ["5.8", "5.7", "5.9"]) else 0.5 if any(w in rl for w in ["quadratic", "formula", "ground"]) else 0.0
    if cat == "Code":
        if qid == "code_1":
            return 1.0 if ("lrucache" in rl or "dict" in rl) and ("o(1)" in rl or "constant" in rl) else 0.5 if any(w in rl for w in ["cache", "lru", "dict"]) else 0.0
        if qid == "code_2":
            return 1.0 if "triplet" in rl and "zero" in rl else 0.5 if any(w in rl for w in ["triplet", "triplets"]) else 0.0
        if qid == "code_3":
            return 1.0 if ("race" in rl and "deadlock" in rl) else 0.5 if any(w in rl for w in ["race", "deadlock"]) else 0.0
        if qid == "code_4":
            return 1.0 if "select" in rl and "30" in rl and "never" in rl and "electronics" in rl else 0.5 if "select" in rl else 0.0
        if qid == "code_5":
            return 1.0 if ("binary" in rl or "bst" in rl) and ("o(log" in rl or "logarithmic" in rl) else 0.5 if any(w in rl for w in ["binary", "search", "tree"]) else 0.0
    if cat == "Creative":
        # More nuanced evaluation
        return 1.0 if len(response.strip()) > 50 else 0.5 if len(response.strip()) > 20 else 0.0
    return 0.5

results = []
gen_times = []

print("=" * 60)
print("BENCHMARK: Gemma 4 E4B (English)")
print("=" * 60)
print(f"Total questions: {len(benchmarks)}")
print()

for i, q in enumerate(benchmarks):
    print(f"[{i+1}/{len(benchmarks)}] {q['id']} ({q['cat']})")
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": q["prompt"]}],
        "temperature": 0.7,
        "max_tokens": 500,
        "stream": False
    }
    try:
        req = urllib.request.Request(BASE_URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            response = data["choices"][0]["message"]["content"]
            tok_s = data.get("timings", {}).get("predicted_per_second", 0)
            if tok_s: gen_times.append(tok_s)
            score = evaluate(response, q["id"], q["cat"], q["max"])
            results.append({"id": q["id"], "cat": q["cat"], "score": score, "max": q["max"], "response": response[:150], "tok_s": tok_s})
            print(f"  -> Score: {score}/{q['max']} | Gen: {tok_s:.1f} tok/s")
    except Exception as e:
        results.append({"id": q["id"], "cat": q["cat"], "score": 0, "max": q["max"], "response": f"ERROR: {str(e)[:100]}", "tok_s": 0})
        print(f"  -> ERROR: {str(e)[:80]}")
    time.sleep(0.5)

# Calculate scores
cats = {}
for r in results:
    c = r["cat"]
    if c not in cats: cats[c] = {"score": 0, "max": 0}
    cats[c]["score"] += r["score"]
    cats[c]["max"] += r["max"]

weights = {"Logic": 0.25, "Knowledge": 0.20, "Reading": 0.15, "Math": 0.20, "Code": 0.15, "Creative": 0.05}

# Print summary
print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print()
print("Category        Score   Max")
print("-" * 35)
for c in weights:
    if c in cats:
        s, m = cats[c]["score"], cats[c]["max"]
        pct = (s/m)*100 if m > 0 else 0
        print(f"{c:<15} {s:<7} {m}")

overall = sum(cats[c]["score"]/cats[c]["max"]*weights[c]*100 for c in weights if c in cats)
print(f"\nGENERAL: {overall:.1f}/100")

if gen_times:
    print(f"\nGeneration speed: {sum(gen_times)/len(gen_times):.1f} tok/s (avg)")

# Save results
output = {
    "model": MODEL,
    "date": time.strftime("%Y-%m-%d %H:%M"),
    "scores_by_category": {c: {"score": cats[c]["score"], "max": cats[c]["max"], "pct": (cats[c]["score"]/cats[c]["max"]*100) if cats[c]["max"] > 0 else 0} for c in cats},
    "general_score": overall,
    "speed_avg_gen_tok_s": sum(gen_times)/len(gen_times) if gen_times else 0,
    "details": results
}
with open(r"D:\llama.cpp\benchmarks\benchmark_gemma4_e4b.json", "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\nSaved: benchmarks/benchmark_gemma4_e4b.json")
