import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

const SUGGESTIONS = [
  "What is the last date to pay the semester fee?",
  "How do I get a bonafide certificate?",
  "What documents are needed for admission?",
  "What is the minimum attendance for exams?",
];
const GREETING = { from: "bot", text: "Hi! Ask me about admissions, fees, exams, hostel or certificates. I answer from official college documents and show where each answer comes from." };

export default function Chatbot() {
  const nav = useNavigate();
  const [msgs, setMsgs] = useState([GREETING]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef(null);

  useEffect(() => {
    api("/chat/history?limit=30").then((h) => {
      const past = h.flatMap((l) => [
        { from: "me", text: l.question },
        { from: "bot", text: l.answer, sources: l.sources, confidence: l.confidence, escalate: l.escalate, logId: l.id, question: l.question },
      ]);
      if (past.length) setMsgs([GREETING, ...past]);
    }).catch(() => {});
  }, []);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  const send = async (q) => {
    q = (q ?? text).trim();
    if (!q || busy) return;
    setText("");
    setMsgs((m) => [...m, { from: "me", text: q }]);
    setBusy(true);
    try {
      const r = await api("/chat/ask", { method: "POST", body: { question: q } });
      setMsgs((m) => [...m, { from: "bot", text: r.answer, sources: r.sources, confidence: r.confidence, escalate: r.escalate, logId: r.log_id, question: q }]);
    } catch (e) {
      setMsgs((m) => [...m, { from: "bot", text: "The assistant is unavailable right now. You can raise a query instead.", escalate: true, question: q }]);
    } finally { setBusy(false); }
  };

  const raise = (m) => nav("/raise", { state: { subject: m.question.slice(0, 120), description: m.question, chat_log_id: m.logId } });

  return (
    <div className="chat">
      <h1>Ask the assistant</h1>
      <div className="chat-window" aria-live="polite">
        {msgs.map((m, i) => (
          <div key={i} className={`bubble ${m.from}`}>
            <p>{m.text}</p>
            {m.sources?.length > 0 && (
              <div className="sources">
                {m.sources.map((s) => <span key={s} className="chip">Source: {s}</span>)}
                <span className="chip soft">Confidence {Math.round(m.confidence * 100)}%</span>
              </div>
            )}
            {m.escalate && m.question && <button className="btn primary small" onClick={() => raise(m)}>Raise a query with this question</button>}
          </div>
        ))}
        {busy && <div className="bubble bot"><p className="muted">Searching the college documents…</p></div>}
        <div ref={end} />
      </div>
      {msgs.length <= 1 && (
        <div className="chips">{SUGGESTIONS.map((s) => <button key={s} className="chip btnchip" onClick={() => send(s)}>{s}</button>)}</div>
      )}
      <form className="composer" onSubmit={(e) => { e.preventDefault(); send(); }}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Type your question…" aria-label="Your question" maxLength={1000} />
        <button className="btn primary" disabled={busy || !text.trim()}>Send</button>
      </form>
    </div>
  );
}
