import os
import time
import random
import uuid
from typing import Dict, Any, cast

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from openai import OpenAI
from pydantic import BaseModel, ValidationError, field_validator

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173"]}})

client = OpenAI()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# In-memory round store (fine for a prototype). Use Redis/DB in production.
ROUNDS: Dict[str, Dict[str, Any]] = {}
ROUND_TTL_SECONDS = 10 * 60  # 10 minutes

def cleanup_old_rounds() -> None:
    now = time.time()
    expired = [
        rid for rid, data in ROUNDS.items()
        if now - float(data.get("created_at", 0)) > ROUND_TTL_SECONDS
    ]
    for rid in expired:
        ROUNDS.pop(rid, None)

class Anchors(BaseModel):
    leftAnchor: str
    rightAnchor: str
    spectrumLabel: str

    @field_validator("leftAnchor", "rightAnchor")
    @classmethod
    def anchor_len(cls, v: str) -> str:
        v = v.strip()
        if not (2 <= len(v) <= 40):
            raise ValueError("Anchor must be 2–40 chars")
        return v

    @field_validator("spectrumLabel")
    @classmethod
    def label_len(cls, v: str) -> str:
        v = v.strip()
        if not (1 <= len(v) <= 20):
            raise ValueError("Label must be 1–20 chars")
        return v


class ClueOut(BaseModel):
    clue: str

    @field_validator("clue")
    @classmethod
    def clue_len(cls, v: str) -> str:
        v = v.strip()
        if not (5 <= len(v) <= 140):
            raise ValueError("Clue must be 5–140 chars")
        return v


def make_anchors(theme: str) -> Anchors:
    resp = client.responses.parse(
        model=MODEL,
        input=[
            {
                "role": "system", 
                "content": (
                    "You design a single round of a Wavelength-style spectrum guessing game.\n"
                    "Output must match the provided schema keys exactly."
                ),
            },
            {
                "role": "user", 
                "content": (
                    f"Theme: {theme}\n\n"
                    "Return short, clear opposite anchors for a spectrum.\n"
                    "Rules:\n"
                    "- Anchors must be true opposites and broadly understandable.\n"
                    "- Avoid politics unless the theme explicitly demands it.\n"
                    "- Keep anchors 1–4 words each.\n"
                    "- spectrumLabel should be 1-4 words describing what the anchors are about."
                ),
            },
        ],
        text_format=Anchors,
    )

    parsed = resp.output_parsed
    if parsed is None:
        # helpful for debugging (output_text exists on Responses) :contentReference[oaicite:1]{index=1}
        raise RuntimeError(f"Failed to parse Anchors. Raw output:\n{resp.output_text}")

    return cast(Anchors, parsed)


def make_clue(theme: str, anchors: Anchors, target: int) -> str:
    resp = client.responses.parse(
        model=MODEL,
        input=[
            {"role": "system", "content": "You write a single clue for a Wavelength-style guessing round."},
            {
                "role": "user",
                "content": (
                    f"Theme: {theme}\n"
                    f"Spectrum: '{anchors.leftAnchor}' (0) ↔ '{anchors.rightAnchor}' (100)\n"
                    f"Target position: {target}/100\n\n"
                    "Write ONE sentence as the clue that implies something near the target.\n"
                    "It is best to reference specific scenarios related to the theme.\n"
                    "Some examples are:\n"
                    "Example: If the spectrum is 'Hot' (0) ↔ 'Cold' (100) and the target position is 0/100, the clue may be 'Lava' or 'Concrete on a summer day'.\n"
                    "Example: If the spectrum is 'Sandwich' (0) ↔ 'Not a Sandwich' (100) and the target position is 50/100, the clue may be 'Hot dog'."
                    "Do NOT mention numbers, percent, target, wheel, slider, or position.\n"
                    "Return JSON with key: clue\n"
                ),
            },
        ],
        text_format=ClueOut,
    )

    parsed = resp.output_parsed
    if parsed is None:
        raise RuntimeError(f"Failed to parse ClueOut. Raw output:\n{resp.output_text}")

    parsed = cast(ClueOut, parsed)
    return parsed.clue


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/round")
def create_round():
    cleanup_old_rounds()

    body = request.get_json(silent=True) or {}
    theme = (body.get("theme") or "").strip()
    if not theme:
        return jsonify({"error": "theme is required"}), 400

    # Server picks target so the model doesn't “cluster” toward the middle.
    target = random.randint(0, 100)

    try:
        anchors = make_anchors(theme)
        clue = make_clue(theme, anchors, target)
    except ValidationError as e:
        return jsonify({"error": "model_output_invalid", "details": e.errors()}), 500
    except Exception as e:
        return jsonify({"error": "generation_failed", "details": str(e)}), 500

    round_id = str(uuid.uuid4())
    ROUNDS[round_id] = {"target": target, "created_at": time.time()}

    # IMPORTANT: do NOT send target yet (prevents easy cheating)
    return jsonify(
        {
            "roundId": round_id,
            "theme": theme,
            "leftAnchor": anchors.leftAnchor,
            "rightAnchor": anchors.rightAnchor,
            "spectrumLabel": anchors.spectrumLabel,
            "clue": clue,
        }
    )


@app.post("/api/reveal")
def reveal():
    cleanup_old_rounds()

    body = request.get_json(silent=True) or {}
    round_id = body.get("roundId")
    guess = body.get("guess")

    if not round_id or round_id not in ROUNDS:
        return jsonify({"error": "unknown_or_expired_round"}), 400

    if guess is None:
        return jsonify({"error": "guess is required"}), 400

    try:
        guess_int = int(guess)
    except (TypeError, ValueError):
        return jsonify({"error": "guess must be an integer 0-100"}), 400

    if not (0 <= guess_int <= 100):
        return jsonify({"error": "guess out of range"}), 400

    target = int(ROUNDS[round_id]["target"])
    ROUNDS.pop(round_id, None)

    distance = abs(guess_int - target)
    num_score = max(0, 100 - distance)
    score = ""
    if (num_score > 80):
        score = "You Won!"
    else:
        score = "AWW... You Lost!"
        

    return jsonify({"target": target, "distance": distance, "score": score})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
