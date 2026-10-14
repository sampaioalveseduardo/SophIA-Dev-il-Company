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
# quantos candidatos a busca entrega para o juiz do reranking
RERANK_CANDIDATOS = 10

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

    def buscar(self, pergunta, quantos=3, max_pares=MAX_PARES):
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
                if pares_usados >= max_pares:
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


GENTILEZAS = (
    "obrigad", "valeu", "vlw", "agradeç", "agradec", "ajudou", "entendi",
    "perfeito", "beleza", "show", "bom dia", "boa tarde", "boa noite",
    "olá", "ola", "oi", "tchau", "até mais", "ate mais", "falou",
)

EMOJIS = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF️]"
)


def limpar_formato(texto):
    """Tira emoji da saida.

    O prompt proibe emoji desde a primeira versao e ainda assim escapa um
    aqui e ali. Como e cosmetico, resolver na saida e deterministico e nao
    depende do modelo colaborar.
    """
    return re.sub(r"[ \t]+", " ", EMOJIS.sub("", texto)).strip()


def eh_conversa_social(mensagem):
    """Agradecimento, saudacao ou despedida: nao e pergunta sobre o material.

    Sem isso, "obrigado" era tratado como pergunta: a busca nao achava nada
    nos trechos, nenhum passava do corte, e a SophIA respondia "Nao encontrei
    essa informacao no material" para quem estava agradecendo.

    Os filtros evitam confundir com pergunta de verdade. Quem pergunta
    escreve mais e costuma usar interrogacao, mas a interrogacao so
    desqualifica a partir de cinco palavras -- senao "oi, tudo bem?" seria
    tratado como consulta ao material.
    """
    texto = mensagem.lower().strip()
    palavras = texto.split()

    if len(palavras) > 8:
        return False
    if "?" in texto and len(palavras) > 4:
        return False

    return any(g in texto for g in GENTILEZAS)


def fontes_necessarias(pergunta):
    """Quantos trechos pedir ao juiz, decidido pelo formato da pergunta.

    Calibrar isso pela instrucao em linguagem natural nao funcionou: pedindo
    "o menor numero possivel", o juiz devolvia um trecho so em todas as
    perguntas e as cruzadas quebravam. A quantidade passou a ser decidida
    aqui, e o juiz so escolhe quais.

    A marca de pergunta composta e grosseira de proposito: um "e" ligando
    dois pedidos, ou dois pontos de interrogacao.
    """
    texto = pergunta.lower()
    composta = " e " in texto or texto.count("?") > 1
    return 3 if composta else 2


def reranquear(pergunta, candidatos, quantos):
    """Reordena os candidatos pedindo ao LLM que escolha os que servem.

    A busca pontua cada trecho sozinho contra a pergunta inteira. Numa
    pergunta de duas partes, o trecho que responde so a segunda metade tem
    nota baixa, porque a outra metade da pergunta nao combina com ele -- e um
    trecho morno sobre o assunto geral passa na frente. O LLM le a pergunta e
    os trechos juntos, entao enxerga essa relacao.

    Tres travas para ele nao quebrar o sistema: so numeros sao aceitos da
    resposta, o limite de pares continua valendo sobre a escolha, e se nao
    vier nada valido o sistema volta para a ordem da busca.
    """
    lista = ""
    for i, (_, _, p) in enumerate(candidatos, 1):
        lista += "[%d] %s — %s: %s\n" % (
            i, p["fonte"], p["referencia"], p["titulo"],
        )
        lista += p["texto"][:280] + "\n\n"

    exemplo = ", ".join(str(n) for n in range(1, quantos + 1))
    instrucao = (
        "Pergunta do aluno: " + pergunta + "\n\n"
        "Trechos numerados:\n\n" + lista +
        "Escolha exatamente %d trechos, do mais útil para o menos útil. "
        "Se a pergunta tiver mais de uma parte, escolha trechos que cubram "
        "todas elas.\n"
        "Responda só com os números separados por vírgula, nada além disso.\n"
        "Exemplo de resposta: %s" % (quantos, exemplo)
    )

    resposta = gerar([{"role": "user", "content": instrucao}])

    ordem = []
    for achado in re.findall(r"\d+", resposta["message"]["content"]):
        i = int(achado) - 1
        if 0 <= i < len(candidatos) and i not in ordem:
            ordem.append(i)

    if not ordem:
        return candidatos[:quantos]

    escolhidos = []
    pares = 0

    for i in ordem:
        if candidatos[i][2].get("tipo") == "par":
            if pares >= MAX_PARES:
                continue
            pares += 1
        escolhidos.append(candidatos[i])
        if len(escolhidos) == quantos:
            break

    return escolhidos or candidatos[:quantos]


def responder_social(mensagem):
    """Responde cortesia sem buscar no material -- nao ha o que buscar."""
    indice = obter_indice()
    resposta = gerar([
        {"role": "system", "content": indice.system_prompt},
        {"role": "user", "content": (
            "O aluno não fez uma pergunta sobre o material. Ele escreveu: "
            '"' + mensagem + '"\n'
            "Responda em uma ou duas frases, com gentileza, e ofereça ajuda "
            "com dúvidas de estágio. Não cite documento nenhum nesta "
            "resposta, porque não há trecho algum para citar. Continuam "
            "valendo as regras de formato: sem emoji, sem asterisco, só "
            "texto simples.\n"
            "Escreva em português do Brasil natural. Para agradecimento: use uma frase curta de agradecimento quando necessário."
        )},
    ])
    return {
        "content": limpar_formato(resposta["message"]["content"]),
        "sources": [],
        "debug": [],
    }


def responder(pergunta):
    """Mesma lógica de tutor.py:responder(), mas devolvendo um dicionário
    em vez de imprimir no terminal — é o que a rota /api/chat consome."""
    if eh_conversa_social(pergunta):
        return responder_social(pergunta)

    indice = obter_indice()

    # a busca vira peneira generosa e o LLM escolhe quais entram no contexto.
    # metade das vagas da peneira fica reservada para trecho de documento:
    # sem isso, 9 dos 10 candidatos vinham do banco de pares.
    candidatos = indice.buscar(
        pergunta, quantos=RERANK_CANDIDATOS, max_pares=RERANK_CANDIDATOS // 2
    )
    achados = reranquear(pergunta, candidatos, fontes_necessarias(pergunta))
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
        "content": limpar_formato(resposta["message"]["content"]),
        "sources": sources,
        "debug": debug,
    }
