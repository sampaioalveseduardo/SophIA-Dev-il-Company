# Pré-requisitos

- Python 3.10 ou mais recente
- Ollama instalado e rodando (ollama.com/download)
- Os dois modelos já baixados no Ollama:

ollama pull qwen3:8b ou a combinar com o arquivo outra versão
ollama pull nomic-embed-text

(outro modelo de geração, troque o valor de `MODELO_LLM` em `backend/rag_core.py`.)

# Como rodar

1. Instale as dependências Python:
pip install -r requirements.txt

2. Garanta que o Ollama está rodando

3. No terminal, rode `python run.py` ou aperte Run em run.py (F5) — já existe uma configuração em `.vscode/launch.json` para isso.

Isso sobe um servidor local e abre automaticamente o navegador em `http://127.0.0.1:5000` com a SophIA pronta para conversar.

Para encerrar, feche o terminal ou aperte Ctrl+C.
