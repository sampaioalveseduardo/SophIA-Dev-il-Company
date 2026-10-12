import csv
import json
import ollama

ENTRADA = "documentos/pedacos.csv"
SAIDA = "documentos/base.csv"
MODELO = "nomic-embed-text"


def vetorizar(texto):
    resposta = ollama.embeddings(model=MODELO, prompt=texto)
    return resposta["embedding"]


with open(ENTRADA, encoding="utf-8") as f:
    pedacos = list(csv.DictReader(f))

print("pedacos lidos:", len(pedacos))

base = []

for i, p in enumerate(pedacos, 1):
    if p.get("tipo") == "par":
        alvo = p["titulo"]
    else:
        alvo = p["titulo"] + "\n" + p["texto"]

    vetor = vetorizar(alvo)
    base.append({**p, "vetor": json.dumps(vetor)})
    print(f"  {i}/{len(pedacos)} vetorizado", end="\r")

print()

with open(SAIDA, "w", newline="", encoding="utf-8") as f:
    escritor = csv.DictWriter(
        f,
        fieldnames=[
            "id", "fonte", "referencia", "titulo", "texto", "tipo", "trecho", "vetor"
        ],
    )
    escritor.writeheader()
    escritor.writerows(base)

print(f"salvo: {SAIDA} com {len(base)} pedacos vetorizados")