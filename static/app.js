// Handle file upload
async function handleUpload(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/upload", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json();
    alert(err.detail);
    return;
  }

  const data = await response.json();
  currentUploadId = data.upload_id; 
  renderColumnSelectors(data.columns);
}

// Render columns
function renderColumnSelectors(columns) {
  const options = columns.map(c => `<option value="${c}">${c}</option>`).join("");

  const sumCheckboxes = columns.map(c => `
    <label>
      <input type="checkbox" name="sum-col" value="${c}"> ${c}
    </label>
  `).join("");

  const avgCheckboxes = columns.map(c => `
    <label>
      <input type="checkbox" name="avg-col" value="${c}"> ${c}
    </label>
  `).join("");

  const container = document.getElementById("column-selectors");
  container.innerHTML = `
    <label>Latitude column
      <select id="lat-col">${options}</select>
    </label>
    <label>Longitude column
      <select id="lon-col">${options}</select>
    </label>

    <fieldset>
      <legend>Columns to sum</legend>
      ${sumCheckboxes}
    </fieldset>

    <fieldset>
      <legend>Columns to average</legend>
      ${avgCheckboxes}
    </fieldset>
  `;
}

// Collect user selections and send to backend
function getCheckedValues(name) {
  const checked = document.querySelectorAll(`input[name="${name}"]:checked`);
  return Array.from(checked).map(el => el.value);
}

const sumCols = getCheckedValues("sum-col");
const avgCols = getCheckedValues("avg-col");