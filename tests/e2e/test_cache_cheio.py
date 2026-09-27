import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
K='k1';T='t1';S='s1'
FC={'fc%d'%i:{'id':'fc%d'%i,'mbId':T,'subId':S,'pergunta':'P %d'%i,'resposta':'R %d'%i,
   'tags':'','dificuldade':2,'acertos':0,'erros':0,'lastConf':0,'criacao':'2026-01-01T10:00:00Z'} for i in range(200)}
seed=make_seed({'studyNickname':'Leo','flashcards':FC,'kingdoms':[{'id':K,'name':'Enf','icon':'💉'}],
 'topics':{K:[{'id':T,'name':'C','subtopics':[{'id':S,'name':'A','priority':70,'studied':True}]}]}})

# Simula o QuotaExceededError de forma deterministica: o setItem da NOSSA chave falha
# enquanto o armazenamento estiver "cheio". Apagar chave libera espaco, como no navegador.
STUB = """
window.__quota={cheio:true, liberouCom:null, tentativas:0};
const _set=localStorage.setItem.bind(localStorage);
const _rem=localStorage.removeItem.bind(localStorage);
localStorage.setItem=function(k,v){
  if(k.indexOf('vdn_local_v1')===0){
    window.__quota.tentativas++;
    if(window.__quota.cheio){ const e=new Error('quota'); e.name='QuotaExceededError'; throw e; }
  }
  return _set(k,v);
};
localStorage.removeItem=function(k){
  if(k.indexOf('vdn_local_v1')===0&&k!==lsKey()){ window.__quota.cheio=false; window.__quota.liberouCom=k; }
  return _rem(k);
};
"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        try:
            print('=== 1) SEM IndexedDB + falta espaço -> apaga cache de OUTRA conta e grava na 2a ===')
            r=await page.evaluate("""(stub)=>{
              localStorage.setItem('vdn_local_v1_OUTRA_CONTA','{"x":1}');
              localStorage.setItem('vdn_local_v1','{"y":1}');
              eval(stub);
              cacheLocalDesligado=false; cacheIdbOk=false;  // navegador SEM IndexedDB: cai na reserva
              let erro=null; try{ gravarCacheLocal(); }catch(e){ erro=e.name; }
              return {erro, tentativas:window.__quota.tentativas, liberou:window.__quota.liberouCom,
                      desligado:cacheLocalDesligado,
                      gravou:!!localStorage.getItem(lsKey()),
                      restantes:Object.keys(localStorage).filter(k=>k.indexOf('vdn_local_v1')===0)};}""",STUB)
            print('   tentativas de gravação:',r['tentativas'],'| liberou espaço apagando:',r['liberou'])
            print('   gravou a própria cópia?',r['gravou'],'| cache desligado?',r['desligado'])
            print('   chaves restantes:',r['restantes'])
            print('   exceção vazou?',r['erro'] or 'não')
            assert r['erro'] is None and r['gravou'] and not r['desligado']
            assert r['tentativas']>=2, 'devia tentar de novo depois de liberar'
            assert 'vdn_local_v1_OUTRA_CONTA' not in r['restantes']
            print('   OK')

            print('\n=== 2) SEM IndexedDB e nem assim cabe: desliga e para de gastar tempo ===')
            r2=await page.evaluate("""()=>{
              window.__quota.cheio=true; window.__quota.tentativas=0;
              localStorage.removeItem=function(k){return undefined;};  // apagar nao ajuda mais
              cacheLocalDesligado=false; cacheIdbOk=false;  // navegador SEM IndexedDB: cai na reserva
              let erro=null; try{ gravarCacheLocal(); }catch(e){ erro=e.name; }
              const desligado=cacheLocalDesligado, t1=window.__quota.tentativas;
              const t=performance.now(); for(let i=0;i<30;i++)gravarCacheLocal();
              return {erro,desligado,t1,depois:window.__quota.tentativas,ms30:Math.round(performance.now()-t)};}""")
            print('   exceção vazou?',r2['erro'] or 'não','| desligou?',r2['desligado'])
            print('   tentativas na falha:',r2['t1'],'| tentativas nas 30 chamadas seguintes:',r2['depois']-r2['t1'])
            print('   custo das 30 chamadas depois de desligado: %d ms'%r2['ms30'])
            assert r2['erro'] is None and r2['desligado'] is True
            assert r2['depois']==r2['t1'], 'continuou tentando gravar depois de desligar'
            assert r2['ms30']<30
            print('   OK')

            print('\n=== 3) a nuvem continua recebendo com o cache desligado ===')
            await page.evaluate("()=>{db.xp=4242;saveDB();}")
            await page.wait_for_timeout(2500)
            xp=await page.evaluate("()=>((window.__root.users.TEST_UID_LEO||{}).vdn_v1||{}).xp")
            print('   xp no Firebase:',xp)
            assert xp==4242
            print('\nOK')
        finally:
            await b.close()
asyncio.run(main())
