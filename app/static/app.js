const questionInput = document.querySelector("#question");
const result = document.querySelector("#result");
const askButton = document.querySelector("#ask");
const historyElement = document.querySelector("#history");

const state = {
  contextQid: localStorage.getItem("whowas_context_qid"),
  pendingQuestion: null,
  history: JSON.parse(localStorage.getItem("whowas_history") || "[]")
};

function createElement(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function clearResult() {
  result.replaceChildren();
  result.className = "result";
}

function renderError(message) {
  clearResult();
  result.classList.add("error");
  result.append(
    createElement("strong", "Impossible de répondre"),
    createElement("p", message)
  );
}

function remember(question, data) {
  state.contextQid = data.person.qid;
  localStorage.setItem("whowas_context_qid", state.contextQid);
  state.history.unshift({question, answer: data.answer, person: data.person.name});
  state.history = state.history.slice(0, 8);
  localStorage.setItem("whowas_history", JSON.stringify(state.history));
  renderHistory();
}

function renderHistory() {
  historyElement.replaceChildren();
  if (!state.history.length) return;
  historyElement.append(createElement("h2", "Historique récent"));
  for (const item of state.history) {
    const button = createElement("button", item.question, "history-item");
    button.type = "button";
    button.title = item.answer;
    button.addEventListener("click", () => {
      questionInput.value = item.question;
      questionInput.focus();
    });
    historyElement.append(button);
  }
}

function renderCandidates(detail) {
  clearResult();
  result.append(createElement("h2", "Précise la personne"));
  result.append(createElement("p", detail.message));
  const list = createElement("div", undefined, "candidate-list");
  for (const candidate of detail.candidates || []) {
    const button = createElement("button", undefined, "candidate");
    button.type = "button";
    button.append(
      createElement("strong", candidate.name),
      createElement("span", candidate.description || candidate.qid)
    );
    button.addEventListener("click", () => ask(candidate.qid));
    list.append(button);
  }
  result.append(list);
}

function renderAnswer(data, question) {
  clearResult();
  const header = createElement("div", undefined, "person-header");
  if (data.person.image_url) {
    const image = document.createElement("img");
    image.src = data.person.image_url;
    image.alt = `Portrait de ${data.person.name}`;
    image.loading = "lazy";
    header.append(image);
  }
  const identity = createElement("div");
  identity.append(
    createElement("h2", data.person.name),
    createElement("p", data.person.description, "description")
  );
  header.append(identity);
  result.append(header, createElement("p", data.answer, "answer"));

  if (data.evidence.values.length > 5) {
    const details = document.createElement("details");
    details.append(createElement("summary", `${data.evidence.values.length} valeurs trouvées`));
    const list = document.createElement("ul");
    for (const value of data.evidence.values) list.append(createElement("li", value));
    details.append(list);
    result.append(details);
  }

  const datedDetails = (data.evidence.details || []).filter(
    item => item.start_date || item.end_date
  );
  if (datedDetails.length) {
    const periods = document.createElement("details");
    periods.append(createElement("summary", "Périodes documentées"));
    const list = document.createElement("ul");
    for (const item of datedDetails) {
      const interval = `${item.start_date || "début inconnu"} → ${item.end_date || "en cours"}`;
      list.append(createElement("li", `${item.value} : ${interval}`));
    }
    periods.append(list);
    result.append(periods);
  }

  const meta = createElement("p", undefined, "meta");
  meta.append(
    document.createTextNode(`Action : ${data.action} · Propriété : ${data.evidence.property_id}`),
    document.createElement("br"),
    document.createTextNode(
      `Résolution : ${data.evidence.resolution} · Confiance : ${Math.round(data.evidence.confidence * 100)} %`
    ),
    document.createElement("br")
  );
  if (/^https:\/\/(www\.wikidata\.org|fr\.wikipedia\.org)\//.test(data.evidence.source_url)) {
    const source = createElement("a", "Consulter la source");
    source.href = data.evidence.source_url;
    source.target = "_blank";
    source.rel = "noreferrer";
    meta.append(source);
  }
  result.append(meta);
  remember(question, data);
}

async function ask(personQid = null) {
  const question = state.pendingQuestion || questionInput.value.trim();
  if (question.length < 3) {
    renderError("Écris une question contenant au moins trois caractères.");
    return;
  }
  state.pendingQuestion = question;
  clearResult();
  result.append(createElement("p", "Recherche dans Wikidata et Wikipédia…"));
  askButton.disabled = true;
  try {
    const response = await fetch("/answer", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        question,
        person_qid: personQid,
        context_qid: personQid ? null : state.contextQid
      })
    });
    const data = await response.json();
    if (response.status === 409) {
      renderCandidates(data.detail);
      return;
    }
    if (!response.ok) throw new Error(data.detail || "Erreur inattendue");
    state.pendingQuestion = null;
    renderAnswer(data, question);
  } catch (error) {
    const message = typeof error.message === "string" ? error.message : "Erreur inattendue";
    renderError(message);
  } finally {
    askButton.disabled = false;
  }
}

document.querySelectorAll("[data-question]").forEach(button => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.question;
    state.pendingQuestion = null;
  });
});
askButton.addEventListener("click", () => ask());
questionInput.addEventListener("input", () => { state.pendingQuestion = null; });
questionInput.addEventListener("keydown", event => {
  if (event.key === "Enter") ask();
});
renderHistory();
