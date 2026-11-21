const U = {
  grupo: 'https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle',
  sup: 'https://celestrak.org/NORAD/elements/supplemental/sup-gp.php?FILE=starlink&FORMAT=tle',
  nome: 'https://celestrak.org/NORAD/elements/gp.php?NAME=STARLINK-1&FORMAT=tle',
  www: 'https://www.celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle',
  com: 'https://celestrak.com/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle',
  estacoes: 'https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle'
};
module.exports = async (req, res) => {
  const out = {};
  await Promise.all(Object.entries(U).map(async ([k, u]) => {
    const t0 = Date.now(), o = out[k] = {};
    try {
      const r = await fetch(u, { signal: AbortSignal.timeout(45000) });
      o.status = r.status; o.cab = Date.now() - t0; o.tipo = r.headers.get('content-type'); o.cors = r.headers.get('access-control-allow-origin'); o.len = r.headers.get('content-length');
      let n = 0, ini = ''; const rd = r.body.getReader(), dec = new TextDecoder();
      for (;;) { const { done, value } = await rd.read(); if (done) break; n += value.length; if (ini.length < 160) ini += dec.decode(value.slice(0, 160)); o.bytes = n; o.ms = Date.now() - t0; }
      o.ini = ini.slice(0, 160); o.fim = Date.now() - t0;
    } catch (e) { o.erro = String(e && e.message || e); o.ao = Date.now() - t0; }
  }));
  res.setHeader('Cache-Control', 'no-store'); res.status(200).json(out);
};
