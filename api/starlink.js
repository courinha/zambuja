/* Órbitas (TLE) de todos os satélites Starlink, para o céu em realidade aumentada.
   Lê o CelesTrak (grupo "starlink") e deixa a resposta 6 h na cache da Vercel: um pedido ao CelesTrak a cada 6 h,
   em vez de um por visitante. Se falhar, a cache continua a servir a última resposta boa até 3 dias. */
module.exports = async (req, res) => {
  try {
    const r = await fetch('https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle', {
      headers: { 'User-Agent': 'zambujeira.pt (cache do grupo starlink, a cada 6 h)' },
      signal: AbortSignal.timeout(20000)
    });
    if (!r.ok) throw new Error('celestrak ' + r.status);
    const linhas = (await r.text()).split(/\r?\n/).map(l => l.trimEnd()).filter(Boolean);
    const out = [];
    for (let i = 0; i + 2 < linhas.length; i++) {
      if (linhas[i + 1] && linhas[i + 2] && linhas[i + 1].startsWith('1 ') && linhas[i + 2].startsWith('2 ')) {
        out.push(linhas[i].trim(), linhas[i + 1], linhas[i + 2]); i += 2;
      }
    }
    if (out.length < 300) throw new Error('lista curta');
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.setHeader('Cache-Control', 'public, max-age=3600, s-maxage=21600, stale-while-revalidate=86400, stale-if-error=259200');
    res.status(200).send(out.join('\n') + '\n');
  } catch (e) {
    res.setHeader('Cache-Control', 'no-store');
    res.status(502).send('');
  }
};
