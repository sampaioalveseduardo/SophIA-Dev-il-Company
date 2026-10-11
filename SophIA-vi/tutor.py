import csv
import json
import math
import sys

csv.field_size_limit(10**7)

BASE = "documentos/base.csv"


def similaridade(a, b):
    produto = sum(x * y for x, y in zip(a, b))
    tamanho_a = math.sqrt(sum(x * x for x in a))
    tamanho_b = math.sqrt(sum(y * y for y in b))
    return produto / (tamanho_a * tamanho_b)


import ollama

MODELO_EMBED = "nomic-embed-text"


def vetorizar(texto):
    return ollama.embeddings(model=MODELO_EMBED, prompt=texto)["embedding"]


with open(BASE, encoding="utf-8") as f:
    base = list(csv.DictReader(f))

for p in base:
    p["vetor"] = json.loads(p["vetor"])

print("base carregada:", len(base), "pedacos")

import re
from collections import Counter

K1 = 1.5
B = 0.75
MAX_PARES = 2


def tokenizar(texto):
    return re.findall(r"\w+", texto.lower())


def texto_para_busca(p):
    """O que o BM25 indexa de cada item.

    Num par pergunta-resposta e so a pergunta, pelo mesmo motivo do vetor:
    a comparacao que interessa e pergunta do aluno contra pergunta do par.
    """
    if p.get("tipo") == "par":
        return p["titulo"]
    return p["titulo"] + " " + p["texto"]


docs = [tokenizar(texto_para_busca(p)) for p in base]
tamanho_medio = sum(len(d) for d in docs) / len(docs)

aparicoes = Counter()
for d in docs:
    for palavra in set(d):
        aparicoes[palavra] += 1

N = len(docs)


def idf(palavra):
    n = aparicoes.get(palavra, 0)
    return math.log(1 + (N - n + 0.5) / (n + 0.5))


print("vocabulario:", len(aparicoes), "palavras distintas")
print("tamanho medio dos pedacos:", round(tamanho_medio), "palavras")

def buscar_bm25(pergunta):
    termos = tokenizar(pergunta)
    notas = []
    for i, d in enumerate(docs):
        contagem = Counter(d)
        nota = 0.0
        for t in termos:
            f = contagem.get(t, 0)
            if f == 0:
                continue
            saturacao = (f * (K1 + 1)) / (f + K1 * (1 - B + B * len(d) / tamanho_medio))
            nota += idf(t) * saturacao
        notas.append((nota, base[i]))
    notas.sort(key=lambda item: item[0], reverse=True)
    return notas


def buscar_vetorial(pergunta):
    v_pergunta = vetorizar(pergunta)
    notas = []
    for p in base:
        notas.append((similaridade(v_pergunta, p["vetor"]), p))
    notas.sort(key=lambda item: item[0], reverse=True)
    return notas


def buscar(pergunta, quantos=3):
    vetorial = buscar_vetorial(pergunta)
    lexical = buscar_bm25(pergunta)

    cosseno = {}
    bm = {}
    pontos = {}

    for posicao, (nota, p) in enumerate(vetorial, 1):
        cosseno[p["id"]] = nota
        pontos[p["id"]] = pontos.get(p["id"], 0) + 1 / (60 + posicao)

    for posicao, (nota, p) in enumerate(lexical, 1):
        bm[p["id"]] = nota
        if nota > 0:
            pontos[p["id"]] = pontos.get(p["id"], 0) + 1 / (60 + posicao)

    por_id = {p["id"]: p for p in base}
    melhores = sorted(pontos.items(), key=lambda item: item[1], reverse=True)
    
    escolhidos = []
    pares_usados = 0

    for pid, _ in melhores:
        if por_id[pid].get("tipo") == "par":
            if pares_usados >= MAX_PARES:
                continue
            pares_usados += 1
        escolhidos.append(pid)
        if len(escolhidos) == quantos:
            break

    return [(cosseno[pid], bm[pid], por_id[pid]) for pid in escolhidos]


