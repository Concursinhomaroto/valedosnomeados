# "Queria tirar cards da fila de revisao, sem colocar o dominado, pq nao precisaria
# revisao agora, como Historia" — dominado e sobre o CARD; pausa e sobre o ESCOPO do
# edital agora. O interruptor de reino ja existia na Camara, mas so valia pros minibosses:
# os 186 flashcards vencidos de Historia continuavam na fila global.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def card(i,mb,venc=True):
    d=(-30 if venc else 30)
    return {'id':'c%d'%i,'mbId':mb,'pergunta':'P%d'%i,'resposta':'R%d'%i,'tags':'',
            'acertos':2,'erros':0,'sm2':{'ef':2.5,'reps':2,'interval':10},'_venc':venc}
CARDS={}
for i in range(1,11): CARDS['c%d'%i]=card(i,'t1')        # Enfermagem, vencidos
for i in range(11,17): CARDS['c%d'%i]=card(i,'t2')       # Historia, vencidos
seed=make_seed({'studyNickname':'Leo','flashcards':CARDS,
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💊','color':'#ec4899'},
              {'id':'k2','name':'Historia','icon':'🏰','color':'#f59e0b'}],
  'topics':{'k1':[{'id':'t1','name':'Urgencia','subtopics':[
                    {'id':'s1','name':'Choque','priority':70,'studied':True,'studiedAt':'2026-01-01'}]}],
            'k2':[{'id':'t2','name':'Brasil Colonia','subtopics':[
                    {'id':'s2','name':'Capitanias','priority':70,'studied':True,'studiedAt':'2026-01-01'}]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.evaluate("""()=>{
          const d=n=>{const x=new Date();x.setDate(x.getDate()-n);return x.toISOString();};
          Object.values(db.flashcards).forEach(c=>{c.ultimaRevisao=d(60);delete c._venc;});
          db.revReinosFora={}; showScreen('flashcards');
        }""")
        await page.wait_for_timeout(400)

        print('=== A) antes de pausar, Historia entra na fila global ===')
        r=await page.evaluate("""()=>({
          global:getAllFCEverywhere().length,
          due:getAllFCEverywhere().filter(c=>fcStatus(c)==='due').length,
          doReino:getAllFCForKingdom('k2').length})""")
        print('   fila global: %d cards · vencidos: %d · Historia tem %d'
              %(r['global'],r['due'],r['doReino']))
        assert r['global']==16 and r['doReino']==6
        print('   OK\n')

        print('=== B) pausando Historia ===')
        r2=await page.evaluate("""()=>{
          revToggleReino('k2');
          return {global:getAllFCEverywhere().length,
                  due:getAllFCEverywhere().filter(c=>fcStatus(c)==='due').length,
                  comPausados:getAllFCEverywhere(true).length,
                  doReino:getAllFCForKingdom('k2').length,
                  cardsIntactos:Object.keys(db.flashcards).length};
        }""")
        print('   fila global: %d (era 16) · vencidos: %d'%(r2['global'],r2['due']))
        print('   "Estudar por Reino" de Historia ainda tem: %d cards'%r2['doReino'])
        print('   nada foi apagado: %d cards no banco'%r2['cardsIntactos'])
        assert r2['global']==10 and r2['doReino']==6 and r2['cardsIntactos']==16
        assert r2['comPausados']==16
        print('   OK — saiu da fila, continua inteiro\n')

        print('=== C) o mesmo interruptor ja valia pros minibosses ===')
        r3=await page.evaluate("()=>revCandidatos().map(c=>c.sub.name)")
        print('   fila de revisao de assunto: %s'%r3)
        assert 'Capitanias' not in r3 and 'Choque' in r3
        print('   OK — um interruptor, as duas filas\n')

        print('=== D) o Resumo Geral conta sem os pausados ===')
        r4=await page.evaluate("""()=>{renderFCMbList();renderFCMain();
          const t=document.getElementById('fc-main-content').textContent.replace(/\\s+/g,' ');
          const nums=[].map.call(document.querySelectorAll('#fc-main-content .stat-val'),e=>e.textContent);
          return {nums,temPausado:t.indexOf('pausado')>=0,
                  temForaDaFila:t.indexOf('fora da fila de revisão')>=0,
                  temHistoria:t.indexOf('Historia')>=0};}""")
        print('   cartoes (Revisar agora / Novos / Em dia): %s'%r4['nums'])
        print('   Historia ainda listada em "Estudar por Reino": %s'%r4['temHistoria'])
        print('   marcada como "pausado" / "fora da fila de revisão": %s / %s'
              %(r4['temPausado'],r4['temForaDaFila']))
        assert r4['nums'][0]=='10', r4['nums']
        assert r4['temHistoria'] and r4['temPausado'] and r4['temForaDaFila']
        print('   OK\n')

        print('=== E) retomar devolve tudo ===')
        r5=await page.evaluate("""()=>{
          revToggleReino('k2'); renderFCMain();
          return {global:getAllFCEverywhere().length,
                  assuntos:revCandidatos().map(c=>c.sub.name),
                  nums:[].map.call(document.querySelectorAll('#fc-main-content .stat-val'),e=>e.textContent)};
        }""")
        print('   fila global: %d · assuntos: %s · cartoes: %s'
              %(r5['global'],r5['assuntos'],r5['nums']))
        assert r5['global']==16 and 'Capitanias' in r5['assuntos'] and r5['nums'][0]=='16'
        print('   OK\n')

        print('=== F) pausar e diferente de dominar ===')
        r6=await page.evaluate("""()=>{
          db.flashcards.c1.dominado=true;
          revToggleReino('k2');
          return {dominados:getAllFCEverywhere(true).filter(c=>c.dominado).length,
                  pausadosMarcados:Object.values(db.flashcards).filter(c=>c.dominado&&c.mbId==='t2').length,
                  historiaDominada:getAllFCForKingdom('k2').filter(c=>c.dominado).length};
        }""")
        print('   dominados no banco: %d · cards de Historia marcados como dominado: %d'
              %(r6['dominados'],r6['historiaDominada']))
        assert r6['dominados']==1 and r6['historiaDominada']==0
        print('   OK — pausar nao marca nada nos cards; e reversivel sem deixar rastro\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
