#!/usr/bin/env python3

import sys
import threading
import time
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

HOST = "127.0.0.1"
PORT = 5000
URL = f"http://{HOST}:{PORT}"


def checar_ollama():
    import ollama as ollama_lib
    import rag_core

    try:
        modelos = {m["model"] for m in ollama_lib.list()["models"]}
    except Exception:
        print()
        print("=" * 70)
        print("Não consegui falar com o Ollama.")
        print("Abra o Ollama (ou rode 'ollama serve' em outro terminal) e")
        print("rode este programa de novo.")
        print("=" * 70)
        raise SystemExit(1)

    necessarios = [rag_core.MODELO_LLM, rag_core.MODELO_EMBED]
    faltando = [m for m in necessarios if not any(m in nome for nome in modelos)]
    if faltando:
        print()
        print("=" * 70)
        print("Faltam modelos no Ollama. Rode antes de continuar:")
        for m in faltando:
            print(f"  ollama pull {m}")
        print("=" * 70)
        raise SystemExit(1)


def abrir_navegador():
    time.sleep(1.2)
    webbrowser.open(URL)


def main():
    print("Conferindo o Ollama e carregando a base do material...")
    checar_ollama()

    import rag_core

    rag_core.obter_indice()

    from app import app

    threading.Thread(target=abrir_navegador, daemon=True).start()

    print()
    print(f"SophIA rodando em {URL}")
    print("Para encerrar, feche esta janela ou aperte Ctrl+C.")
    print()

    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