MODELO_LLM = "qwen3:8b"
CORTE = 0.68
CORTE_BM25 = 10.0

with open("system-prompt-final-v4", encoding="utf-8") as f:
    SYSTEM = f.read()

USAR_CPU = "--cpu" in sys.argv


def gerar(mensagens):
    """Chama o modelo e, se a GPU falhar, explica como resolver.

    Quando o Ollama e encerrado a forca, o contexto CUDA fica preso e o
    carregamento seguinte morre com "CUDA error: shared object initialization
    failed". Nao adianta cair para CPU: o qwen3:8b leva minutos por resposta
    assim. O que resolve e reiniciar o servico direito.
    """
    opcoes = {"num_gpu": 0} if USAR_CPU else None

    try:
        return ollama.chat(
            model=MODELO_LLM, messages=mensagens, think=False, options=opcoes
        )
    except ollama.ResponseError as erro:
        if "CUDA" not in str(erro):
            raise

        print()
        print("A GPU falhou ao carregar o modelo.")
        print("Costuma acontecer quando o Ollama foi fechado a forca e o")
        print("contexto da placa ficou preso. Para resolver:")
        print("  1. feche o Ollama pela bandeja do Windows, ao lado do relogio")
        print("  2. espere uns 10 segundos")
        print("  3. abra o Ollama de novo e rode este programa")
        print()
        print("Se precisar rodar agora sem GPU, use: python tutor.py --cpu")
        print("(funciona, mas cada resposta leva varios minutos)")
        raise SystemExit(1)


def responder(pergunta):
    print("=" * 70)
    print("PERGUNTA:", pergunta)
    print("=" * 70)

    achados = buscar(pergunta, quantos=3)
    aprovados = [(c, b, p) for c, b, p in achados if c >= CORTE or b >= CORTE_BM25]

    print()
    for c, b, p in achados:
        passou = c >= CORTE or b >= CORTE_BM25
        marca = "ok   " if passou else "baixa"
        tipo = "PAR   " if p.get("tipo") == "par" else "trecho"
        print(
            f"  {marca} cos {c:.3f}  bm25 {b:5.1f}  {tipo}  "
            f"{p['fonte']} | {p['referencia']}"
        )

    if not aprovados:
        print()
        print("RESPOSTA: Não encontrei essa informação no material.")
        print()
        return

    contexto = ""
    for c, b, p in aprovados:
        contexto += f"[{p['fonte']} — {p['referencia']}] {p['titulo']}\n{p['texto']}\n\n"

    resposta = gerar([
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"{contexto}Pergunta: {pergunta}"},
    ])

    print()
    print("RESPOSTA:", resposta["message"]["content"].strip())
    print()
    consultados = []
    for _, _, p in aprovados:
        rotulo = f"{p['fonte']}, {p['referencia']}"
        if p.get("tipo") == "par":
            rotulo += " (par)"
        consultados.append(rotulo)

    print("TRECHOS CONSULTADOS:", "; ".join(consultados))
    print()


def conversar():
    """Modo conversa: o usuario digita a pergunta e a SophIA responde.

    Nao da para fazer isso no 'ollama run' direto: la a conversa e so com o
    modelo, sem os documentos. A busca que encontra o trecho certo esta aqui
    no Python, e e ela que impede a SophIA de inventar.
    """
    print()
    print("=" * 70)
    print("SophIA — tutora de estágio do polo UNOPAR Salgueiro")
    print("=" * 70)
    print("Digite a sua pergunta e aperte Enter.")
    print("Para sair, escreva 'sair' ou aperte Ctrl+C.")

    while True:
        try:
            pergunta = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté mais.")
            return

        if not pergunta:
            continue
        if pergunta.lower() in ("sair", "exit", "quit"):
            print("Até mais.")
            return

        print()
        responder(pergunta)


conversar()
