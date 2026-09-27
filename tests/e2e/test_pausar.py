# -*- coding: utf-8 -*-
# O simulado morava so na memoria: fechou a aba, perdeu as 120 respostas. Numa prova de
# 4 horas isso inviabiliza comecar — voce so abre se souber que termina hoje. Aqui a
# prova em andamento e gravada a cada resposta, e o relogio conta so o tempo em que ela
# esteve ABERTA: pausar de noite e voltar de manha nao pode somar a madrugada.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
from test_banco_provas import LOTE

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Choque septico','priority':70,'studied':True},
          {'id':'s2','name':'PCR','priority':70,'studied':True}]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('provas');window.confirm=()=>true;return true;}")

        print('=== A) pausar guarda resposta, grifo e tempo ===')
        r=await page.evaluate("""(x)=>{
          (%s)(10);
          simColarIniciar(false);
          simGeralActive.questoes[0].userAnswer='C';
          simGeralActive.questoes[1].userAnswer='E';
          simGeralActive.questoes[0].marcas=[{ini:0,fim:4,cor:'amarelo'}];
          simGeralActive.startedAt=Date.now()-600000;   // 10 min de prova
          simGeralPausar();
          const p=db.simGeralEmAndamento;
          return {guardou:!!p, questoes:(p.questoes||[]).length,
                  respostas:(p.questoes||[]).filter(q=>q.userAnswer).length,
                  marcas:((p.questoes||[])[0].marcas||[]).length,
                  acumulado:p.acumuladoSec, ativo:simGeralActive===null,
                  relogio:sgTimerInterval===null,
                  cartao:document.querySelector('#simgeral-content .sim-pausado')!==null
                         ||simAndamentoCardHTML().includes('sim-pausado')};}"""%LOTE,0)
        print('   guardou %s questões · %s respondidas · %s grifo · ⏱ %ss'
              %(r['questoes'],r['respostas'],r['marcas'],r['acumulado']))
        print('   saiu da prova: %s · relógio parado: %s · cartão de retomar: %s'
              %(r['ativo'],r['relogio'],r['cartao']))
        assert r['guardou'] and r['questoes']==10 and r['respostas']==2 and r['marcas']==1
        assert 598<=r['acumulado']<=602, r['acumulado']
        assert r['ativo'] and r['relogio'] and r['cartao']
        print('   OK\n')

        print('=== B) o relogio NAO anda enquanto esta pausado ===')
        r=await page.evaluate("""()=>{
          const antes=db.simGeralEmAndamento.acumuladoSec;
          // como se voce tivesse fechado o app e voltado 8 horas depois
          db.simGeralEmAndamento.startedAt=Date.now()-8*3600*1000;
          db.simGeralEmAndamento.salvoEm=Date.now()-8*3600*1000;
          simGeralRetomar();
          const agora=sgDecorrido(simGeralActive);
          const seFosseRelogioDeParede=Math.floor((Date.now()-(Date.now()-8*3600*1000))/1000);
          return {antes,agora,parede:seFosseRelogioDeParede,
                  respostas:simGeralActive.questoes.filter(q=>q.userAnswer).length,
                  marcas:(simGeralActive.questoes[0].marcas||[]).length,
                  naTela:document.getElementById('simgeral-content').innerHTML.includes('Finalizar Simulado')};}""")
        print('   antes de pausar: %ss · depois de 8h parado: %ss (relógio de parede daria %ss)'
              %(r['antes'],r['agora'],r['parede']))
        assert abs(r['agora']-r['antes'])<=2, (r['antes'],r['agora'])
        print('   voltou com %s respostas e %s grifo · prova aberta na tela: %s'
              %(r['respostas'],r['marcas'],r['naTela']))
        assert r['respostas']==2 and r['marcas']==1 and r['naTela']
        print('   OK\n')

        print('=== C) o tempo soma os trechos, nao o relogio de parede ===')
        r=await page.evaluate("""()=>{
          simGeralActive.startedAt=Date.now()-300000;      // mais 5 min nesta sentada
          const decorrido=sgDecorrido(simGeralActive);
          simGeralActive.questoes.forEach(q=>{q.userAnswer=q.correta;});
          simGeralCorrigir();
          return {decorrido,gasto:simGeralActive.tempoGastoSec,
                  rascunho:db.simGeralEmAndamento};}""")
        print('   10 min + 5 min = %ss · tempo gravado na prova: %ss'%(r['decorrido'],r['gasto']))
        assert 898<=r['gasto']<=902, r['gasto']
        print('   rascunho depois de finalizar: %s'%r['rascunho'])
        assert r['rascunho'] is None
        print('   OK\n')

        print('=== D) grava sozinho a cada resposta (fechar a aba nao perde) ===')
        r=await page.evaluate("""async(x)=>{
          simGeralReset();
          (%s)(8);
          simColarIniciar(false);
          const semSalvar=db.simGeralEmAndamento;
          sgSelectAnswer(0,'C'); sgSelectAnswer(1,'E'); sgSelectAnswer(2,'C');
          const naHora=db.simGeralEmAndamento;                  // ainda no debounce
          await new Promise(r=>setTimeout(r,SIM_ANDAMENTO_SALVA_MS+400));
          const p=db.simGeralEmAndamento;
          return {antes:semSalvar, durante:!!naHora,
                  depois:(p&&p.questoes||[]).filter(q=>q.userAnswer).length,
                  debounce:SIM_ANDAMENTO_SALVA_MS};}"""%LOTE,0)
        print('   antes de responder: %s · 3 respostas → gravou %s'%(r['antes'],r['depois']))
        assert r['antes'] is None and r['depois']==3
        print('   uma gravação só pras 3 (debounce de %sms), não uma por clique'%r['debounce'])
        print('   OK\n')

        print('=== E) comecar outra prova avisa antes de apagar a pausada ===')
        r=await page.evaluate("""async(x)=>{
          simGeralPausar();
          const pausada=db.simGeralEmAndamento.questoes.length;
          window.confirm=()=>false;                       // "não, quero terminar aquela"
          (%s)(5);
          simColarIniciar(false);
          const bloqueou=db.simGeralEmAndamento&&db.simGeralEmAndamento.questoes.length===pausada
                         &&simGeralActive===null;
          window.confirm=()=>true;                        // "pode apagar"
          simColarIniciar(false);
          return {pausada,bloqueou,
                  abriu:!!simGeralActive&&simGeralActive.questoes.length===5,
                  rascunhoLimpo:db.simGeralEmAndamento===null};}"""%LOTE,0)
        print('   disse NÃO: prova pausada intacta (%s itens) e nada abriu: %s'
              %(r['pausada'],r['bloqueou']))
        print('   disse SIM: abriu a nova (%s) e o rascunho antigo saiu: %s'
              %(r['abriu'],r['rascunhoLimpo']))
        assert r['bloqueou'] and r['abriu'] and r['rascunhoLimpo']
        print('   OK\n')

        print('=== F) descartar o pausado, de proposito ===')
        r=await page.evaluate("""()=>{
          sgSelectAnswer(0,'C');
          simGeralPausar();
          const tinha=!!db.simGeralEmAndamento;
          window.confirm=()=>false;
          simGeralDescartarPausado();
          const sobreviveu=!!db.simGeralEmAndamento;
          window.confirm=()=>true;
          simGeralDescartarPausado();
          return {tinha,sobreviveu,agora:db.simGeralEmAndamento,
                  cartao:simAndamentoCardHTML()};}""")
        print('   tinha pausado: %s · cancelou e sobreviveu: %s · confirmou: %s'
              %(r['tinha'],r['sobreviveu'],r['agora']))
        assert r['tinha'] and r['sobreviveu'] and r['agora'] is None and r['cartao']==''
        print('   sem pausado, o cartão some da tela de configuração')
        print('   OK\n')

        print('=== G) revisao de prova antiga nao vira rascunho ===')
        r=await page.evaluate("""async()=>{
          simGeralReset();
          const feita=db.provas.find(p=>(p.tentativas||[]).length);
          provaRevisar(feita.id);
          simGeralSalvarAndamento(true);
          return {revisando:!!simGeralActive.revisando,rascunho:db.simGeralEmAndamento};}""")
        print('   revisando: %s · rascunho criado: %s'%(r['revisando'],r['rascunho']))
        assert r['revisando'] and r['rascunho'] is None
        print('   só o que está em aberto pode ser retomado')
        print('   OK\n')

        print('=== H) o cartao mostra o que interessa pra decidir ===')
        r=await page.evaluate("""async(x)=>{
          simGeralReset();
          (%s)(12);
          simColarIniciar(false);
          simGeralActive.questoes.slice(0,7).forEach(q=>{q.userAnswer='C';});
          simGeralActive.startedAt=Date.now()-3725000;   // 1h02
          simGeralPausar();
          const h=simAndamentoCardHTML();
          return {tem:h.includes('sim-pausado'),
                  numeros:/7\\/12 respondidas/.test(h),
                  tempo:/01:02:0\\d/.test(h),
                  continuar:h.includes('simGeralRetomar()'),
                  descartar:h.includes('simGeralDescartarPausado()')};}"""%LOTE,0)
        print('   cartão: %s · "7/12 respondidas": %s · tempo 01:02: %s'
              %(r['tem'],r['numeros'],r['tempo']))
        print('   botões continuar/descartar: %s / %s'%(r['continuar'],r['descartar']))
        assert all(r.values())
        print('   OK\n')

        print('=== I) o botao Pausar esta na barra do relogio ===')
        r=await page.evaluate("""()=>{
          simGeralRetomar();
          const barra=document.querySelector('#simgeral-content .sg-timer-bar');
          const b=[...barra.querySelectorAll('button')].map(e=>e.textContent.trim());
          barra.querySelector('button').click();
          return {botoes:b, saiu:simGeralActive===null, guardou:!!db.simGeralEmAndamento};}""")
        print('   botões da barra: %s'%r['botoes'])
        assert any('Pausar' in x for x in r['botoes']) and any('Finalizar' in x for x in r['botoes'])
        assert r['saiu'] and r['guardou']
        print('   clicou em Pausar: saiu da prova e guardou')
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
