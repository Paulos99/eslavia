import { formatLeadEmailFields, leadInbox } from "./leadEmail";

export async function submitLead(payload: {
  name: string;
  contact: string;
  consent: boolean;
}): Promise<{ ok: boolean; error?: string }> {
  const endpoint = import.meta.env.VITE_LEAD_API_URL || "/api/wholesale-lead";
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const text = await res.text();
    let parsed: { ok?: boolean; error?: string } | null = null;
    try {
      parsed = JSON.parse(text) as { ok?: boolean; error?: string };
    } catch {
      parsed = null;
    }
    if (parsed && res.ok && parsed.ok) return { ok: true };
    if (parsed && !parsed.ok && res.status >= 400 && res.status < 500 && res.status !== 404) {
      return { ok: false, error: parsed.error || "Не удалось отправить заявку" };
    }
  } catch {
    // GitHub Pages has no API — send the email from the browser.
  }
  return sendLeadViaEmail(payload);
}

async function sendLeadViaEmail(payload: {
  name: string;
  contact: string;
}): Promise<{ ok: boolean; error?: string }> {
  const to = leadInbox();
  if (!to) {
    return { ok: false, error: "Не удалось отправить заявку" };
  }

  try {
    const fields = formatLeadEmailFields(payload);
    if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.contact)) {
      (fields as Record<string, string>)["_replyto"] = payload.contact;
    }
    const res = await fetch(`https://formsubmit.co/ajax/${encodeURIComponent(to)}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(fields),
    });
    const data = (await res.json().catch(() => ({}))) as { success?: boolean | string; message?: string };
    if (data.success === true || data.success === "true") return { ok: true };
    if (String(data.message || "").toLowerCase().includes("activation")) return { ok: true };
    return { ok: false, error: "Не удалось отправить заявку" };
  } catch {
    return { ok: false, error: "Не удалось отправить заявку" };
  }
}
