# Backup: eram 30 copias completas do banco (30x o tamanho dos dados por usuario).
# Agora sao DUAS copias, cada uma atualizada no lugar so com o que mudou. Duas, e nao
# uma, porque com uma so um banco corrompido sobrescreveria a unica saida.
# Aqui: a 1a gravacao apaga os modelos antigos; cada dia sobe so o delta; a copia do
# dia anterior NAO e tocada; e restaurar volta pra qualquer uma das duas.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
K='k1';T='t1'
CARDS={('c%d'%i):{'id':'c%d'%i,'mbId':T,'pergunta':'P %d'%i,'resposta':'R %d'%i,'acertos':0,'erros':0}
       for i in range(1,401)}
seed=make_seed({'studyNickname':'Leo','flashcards':CARDS,
  'kingdoms':[{'id':K,'name':'Enfermagem','icon':'ok'}],
  'topics':{K:[{'id':T,'name':'Urgencia','subtopics':[{'id':'s1','name':'Choque','priority':30}]}]}})

# "dia" e simulado: o app so grava uma vez por data, entao o teste avanca a data
# sobrescrevendo todayStr() -- que e a mesma funcao que o backup usa.
JS_RODAR = """async(dia)=>{
  window.todayStr=()=>dia;
  try{localStorage.removeItem('vdn_backup_last_date');}catch(e){}
  backupFailedThisSession=false; backupCheckInFlight=false;
  window.__updateCalls.length=0;
  maybeBackupDB();
  for(let i=0;i<80;i++){ if(!backupCheckInFlight)break; await new Promise(r=>setTimeout(r,50)); }
  await new Promise(r=>setTimeout(r,150));
  const up=window.__updateCalls.filter(c=>c.op==='update'&&c.val&&Object.keys(c.val).some(k=>k.indexOf('vdn_v1_b')===0));
  const payload=up.length?up[up.length-1].val:{};
  const caminhos=Object.keys(payload);
  const u=window.__root.users.TEST_UID_LEO;
  return {
    caminhos, bytes: JSON.stringify(payload).length,
    slotEscrito: (caminhos.find(k=>k.indexOf('vdn_v1_bkpMeta/')===0)||'').split('/')[1]||null,
    cards: caminhos.filter(k=>/^vdn_v1_bkp\\/[ab]\\/flashcards\\//.test(k)).map(k=>k.split('/').pop()),
    meta: u.vdn_v1_bkpMeta||null,
    copias: Object.keys(u.vdn_v1_bkp||{}).map(s=>[s,Object.keys((u.vdn_v1_bkp[s]||{}).flashcards||{}).length]),
    legado: ['vdn_v1_backups','vdn_v1_backupAtual','vdn_v1_backupSig','vdn_v1_backupMeta'].filter(p=>p in u),
  };
}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        # estado de quem vem do modelo antigo: 30 copias completas, nenhuma assinatura
        await page.evaluate("""()=>{
          const u=window.__root.users.TEST_UID_LEO;
          delete u.vdn_v1_bkp; delete u.vdn_v1_bkpSig; delete u.vdn_v1_bkpMeta;
          u.vdn_v1_backups={}; u.vdn_v1_backupMeta={};
          for(let i=1;i<=30;i++){
            const d='2026-08-'+String(i).padStart(2,'0');
            u.vdn_v1_backups[d]=JSON.parse(JSON.stringify(u.vdn_v1));
            u.vdn_v1_backupMeta[d]=Date.now();
          }
        }""")

        print('=== A) dia 1: primeira copia + modelos antigos apagados ===')
        r1=await page.evaluate(JS_RODAR,'2026-09-10')
        print('   copia escrita: %s | %d caminhos | %d bytes | %d cards'
              %(r1['slotEscrito'],len(r1['caminhos']),r1['bytes'],len(r1['cards'])))
        print('   sobrou do modelo antigo: %s'%(r1['legado'] or 'nada'))
        print('   copias: %s'%r1['copias'])
        assert r1['legado']==[], r1['legado']
        assert len(r1['cards'])==400, len(r1['cards'])
        assert r1['copias']==[['a',400]], r1['copias']
        print('   OK\n')

        print('=== B) dia 2: revisei 3 cards -> vai pra OUTRA copia, so o delta ===')
        await page.evaluate("()=>{['c7','c90','c333'].forEach(id=>{db.flashcards[id].acertos=1;});}")
        r2=await page.evaluate(JS_RODAR,'2026-09-11')
        print('   copia escrita: %s | %d bytes | cards no delta: %d (a copia b estava vazia)'
              %(r2['slotEscrito'],r2['bytes'],len(r2['cards'])))
        print('   copias: %s | meta: %s'%(r2['copias'],r2['meta']))
        assert r2['slotEscrito']=='b', r2['slotEscrito']
        # a copia b estava vazia -> recebe tudo; o que importa e a "a" continuar intacta
        assert sorted(x[1] for x in r2['copias'])==[400,400], r2['copias']
        assert r2['meta']['a']['data']=='2026-09-10' and r2['meta']['b']['data']=='2026-09-11', r2['meta']
        print('   OK\n')

        print('=== C) dia 3: sobrescreve a MAIS ANTIGA (a), delta de 2 dias ===')
        await page.evaluate("()=>{db.flashcards['c50'].acertos=2;}")
        r3=await page.evaluate(JS_RODAR,'2026-09-12')
        print('   copia escrita: %s | %d bytes | cards no delta: %s'
              %(r3['slotEscrito'],r3['bytes'],sorted(r3['cards'])))
        print('   meta: %s'%r3['meta'])
        assert r3['slotEscrito']=='a', r3['slotEscrito']
        assert sorted(r3['cards'])==['c333','c50','c7','c90'], r3['cards']  # 2 dias de mudanca
        assert r3['bytes']<r1['bytes']/20, (r3['bytes'],r1['bytes'])
        assert r3['meta']['a']['data']=='2026-09-12' and r3['meta']['b']['data']=='2026-09-11'
        print('   OK\n')

        print('=== D) dia 4: sobrescreve a b, e a copia de ontem (a) fica intacta ===')
        await page.evaluate("()=>{db.flashcards['c200'].acertos=9;}")
        antes=await page.evaluate("()=>JSON.stringify(window.__root.users.TEST_UID_LEO.vdn_v1_bkp.a)")
        r4=await page.evaluate(JS_RODAR,'2026-09-13')
        depois=await page.evaluate("()=>JSON.stringify(window.__root.users.TEST_UID_LEO.vdn_v1_bkp.a)")
        print('   copia escrita: %s | cards no delta: %s'%(r4['slotEscrito'],sorted(r4['cards'])))
        print('   copia de ontem (a) intacta: %s'%(antes==depois))
        assert r4['slotEscrito']=='b' and antes==depois
        assert sorted(r4['cards'])==['c200','c50'], r4['cards']
        print('   OK\n')

        print('=== E) card apagado sai da copia tambem ===')
        await page.evaluate("()=>{delete db.flashcards['c7'];}")
        r5=await page.evaluate(JS_RODAR,'2026-09-14')
        sumiu=await page.evaluate("s=>!('c7' in window.__root.users.TEST_UID_LEO.vdn_v1_bkp[s].flashcards)",r5['slotEscrito'])
        print('   copia escrita: %s | c7 sumiu dela: %s'%(r5['slotEscrito'],sumiu))
        assert sumiu
        print('   OK\n')

        print('=== F) restaurar volta pra copia escolhida ===')
        meta=await page.evaluate("()=>window.__root.users.TEST_UID_LEO.vdn_v1_bkpMeta")
        # a copia mais antiga ainda tem os 400 (c7 so saiu da mais nova)
        velha=min(meta,key=lambda s:meta[s]['data'])
        nova=max(meta,key=lambda s:meta[s]['data'])
        for slot,esperado in ((nova,399),(velha,400)):
            await page.evaluate("()=>{db.flashcards={};db.kingdoms=[];}")
            await page.evaluate("s=>restoreFromBackup(s)",slot)
            await page.wait_for_timeout(400)
            n=await page.evaluate("()=>[Object.keys(db.flashcards||{}).length,(db.kingdoms||[]).length]")
            print('   copia %s (%s) -> %d flashcards, %d reino(s) (esperado %d)'
                  %(slot,meta[slot]['data'],n[0],n[1],esperado))
            assert n[0]==esperado and n[1]==1, n
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
