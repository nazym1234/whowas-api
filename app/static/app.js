const state = {
  contextQid: localStorage.getItem("whowas_context_qid"),
  contextQids: JSON.parse(localStorage.getItem("whowas_context_qids") || "[]"),
  contextFrames: JSON.parse(localStorage.getItem("whowas_context_frames") || "[]"),
  lastQuestion: localStorage.getItem("whowas_last_question"),
  lastPropertyId: localStorage.getItem("whowas_last_property_id"),
  pendingQuestion: null,
  history: JSON.parse(localStorage.getItem("whowas_history") || "[]"),
  gameSession: null
};
const questionInput = document.querySelector("#question");
const conversation = document.querySelector("#conversation");
const askButton = document.querySelector("#ask");

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function showView(name) {
  document.querySelectorAll(".view").forEach(view => view.classList.toggle("active", view.id === `${name}-view`));
  document.querySelectorAll(".nav-item").forEach(item => item.classList.toggle("active", item.dataset.view === name));
  if (name === "history") renderHistory();
  if (name === "search") document.querySelector("#people-search").focus();
}

function addMessage(role, content) {
  const article = el("article", undefined, `message ${role}-message`);
  article.append(el("div", role === "assistant" ? "W" : "Toi", "avatar"));
  const bubble = el("div", undefined, "bubble");
  if (typeof content === "string") bubble.append(el("p", content));
  else bubble.append(content);
  article.append(bubble);
  conversation.append(article);
  article.scrollIntoView({behavior: "smooth", block: "end"});
  return article;
}

function answerCard(data) {
  const card = el("div", undefined, "answer-card");
  const head = el("div", undefined, "person-row");
  if (data.person.image_url) {
    const image = document.createElement("img");
    image.src = data.person.image_url;
    image.alt = `Portrait de ${data.person.name}`;
    image.loading = "lazy";
    head.append(image);
  }
  const identity = el("div");
  identity.append(el("strong", data.person.name), el("span", data.person.description || "Personnalité"));
  head.append(identity);
  card.append(head, el("p", data.answer, "answer-text"));
  const footer = el("div", undefined, "answer-footer");
  footer.append(el("span", `Confiance ${Math.round(data.evidence.confidence * 100)} %`));
  if (/^https:\/\/(www\.wikidata\.org|fr\.wikipedia\.org)\//.test(data.evidence.source_url)) {
    const linkLabel = data.evidence.resolution === "no_data"
      ? `Voir la fiche Wikidata de ${data.person.name} ↗`
      : "Voir la source ↗";
    const link = el("a", linkLabel);
    link.href = data.evidence.source_url;
    link.target = "_blank";
    link.rel = "noreferrer";
    footer.append(link);
  }
  card.append(footer);
  return card;
}

function remember(question, data) {
  state.contextQid = data.person.qid;
  const relationProperties = ["P22", "P25", "P26", "P40", "P3373"];
  const responsePeople = [data.person, ...(data.related_people || [])];
  if (data.evidence.resolution === "conversation_group" || data.action === "compare") {
    state.contextQids = responsePeople.map(person => person.qid);
  } else if (relationProperties.includes(data.evidence.property_id) && data.related_people.length) {
    state.contextQids = data.related_people.map(person => person.qid);
  } else {
    state.contextQids = [data.person.qid];
  }
  const frame = {
    subject_qid: state.contextQid,
    mentioned_qids: state.contextQids,
    question,
    people: responsePeople.map(person => ({qid: person.qid, name: person.name}))
  };
  state.contextFrames.push(frame);
  state.contextFrames = state.contextFrames.slice(-20);
  localStorage.setItem("whowas_context_qid", state.contextQid);
  localStorage.setItem("whowas_context_qids", JSON.stringify(state.contextQids));
  localStorage.setItem("whowas_context_frames", JSON.stringify(state.contextFrames));
  state.lastQuestion = question;
  state.lastPropertyId = data.evidence.property_id;
  localStorage.setItem("whowas_last_question", state.lastQuestion);
  localStorage.setItem("whowas_last_property_id", state.lastPropertyId);
  state.history.unshift({question, answer: data.answer, person: data.person.name, qid: data.person.qid, date: new Date().toISOString()});
  state.history = state.history.slice(0, 50);
  localStorage.setItem("whowas_history", JSON.stringify(state.history));
}

function candidatePicker(detail, question) {
  const box = el("div");
  box.append(el("p", detail.message));
  const list = el("div", undefined, "candidate-list");
  for (const candidate of detail.candidates || []) {
    const button = el("button", undefined, "candidate");
    button.append(el("strong", candidate.name), el("span", candidate.description || candidate.qid));
    button.addEventListener("click", () => ask(candidate.qid, question));
    list.append(button);
  }
  box.append(list);
  return box;
}

