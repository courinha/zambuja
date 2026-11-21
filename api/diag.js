const U = {
  ivan: 'https://tle.ivanstanojevic.net/api/tle/?search=starlink&page-size=100&page=1',
  ivan2: 'https://tle.ivanstanojevic.net/api/tle/?search=starlink&page-size=100&page=40',
  keep: 'https://api.keeptrack.space/v2/sats',
  keep3: 'https://api.keeptrack.space/v3/sats',
  satnogs: 'https://db.satnogs.org/api/tle/?format=json',
  starlinkcom: 'https://api.starlink.com/public-files/ephemerides/MANIFEST.txt',
  supjson: 'https://celestrak.org/NORAD/elements/supplemental/sup-gp.php?FILE=starlink&FORMAT=csv'
};
module.exports = async (req, res) => {
  const out = {};
  await Promise.all(Object.entries(U).map(async ([k, u]) => {
    const t0 = Date.now(), o = out[k] = {};
    try {
      const r = await fetch(u, { signal: AbortSignal.timeout(45000) });
      o.status = r.status; o.cab = Date.now() - t0; o.tipo = r.headers.get('content-type'); o.cors = r.headers.get('access-control-allow-origin'); o.len = r.headers.get('content-length');
      let n = 0, ini = '', todo = ''; const rd = r.body.getReader(), dec = new TextDecoder();
      for (;;) { const { done, value } = await rd.read(); if (done) break; n += value.length; if (ini.length < 400) ini += dec.decode(value.slice(0, 400)); o.bytes = n; if (todo.length < 6e7) todo += dec.decode(value); o.ms = Date.now() - t0; }
      o.ini = ini.slice(0, 400); o.fim = Date.now() - t0; o.nstar = (todo.match(/STARLINK/gi) || []).length;
    } catch (e) { o.erro = String(e && e.message || e); o.ao = Date.now() - t0; }
  }));
  res.setHeader('Cache-Control', 'no-store'); res.status(200).json(out);
};
