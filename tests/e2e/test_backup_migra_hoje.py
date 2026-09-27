# Quem ja tinha rodado o backup do modelo ANTIGO hoje ficava com a chave local
# 'vdn_backup_last_date' marcada com a data de hoje. Se o modelo novo usasse a mesma
# chave, ele curto-circuitava o dia inteiro: nenhuma copia nova era gravada e o selo
# dizia "sem backup" ate amanha. Aqui: o modelo novo grava na hora, mesmo assim.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
CARDS={('c%d'%i):{'id':'c%d'%i,'mbId':'t1','pergunta':'P','resposta':'R'} for i in range(1,51)}
seed=make_seed({'studyNickname':'Leo','flashcards':CARDS,
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'ok'}],
  'topics':{'k1':[{'id':'t1','name':'Urgencia','subtopics':[{'id':'s1','name':'Choque'}]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        # estado real de quem abriu o app hoje ANTES do deploy: backup antigo ja feito,
        # chave local antiga marcada com hoje, e nada nos caminhos novos.
        await page.evaluate("""()=>{
          const u=window.__root.users.TEST_UID_LEO;
          delete u.vdn_v1_bkp; delete u.vdn_v1_bkpSig; delete u.vdn_v1_bkpMeta;
          u.vdn_v1_backups={}; u.vdn_v1_backupMeta={};
          u.vdn_v1_backups[todayStr()]=JSON.parse(JSON.stringify(u.vdn_v1));
          u.vdn_v1_backupMeta[todayStr()]=Date.now();
          try{localStorage.setItem('vdn_backup_last_date',todayStr());}catch(e){}
          try{localStorage.removeItem('vdn_bkp2_last_date');}catch(e){}
          backupFailedThisSession=false; backupCheckInFlight=false;
        }""")
        antiga=await page.evaluate("()=>localStorage.getItem('vdn_backup_last_date')")
        print('chave local do modelo antigo: %s (hoje)'%antiga)

        await page.evaluate("()=>{saveDB();}")
        await page.wait_for_timeout(900)
        r=await page.evaluate("""()=>{
          const u=window.__root.users.TEST_UID_LEO;
          return {meta:u.vdn_v1_bkpMeta||null,
                  cards:Object.keys(((u.vdn_v1_bkp||{}).a||{}).flashcards||{}).length,
                  legadoSobrou:['vdn_v1_backups','vdn_v1_backupMeta'].filter(k=>k in u),
                  chaveNova:localStorage.getItem('vdn_bkp2_last_date')};
        }""")
        print('meta nova: %s'%r['meta'])
        print('cards na copia a: %d'%r['cards'])
        print('sobrou do modelo antigo: %s'%(r['legadoSobrou'] or 'nada'))
        print('chave local nova: %s'%r['chaveNova'])
        assert r['meta'] and r['cards']==50 and not r['legadoSobrou']
        print('   OK — o backup do modelo novo saiu HOJE, sem esperar amanha\n')

        estado=await page.evaluate("""async()=>{
          backupEstadoChecado=false; backupCheckInicial();
          await new Promise(r=>setTimeout(r,300));
          return {estado:backupEstado.estado,ultima:backupEstado.ultima,
                  selo:(document.getElementById('backup-badge')||{}).textContent||''};
        }""")
        print('selo: estado=%s ultima=%s texto=%r'%(estado['estado'],estado['ultima'],estado['selo'].strip()))
        assert estado['estado']=='ok' and estado['ultima']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
