# -*- coding: utf-8 -*-
# Segundo achado do usuario, depois do backfill de db.provas (PR #44) ja no ar: o acervo
# continuava vazio porque a MAIOR PARTE do estudo dele e por assunto (miniboss,
# sub.simHistorico), nao Simulado Geral (db.provas) — 14 de 15 provas tinham tentativas:0.
# simCorrigir (a correcao do miniboss) NUNCA escrevia no acervo, nem ao vivo nem em
# backfill nenhum: so o Simulado Geral tinha caminho pra la.
#
# acervoBackfillDeMinibossAntigos() varre sub.simHistorico de TODOS os assuntos (via
# simIndiceAssuntos), poe cada questao no Acervo (criando com subId/subName/kingdomId
# certos — miniboss nunca passava por bancoAdicionarOuFundir antes) e soma os contadores,
# em ordem cronologica de hist.data entre TODOS os assuntos. Ignora hist.geral===true
# (espelho que simGeralCorrigir ja grava do MESMO resultado que foi pra db.provas —
# contar nos dois lados duplicaria). simCorrigir agora chama o mesmo caminho ao vivo,
# na hora da correcao, antes do aparar de HIST_SUB_VIVO que tira `questoes` do que evictar.
#
# acervoAtualizarContadores ganhou um 4o parametro opcional (`quando`): sem ele, alguem
# reprocessado numa ordem que nao e globalmente cronologica entre fonte-prova e
# fonte-miniboss podia fazer uma tentativa VELHA sobrescrever ultimoResultado de uma NOVA.
# Com `quando`, so avanca se a data for >= a que ja estava.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SUB='sub-m1'; SUB2='sub-m2'; TOPIC='topic-m1'; KING='king-m1'

def seed():
    subs=[{'id':SUB,'name':'Choque Séptico','priority':100,'studied':True},
          {'id':SUB2,'name':'Trauma Cranioencefálico','priority':100,'studied':True}]
    extra={'studyNickname':'Reitor','studyCharacter':'ash','geminiApiKey':'FAKE',
        'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
        'topics':{KING:[{'id':TOPIC,'name':'Urgência e Emergência','subtopics':subs}]}}
    return make_seed(extra)

