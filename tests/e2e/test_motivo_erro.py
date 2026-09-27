# -*- coding: utf-8 -*-
# Errar por nao saber, por ler errado e por chutar sao tres problemas com tres
# consertos diferentes. Tratar os tres como "falta de conteudo" e o motivo de
# estudar 4h por dia e nao sair do lugar: volta pro PDF quando o problema era leitura
# ou decisao de marcar.
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
        await page.evaluate("()=>{showScreen('provas');return true;}")

        print('=== A) o cartao antigo saiu do painel e o novo entrou ===')
        r=await page.evaluate("""()=>{showScreen('dashboard');
          return {velho:!!document.getElementById('week-study-chart'),
                  novo:!!document.getElementById('controle-erros'),
                  fn:typeof window.renderWeekStudyChart,
                  titulo:[...document.querySelectorAll('.dash-sec')]
                          .map(e=>e.innerText.trim()).filter(t=>/CONTROLE|ASSUNTOS DA SEM/i.test(t))};}""")
        print('   "Assuntos da semana": %s · "Controle de erros": %s'%(r['velho'],r['novo']))
        print('   títulos no painel: %s'%r['titulo'])
        assert not r['velho'] and r['novo']
        assert not any('ASSUNTOS DA SEM' in t.upper() for t in r['titulo'])
        print('   OK\n')

        print('=== B) estado vazio explica o que fazer ===')
        r=await page.evaluate("()=>document.getElementById('controle-erros').innerText")
        print('   %r'%r.replace('\n',' ')[:100])
        assert 'Nenhum erro classificado' in r and 'Não sabia' in r
        print('   OK\n')

        print('=== C) os botoes aparecem, e sao diferentes no acerto e no erro ===')
        r=await page.evaluate("""async(x)=>{
          showScreen('provas');
          (%s)(9);
          simColarIniciar(false);
          // 0..5 certos, 6..8 errados
          simGeralActive.questoes.forEach((q,i)=>{q.userAnswer=i<6?q.correta:(q.correta==='C'?'E':'C');});
          simGeralActive.tempoGastoSec=600;
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          const cx=[...document.querySelectorAll('.sim-motivo')];
          return {n:cx.length,
                  certo:cx[0].innerText.replace(/\\n/g,' ').trim(),
                  errado:cx[6].innerText.replace(/\\n/g,' ').trim()};}"""%LOTE,0)
        print('   %s blocos de classificação'%r['n'])
        print('   no acerto: %r'%r['certo'])
        print('   no erro:   %r'%r['errado'])
        assert r['n']==9
        assert 'Acertou por sorte' in r['certo'] and 'Acertei no chute' in r['certo']
        assert 'Por que errou' in r['errado']
        for lbl in ['Não sabia','Li errado','Chutei']:
            assert lbl in r['errado'], lbl
        print('   OK\n')

        print('=== D) um clique classifica, e o clique de novo desmarca ===')
        r=await page.evaluate("""()=>{
          simMotivoSalvar(6,'atencao');
          const a={naQuestao:simGeralActive.questoes[6].motivo,
                   naProva:provaQuestoes(db.provas[0])[6].motivo,
                   ativo:!!document.querySelector('#sim-motivo-6 .sim-motivo-btn.ativo'),
                   nota:(document.querySelector('#sim-motivo-6 .sim-motivo-nota')||{}).innerText||''};
          simMotivoSalvar(6,'atencao');
          return {a,depois:simGeralActive.questoes[6].motivo,
                  naProvaDepois:provaQuestoes(db.provas[0])[6].motivo,
                  aindaAtivo:!!document.querySelector('#sim-motivo-6 .sim-motivo-btn.ativo')};}""")
        print('   marcou: %r (guardado na prova: %r)'%(r['a']['naQuestao'],r['a']['naProva']))
        print('   conserto exibido: %r'%r['a']['nota'][:60])
        print('   clicando de novo: %r · botão ativo: %s'%(r['depois'],r['aindaAtivo']))
        assert r['a']['naQuestao']=='atencao' and r['a']['naProva']=='atencao' and r['a']['ativo']
        assert 'leitura' in r['a']['nota'] or 'trocou' in r['a']['nota']
        # naProvaDepois: desmarcar apaga a entrada esparsa (nao fica '' guardado a toa),
        # entao a leitura hidratada volta pra undefined — mesmo estado de "nunca marcado".
        assert r['depois']=='' and not r['naProvaDepois'] and not r['aindaAtivo']
        print('   OK\n')

        print('=== E) o painel soma os baldes e aponta o gargalo ===')
        r=await page.evaluate("""()=>{
          simMotivoSalvar(6,'atencao');
          simMotivoSalvar(7,'atencao');
          simMotivoSalvar(8,'conteudo');
          simMotivoSalvar(0,'sorte');
          const ag=motivosAgregado();
          showScreen('dashboard');
          const txt=document.getElementById('controle-erros').innerText.replace(/\\n/g,' | ');
          return {tot:ag.tot,classificadas:ag.classificadas,erradas:ag.erradas,
                  foot:document.getElementById('controle-erros-foot').innerText,txt};}""")
        print('   baldes: %s'%r['tot'])
        print('   painel: %s'%r['txt'][:190])
        print('   rodapé: %r'%r['foot'])
        assert r['tot']=={'conteudo':1,'atencao':2,'chute':0,'sorte':1,'datado':0}
        assert r['erradas']==3
        # o que importa e o conselho NAO mandar de volta pro conteudo
        assert 'leitura' in r['txt'] and 'Voltar pro PDF não resolve' in r['txt']
        assert '1 acerto(s) de sorte' in r['txt']
        assert 'Li errado' in r['txt']
        print('   com "Li errado" dominando, o conselho para de mandar pro PDF')
        print('   OK\n')

        print('=== F) o gargalo muda quando os numeros mudam ===')
        r=await page.evaluate("""()=>{
          simGeralActive=null;
          const pr=db.provas[0];
          [6,7,8].forEach(i=>provaMarcar(pr,i,{...provaQuestoes(pr)[i],motivo:'chute'}));
          renderControleErros();
          const a=document.getElementById('controle-erros').innerText;
          [6,7,8].forEach(i=>provaMarcar(pr,i,{...provaQuestoes(pr)[i],motivo:'conteudo'}));
          renderControleErros();
          const c=document.getElementById('controle-erros').innerText;
          return {chute:/decis/i.test(a)&&/branco/i.test(a),
                  conteudo:/conteúdo/i.test(c)&&/resumo/i.test(c)&&/flashcard/i.test(c)};}""")
        print('   com "Chutei" dominando, fala de decisão e de branco: %s'%r['chute'])
        print('   com "Não sabia" dominando, fala de conteúdo: %s'%r['conteudo'])
        assert r['chute'] and r['conteudo']
        print('   OK\n')

        print('=== G) o motivo sobrevive e volta na revisao ===')
        r=await page.evaluate("""()=>{
          provaRevisar(db.provas[0].id);
          const btn=document.querySelector('#sim-motivo-6 .sim-motivo-btn.ativo');
          return {motivo:simGeralActive.questoes[6].motivo,
                  botao:btn?btn.innerText.trim():null};}""")
        print('   na revisão: %r · botão aceso: %r'%(r['motivo'],r['botao']))
        assert r['motivo']=='conteudo' and 'Não sabia' in (r['botao'] or '')
        print('   OK\n')

        print('=== H) assunto onde o gargalo mais aparece ===')
        r=await page.evaluate("""()=>{
          const ag=motivosAgregado();
          return {porAssunto:ag.porAssunto,
                  txt:document.getElementById('controle-erros')?
                      (renderControleErros(),document.getElementById('controle-erros').innerText):''};}""")
        print('   por assunto: %s'%r['porAssunto'])
        assert any(v['conteudo']>0 for v in r['porAssunto'].values())
        assert 'mais aparece' in r['txt']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
