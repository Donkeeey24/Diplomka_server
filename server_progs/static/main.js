let chart;
let autoRefresh = false;
let refreshInterval;
let lastUsedData = [];

// --- LOGIN MODAL FUNCTIONALITA ---
async function doLogin() {
  const username = document.getElementById("loginUser").value;
  const password = document.getElementById("loginPass").value;
  const resp = await fetch("/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
  });
  if (resp.ok) {
    const data = await resp.json();
    window.localStorage.setItem("access_token", data.access_token);
    document.getElementById("loginModal").style.display = "none";
    document.getElementById("main-content").style.display = "";
    initializeApp();
  } else {
    document.getElementById("loginError").textContent = "Chybný login!";
  }
}

function getAuthHeader() {
  const token = window.localStorage.getItem("access_token");
  return token ? { Authorization: "Bearer " + token } : {};
}

async function checkLogin() {
  const token = window.localStorage.getItem("access_token");
  if (token) {
    try {
      const resp = await fetch("/protected", { headers: getAuthHeader() });
      if (resp.ok) {
        document.getElementById("loginModal").style.display = "none";
        document.getElementById("main-content").style.display = "";
        initializeApp();
        return;
      }
    } catch {}
  }
  document.getElementById("loginModal").style.display = "flex";
  document.getElementById("main-content").style.display = "none";
  document.getElementById("loginError").textContent = "";
  document.getElementById("loginPass").addEventListener("keyup", e => {
    if (e.key === "Enter") doLogin();
  });
  document.getElementById("loginUser").addEventListener("keyup", e => {
    if (e.key === "Enter") doLogin();
  });
}

// --- APP FUNCTIONALITA ---
async function fetchSensors() {
  try {
    const resp = await fetch("/sensors", { headers: getAuthHeader() });
    const sensors = await resp.json();
    const select = document.getElementById("sensorSelect");
    select.innerHTML = '<option value="">Všechny</option>';
    sensors.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      select.appendChild(opt);
    });
  } catch (e) {
    alert("Nepodařilo se načíst seznam senzorů!");
  }
}

function getLocalInputUTCString(fieldId) {
  const val = document.getElementById(fieldId).value;
  if (!val) return "";
  const d = new Date(val);
  return d.getUTCFullYear() + "-" +
         String(d.getUTCMonth()+1).padStart(2,'0') + "-" +
         String(d.getUTCDate()).padStart(2,'0') + " " +
         String(d.getUTCHours()).padStart(2,'0') + ":" +
         String(d.getUTCMinutes()).padStart(2,'0') + ":" +
         String(d.getUTCSeconds()).padStart(2,'0') + "+00:00";
}

function getUTCStringMinutesAgo(minutes) {
  const now = new Date();
  now.setSeconds(0, 0);
  const past = new Date(now.getTime() - minutes * 60 * 1000);
  return past.getUTCFullYear() + "-" +
         String(past.getUTCMonth()+1).padStart(2,'0') + "-" +
         String(past.getUTCDate()).padStart(2,'0') + " " +
         String(past.getUTCHours()).padStart(2,'0') + ":" +
         String(past.getUTCMinutes()).padStart(2,'0') + ":" +
         String(past.getUTCSeconds()).padStart(2,'0') + "+00:00";
}

async function fetchData({from, to, sensor}) {
  let url = "/data";
  const params = [];
  if (from) params.push("from_time=" + encodeURIComponent(from));
  if (to) params.push("to_time=" + encodeURIComponent(to));
  if (sensor) params.push("sensor_uuid=" + encodeURIComponent(sensor));
  if (params.length) url += "?" + params.join("&");
  const resp = await fetch(url, { headers: getAuthHeader() });
  const data = await resp.json();
  return data;
}

function aggregateData(data, maxPoints) {
  if (data.length <= maxPoints) return data;
  const bucketSize = Math.ceil(data.length / maxPoints);
  const buckets = [];
  for (let i = 0; i < data.length; i += bucketSize) {
    const slice = data.slice(i, i + bucketSize);
    const avgY = slice.reduce((sum, d) => sum + parseFloat(d.value), 0) / slice.length;
    const avgTime = new Date(
      slice.reduce((sum, d) => sum + new Date(d.time).getTime(), 0) / slice.length
    );
    buckets.push({
      time: avgTime.toISOString(),
      value: avgY
    });
  }
  return buckets;
}

async function loadData() {
  let useLastX = autoRefresh;
  let maxPoints = Number(document.getElementById("maxPoints").value) || 200;
  let sensor = document.getElementById("sensorSelect").value;
  let from, to;

  if (useLastX) {
    let lastMinutes = Number(document.getElementById("lastMinutes").value) || 10;
    from = getUTCStringMinutesAgo(lastMinutes);
    to = getUTCStringMinutesAgo(0);
  } else {
    from = getLocalInputUTCString("from");
    to = getLocalInputUTCString("to");
  }

  const data = await fetchData({from, to, sensor});
  data.sort((a, b) => new Date(a.time) - new Date(b.time));
  renderChart(data);
}

function renderChart(data) {
  const maxPoints = Number(document.getElementById("maxPoints").value) || 200;
  const reducedData = aggregateData(data, maxPoints);
  lastUsedData = reducedData;

  const chartData = reducedData.map((d) => ({
    x: d.time,
    y: Number(d.value)
  }));

  const ctx = document.getElementById('myChart').getContext('2d');
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [{
        label: 'Value',
        data: chartData,
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1,
        pointRadius: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          type: 'time',
          time: {
            tooltipFormat: 'yyyy-MM-dd HH:mm',
            displayFormats: {
              minute: 'HH:mm',
              hour: 'HH:mm',
              day: 'dd.MM.',
              month: 'LLL yyyy'
            }
          },
          title: {
            display: true,
            text: 'Čas'
          }
        },
        y: {
          title: {
            display: true,
            text: 'Hodnota'
          }
        }
      }
    }
  });
}

function toggleAutoRefresh() {
  autoRefresh = !autoRefresh;
  document.getElementById("autorefresh-status").textContent = autoRefresh ? "ON" : "OFF";
  if (autoRefresh) {
    loadData();
    refreshInterval = setInterval(() => {
      loadData();
    }, 5000);
  } else {
    clearInterval(refreshInterval);
  }
}

function downloadCSV() {
  if (!lastUsedData || !lastUsedData.length) {
    alert("Žádná data k exportu!");
    return;
  }
  let csv = "time,value\n";
  lastUsedData.forEach(d => {
    csv += `"${d.time.replace(/"/g, '""')}",${d.value}\n`;
  });
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `export-meteo-${(new Date()).toISOString().slice(0,19).replace(/[-T:]/g,"")}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function initializeApp() {
  document.getElementById("lastMinutes").addEventListener("change", () => {
    if (autoRefresh) {
      clearInterval(refreshInterval);
      toggleAutoRefresh();
    }
  });
  document.getElementById("maxPoints").addEventListener("change", () => loadData());
  document.getElementById("sensorSelect").addEventListener("change", () => loadData());
  fetchSensors().then(loadData);
}

document.addEventListener("DOMContentLoaded", checkLogin);