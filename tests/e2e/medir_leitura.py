import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

TXT=('- A judicializacao da saude cresceu de forma sustentada na ultima decada, com impacto direto '
     'no orcamento dos entes federados e na organizacao das filas de acesso a procedimentos de alta '
     'complexidade, segundo levantamento do Conselho Nacional de Justica.\n'
     '- O fenomeno concentra-se em medicamentos de alto custo ainda nao incorporados ao rol da '
     'Comissao Nacional de Incorporacao de Tecnologias no SUS.')

def seed():
    t={'id':'rep_x','nome':'Judicializacao da Saude','eixoId':'saude'}
    for c in ['panorama','causas','consequencias','resolucoes','jurisprudencia','aspectosPositivos',
              'aspectosNegativos','comparacao','estatistica','solucoes','exemplosAssociados',
              'argumentoAutoridade','repertorio']:
        t[c]=TXT
    return make_seed({'studyNickname':'Leo','repertorio':{
        'eixos':[{'id':'saude','nome':'Saúde Pública e SUS','icon':'⚕️','color':'#06b6d4'}],
        'temas':{'rep_x':t}}})

async def main():
    async with async_playwright() as p:
        browser,page,_=await setup_page(p, seed())
        try:
            for larg in [1920,1440,1280]:
                await page.set_viewport_size({'width':larg,'height':900})
                await page.evaluate("() => { showScreen('repertorio'); repSelectTema('rep_x'); }")
                await page.wait_for_timeout(600)
                r=await page.evaluate("""() => {
                  // acha o elemento que contem o texto longo de uma secao
                  const alvos=[...document.querySelectorAll('#rep-main-content *')]
                    .filter(e=>e.children.length===0 && (e.textContent||'').length>150);
                  if(!alvos.length)return null;
                  const e=alvos[0];
                  const cs=getComputedStyle(e);
                  const fs=parseFloat(cs.fontSize);
                  // largura de um "0" na fonte real -> caracteres por linha
                  const cv=document.createElement('canvas').getContext('2d');
                  cv.font=cs.fontWeight+' '+cs.fontSize+' '+cs.fontFamily;
                  const w0=cv.measureText('0').width;
                  const cx=e.getBoundingClientRect().width;
                  return {fonte:fs, alturaLinha:cs.lineHeight, larguraCaixa:Math.round(cx),
                          charsPorLinha:Math.round(cx/w0)};
                }""")
                print(f'janela {larg}px ->', r)
        finally:
            await browser.close()
asyncio.run(main())
