# Cadeira colocada no editor vira assento de verdade.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

MONTA = '''()=>{
  // mapa novo com duas cadeiras da folha "chair": frame 1 (de frente) e 5 (de costas)
  mapedMapa=mapedMapaVazio(20,15);
  const ts=SALA_TS_BY_NAME.chair;
  mapedMapa.layers.push({draworder:'topdown',id:99,name:'Obj_chair',objects:[
    {gid:ts.f+1,height:64,id:1,name:'',rotation:0,type:'',visible:true,width:32,x:5*32,y:6*32+32},
    {gid:ts.f+5,height:64,id:2,name:'',rotation:0,type:'',visible:true,width:32,x:9*32,y:6*32+32}
  ],opacity:1,type:'objectgroup',visible:true,x:0,y:0});
  mapedSujo=false;
  return {assentosAntes:mapedContaAssentos()};
}'''
LE = '''()=>{
  const sit=mapedMapa.layers.find(l=>l.name==='Sit');
  const marcas=[];
  if(sit)sit.data.forEach((v,i)=>{ if(v)marcas.push({x:i%mapedMapa.width,y:Math.floor(i/mapedMapa.width),v}); });
  return {assentos:mapedContaAssentos(), marcas};
}'''

async def main():
    async with async_playwright() as pw:
        browser,page,errors=await setup_page(pw, make_seed({'studyNickname':'R','studyCharacter':'ash'}))
        try:
            antes=await page.evaluate(MONTA)
            print('=== mapa do editor com 2 cadeiras colocadas ===')
            print('  assentos antes de marcar:',antes['assentosAntes'])
            assert antes['assentosAntes']==0, 'a cadeira colocada já contava como assento?'
            print('  ✓ confirmado: colocar a cadeira NÃO cria assento (era o bug)')

            await page.evaluate("()=>mapedMarcarAssentos()")
            r=await page.evaluate(LE)
            print('\n=== depois de "Marcar cadeiras" ===')
            print('  assentos:',r['assentos'],'| marcas:',r['marcas'])
            assert r['assentos']==2, r
            # frame 1 = de frente -> senta virado pra baixo (1); frame 5 = de costas -> pra cima (4)
            porX={m['x']:m['v'] for m in r['marcas']}
            assert porX[5]==1, f'frame 1 devia virar direção 1 (baixo), veio {porX.get(5)}'
            assert porX[9]==4, f'frame 5 devia virar direção 4 (cima), veio {porX.get(9)}'
            print('  ✓ direções conferidas no mapa campus: frame 1 → baixo, frame 5 → cima')

            print('\n=== não sobrescreve o que você marcou à mão ===')
            await page.evaluate("()=>{mapedSit().data[6*mapedMapa.width+5]=3;}")  # troca pra direita
            await page.evaluate("()=>mapedMarcarAssentos()")
            v=await page.evaluate("()=>mapedSit().data[6*mapedMapa.width+5]")
            print('  valor na cadeira que você ajustou:',v)
            assert v==3, f'sobrescreveu o ajuste manual: {v}'
            print('  ✓ respeita o ajuste manual')

            print('\n=== o jogo enxerga esses assentos ===')
            n=await page.evaluate('''()=>{
              const m=mapedParaPublicar();
              const sit=m.layers.find(l=>l.name==='Sit');
              const DIRS={1:'down',2:'left',3:'right',4:'up'};
              const assentos=[];
              sit.data.forEach((v,i)=>{ if(v)assentos.push(DIRS[v]); });
              return {camadas:m.layers.map(l=>l.name), assentos};
            }''')
            print('  camadas publicadas:',n['camadas'])
            print('  assentos que o jogo vai ler:',n['assentos'])
            assert 'Sit' in n['camadas'], 'a camada Sit não foi publicada'
            assert len(n['assentos'])==2, n
            print('  ✓ a camada Sit vai junto na publicação')
            print('\nOK — cadeira do editor vira assento, com a direção que dá pra afirmar')
        finally:
            await browser.close()
asyncio.run(main())
