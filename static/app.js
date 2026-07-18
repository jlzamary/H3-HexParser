let currentUploadId = null;

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

  document.getElementById("resolution-section").style.display = "";
  document.getElementById("process-btn").style.display = "";
  document.getElementById("map-frame").style.display = "none";
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

// Send the selected columns/resolution to the backend and render the returned map
async function handleProcess() {
  if (!currentUploadId) {
    alert("Please upload a file first.");
    return;
  }

  const payload = {
    upload_id: currentUploadId,
    lat_col: document.getElementById("lat-col").value,
    lon_col: document.getElementById("lon-col").value,
    sum_cols: getCheckedValues("sum-col"),
    avg_cols: getCheckedValues("avg-col"),
    resolution: parseInt(document.getElementById("resolution-input").value, 10),
  };

  const response = await fetch("/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json();
    alert(err.detail);
    return;
  }

  const html = await response.text();
  const mapFrame = document.getElementById("map-frame");
  mapFrame.srcdoc = html;
  mapFrame.style.display = "";
}

document.getElementById("file-input").addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (file) {
    handleUpload(file);
  }
});

document.getElementById("process-btn").addEventListener("click", handleProcess);