import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors
from medir_leitura import seed as seed_leitura

MEDE = """(tema) => {
  document.documentElement.setAttribute('data-theme', tema);
  const cs=getComputedStyle(document.documentElement);
  const v=n=>cs.getPropertyValue(n).trim();
  const rgb=(c)=>{const d=document.createElement('div');d.style.color=c;document.body.appendChild(d);
    const x=getComputedStyle(d).color;d.remove();
    const m=x.match(/\\d+/g);return m?m.slice(0,3).map(Number):null;};
  const lin=c=>{c/=255;return c<=0.03928?c/12.92:Math.pow((c+0.055)/1.055,2.4);};
  const L=c=>{const p=rgb(c);return p?0.2126*lin(p[0])+0.7152*lin(p[1])+0.0722*lin(p[2]):null;};
  const cr=(a,b)=>{const la=L(a),lb=L(b);if(la===null||lb===null)return null;
    const hi=Math.max(la,lb),lo=Math.min(la,lb);return (hi+0.05)/(lo+0.05);};
  const fundos=['--panel','--panel2','--bg'].map(v);
  const out={};
  ['--red-t','--green-t','--orange-t','--cyan-t','--gold-t','--pink-t','--muted','--text2','--accent']
    .forEach(n=>{const c=v(n); out[n]= c ? Math.min(...fundos.map(f=>cr(c,f))) : null;});
  out['--danger definida'] = !!v('--danger');
  return out;
}"""

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, seed_leitura())
        try:
            ruins=[]
            for tema in ['light','dark']:
                r=await page.evaluate(MEDE, tema)
                print(f'\n=== tema {tema} (pior contraste sobre painel/painel2/fundo) ===')
                for k,val in r.items():
                    if k=='--danger definida':
                        print(f'  {k}: {val}'); assert val, '--danger continua indefinida'; continue
                    assert val is not None, f'{k} não resolveu'
                    ok = val>=4.5
                    print(f'  {k:11s} {val:5.2f}:1  {"OK" if ok else "RUIM"}')
                    if not ok: ruins.append((tema,k,round(val,2)))
            assert not ruins, f'ainda abaixo de 4,5:1 -> {ruins}'

            # largura de leitura, nas mesmas janelas de antes
            print('\n=== largura da linha de leitura ===')
            for larg in [1920,1440,1280]:
                await page.set_viewport_size({'width':larg,'height':900})
                await page.evaluate("() => { showScreen('repertorio'); repSelectTema('rep_x'); }")
                await page.wait_for_timeout(500)
                r=await page.evaluate("""() => {
                  const e=[...document.querySelectorAll('.rep-secao-body')]
                    .filter(x=>(x.textContent||'').length>150)[0];
                  if(!e)return null;
                  const cs=getComputedStyle(e);
                  const cv=document.createElement('canvas').getContext('2d');
                  cv.font=cs.fontWeight+' '+cs.fontSize+' '+cs.fontFamily;
                  return Math.round(e.getBoundingClientRect().width/cv.measureText('0').width);}""")
                print(f'  janela {larg}px -> {r} caracteres por linha')
                assert r and r<=80, f'ainda {r} caracteres por linha em {larg}px'
            assert not real_errors(errors), real_errors(errors)
            print('\nOK — semáforo legível nos dois temas, --danger existe, leitura na faixa confortável')
        finally:
            await browser.close()
asyncio.run(main())
