/* Órbitas (TLE) de todos os satélites Starlink, para o céu em realidade aumentada.
   Lê o CelesTrak (grupo "starlink"); se não responder em 14 s (acontece), lê uma cópia pública dos mesmos
   dados (github.com/astrion-tech/celestrak-mirror, atualizada de 30 em 30 min).
   A resposta fica 6 h na cache da Vercel: um pedido à fonte a cada 6 h, em vez de um por visitante.
   Se as fontes falharem, a cache continua a servir a última resposta boa até 3 dias. */
const tle = txt => {
  const l = txt.split(/\r?\n/).map(x => x.trimEnd()).filter(Boolean), out = [];
  for (let i = 0; i + 2 < l.length; i++) {
    if (l[i + 1].startsWith('1 ') && l[i + 2].startsWith('2 ')) { out.push(l[i].trim(), l[i + 1], l[i + 2]); i += 2; }
  }
  return out;
};
const ler = async (u, ms) => tle(await (await fetch(u, { signal: AbortSignal.timeout(ms) })).text());
const FONTES = [
  ['celestrak', () => ler('https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle', 14000)],
  ['copia', () => ler('https://raw.githubusercontent.com/astrion-tech/celestrak-mirror/main/tle/starlink.tle', 20000)]
];
module.exports = async (req, res) => {
  const erros = [];
  for (const [nome, ler] of FONTES) {
    try {
      const out = await ler();
      if (out.length < 900) throw new Error('lista curta (' + out.length / 3 + ')');
      // /api/starlink?resumo=1 devolve só a contagem (para verificar sem descarregar a lista toda)
      if (req.query && req.query.resumo) { res.setHeader('Cache-Control', 'no-store'); return res.status(200).json({ fonte: nome, satelites: out.length / 3, primeiro: out.slice(0, 3), erros }); }
      res.setHeader('Content-Type', 'text/plain; charset=utf-8');
      res.setHeader('X-Fonte', nome);
      res.setHeader('Cache-Control', 'public, max-age=3600, s-maxage=21600, stale-while-revalidate=86400, stale-if-error=259200');
      return res.status(200).send(out.join('\n') + '\n');
    } catch (e) { erros.push(nome + ': ' + (e && e.message || e)); }
  }
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.status(502).send('sem orbitas · ' + erros.join(' | '));
};
