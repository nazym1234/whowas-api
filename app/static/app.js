const questionInput = document.querySelector("#question");
const result = document.querySelector("#result");
const askButton = document.querySelector("#ask");

async function ask() {
  result.className = "result";
  result.innerHTML = "<p>Recherche dans Wikidata…</p>";
  askButton.disabled = true;
  try {
    const response = await fetch("/answer", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question: questionInput.value})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Erreur inattendue");
    result.innerHTML = `
      <h2>${data.person.name}</h2>
      <p>${data.answer}</p>
      <p class="meta">Intention : <strong>${data.intent}</strong> · Propriété : <strong>${data.evidence.property_id}</strong><br>
      <a href="${data.evidence.source_url}" target="_blank" rel="noreferrer">Consulter la donnée source Wikidata</a></p>`;
  } catch (error) {
    result.className = "result error";
    result.innerHTML = `<strong>Impossible de répondre</strong><p>${error.message}</p>`;
  } finally {
    askButton.disabled = false;
  }
}

document.querySelectorAll("[data-question]").forEach(button => {
  button.addEventListener("click", () => { questionInput.value = button.dataset.question; });
});
askButton.addEventListener("click", ask);
questionInput.addEventListener("keydown", event => {
  if (event.key === "Enter") ask();
});
