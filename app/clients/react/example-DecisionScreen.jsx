// Chhoto example: Net-profit decision screen (React). Copy kore nijer style diye sajan.
import { useState } from "react";
import api from "./agrisphere-api";

export default function DecisionScreen() {
  const [qty, setQty] = useState(500);
  const [res, setRes] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true); setErr("");
    try {
      setRes(await api.decide({ crop: "tomato", quantityKg: Number(qty), grade: "A", market: "Dhaka" }));
    } catch (e) {
      setErr(e.status === 401 ? "Abar login korun" : e.message);
    } finally { setLoading(false); }
  }

  return (
    <div>
      <input type="number" value={qty} onChange={(e) => setQty(e.target.value)} /> kg
      <button onClick={run} disabled={loading}>{loading ? "Hishab hochhe..." : "Becbo na opekkha korbo?"}</button>
      {err && <p style={{ color: "red" }}>{err}</p>}
      {res && (
        <div>
          <h3>Recommended: {res.options.find((o) => o.id === res.recommended)?.label}</h3>
          {res.options.map((o) => (
            <p key={o.id}>{o.label}: {o.net.downside} - {o.net.base} - {o.net.best} tk</p>
          ))}
          <ul>{res.explanation.map((t, i) => <li key={i}>{t}</li>)}</ul>
          <small>{res.disclaimer}</small>
        </div>
      )}
    </div>
  );
}