async function ask(personQid = null, forcedQuestion = null) {
  const question = forcedQuestion || state.pendingQuestion || questionInput.value.trim();
  if (question.length < 3) return;
  if (!personQid) {
    addMessage("user", question);
    questionInput.value = "";
  }
  state.pendingQuestion = question;
  askButton.disabled = true;
  const loading = addMessage("assistant", "Je cherche dans Wikidata et Wikipédia…");
  try {
    const response = await fetch("/answer", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        question,
        person_qid: personQid,
        context_qid: personQid ? null : state.contextQid,
        context_qids: personQid ? [] : state.contextQids,
        context_question: personQid ? null : state.lastQuestion,
        context_property_id: personQid ? null : state.lastPropertyId
      })
    });
    const data = await response.json();
    loading.remove();
    if (response.status === 409) {
      addMessage("assistant", candidatePicker(data.detail, question));
      return;
    }
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Erreur inattendue");
    state.pendingQuestion = null;
    addMessage("assistant", answerCard(data));
    remember(question, data);
  } catch (error) {
    loading.remove();
    addMessage("assistant", `Je n’ai pas pu répondre : ${error.message}`);
  } finally {
    state.pendingQuestion = null;
    askButton.disabled = false;
    questionInput.focus();
  }
}

let searchTimer;
async function searchPeople(query) {
  const results = document.querySelector("#search-results");
  if (query.trim().length < 2) {
    results.className = "people-grid empty-state";
    results.textContent = "Saisis au moins deux caractères.";
    return;
  }
  results.textContent = "Recherche…";
  try {
    const response = await fetch(`/people/search?q=${encodeURIComponent(query)}`);
    const people = await response.json();
    results.replaceChildren();
    results.className = "people-grid";
    if (!people.length) results.append(el("p", "Aucune personnalité trouvée.", "empty-state"));
    for (const person of people) {
      const card = el("button", undefined, "person-card");
      card.append(el("div", person.name.charAt(0), "initial"));
      const info = el("div");
      info.append(el("strong", person.name), el("span", person.description || person.qid));
      card.append(info, el("span", "Discuter →", "card-action"));
      card.addEventListener("click", () => {
        state.contextQid = person.qid;
        state.contextQids = [person.qid];
        localStorage.setItem("whowas_context_qid", person.qid);
        localStorage.setItem("whowas_context_qids", JSON.stringify(state.contextQids));
        showView("chat");
        questionInput.value = `Qui est ${person.name} ?`;
        questionInput.focus();
      });
      results.append(card);
    }
  } catch (_error) {
    results.textContent = "La recherche est momentanément indisponible.";
  }
}

function renderHistory() {
  const list = document.querySelector("#history-list");
  document.querySelector("#history-count").textContent = `${state.history.length} question${state.history.length > 1 ? "s" : ""}`;
  list.replaceChildren();
  if (!state.history.length) {
    list.append(el("div", "Aucune question pour le moment.", "empty-state panel-empty"));
    return;
  }
  for (const item of state.history) {
    const card = el("article", undefined, "history-card");
    const top = el("div", undefined, "history-top");
    top.append(el("strong", item.person), el("time", item.date ? new Date(item.date).toLocaleString("fr-FR") : ""));
    card.append(top, el("h3", item.question), el("p", item.answer));
    const replay = el("button", "Reposer cette question", "replay");
    replay.addEventListener("click", () => { showView("chat"); questionInput.value = item.question; questionInput.focus(); });
    card.append(replay);
    list.append(card);
  }
}

function renderGame(data) {
  const content = document.querySelector("#game-content");
  content.replaceChildren();
  if (data.finished) {
    content.append(el("span", "Ma proposition", "eyebrow"));
    const guess = data.guesses[0];
    content.append(el("h2", guess ? `Tu pensais à ${guess.name} ?` : "Je n’ai pas trouvé…"));
    if (guess) content.append(el("p", `Compatibilité : ${guess.score}/${Math.max(guess.max_score, 1)} réponses exploitables.`));
    const restart = el("button", "Rejouer", "primary");
    restart.addEventListener("click", startGame);
    content.append(restart);
    return;
  }
  content.append(el("span", `Question ${data.progress} / 12`, "eyebrow"), el("h2", data.question));
  const choices = el("div", undefined, "game-choices");
  [["yes", "Oui"], ["no", "Non"], ["unknown", "Je ne sais pas"]].forEach(([value, label]) => {
    const button = el("button", label, value === "yes" ? "primary" : "secondary");
    button.addEventListener("click", () => answerGame(value));
    choices.append(button);
  });
  content.append(choices);
}

async function startGame() {
  const response = await fetch("/akinator/start", {method: "POST"});
  const data = await response.json();
  state.gameSession = data.session_id;
  renderGame(data);
}

async function answerGame(answer) {
  const response = await fetch("/akinator/answer", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({session_id: state.gameSession, answer})
  });
  const data = await response.json();
  if (!response.ok) return startGame();
  renderGame(data);
}

document.querySelectorAll(".nav-item").forEach(button => button.addEventListener("click", () => showView(button.dataset.view)));
document.querySelectorAll("[data-question]").forEach(button => button.addEventListener("click", () => { questionInput.value = button.dataset.question; questionInput.focus(); }));
askButton.addEventListener("click", () => ask());
questionInput.addEventListener("keydown", event => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); ask(); } });
questionInput.addEventListener("input", () => { state.pendingQuestion = null; });
document.querySelector("#people-search").addEventListener("input", event => { clearTimeout(searchTimer); searchTimer = setTimeout(() => searchPeople(event.target.value), 280); });
document.querySelector("#game-start").addEventListener("click", startGame);
document.querySelector("#clear-history").addEventListener("click", () => { state.history = []; localStorage.removeItem("whowas_history"); renderHistory(); });
renderHistory();
