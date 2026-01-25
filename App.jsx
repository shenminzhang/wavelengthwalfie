import { useMemo, useState } from "react";
import Wheel from "./Wheel";
import "./App.css";

const API_BASE = "http://localhost:5000/api";

export default function App() {
  const [theme, setTheme] = useState("");
  const [loading, setLoading] = useState(false);
  const [round, setRound] = useState(null); // { roundId, anchors..., clue }
  const [guess, setGuess] = useState(50);
  const [reveal, setReveal] = useState(null); // { target, distance, score }
  const [error, setError] = useState("");

  const step = useMemo(() => {
    if (!round) return "theme";
    if (!reveal) return "play";
    return "reveal";
  }, [round, reveal]);

  async function generateRound() {
    setError("");
    setLoading(true);
    setReveal(null);
    setRound(null);

    try {
      const res = await fetch(`${API_BASE}/round`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || "Failed to generate round");
      setRound(data);
      setGuess(50);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function submitGuess() {
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/reveal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roundId: round.roundId, guess }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || "Failed to reveal");
      setReveal(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setRound(null);
    setReveal(null);
    setTheme("");
    setGuess(50);
    setError("");
  }

  return (
    <div className="page">
      <div className="card">
        <div className="headerRow">
          <h1>Play Wavelength With Alfie!</h1>
          <img className="alfieImg" src="/alfie.png" alt="alfie"/>
        </div>

        {step === "theme" && (
          <>
            <label className="label">Choose a theme:</label>
            <input
              className="input"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              placeholder='Your theme of choice, e.g. "brainrot"'
            />
            <button className="btn" disabled={!theme.trim() || loading} onClick={generateRound}>
              {loading ? "Loading..." : "Let's Play!"}
            </button>
          </>
        )}

        {step !== "theme" && round && (
          <>
            <div className="meta">
              <div className="metaText"><strong>Theme of Choice:</strong> {round.theme}</div>
              <div className="metaText"><strong>{round.spectrumLabel}:</strong> Is it... {round.leftAnchor.toLowerCase()} or... {round.rightAnchor.toLowerCase()}?</div>
            </div>

            <div className="clue">
              <div className="clueText">Your Clue🤔: {round.clue}</div>
            </div>

            <Wheel
              guess={guess}
              target={reveal?.target ?? null}
              leftLabel={round.leftAnchor}
              rightLabel={round.rightAnchor}
              onChange={setGuess}
              disabled={!!reveal}
            />

            {!reveal ? (
              <button className="btn" disabled={loading} onClick={submitGuess}>
                {loading ? "Loading..." : "Reveal"}
              </button>
            ) : (
              <div className="result">
                <div><strong>Your guess:</strong> {guess}</div>
                <div><strong>Target:</strong> {reveal.target}</div>
                <div>
                  {reveal.target < 45
                  ? `It's more ${round.leftAnchor.toLowerCase()}.`
                  : reveal.target > 55
                  ? `It's more ${round.leftAnchor.toLowerCase()}.`
                  : "Wow - it's an even split!"}
                </div>
                <div>{reveal.score}</div>
                <button className="btn" onClick={reset}>Play With Alfie Again!</button>
              </div>
            )}
          </>
        )}

        {error && <div className="error">{error}</div>}
      </div>
    </div>
  );
}

