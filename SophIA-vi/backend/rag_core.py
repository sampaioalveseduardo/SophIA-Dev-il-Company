import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

import ollama

RAIZ = Path(__file__).resolve().parent.parent
BASE_CSV = RAIZ / "documentos" / "base.csv"
SYSTEM_PROMPT_PATH = RAIZ / "system-prompt-final-v4"

MODELO_EMBED = "nomic-embed-text"
MODELO_LLM = "qwen3:8b"
CORTE = 0.68
CORTE_BM25 = 10.0
K1 = 1.5
B = 0.75
MAX_PARES = 2

csv.field_size_limit(10**7)


def similaridade(a, b):
    produto = sum(x * y for x, y in zip(a, b))
    tamanho_a = math.sqrt(sum(x * x for x in a))
    tamanho_b = math.sqrt(sum(y * y for y in b))
    return produto / (tamanho_a * tamanho_b)


def vetorizar(texto):
    return ollama.embeddings(model=MODELO_EMBED, prompt=texto)["embedding"]


def tokenizar(texto):
    return re.findall(r"\w+", texto.lower())


def texto_para_busca(p):
    if p.get("tipo") == "par":
        return p["titulo"]
    return p["titulo"] + " " + p["texto"]


class _Indice:
    """Carrega base.csv e monta o índice BM25 uma única vez, na subida do servidor."""

    def __init__(self):
        with open(BASE_CSV, encoding="utf-8") as f:
            self.base = list(csv.DictReader(f))

        for p in self.base:
            p["vetor"] = json.loads(p["vetor"])

        self.docs = [tokenizar(texto_para_busca(p)) for p in self.base]
        self.tamanho_medio = sum(len(d) for d in self.docs) / len(self.docs)

        self.aparicoes = Counter()
        for d in self.docs:
            for palavra in set(d):
                self.aparicoes[palavra] += 1

        self.N = len(self.docs)

        with open(SYSTEM_PROMPT_PATH, encoding="utf-8") as f:
            self.system_prompt = f.read()

        print(f"[rag_core] base carregada: {len(self.base)} pedacos")
        print(f"[rag_core] vocabulario: {len(self.aparicoes)} palavras distintas")

    def idf(self, palavra):
        n = self.aparicoes.get(palavra, 0)
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def buscar_bm25(self, pergunta):
        termos = tokenizar(pergunta)
        notas = []
        for i, d in enumerate(self.docs):
            contagem = Counter(d)
            nota = 0.0
            for t in termos:
                f = contagem.get(t, 0)
                if f == 0:
                    continue
                saturacao = (f * (K1 + 1)) / (
                    f + K1 * (1 - B + B * len(d) / self.tamanho_medio)
                )
                nota += self.idf(t) * saturacao
            notas.append((nota, self.base[i]))
        notas.sort(key=lambda item: item[0], reverse=True)
        return notas

    def buscar_vetorial(self, pergunta):
        v_pergunta = vetorizar(pergunta)
        notas = []
        for p in self.base:
            notas.append((similaridade(v_pergunta, p["vetor"]), p))
        notas.sort(key=lambda item: item[0], reverse=True)
        return notas

    def buscar(self, pergunta, quantos=3):
        vetorial = self.buscar_vetorial(pergunta)
        lexical = self.buscar_bm25(pergunta)

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

        por_id = {p["id"]: p for p in self.base}
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


_indice = None


def obter_indice():
    global _indice
    if _indice is None:
        _indice = _Indice()
    return _indice


def gerar(mensagens):
    return ollama.chat(model=MODELO_LLM, messages=mensagens, think=False)


def responder(pergunta):
    """Mesma lógica de tutor.py:responder(), mas devolvendo um dicionário
    em vez de imprimir no terminal — é o que a rota /api/chat consome."""
    indice = obter_indice()

    achados = indice.buscar(pergunta, quantos=3)
    aprovados = [(c, b, p) for c, b, p in achados if c >= CORTE or b >= CORTE_BM25]

    debug = [
        {
            "fonte": p["fonte"],
            "referencia": p["referencia"],
            "cosseno": round(c, 3),
            "bm25": round(b, 1),
            "tipo": p.get("tipo"),
            "aprovado": c >= CORTE or b >= CORTE_BM25,
        }
        for c, b, p in achados
    ]

    if not aprovados:
        return {
            "content": "Não encontrei essa informação no material.",
            "sources": [],
            "debug": debug,
        }

    contexto = ""
    for c, b, p in aprovados:
        contexto += f"[{p['fonte']} — {p['referencia']}] {p['titulo']}\n{p['texto']}\n\n"

    resposta = gerar(
        [
            {"role": "system", "content": indice.system_prompt},
            {"role": "user", "content": f"{contexto}Pergunta: {pergunta}"},
        ]
    )

    sources = []
    for _, _, p in aprovados:
        rotulo = f"{p['fonte']}, {p['referencia']}"
        if p.get("tipo") == "par":
            rotulo += " (par pergunta-resposta)"
        sources.append(rotulo)

    return {
        "content": resposta["message"]["content"].strip(),
        "sources": sources,
        "debug": debug,
    }
