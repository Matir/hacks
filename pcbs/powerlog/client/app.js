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
