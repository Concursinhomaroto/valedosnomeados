# -*- coding: utf-8 -*-
# O teste que interessa de verdade: fechar o app e abrir de novo. Os outros checam a
# logica em memoria; este checa o que acontece quando o celular mata a aba no meio da
# prova. O db gravado na primeira sessao vira a semente da segunda — e exatamente o
# que o app faz ao carregar.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
from test_banco_provas import LOTE
from test_pausar import seed

async def main():
    async with async_playwright() as p:
        print('=== sessão 1: faz metade da prova e some ===')
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('provas');window.confirm=()=>true;return true;}")
        r=await page.evaluate("""async(x)=>{
          (%s)(20);
          simColarIniciar(false);
          for(let i=0;i<11;i++)sgSelectAnswer(i,i%%2?'E':'C');
          simGeralActive.questoes[3].marcas=[{ini:2,fim:9,cor:'verde'}];
          simGeralActive.startedAt=Date.now()-2700000;   // 45 min
          // debounce da gravacao + os 800ms que o saveDB espera pra ir pra nuvem
          await new Promise(r=>setTimeout(r,SIM_ANDAMENTO_SALVA_MS+1600));
          return {respondidas:simGeralActive.questoes.filter(q=>q.userAnswer).length,
                  gravadas:(db.simGeralEmAndamento.questoes||[]).filter(q=>q.userAnswer).length,
                  tempo:db.simGeralEmAndamento.acumuladoSec};}"""%LOTE,0)
        print('   11/20 respondidas, 45 min · gravado sem pausar: %s respostas, %ss'
              %(r['gravadas'],r['tempo']))
        assert r['respondidas']==11 and r['gravadas']==11 and 2698<=r['tempo']<=2702
        # o que o Firebase guardou vira a semente da proxima sessao
        salvo=await page.evaluate("()=>window.__root.users.TEST_UID_LEO.vdn_v1")
        graves=[e for e in errs if 'selectedPixTier' not in e]
        assert not graves,graves
        await b.close()
        print('   (aba fechada sem pausar, como se o celular tivesse matado o app)\n')

        print('=== sessão 2: abre o app de novo ===')
        b,page,errs=await setup_page(p,salvo)
        r=await page.evaluate("""()=>{
          showScreen('simgeral');
          const h=document.getElementById('simgeral-content').innerHTML;
          const p=db.simGeralEmAndamento;
          return {sobreviveu:!!p, respostas:(p.questoes||[]).filter(q=>q.userAnswer).length,
                  total:(p.questoes||[]).length, tempo:p.acumuladoSec,
                  marcas:((p.questoes||[])[3].marcas||[]).length,
                  cartao:h.includes('sim-pausado'), numeros:/11\\/20 respondidas/.test(h),
                  relogio:/00:45:0\\d/.test(h)};}""")
        print('   cartão na tela: %s · "%s" · ⏱ 45 min: %s'
              %(r['cartao'],'11/20 respondidas' if r['numeros'] else '???',r['relogio']))
        assert r['sobreviveu'] and r['respostas']==11 and r['total']==20
        assert 2698<=r['tempo']<=2702 and r['marcas']==1
        assert r['cartao'] and r['numeros'] and r['relogio']
        print('   as 11 respostas, o grifo e os 45 min atravessaram o fechamento')

        r=await page.evaluate("""()=>{
          simGeralRetomar();
          const el=document.getElementById('sg-timer-display');
          const h=document.getElementById('simgeral-content').innerHTML;
          return {abriu:!!simGeralActive,
                  respostas:simGeralActive.questoes.filter(q=>q.userAnswer).length,
                  marcas:(simGeralActive.questoes[3].marcas||[]).length,
                  decorrido:sgDecorrido(simGeralActive),
                  progresso:/11\\/20 respondidas/.test(h),
                  rodando:sgTimerInterval!==null,
                  relogio:el?el.textContent:''};}""")
        print('   continuou: %s respostas, %s grifo, ⏱ %ss, relógio andando: %s (%s)'
              %(r['respostas'],r['marcas'],r['decorrido'],r['rodando'],r['relogio'].strip()))
        assert r['abriu'] and r['respostas']==11 and r['marcas']==1
        assert 2698<=r['decorrido']<=2705 and r['progresso'] and r['rodando']

        r=await page.evaluate("""()=>{
          for(let i=11;i<20;i++)sgSelectAnswer(i,'C');
          simGeralCorrigir();
          return {corrigido:!!simGeralActive.corrected,
                  total:simGeralActive.questoes.length,
                  tempo:simGeralActive.tempoGastoSec,
                  rascunho:db.simGeralEmAndamento,
                  noBanco:(db.provas||[]).length};}""")
        print('   terminou as 20 · tempo total da prova: %ss (45 min + o resto)'%r['tempo'])
        print('   rascunho apagado: %s · provas no banco: %s'
              %(r['rascunho'] is None,r['noBanco']))
        assert r['corrigido'] and r['total']==20 and r['tempo']>=2700 and r['rascunho'] is None
        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('   erros de JS: %s'%(graves or 'nenhum'))
        assert not graves,graves
        await b.close()
        print('   OK\n')
        print('OK')

asyncio.run(main())
