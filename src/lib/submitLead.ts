export async function submitLead(payload: {
  name: string;
  contact: string;
  consent: boolean;
}): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch("/api/wholesale-lead", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  try {
    return (await res.json()) as { ok: boolean; error?: string };
  } catch {
    return { ok: false, error: "Не удалось отправить заявку" };
  }
}
