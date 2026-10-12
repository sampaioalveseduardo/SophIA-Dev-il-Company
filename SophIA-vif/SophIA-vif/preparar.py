from pypdf import PdfReader
import re
import csv

PDF = "documentos/originais/manual-estagio.pdf"
TAMANHO = 500
SEPARADORES = ["\n", ". ", " "]


def arrumar_espacos(linha):
    linha = re.sub(r"\s+", " ", linha)
    linha = re.sub(r"\s+([.,;:!?%)\]])", r"\1", linha)
    linha = re.sub(r"([(\[])\s+", r"\1", linha)
    linha = re.sub(r"(\d)\s*([./-])\s*(\d)", r"\1\2\3", linha)
    return linha.strip()


def limpar(texto_bruto):
    linhas = [arrumar_espacos(l) for l in texto_bruto.splitlines()]
    linhas = [l for l in linhas if l]
    linhas = [l for l in linhas if not re.fullmatch(r"\d+", l)]
    return linhas

def eh_titulo(linha):
    letras = [c for c in linha if c.isalpha()]
    if not letras:
        return False
    maiusculas = sum(1 for c in letras if c.isupper())
    return maiusculas / len(letras) > 0.8 and len(linha) < 70

def dividir(texto, tamanho=TAMANHO):
    if len(texto) <= tamanho:
        return [texto]

    for sep in SEPARADORES:
        if sep not in texto:
            continue

        pedacos = []
        atual = ""

        for parte in texto.split(sep):
            candidato = atual + sep + parte if atual else parte
            if len(candidato) <= tamanho:
                atual = candidato
            else:
                if atual:
                    pedacos.append(atual)
                atual = parte

        if atual:
            if pedacos and len(atual) < 100:
                pedacos[-1] = pedacos[-1] + sep + atual
            else:
                pedacos.append(atual)

        return pedacos

    return [texto]


def ler_pdf(caminho):
    leitor = PdfReader(caminho)
    secoes = []
    for numero, pagina in enumerate(leitor.pages, 1):
        linhas = limpar(pagina.extract_text())
        if not linhas:
            continue
        fim_titulo = 1
        while fim_titulo < len(linhas) and eh_titulo(linhas[fim_titulo]):
            fim_titulo += 1

        secoes.append({
            "referencia": f"slide {numero}",
            "titulo": " ".join(linhas[:fim_titulo]),
            "corpo": "\n".join(linhas[fim_titulo:]),
        })
    return secoes


def ler_txt(caminho):
    with open(caminho, encoding="utf-8") as f:
        blocos = [b.strip() for b in f.read().split("\n\n") if b.strip()]
    secoes = []
    for bloco in blocos:
        linhas = bloco.splitlines()
        titulo = linhas[0].rstrip(":")
        secoes.append({
            "referencia": f"seção {titulo}",
            "titulo": titulo,
            "corpo": "\n".join(linhas[1:]),
        })
    return secoes


def ler_pares(caminho):
    """Le o arquivo de perguntas e respostas escritas a mao.

    Cada bloco tem 4 campos obrigatorios: PERGUNTA, RESPOSTA, ORIGEM e TRECHO,
    e pode ter linhas TAMBEM com outras formas de fazer a mesma pergunta.
    A fonte e a referencia vem do campo ORIGEM, para a citacao apontar
    para o documento de verdade e nao para este arquivo.
    O TRECHO e so para conferencia humana: nao entra no que a SophIA le.

    Cada TAMBEM gera uma entrada separada no indice, apontando para a MESMA
    resposta. Isso existe porque o vetor do par e so da pergunta: medimos que
    uma pergunta coloquial ("nao consigo mandar, tem 15MB") fica a cosseno
    0.57 da pergunta formal ("qual o tamanho maximo do arquivo"), longe
    demais para ser recuperada. Varias formulacoes cobrem essa distancia.
    """
    with open(caminho, encoding="utf-8") as f:
        linhas = f.read().splitlines()

    secoes = []
    atual = {}
    tambem = []

    def fechar():
        fonte, _, referencia = atual["ORIGEM"].partition(",")
        for pergunta in [atual["PERGUNTA"]] + tambem:
            secoes.append({
                "fonte": fonte.strip(),
                "referencia": referencia.strip(),
                "titulo": pergunta,
                "corpo": atual["RESPOSTA"],
                "trecho": atual["TRECHO"],
            })

    for linha in linhas:
        if linha.startswith("#"):
            continue

        if linha.startswith("TAMBEM:"):
            tambem.append(linha[len("TAMBEM:"):].strip())
            continue

        for campo in ("PERGUNTA", "RESPOSTA", "ORIGEM", "TRECHO"):
            if linha.startswith(campo + ":"):
                # o TRECHO fecha o bloco, entao uma PERGUNTA nova comeca outro
                if campo == "PERGUNTA" and len(atual) == 4:
                    fechar()
                    atual, tambem = {}, []
                atual[campo] = linha[len(campo) + 1:].strip()

    if len(atual) == 4:
        fechar()

    return secoes


