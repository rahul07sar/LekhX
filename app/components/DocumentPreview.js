import { resolveBackendUrl } from "../lib/api.js";

export function createDocumentPreview(documentRecord) {
  const card = document.createElement("div");
  card.className = "lekhx-card";

  if (!documentRecord) {
    const heading = document.createElement("h2");
    heading.className = "lekhx-preview-heading";
    heading.textContent = "Document Preview";

    const emptyCopy = document.createElement("p");
    emptyCopy.className = "lekhx-muted";
    emptyCopy.textContent =
      "Select an office format (.docx, .pdf, .xlsx, .pptx, .md), choose a language and template on the left, and enter your brief to generate an offline document.";

    card.append(heading, emptyCopy);
    return card;
  }

  const plan = documentRecord.plan || {};
  card.setAttribute("dir", plan.direction === "rtl" ? "rtl" : "ltr");

  const header = document.createElement("div");
  header.className = "lekhx-preview-header";

  const titleWrap = document.createElement("div");
  const title = document.createElement("h2");
  title.className = "lekhx-preview-heading";
  title.textContent = plan.title || documentRecord.title || "Generated Document";

  const meta = document.createElement("div");
  meta.className = "lekhx-preview-meta";
  meta.textContent = `${documentRecord.filename} • ${String(documentRecord.format || "").toUpperCase()} • ${documentRecord.language} • ${documentRecord.size_bytes} bytes`;
  titleWrap.append(title, meta);

  const docId = documentRecord.document_id || documentRecord.id;
  const downloadPath = documentRecord.download_url || `/api/documents/${docId}/download`;
  const downloadLink = document.createElement("a");
  downloadLink.className = "lekhx-download-link";
  downloadLink.href = resolveBackendUrl(downloadPath);
  downloadLink.setAttribute("download", documentRecord.filename || "document");
  downloadLink.textContent = `Download ${documentRecord.filename}`;

  header.append(titleWrap, downloadLink);
  card.appendChild(header);

  const sections = Array.isArray(plan.sections) ? plan.sections : [];
  for (const section of sections) {
    const secEl = document.createElement("section");
    secEl.className = "lekhx-preview-section";

    const secHeading = document.createElement("h3");
    secHeading.textContent = section.heading || "";
    secEl.appendChild(secHeading);

    const paragraphs = Array.isArray(section.paragraphs) ? section.paragraphs : [];
    for (const para of paragraphs) {
      const p = document.createElement("p");
      p.textContent = para;
      secEl.appendChild(p);
    }

    const bullets = Array.isArray(section.bullets) ? section.bullets : [];
    if (bullets.length > 0) {
      const ul = document.createElement("ul");
      for (const bullet of bullets) {
        const li = document.createElement("li");
        li.textContent = bullet;
        ul.appendChild(li);
      }
      secEl.appendChild(ul);
    }
    card.appendChild(secEl);
  }

  const tables = Array.isArray(plan.tables) ? plan.tables : [];
  for (const table of tables) {
    const wrap = document.createElement("div");
    wrap.className = "lekhx-preview-section";

    if (table.title) {
      const th = document.createElement("h3");
      th.textContent = table.title;
      wrap.appendChild(th);
    }

    const tableEl = document.createElement("table");
    tableEl.className = "lekhx-table";

    const headers = Array.isArray(table.headers) ? table.headers : [];
    if (headers.length > 0) {
      const thead = document.createElement("thead");
      const tr = document.createElement("tr");
      for (const h of headers) {
        const thCell = document.createElement("th");
        thCell.textContent = String(h);
        tr.appendChild(thCell);
      }
      thead.appendChild(tr);
      tableEl.appendChild(thead);
    }

    const rows = Array.isArray(table.rows) ? table.rows : [];
    const tbody = document.createElement("tbody");
    for (const row of rows) {
      const tr = document.createElement("tr");
      for (const cell of row) {
        const td = document.createElement("td");
        td.textContent = String(cell);
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    tableEl.appendChild(tbody);
    wrap.appendChild(tableEl);
    card.appendChild(wrap);
  }

  const slides = Array.isArray(plan.slides) ? plan.slides : [];
  if (slides.length > 0) {
    const slidesWrap = document.createElement("div");
    slidesWrap.className = "lekhx-preview-section";
    const slidesTitle = document.createElement("h3");
    slidesTitle.textContent = `Slides (${slides.length})`;
    slidesWrap.appendChild(slidesTitle);

    slides.forEach((slide, idx) => {
      const slideBox = document.createElement("div");
      slideBox.className = "lekhx-slide-card";

      const st = document.createElement("strong");
      st.textContent = `Slide ${idx + 1}: ${slide.title || ""}`;
      slideBox.appendChild(st);

      const bullets = Array.isArray(slide.bullets) ? slide.bullets : [];
      if (bullets.length > 0) {
        const ul = document.createElement("ul");
        for (const bullet of bullets) {
          const li = document.createElement("li");
          li.textContent = bullet;
          ul.appendChild(li);
        }
        slideBox.appendChild(ul);
      }
      slidesWrap.appendChild(slideBox);
    });
    card.appendChild(slidesWrap);
  }

  return card;
}
