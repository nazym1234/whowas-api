const personSelect = document.querySelector("#person");
const questionInput = document.querySelector("#question");
const result = document.querySelector("#result");
const askButton = document.querySelector("#ask");

async function loadPeople() {
  const response = await fetch("/people");
  const people = await response.json();
  personSelect.innerHTML = people.map(person =>
    `<option value="${person.qid}">${person.name} — ${person.description}</option>`
  ).join("");
}

async function ask() {
  result.className = "result";
  result.innerHTML = "<p>Recherche dans Wikidata…</p>";
  askButton.disabled = true;
  try {
    const response = await fetch("/answer", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({person_qid: personSelect.value, question: questionInput.value})
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
loadPeople().catch(() => { personSelect.innerHTML = "<option>Erreur de chargement</option>"; });

