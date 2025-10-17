const appEl   = document.getElementById("app");
const listEl  = document.getElementById("list");
const emptyEl = document.getElementById("emptyState");

const openBtn = document.getElementById("addBtn");

const helpBtn = document.getElementById("helpBtn");
helpBtn.addEventListener("click", () => {
  window.location.href = "/help";
});

// Wiring for Galal to implement later
openBtn.addEventListener("click", () => {
    console.log("TODO: implement New Assignment flow in a separate task.");
});

async function fetchAssignments() {
  const res = await fetch("/api/assignments");
  const data = await res.json();
  renderList(data);
}

function renderList(items) {
  listEl.innerHTML = "";

  if (!items.length) {
    // Empty-mode
    appEl.classList.add("empty-mode");
    emptyEl.textContent = "No Current Assignments";
    emptyEl.classList.remove("hidden");
    return;
  }

  // Has data: restore normal layout
  appEl.classList.remove("empty-mode");
  emptyEl.classList.add("hidden");

  const groups = groupByDate(items);
  Object.keys(groups).forEach(key => {
    const header = document.createElement("div");
    header.className = "meta";
    header.textContent = key;
    listEl.appendChild(header);
    groups[key].forEach(item => listEl.appendChild(card(item)));
  });
}

function groupByDate(items) {
  const map = {};
  for (const it of items) {
    const label = new Date(it.due_date + "T00:00:00")
      .toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
    if (!map[label]) map[label] = [];
    map[label].push(it);
  }
  return map;
}

function card(a) {
  const el = document.createElement("div");
  el.className = "card";

  const head = document.createElement("div");
  head.className = "card-head";

  const left = document.createElement("div");
  left.className = "row";

  const check = document.createElement("input");
  check.type = "checkbox";
  check.checked = !!a.completed;
  check.addEventListener("change", () => saveEdit(a.id, { completed: check.checked }));

  const title = document.createElement("div");
  title.className = "title";
  title.textContent = a.title;

  left.append(check, title);

  const actions = document.createElement("div");
  actions.className = "actions";

  // Edit is a no-op for now (form not implemented on this screen)
  const editBtn = document.createElement("button");
  editBtn.className = "btn-icon";
  editBtn.textContent = "Edit";
  editBtn.addEventListener("click", () => console.log("TODO: implement Edit elsewhere"));

  const delBtn = document.createElement("button");
  delBtn.className = "btn-icon";
  delBtn.innerHTML = `
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
       width="18" height="18" fill="currentColor">
    <path d="M9 3v1H4v2h16V4h-5V3H9zm1 6v9h2V9h-2zm4 0v9h2V9h-2zM6 6v14
             c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V6H6z"/>
  </svg>`;
  delBtn.addEventListener("click", () => destroy(a.id));

  actions.append(editBtn, delBtn);
  head.append(left, actions);

  const meta = document.createElement("div");
  meta.className = "meta";

  if (a.course) {
    const b = document.createElement("span");
    b.className = "badge";
    b.textContent = a.course;
    meta.appendChild(b);
  }

  const due = document.createElement("span");
  due.textContent = new Date(a.due_date + "T00:00:00").toLocaleDateString();
  meta.appendChild(due);

  const pr = document.createElement("span");
  pr.className = "badge";
  pr.textContent = `P${a.priority || 2}`;
  meta.appendChild(pr);

  if (a.notes) {
    const n = document.createElement("div");
    n.textContent = a.notes;
    n.style.fontSize = "13px";
    n.style.opacity = "0.9";
    el.append(head, meta, n);
  } else {
    el.append(head, meta);
  }
  return el;
}

async function saveEdit(id, fields) {
  await fetch(`/api/assignments/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields)
  });
}

async function destroy(id) {
  const ok = confirm("Delete this assignment?");
  if (!ok) return;
  await fetch(`/api/assignments/${id}`, { method: "DELETE" });
  await fetchAssignments();
}

fetchAssignments();