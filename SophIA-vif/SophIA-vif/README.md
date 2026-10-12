# SophIA — tutora virtual do polo UNOPAR Salgueiro

Interface web do tutor construído nos Desafios 2.1 e 2.2 do Módulo 2.

## Como rodar

**1. Instale o Ollama** em [ollama.com/download](https://ollama.com/download) e
baixe os dois modelos:

```
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

Se a sua máquina usar outro modelo de geração, troque o valor de `MODELO_LLM`
em `backend/rag_core.py`.

**2. Crie o ambiente**, uma vez só, dentro desta pasta:

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**3. Rode:**

```
.\rodar
```

O navegador abre sozinho em `http://127.0.0.1:5000`. Para encerrar, feche a
janela ou aperte Ctrl+C.

> O `.\rodar` chama o Python de dentro do `.venv` desta pasta, então não é
> preciso ativar nada. Pelo botão Run do VS Code não funciona: ele usa o
> Python do sistema, que não tem as bibliotecas instaladas.

## O que tem aqui

```
rodar.bat              atalho que sobe tudo
run.py                 confere o Ollama e inicia o servidor
backend/app.py         servidor Flask: serve o site e expõe /api/chat
backend/rag_core.py    o RAG — busca, reranking e geração da resposta
static/                a interface: HTML, CSS e JavaScript
system-prompt-final-v4 as regras de comportamento da SophIA
documentos/            o material e a base já indexada
preparar.py            corta o material em pedaços       (só se o material mudar)
indexar.py             calcula os vetores de cada pedaço (só se o material mudar)
```

A `documentos/base.csv` já vem pronta, então o servidor sobe sem precisar
reindexar nada.

## Como a resposta é construída

Quando chega uma pergunta:

```
1. busca híbrida   cosseno (significado) + BM25 (palavra exata), fundidos
                   por posição. Traz 10 candidatos.

2. reranking       o qwen3:8b lê a pergunta e os 10 candidatos juntos e
                   escolhe 2 ou 3. Quantos depende do formato da pergunta:
                   3 se ela tem " e " ou dois pontos de interrogação,
                   2 nos outros casos.

3. corte           só responde se algum trecho passar de cosseno 0,68 OU
                   BM25 10,0. Senão, diz que não encontrou no material.

4. resposta        o modelo responde usando só os trechos aprovados, e
                   cita a fonte de cada informação.
```

Saudação e agradecimento não passam por nada disso: são respondidos direto,
sem busca, porque não há o que buscar no material.

## O que medimos

Vinte perguntas fixas — 10 sobre material coberto, 5 que cruzam fontes e 5
fora do material:

```
                               acertos   cruzam fontes
sem reranking                    12         0 de 5
com reranking                    16         4 de 5

só busca vetorial, sem BM25      11         o BM25 vale 5 acertos
```

O detalhe do método, o chunking semântico que testamos e descartamos, e a
verificação de resposta que não funcionou estão no relatório do Desafio 2.2,
no repositório principal do projeto.

## Se der erro

**`ModuleNotFoundError: No module named 'ollama'`** — você rodou com o Python
do sistema. Use `.\rodar`.

**`CUDA error: shared object initialization failed`** — o Ollama foi fechado à
força e o contexto da placa de vídeo ficou preso. Feche o Ollama pela bandeja
do Windows, ao lado do relógio, espere uns 10 segundos e abra de novo. Nunca
feche o Ollama pelo Gerenciador de Tarefas.

**A primeira pergunta demora uns 20 segundos** — é o modelo carregando na
memória. Da segunda em diante fica rápido.