def resp_ce(n,rotulo='q'):
    itens=[{'afirmacao':f'Afirmação {rotulo}-{i+1} sobre o assunto.',
            'gabarito':'C' if i%2 else 'E','explicacao':f'Porque {i+1}.'} for i in range(n)]
    return json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(itens)}]},'finishReason':'STOP'}]})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())

        print('=== A) simCorrigir (miniboss) registra no ACERVO na hora, sem esperar backfill ===')
        prompts=[]
        async def gem(route,request):
            prompts.append(request.post_data or '')
            await route.fulfill(status=200,content_type='application/json',body=resp_ce(3,'viva'))
        await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
        await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
        await page.evaluate("""([id])=>{
          db.simFormato='certoerrado'; db.simNivel='dificil'; openSim.add(id);
          const host=document.createElement('div'); host.id='sim-'+id;
          document.body.appendChild(host); host.innerHTML=simPanelHTML(simFindSub(id));
          document.getElementById('sim-qtd-'+id).value='3';
        }""",[SUB])
        await page.evaluate("(id)=>generateSimulado(id)",SUB)
        await page.wait_for_function("(id)=>!!(simActive[id]&&simActive[id].questoes.length)",arg=SUB,timeout=20000)
        r=await page.evaluate("""(id)=>{
          db.acervo=[];
          simActive[id].questoes.forEach((q,i)=>simSelectAnswer(id,i,q.correta));
          simCorrigir(id);
          const item=db.acervo.find(x=>x.questao.includes('viva-1'));
          return {tamanho:db.acervo.length,
                  item:item?{subId:item.subId,subName:item.subName,kingdomId:item.kingdomId,
                             vezes:item.vezesRespondida,acertos:item.acertos,
                             ultimoResultado:item.ultimoResultado,
                             temUltimaVezEm:!!item.ultimaVezEm}:null,
                  histMarcado:!!simFindSub(id).simHistorico[0]._acervoBackfillEm};}""",SUB)
        print('   %s'%r)
        assert r['tamanho']==3, r['tamanho']
        assert r['item'] and r['item']['subId']==SUB and r['item']['subName']=='Choque Séptico'
        assert r['item']['kingdomId']==KING
        assert r['item']['vezes']==1 and r['item']['acertos']==1
        assert r['item']['ultimoResultado']=='C'
        assert r['item']['temUltimaVezEm']
        assert r['histMarcado'], 'hist recem-criado devia sair marcado pro backfill nao contar de novo'
        print('   OK\n')

        print('=== B) backfill retroativo: sub.simHistorico legado (nunca marcado) entra no acervo, somando por chave v2 ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];
          const subA=simFindSub('%s'), subB=simFindSub('%s');
          subA.simHistorico=[]; subB.simHistorico=[];
          const compartilhada={questao:'A mesma questão respondida nos dois assuntos.',
            alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],
            correta:'C',formato:'certoerrado',userAnswer:null};
          const soDeA={questao:'Só existe no histórico de A.',
            alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],
            correta:'E',formato:'certoerrado',userAnswer:null};
          // A: jan (acertou a compartilhada) e fev (acertou a compartilhada de novo + errou a propria)
          subA.simHistorico=[
            {id:genId(),data:'2024-02-01T00:00:00.000Z',quantidade:2,acertos:1,erros:1,
             questoes:[{...compartilhada,userAnswer:'C'},{...soDeA,userAnswer:'C'}],formato:'certoerrado'},
            {id:genId(),data:'2024-01-01T00:00:00.000Z',quantidade:1,acertos:1,erros:0,
             questoes:[{...compartilhada,userAnswer:'C'}],formato:'certoerrado'}
          ];
          // B: marco — errou a MESMA questao compartilhada (a mais recente de todas as 3)
          subB.simHistorico=[
            {id:genId(),data:'2024-03-01T00:00:00.000Z',quantidade:1,acertos:0,erros:1,
             questoes:[{...compartilhada,userAnswer:'E'}],formato:'certoerrado'}
          ];
          const rel=acervoBackfillDeMinibossAntigos();
          const item=db.acervo.find(x=>x.questao.includes('mesma questão'));
          const soA=db.acervo.find(x=>x.questao.includes('Só existe'));
          return {rel,
                  item:item?{vezes:item.vezesRespondida,acertos:item.acertos,erros:item.erros,
                             ultimoResultado:item.ultimoResultado,ultimaVezEm:item.ultimaVezEm,
                             subId:item.subId}:null,
                  soA:soA?{subId:soA.subId,subName:soA.subName}:null};}"""%(SUB,SUB2))
        print('   relatório: %s'%r['rel'])
        print('   item compartilhado: %s'%r['item'])
        assert r['rel']['tentativasContadas']==3, r['rel']
        # compartilhada aparece 3x (fev, jan, mar) — a 1a e "nova", as outras 2 sao "colisao"
        # (mesma identidade, achada de novo); soDeA e nova uma unica vez. Novas=2, colisoes=2.
        assert r['rel']['questoesNovas']==2 and r['rel']['questoesColidiram']==2, r['rel']
        assert r['item']['vezes']==3 and r['item']['acertos']==2 and r['item']['erros']==1
        assert r['item']['ultimoResultado']=='X', 'março (a mais recente) errou — tinha que vencer'
        assert r['item']['ultimaVezEm'].startswith('2024-03-01'), r['item']['ultimaVezEm']
        assert r['soA'] and r['soA']['subId']=='%s'%SUB
        print('   OK\n')

        print('=== C) idempotente: rodar de nova nao soma de novo (marca por TENTATIVA, nao por assunto) ===')
        r=await page.evaluate("""()=>{
          const item=db.acervo.find(x=>x.questao.includes('mesma questão'));
          const antes={vezes:item.vezesRespondida,acertos:item.acertos,erros:item.erros};
          const rel2=acervoBackfillDeMinibossAntigos();
          const depois={vezes:item.vezesRespondida,acertos:item.acertos,erros:item.erros};
          return {antes,depois,rel2};}""")
        print('   %s'%r)
        assert r['antes']==r['depois']
        assert r['rel2']==({'assuntosMigrados':0,'tentativasContadas':0,'questoesNovas':0,'questoesColidiram':0})
        print('   OK\n')

        print('=== D) hist.geral===true e ignorado — e o espelho que simGeralCorrigir ja manda pra db.provas ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];
          const sub=simFindSub('%s'); sub.simHistorico=[];
          sub.simHistorico=[{id:genId(),data:new Date().toISOString(),quantidade:1,acertos:1,erros:0,
            geral:true,questoes:[{questao:'Questão que já foi pro db.provas via Simulado Geral.',
              alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],
              correta:'C',formato:'certoerrado',userAnswer:'C'}],formato:'certoerrado'}];
          const rel=acervoBackfillDeMinibossAntigos();
          return {rel,acervoTemAlgo:db.acervo.length>0};}"""%SUB)
        print('   %s'%r)
        assert r['rel']==({'assuntosMigrados':0,'tentativasContadas':0,'questoesNovas':0,'questoesColidiram':0})
        assert not r['acervoTemAlgo'], 'entrada geral:true nao pode duplicar o que já foi pro db.provas'
        print('   OK\n')

        print('=== E) ordem cronológica global entre fontes: prova (db.provas) mais nova nao regride pra tras ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];
          const item={questao:'Questão vista tanto no Geral quanto no miniboss.',
            formato:'certoerrado',alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],
            correta:'C',subId:'%s',subName:'Choque Séptico'};
          const chave=acervoChave2(item);
          bancoAdicionarOuFundir(item,'ia');
          const acervoItem=db.acervo.find(x=>acervoChave2De(x)===chave);
          // simula: db.provas ja contou uma tentativa de MAIO (mais nova)
          acervoAtualizarContadores(acervoItem,'C',null,'2024-05-01T00:00:00.000Z');
          // agora o backfill do miniboss traz uma tentativa de JANEIRO (mais velha) da MESMA questao
          const sub=simFindSub('%s'); sub.simHistorico=[
            {id:genId(),data:'2024-01-01T00:00:00.000Z',quantidade:1,acertos:0,erros:1,
             questoes:[{...item,userAnswer:'E'}],formato:'certoerrado'}];
          acervoBackfillDeMinibossAntigos();
          const depois=db.acervo.find(x=>acervoChave2De(x)===chave);
          return {vezes:depois.vezesRespondida,acertos:depois.acertos,erros:depois.erros,
                  ultimoResultado:depois.ultimoResultado,ultimaVezEm:depois.ultimaVezEm};}"""%(SUB,SUB))
        print('   %s'%r)
        assert r['vezes']==2 and r['acertos']==1 and r['erros']==1, 'contadores continuam somando sempre'
        assert r['ultimoResultado']=='C', 'maio (mais nova, já contada) não pode ser sobrescrita por janeiro'
        assert r['ultimaVezEm'].startswith('2024-05-01'), r['ultimaVezEm']
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
