import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from seed_painel import seed

# injeta um reino com atrasadas E aproveitamento — a combinacao que zerava o nome
INJETA = """() => {
  // redesign A3: "Reinos que precisam de atenção" virou uma aba do Diagnóstico — abre ela
  document.getElementById('dd-reinos').checked=true;
  const linhas=[
    {name:'História de Cabo Verde e do Mundo', icon:'🕌', overdue:5, pct:12},
    {name:'Enfermagem', icon:'💊', overdue:0, pct:59},
    {name:'SUS', icon:'⚕', overdue:2, pct:74}];
  const el=document.getElementById('avg-time-list');
  el.innerHTML=linhas.map(r=>`
    <div class="atencao-item">
      <span style="font-size:16px;flex-shrink:0">${r.icon}</span>
      <div class="atencao-nome" style="flex:1;min-width:0;font-weight:800;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${r.name}</div>
      ${r.overdue>0?`<span style="background:rgba(220,38,38,0.1);color:var(--red-t);border-radius:999px;padding:2px 8px;font-size:9.5px;font-weight:900;flex-shrink:0">🔔 ${r.overdue} atrasadas</span>`:''}
      <div class="faixa-trilho" style="max-width:62px"><i style="width:${r.pct}%;background:var(--red)"></i></div>
      <span style="font-size:11px;font-weight:900;flex-shrink:0;width:34px;text-align:right">${r.pct}%</span>
    </div>`).join('');
  return true;
}"""

MEDE = """() => {
  const el=document.getElementById('avg-time-list');
  const cartao=el.closest('.section-card').getBoundingClientRect();
  const linhas=[...el.children].map(l=>{
    const nome=l.querySelector('.atencao-nome');
    const nr=nome?nome.getBoundingClientRect():null;
    return {nome:(nome?nome.textContent:'').slice(0,22), larguraNome:nr?Math.round(nr.width):0,
            passaDoCartao:Math.round(l.getBoundingClientRect().right-cartao.right)};
  });
  const b=document.getElementById('notif-permission-btn');
  b.style.display='inline-flex';
  const bc=b.closest('.section-card').getBoundingClientRect();
  return {linhas, botaoPassa:Math.round(b.getBoundingClientRect().right-bc.right)};
}"""

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, seed())
        try:
            for w,h,nome in [(1080,810,'iPad 9 paisagem'),(810,1080,'iPad 9 retrato'),
                             (1024,768,'iPad antigo'),(1920,1080,'desktop')]:
                await page.set_viewport_size({'width':w,'height':h})
                await page.evaluate("() => showScreen('dashboard')")
                await page.wait_for_timeout(600)
                await page.evaluate(INJETA)
                await page.wait_for_timeout(250)
                r=await page.evaluate(MEDE)
                print(f'{nome} ({w}x{h}): botão Lembretes passa {r["botaoPassa"]}px do cartão')
                for l in r['linhas']:
                    print(f'    nome "{l["nome"]}" -> {l["larguraNome"]}px | linha passa {l["passaDoCartao"]}px')
                assert r['botaoPassa']<=0, f'{nome}: o botão Lembretes ainda vaza do cartão'
                for l in r['linhas']:
                    assert l['larguraNome']>=100, \
                        f'{nome}: nome do reino com {l["larguraNome"]}px (sumia por completo antes)'
                    assert l['passaDoCartao']<=0, f'{nome}: linha do reino vazando do cartão'
                print()
            assert not real_errors(errors), real_errors(errors)
            print('OK — botão Lembretes dentro do cartão e nome do reino sempre legível')
        finally:
            await browser.close()
asyncio.run(main())
