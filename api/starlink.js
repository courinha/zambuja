/* Órbitas (TLE) de todos os satélites Starlink, para o céu em realidade aumentada.
   Tenta o CelesTrak (grupo "starlink", depois os dados suplementares) e, se falhar, a base SatNOGS.
   A resposta fica 6 h na cache da Vercel: um pedido à fonte a cada 6 h, em vez de um por visitante.
   Se as fontes falharem, a cache continua a servir a última resposta boa até 3 dias. */
const UA = { 'User-Agent': 'zambujeira.pt (cache do grupo starlink, a cada 6 h)' };
const tle = txt => {
  const l = txt.split(/\r?\n/).map(x => x.trimEnd()).filter(Boolean), out = [];
  for (let i = 0; i + 2 < l.length; i++) {
    if (l[i + 1].startsWith('1 ') && l[i + 2].startsWith('2 ')) { out.push(l[i].trim(), l[i + 1], l[i + 2]); i += 2; }
  }
  return out;
};
const FONTES = [
  ['celestrak', async () => tle(await (await fetch('https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle', { headers: UA, signal: AbortSignal.timeout(15000) })).text())],
  ['celestrak-sup', async () => tle(await (await fetch('https://celestrak.org/NORAD/elements/supplemental/sup-gp.php?FILE=starlink&FORMAT=tle', { headers: UA, signal: AbortSignal.timeout(15000) })).text())],
  ['satnogs', async () => {
    const j = await (await fetch('https://db.satnogs.org/api/tle/?format=json', { headers: UA, signal: AbortSignal.timeout(20000) })).json();
    const out = [];
    for (const s of j) if (s && /STARLINK/i.test(s.tle0 || '') && s.tle1 && s.tle2) out.push(String(s.tle0).replace(/^0 /, '').trim(), s.tle1, s.tle2);
    return out;
  }]
];
module.exports = async (req, res) => {
  const erros = [];
  for (const [nome, ler] of FONTES) {
    try {
      const out = await ler();
      if (out.length < 900) throw new Error('lista curta (' + out.length / 3 + ')');
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
