import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rag_core

RAIZ = Path(__file__).resolve().parent.parent
STATIC_DIR = RAIZ / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")

ASSISTENTE = {
    "name": "SophIA",
    "description": "Tutora institucional virtual do polo UNOPAR Salgueiro",
    "avatarUrl": "/assistant-avatar.svg",
}

SUGESTOES = [
    "Posso enviar o termo em PDF?",
    "Estou com uma dúvida sobre o estágio, pode me ajudar?",
    "Perdi o prazo de preenchimento do cadastro de estágio.",
]


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/api/assistant")
def get_assistant():
    return jsonify({"assistant": ASSISTENTE, "suggestions": SUGESTOES})


@app.get("/api/health")
def health():
    try:
        import ollama

        modelos = {m["model"] for m in ollama.list()["models"]}
        faltando = [
            m
            for m in (rag_core.MODELO_LLM, rag_core.MODELO_EMBED)
            if not any(m in nome for nome in modelos)
        ]
        return jsonify({"ollama": "ok", "modelos_faltando": faltando})
    except Exception as erro:
        return jsonify({"ollama": "indisponivel", "erro": str(erro)}), 503


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    pergunta = (payload.get("question") or "").strip()

    if not pergunta:
        return jsonify({"error": "Pergunta vazia."}), 400

    try:
        resultado = rag_core.responder(pergunta)
    except Exception as erro:
        mensagem = str(erro)
        dica = ""
        if "CUDA" in mensagem:
            dica = (
                " A GPU parece ter travado — feche o Ollama pela bandeja do "
                "Windows, espere uns 10 segundos e abra de novo."
            )
        elif "connect" in mensagem.lower() or "connection" in mensagem.lower():
            dica = " Confira se o Ollama está rodando (ollama serve)."
        return jsonify({"error": f"Não foi possível gerar a resposta: {mensagem}.{dica}"}), 502

    return jsonify(resultado)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
