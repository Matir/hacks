const maxReadingsPerChan = 1024;

function getWSEndpoint() {
  var protocol = document.location.protocol == "https:" ? "wss://" : "ws://";
  var host = document.location.host;
  return protocol + host + "/ws";
};

function connectWS(cb) {
  var endpoint = getWSEndpoint();
  var ws = new WebSocket(endpoint);
  ws.onmessage = function(msg) {
    cb(JSON.parse(msg.data));
  };
  return ws;
};

async function getRawReadings() {
  let resp = await fetch('/readings');
  return await resp.json();
};

function parseReadings(chans, newReadings) {
  for (var i=0;i<newReadings.length;i++) {
    r = newReadings[i];
    r['tsmillis'] = Date.parse(r['Timestamp']);
    var chid = r['ChannelID'];
    if (chans[chid] === undefined) {
      chans[chid] = Array();
    }
    chans[chid].push(r);
  }
  for (var c=0;c<chans.length;c++) {
    chans[c].sort(function(a, b) {
      if (a['tsmillis'] < b['tsmillis'])
        return -1;
      return 1;
    });
    if (chans[c].length > maxReadingsPerChan) {
      chans[c] = chans[c].slice(chans[c].length - maxReadingsPerChan);
    }
  }
  return chans;
};

async function getReadings() {
  let raw = await getRawReadings();
  return parseReadings({}, raw);
};

async function setupReadingHandler(displayUpdater) {
  var readings = await getReadings();
  connectWS(function(data) {
    parseReadings(readings, data);
    if (displayUpdater !== undefined)
      displayUpdater(readings);
  });
};

function getGraphReadings(chanReadings) {
  var v = Array();
  var a = Array();
  for (var i=0;i<chanReadings.length;i++) {
    v.push(chanReadings[i]['Millivolts']/1000);
    a.push(chanReadings[i]['Milliamps']/1000);
  }
  return {
    'voltages': v,
    'current': a,
  };
};

function createCharts(readings) {
  var charts = {};
  for(var i=1;i<=channels;i++) {
    let canvas = document.getElementById('ch'+i+'-graph');
    let graphData = getGraphReadings(readings[i]);
    charts[i] = new Chart(canvas, {
      type: 'line',
      data: {
        datasets: [
          {
            label: 'Volts',
            data: graphData.voltages,
            fill: false,
            borderColor: 'rgba(255, 0, 0, 0.5)',
          },
          {
            label: 'Amps',
            data: graphData.current,
            fill: false,
            borderColor: 'rgba(0, 0, 255, 0.5)',
          }
        ]
      },
      options: {
        responsive: false,
        maintainAspectRatio: false,
      }
    });
  }
  return charts;
};

function updateChartData(charts, readings) {
  for(var i=1;i<=channels;i++) {
    let chart = charts[i];
    let graphData = getGraphReadings(readings[i]);
    chart.data.datasets[0].data = graphData.voltages;
    chart.data.datasets[1].data = graphData.current;
    chart.update();
  }
}

async function main() {
  window.readings = await getReadings();
  window.charts = createCharts(window.readings);
  connectWS(function(data) {
    parseReadings(window.readings, data);
    updateChartData(window.charts, window.readings);
  });
};

window.addEventListener("load", main);
