/* Órbitas (TLE) da Estação Espacial Internacional, da Tiangong e do Hubble, para o céu do site.
   Lê o CelesTrak e deixa a resposta 6 h na cache da Vercel: o CelesTrak recebe 3 pedidos a cada 6 h,
   em vez de um por visitante (bloqueia quem descarrega a mesma lista muitas vezes). Se falhar, a cache
   continua a servir a última resposta boa até 7 dias. */
const IDS = ['25544', '48274', '20580'];
module.exports = async (req, res) => {
  try {
    const partes = await Promise.all(IDS.map(id =>
      fetch(`https://celestrak.org/NORAD/elements/gp.php?CATNR=${id}&FORMAT=tle`, {
        headers: { 'User-Agent': 'zambuja.vercel.app (cache de 3 TLE, a cada 6 h)' },
        signal: AbortSignal.timeout(9000)
      }).then(r => (r.ok ? r.text() : '')).catch(() => '')));
    const txt = partes.map(t => t.trim()).filter(t => /^1 \d{5}/m.test(t)).join('\n');
    if (!txt) throw new Error('sem órbitas');
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.setHeader('Cache-Control', 'public, max-age=3600, s-maxage=21600, stale-while-revalidate=86400, stale-if-error=604800');
    res.status(200).send(txt + '\n');
  } catch (e) {
    res.setHeader('Cache-Control', 'no-store');
    res.status(502).send('');
  }
};
