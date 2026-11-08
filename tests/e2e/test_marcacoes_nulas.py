# -*- coding: utf-8 -*-
# O Painel quebrava com "Cannot read properties of null (reading 'm')" quando uma prova (viva ou arquivada) tinha uma entrada
# nula em `marcacoes` (buraco que a nuvem devolve). O controle de erros e o resto do Painel tem que abrir mesmo assim.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,make_seed({'studyNickname':'Leo'}))
        await page.evaluate("()=>{window.confirm=()=>true;return true;}")
        print('=== A) marcacoes com entrada nula: o agregado e o Painel nao quebram ===')
        r=await page.evaluate("""()=>{
          db.provasArquivo=[{id:'a1',num:1,tentativas:[{respostas:['C','E'],acertos:1}],marcacoes:{0:{m:'conteudo',s:'Assunto X',k:'💉'},1:null,2:undefined}}];
          db.provas=[{id:'p1',num:2,chaves:['x','y'],chaves2:['x','y'],tentativas:[{respostas:['C','E'],acertos:0}],marcacoes:{0:null,1:{m:'atencao',s:'Assunto Y'}}}];
          let erro=null,agg=null;try{agg=motivosAgregado();}catch(e){erro=String(e);}
          let erro2=null;try{showScreen('dashboard');renderDashboard();}catch(e){erro2=String(e);}
          const clone=provaMarcacoesClone({0:null,1:{m:'chute',g:[{a:1}]}});
          return {erro,erro2,tot:agg&&agg.tot,clone:Object.keys(clone)};}""")
        print('   ',r)
        assert r['erro'] is None and r['erro2'] is None
        assert r['tot']['conteudo']==1 and r['tot']['atencao']==1 and r['clone']==['1']
        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves,graves
        await b.close()
        print('OK')
asyncio.run(main())
