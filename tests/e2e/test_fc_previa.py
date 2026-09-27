# "Cliquei em 5 dias e foi para 1." Nao era o aviso: fcStudyConf carimbava
# ultimaRevisao=agora ANTES de calcular o FSRS, entao a conta via "0 dias desde a ultima
# revisao", R~1, e o ganho de estabilidade colapsava. A previa do botao usava a data
# antiga (a certa) — por isso os dois discordavam.
import asyncio, sys, json
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
      'topics':{'k1':[{'id':'t1','name':'Farmaco','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Interacoes','priority':70,'studied':True}]}]},
      'flashcards':{}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())

        print('=== A) previa e agendamento tem que bater nos 4 botoes ===')
        r=await page.evaluate("""()=>{
          const fora=[];
          const linhas=[];
          [1,2,3,4].forEach(conf=>{
            // card revisado ha 20 dias, com estabilidade de 12 dias
            const id='c'+conf;
            db.flashcards[id]={id,mbId:'t1',subId:'s1',pergunta:'p','resposta':'r',
              dificuldade:3,acertos:4,erros:1,lastConf:3,
              fsrs:{S:12,D:5},
              criacao:'2026-06-01T10:00:00.000Z',
              ultimaRevisao:new Date(Date.now()-20*86400000).toISOString()};
            const previa=fsrsPrevia(db.flashcards[id],conf);
            fcStudyCards=[db.flashcards[id]]; fcStudyIdx=0;
            fcStudyConf(id,conf);
            const real=fcNextInterval(db.flashcards[id]);
            linhas.push([conf,previa,real]);
            if(previa!==real)fora.push(conf);
          });
          return {linhas,fora};}""")
        lbl={1:'Não lembrei',2:'Difícil',3:'Lembrei',4:'Fácil'}
        for conf,previa,real in r['linhas']:
            print('   %-12s botão dizia %3s dia(s) · agendou %3s dia(s)  %s'
                  %(lbl[conf],previa,real,'OK' if previa==real else '← DIVERGE'))
        assert not r['fora'], r['fora']
        print('   OK\n')

        print('=== B) o caso da tela: "Difícil → 5 dias" agenda 5, nao 1 ===')
        r=await page.evaluate("""()=>{
          const id='real';
          db.flashcards[id]={id,mbId:'t1',subId:'s1',pergunta:'p',resposta:'r',
            dificuldade:3,acertos:1,erros:1,lastConf:3,fsrs:{S:9.5,D:6},
            criacao:'2026-06-01T10:00:00.000Z',
            ultimaRevisao:new Date(Date.now()-14*86400000).toISOString()};
          const previa=fsrsPrevia(db.flashcards[id],2);
          fcStudyCards=[db.flashcards[id]]; fcStudyIdx=0;
          fcStudyConf(id,2);
          return {previa,real:fcNextInterval(db.flashcards[id]),
                  S:db.flashcards[id].fsrs.S};}""")
        print('   prévia: %s dias · agendado: %s dias · estabilidade: %s'
              %(r['previa'],r['real'],r['S']))
        assert r['previa']==r['real'] and r['real']>1
        print('   OK\n')

        print('=== C) lembrar de algo QUASE esquecido vale mais que revisar na hora ===')
        r=await page.evaluate("""()=>{
          const mk=(id,diasAtras)=>{db.flashcards[id]={id,mbId:'t1',subId:'s1',pergunta:'p',
            resposta:'r',dificuldade:3,acertos:4,erros:1,fsrs:{S:12,D:5},
            criacao:'2026-06-01T10:00:00.000Z',
            ultimaRevisao:new Date(Date.now()-diasAtras*86400000).toISOString()};return db.flashcards[id];};
          const cedo=mk('cedo',1), tarde=mk('tarde',25);
          fcStudyCards=[cedo];fcStudyIdx=0;fcStudyConf('cedo',3);
          fcStudyCards=[tarde];fcStudyIdx=0;fcStudyConf('tarde',3);
          return {cedo:fcNextInterval(cedo),tarde:fcNextInterval(tarde),
                  Scedo:cedo.fsrs.S,Starde:tarde.fsrs.S};}""")
        print('   revisado 1 dia depois:  %s dias (S=%s)'%(r['cedo'],r['Scedo']))
        print('   revisado 25 dias depois: %s dias (S=%s)'%(r['tarde'],r['Starde']))
        assert r['tarde']>r['cedo'], 'e isso que o bug destruia'
        print('   OK\n')

        print('=== D) fcGridMark (que ja estava certo) continua certo ===')
        r=await page.evaluate("""()=>{
          const id='grid';
          db.flashcards[id]={id,mbId:'t1',subId:'s1',pergunta:'p',resposta:'r',
            dificuldade:3,acertos:4,erros:1,fsrs:{S:12,D:5},
            criacao:'2026-06-01T10:00:00.000Z',
            ultimaRevisao:new Date(Date.now()-20*86400000).toISOString()};
          const previa=fsrsPrevia(db.flashcards[id],3);
          fcGridMark(id,true);
          return {previa,real:fcNextInterval(db.flashcards[id])};}""")
        print('   prévia %s · real %s'%(r['previa'],r['real']))
        assert r['previa']==r['real']
        print('   OK\n')

        print('=== E) a data da proxima revisao anda a partir de HOJE ===')
        r=await page.evaluate("""()=>{
          const c=db.flashcards['real'];
          return {ultima:c.ultimaRevisao.slice(0,10),hoje:todayStr(),
                  proxima:fcNextReview(c),intervalo:fcNextInterval(c)};}""")
        print('   ultimaRevisao=%s (hoje=%s) · próxima=%s (+%s dias)'
              %(r['ultima'],r['hoje'],r['proxima'],r['intervalo']))
        assert r['ultima']==r['hoje'] and r['proxima']>r['hoje']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
