export function createTemplateGallery({ templates, selectedTemplateId, onSelect }) {
  const container = document.createElement("div");

  const label = document.createElement("span");
  label.className = "lekhx-label";
  label.textContent = `Templates (${templates.length})`;
  container.appendChild(label);

  const list = document.createElement("div");
  list.className = "lekhx-template-list";

  for (const template of templates) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `lekhx-template-item${template.id === selectedTemplateId ? " active" : ""}`;
    btn.addEventListener("click", function () {
      onSelect(template.id);
    });

    const title = document.createElement("div");
    title.className = "lekhx-template-title";
    title.textContent = template.name;

    const desc = document.createElement("div");
    desc.className = "lekhx-template-desc";
    desc.textContent = template.description || "";

    btn.append(title, desc);
    list.appendChild(btn);
  }

  container.appendChild(list);
  return container;
}
