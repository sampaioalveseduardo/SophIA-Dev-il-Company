## Como rodar

**1. Instale o Ollama** em [ollama.com/download](https://ollama.com/download) e
baixe os dois modelos:

```
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

Outro modelo de geração: troque o valor de `MODELO_LLM`
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

A `documentos/base.csv` já vem pronta, então o servidor sobe sem precisar
reindexar nada.

## Se der erro

**`ModuleNotFoundError: No module named 'ollama'`** — você rodou com o Python
do sistema. Use `.\rodar`.

**`CUDA error: shared object initialization failed`** — o Ollama foi fechado à
força e o contexto da placa de vídeo ficou preso. Feche o Ollama pela bandeja
do Windows, ao lado do relógio, espere uns 10 segundos e abra de novo. Nunca
feche o Ollama pelo Gerenciador de Tarefas.

**A primeira pergunta demora uns 20 segundos** — é o modelo carregando na
memória. Da segunda em diante fica rápido.
