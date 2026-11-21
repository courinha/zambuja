/* Órbitas (TLE) da Estação Espacial Internacional, da Tiangong e do Hubble, para o céu do site.
   Lê o CelesTrak e deixa a resposta 6 h na cache da Vercel: o CelesTrak recebe 3 pedidos a cada 6 h,
   em vez de um por visitante (bloqueia quem descarrega a mesma lista muitas vezes). Se falhar, a cache
   continua a servir a última resposta boa até 7 dias. */
const IDS = ['25544', '48274', '20580'];
module.exports = async (req, res) => {
  try {
    const ler = (id, ms) => fetch(`https://celestrak.org/NORAD/elements/gp.php?CATNR=${id}&FORMAT=tle`, {
      headers: { 'User-Agent': 'zambujeira.pt (cache de 3 TLE, a cada 6 h)' },
      signal: AbortSignal.timeout(ms)
    }).then(r => (r.ok ? r.text() : '')).then(t => (/^1 \d{5}/m.test(t) ? t.trim() : '')).catch(() => '');
    // cada satélite tem duas tentativas (o CelesTrak às vezes não responde à primeira)
    const partes = await Promise.all(IDS.map(async id => (await ler(id, 9000)) || ler(id, 14000)));
    const boas = partes.filter(Boolean), txt = boas.join('\n');
    if (!txt) throw new Error('sem órbitas');
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    // lista incompleta (faltou algum satélite): fica só 10 min na cache, para voltar a tentar depressa
    res.setHeader('Cache-Control', boas.length === IDS.length
      ? 'public, max-age=3600, s-maxage=21600, stale-while-revalidate=86400, stale-if-error=604800'
      : 'public, max-age=300, s-maxage=600');
    res.status(200).send(txt + '\n');
  } catch (e) {
    res.setHeader('Cache-Control', 'no-store');
    res.status(502).send('');
  }
};
