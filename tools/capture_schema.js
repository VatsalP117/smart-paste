// Capture a page's form as Smart Paste FormSchema JSON.
//
// How to use:
//   1. Open the form in Chrome. If it has repeated rows (e.g. IRCTC passengers),
//      add all the rows first so they exist in the page.
//   2. Open DevTools (Cmd+Option+J), paste this whole file into the Console, press Enter.
//   3. The JSON is copied to your clipboard. Save it as evals/forms/<name>.json.
//   4. Edit by hand: rename IDs to readable ones, set "group" and "row" for
//      repeated sections, delete fields you don't care about.
//
// This is a rough first version of the extension's form reader. Notice what's
// hard: missing labels, odd IDs, dropdowns that aren't real <select>s.

(() => {
  const FORM_NAME = prompt("Name for this form (e.g. address_india)?", "my_form") || "my_form";

  const clean = (s) => (s || "").replace(/\s+/g, " ").trim() || null;
  const slug = (s) => (s || "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 40);

  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const st = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && st.visibility !== "hidden" && st.display !== "none";
  };

  const labelFor = (el) => {
    if (el.labels && el.labels.length) return clean(el.labels[0].innerText);
    if (el.getAttribute("aria-label")) return clean(el.getAttribute("aria-label"));
    const by = el.getAttribute("aria-labelledby");
    if (by) {
      const text = by.split(" ").map((id) => document.getElementById(id)?.innerText || "").join(" ");
      if (clean(text)) return clean(text);
    }
    return null;
  };

  // Nearest visible text before the field, for forms with no real <label>.
  const nearbyText = (el) => {
    let node = el;
    for (let depth = 0; depth < 4 && node; depth++) {
      node = node.parentElement;
      const text = clean(node?.innerText);
      if (text && text.length < 120) return text;
    }
    return null;
  };

  const kindOf = (el) => {
    const tag = el.tagName.toLowerCase();
    if (tag === "select") return "select";
    if (tag === "textarea") return "textarea";
    const t = (el.type || "text").toLowerCase();
    if (["email", "tel", "number", "date", "radio", "checkbox"].includes(t)) return t;
    return "text";
  };

  const skipTypes = new Set(["hidden", "submit", "button", "reset", "image", "file", "password", "search"]);
  const els = [...document.querySelectorAll("input, select, textarea")].filter(
    (el) => !skipTypes.has((el.type || "").toLowerCase()) && visible(el)
  );

  const fields = [];
  const usedIds = new Set();
  const seenRadioGroups = new Set();

  for (const el of els) {
    const kind = kindOf(el);
    let options = null;

    if (kind === "radio") {
      // One field per radio group, with each radio's label as an option.
      if (!el.name || seenRadioGroups.has(el.name)) continue;
      seenRadioGroups.add(el.name);
      options = [...document.querySelectorAll(`input[type=radio][name="${CSS.escape(el.name)}"]`)]
        .map((r) => labelFor(r) || r.value)
        .filter(Boolean);
    }
    if (kind === "select") {
      options = [...el.options].map((o) => clean(o.text)).filter((t) => t && !/^(select|choose|--)/i.test(t));
    }

    const label = labelFor(el);
    let id = slug(label || el.name || el.id || el.placeholder) || `field_${fields.length}`;
    while (usedIds.has(id)) id = `${id}_2`;
    usedIds.add(id);

    const field = {
      id,
      kind,
      label,
      placeholder: clean(el.placeholder),
      autocomplete: el.getAttribute("autocomplete") && el.getAttribute("autocomplete") !== "off" ? el.getAttribute("autocomplete") : null,
      nearby_text: label ? null : nearbyText(el),
      pattern: el.getAttribute("pattern"),
      max_length: el.maxLength > 0 ? el.maxLength : null,
      required: !!el.required || el.getAttribute("aria-required") === "true",
      options,
      group: null,
      row: null,
    };
    // Drop empty keys to keep the file readable.
    for (const k of Object.keys(field)) if (field[k] === null) delete field[k];
    fields.push(field);
  }

  const schema = { name: FORM_NAME, url_host: location.host, fields };
  const json = JSON.stringify(schema, null, 2);
  copy(json); // DevTools-only helper: puts the text on your clipboard
  console.log(`Captured ${fields.length} fields. JSON copied to clipboard.`);
  console.log(json);
})();