def ler_transcritos(caminho):
    """Le os slides que sao tabela em imagem, transcritos a mao.

    O pypdf extrai zero texto util dos slides 19, 20 e 21: todo o conteudo
    esta dentro de capturas de tela. A referencia continua sendo o slide de
    origem, para a citacao apontar para o lugar certo do manual.
    """
    with open(caminho, encoding="utf-8") as f:
        linhas = f.read().splitlines()

    secoes = []
    atual = None

    for linha in linhas:
        if linha.startswith("#"):
            continue
        if linha.startswith("SLIDE:"):
            atual = {
                "referencia": "slide " + linha[len("SLIDE:"):].strip(),
                "titulo": "",
                "corpo": "",
            }
            secoes.append(atual)
        elif atual is None:
            continue
        elif linha.startswith("TITULO:"):
            atual["titulo"] = linha[len("TITULO:"):].strip()
        elif linha.startswith("TEXTO:"):
            atual["corpo"] = linha[len("TEXTO:"):].strip()
        elif linha.strip():
            atual["corpo"] += "\n" + linha.strip()

    return secoes


FONTES = [
    {
        "nome": "Manual de Estágio",
        "arquivo": "documentos/originais/manual-estagio.pdf",
        "leitor": ler_pdf,
        "tipo": "trecho",
    },
    {
        "nome": "Manual de Estágio",
        "arquivo": "documentos/slides-transcritos.txt",
        "leitor": ler_transcritos,
        "tipo": "trecho",
    },
    {
        "nome": "Informações do Polo",
        "arquivo": "documentos/informacoes-polo.txt",
        "leitor": ler_txt,
        "tipo": "trecho",
    },
    {
        "nome": "Perguntas e Respostas",
        "arquivo": "documentos/perguntas-respostas.txt",
        "leitor": ler_pares,
        "tipo": "par",
    },
]

pedacos = []

for fonte in FONTES:
    secoes = fonte["leitor"](fonte["arquivo"])
    antes = len(pedacos)

    for s in secoes:
        if not s["corpo"].strip():
            continue

        # um par pergunta-resposta nao se divide: a resposta inteira e a
        # unidade que faz sentido recuperar, e ela ja e curta
        if fonte["tipo"] == "par":
            partes = [s["corpo"]]
        else:
            partes = dividir(s["corpo"])

        for parte in partes:
            pedacos.append({
                # num par, a fonte vem do campo ORIGEM do proprio bloco
                "fonte": s.get("fonte") or fonte["nome"],
                "referencia": s["referencia"],
                "titulo": s["titulo"],
                "texto": parte,
                "tipo": fonte["tipo"],
                "trecho": s.get("trecho", ""),
            })

    print(f"{fonte['nome']}: {len(secoes)} secoes -> {len(pedacos) - antes} pedacos")

pedacos = [p for p in pedacos if re.search(r"[A-Za-zÀ-ÿ]", p["texto"])]

# fragmento curto demais nao responde nada e casa com qualquer pergunta.
# O slide 21 e tabela em imagem e deixava solto um "Realizar Cadastro" de 17
# caracteres, que o conteudo transcrito agora cobre direito.
pedacos = [p for p in pedacos if p["tipo"] == "par" or len(p["texto"]) >= 30]

print()
print("=== RESULTADO ===")
print("total de pedacos:", len(pedacos))

tamanhos = [len(p["texto"]) for p in pedacos]
print("menor :", min(tamanhos), "chars")
print("maior :", max(tamanhos), "chars")
print("media :", sum(tamanhos) // len(tamanhos), "chars")

trechos = sum(1 for p in pedacos if p["tipo"] == "trecho")
pares = sum(1 for p in pedacos if p["tipo"] == "par")
print("trechos de documento:", trechos)
print("pares pergunta-resposta:", pares)

print()
print("=== PEDACOS SUSPEITOS (menos de 50 chars) ===")
for p in pedacos:
    if len(p["texto"]) < 50 and p["tipo"] == "trecho":
        print(f"  {p['fonte']} | {p['referencia']} | {p['texto']!r}")

SAIDA = "documentos/pedacos.csv"

with open(SAIDA, "w", newline="", encoding="utf-8") as f:
    escritor = csv.DictWriter(
        f,
        fieldnames=["id", "fonte", "referencia", "titulo", "texto", "tipo", "trecho"],
    )
    escritor.writeheader()
    for i, p in enumerate(pedacos, 1):
        escritor.writerow({"id": i, **p})

print()
print(f"salvo: {SAIDA} com {len(pedacos)} pedacos")