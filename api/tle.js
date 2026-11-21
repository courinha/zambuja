/* Órbitas (TLE) da Estação Espacial Internacional, da Tiangong e do Hubble, para o céu do site.
   Lê o CelesTrak e deixa a resposta 6 h na cache da Vercel: o CelesTrak recebe 3 pedidos a cada 6 h,
   em vez de um por visitante (bloqueia quem descarrega a mesma lista muitas vezes).
   Se o CelesTrak não responder (acontece), vai buscar o que faltar a uma cópia pública dos mesmos dados
   (github.com/astrion-tech/celestrak-mirror, atualizada de 30 em 30 min).
   Se tudo falhar, a cache continua a servir a última resposta boa até 7 dias. */
const IDS = ['25544', '48274', '20580'];
const COPIA = 'https://raw.githubusercontent.com/astrion-tech/celestrak-mirror/main/tle/';
const texto = (u, ms) => fetch(u, { signal: AbortSignal.timeout(ms) }).then(r => (r.ok ? r.text() : '')).catch(() => '');
// devolve o bloco de 3 linhas do satélite com este número, ou ''
const bloco = (txt, id) => {
  const l = txt.split(/\r?\n/);
  for (let i = 0; i + 2 < l.length; i++) {
    if (l[i + 1].startsWith('1 ' + id) && l[i + 2].startsWith('2 ' + id)) return [l[i].trimEnd(), l[i + 1].trimEnd(), l[i + 2].trimEnd()].join('\n');
  }
  return '';
};
module.exports = async (req, res) => {
  try {
    const partes = await Promise.all(IDS.map(async id =>
      bloco(await texto(`https://celestrak.org/NORAD/elements/gp.php?CATNR=${id}&FORMAT=tle`, 8000), id)));
    if (partes.some(p => !p)) {
      const [est, cie] = await Promise.all([texto(COPIA + 'stations.tle', 8000), texto(COPIA + 'science.tle', 8000)]);
      IDS.forEach((id, i) => { if (!partes[i]) partes[i] = bloco(est, id) || bloco(cie, id); });
    }
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
