# -*- coding: utf-8 -*-
# Passo 8.4 do redesenho de Simulados: a aba Acervo (ex-Banco de Questões) ganha filtros
# como chips com contagem viva em três faixas — ESTADO, NÍVEL, NATUREZA — no lugar de
# selects/checkboxes soltos, chips sugeridos de pegadinha no editor (aplicação manual,
# sobre o tags[] que já existia desde o passo 2, sem tocar em nada da IA), e um mapa de
# calor por assunto (tamanho = quantidade, cor = acerto, contorno âmbar = banco raso).
#
# Os campos antigos (naoRespondida/status/faixaMin/faixaMax) continuam vivos por baixo —
# test_banco_filtros.py cobre eles diretamente e não devia quebrar com isto.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from test_acervo import seed, QS

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)

        async def ir_pro_acervo():
            await page.evaluate("()=>{showScreen('banco');renderSimGeralScreen();return true;}")

        print('=== A) chips ESTADO/NÍVEL/NATUREZA nascem com contagem viva certa ===')
        await page.evaluate("""()=>{
          db.acervo=[];db.provas=[];
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',10,'A');
          qs.forEach((q,i)=>{
            q._chaveForte=acervoChave2(q);
            Object.assign(q,acervoCamposNovos('ia'));
            if(i<3){q.vezesRespondida=3;q.acertos=0;q.erros=3;q.dificuldadeAferida='dificil';q.ultimoResultado='X';}
            if(i===3)q.tags=['norma revogada'];
            if(i===4)q.status='revisar';
          });
          db.acervo=qs;
          return true;}""")
        await ir_pro_acervo()
        r=await page.evaluate("""()=>({
          estado:[...document.querySelectorAll('#banco-filtro-estado .banco-chip')].map(b=>b.textContent.trim()),
          nivel:[...document.querySelectorAll('#banco-filtro-nivel .banco-chip')].map(b=>b.textContent.trim()),
          natureza:[...document.querySelectorAll('#banco-filtro-tags-chips .banco-chip')].map(b=>b.textContent.trim())})""")
        print('   estado: %s'%r['estado'])
        print('   nível: %s'%r['nivel'])
        print('   natureza: %s'%r['natureza'])
        assert any('nunca vista 6' in x for x in r['estado'])
        assert any('errada 3' in x for x in r['estado'])
        assert any('quarentena 1' in x for x in r['estado'])
        assert any('difícil 3' in x for x in r['nivel'])
        assert any('norma revogada 1' in x for x in r['natureza'])
        print('   OK\n')

        print('=== B) clicar um chip ESTADO filtra; clicar de nono desmarca ===')
        r=await page.evaluate("""()=>{
          bancoFiltroMudouEstado('errada');
          const conta1=document.getElementById('banco-filtro-conta').textContent;
          const ativo=!!document.querySelector('#banco-filtro-estado .banco-chip.ativo');
          bancoFiltroMudouEstado('errada');
          const conta2=document.getElementById('banco-filtro-conta').textContent;
          const aindaAtivo=!!document.querySelector('#banco-filtro-estado .banco-chip.ativo');
          return {conta1,ativo,conta2,aindaAtivo};}""")
        print('   %s'%r)
        assert '3' in r['conta1'] and r['ativo']
        assert '10' in r['conta2'] and not r['aindaAtivo']
        print('   OK\n')

        print('=== C) chip NÍVEL filtra por dificuldadeAferida ===')
        r=await page.evaluate("""()=>{
          bancoFiltroMudouNivel('dificil');
          const conta=document.getElementById('banco-filtro-conta').textContent;
          bancoFiltroMudouNivel('dificil');
          return conta;}""")
        print('   difícil: %s'%r)
        assert '3' in r
        print('   OK\n')

        print('=== D) chip NATUREZA (tag) filtra igual o checkbox antigo fazia ===')
        r=await page.evaluate("""()=>{
          bancoFiltroToggleTagChip('norma revogada');
          const conta=document.getElementById('banco-filtro-conta').textContent;
          const ativo=!!document.querySelector('#banco-filtro-tags-chips .banco-chip.ativo');
          bancoFiltroToggleTagChip('norma revogada');
          return {conta,ativo};}""")
        print('   %s'%r)
        assert '1' in r['conta'] and r['ativo']
        print('   OK\n')

        print('=== E) editor: chips de pegadinha sugeridos aplicam/removem tag, nos dois sentidos ===')
        r=await page.evaluate("""()=>{
          bancoCriarAbrir();
          renderSimGeralScreen();
          const prefixo='banco-novo-';
          bancoTagSugeridaToggle(prefixo,'troca de número');
          const viaChip=document.getElementById(prefixo+'tags').value;
          const chipAtivo=[...document.querySelectorAll('#'+prefixo+'tags-sugeridas .banco-chip')]
            .some(btn=>btn.textContent.trim()==='troca de número'&&btn.classList.contains('ativo'));
          document.getElementById(prefixo+'tags').value='direta, troca de número';
          bancoTagsSugeridasAtualizar(prefixo);
          const duasAtivas=[...document.querySelectorAll('#'+prefixo+'tags-sugeridas .banco-chip.ativo')].length;
          bancoTagSugeridaToggle(prefixo,'troca de número');
          const depoisRemover=document.getElementById(prefixo+'tags').value;
          return {viaChip,chipAtivo,duasAtivas,depoisRemover};}""")
        print('   %s'%r)
        assert r['viaChip']=='troca de número' and r['chipAtivo']
        assert r['duasAtivas']==2
        assert r['depoisRemover']=='direta'
        print('   OK\n')

        print('=== F) mapa do acervo: célula por assunto, contorno em banco raso, clique filtra por assunto ===')
        r=await page.evaluate("""()=>{
          bancoCriarCancelar();
          renderSimGeralScreen();
          const cels=[...document.querySelectorAll('#banco-content .banco-mapa-cel')];
          const raso=cels.filter(c=>c.classList.contains('banco-mapa-raso')).length;
          cels[0].click();
          return {numCels:cels.length,raso,modo:document.getElementById('montar-modo').value,
                  sel:[...montarSel]};}""")
        print('   %s'%r)
        assert r['numCels']>=1 and r['raso']>=1
        assert r['modo']=='assunto' and 'sE1' in r['sel']
        print('   OK\n')

        print('=== G) "gerar onde é raso" abre Treinar, expande a montagem avançada e pré-marca os rasos ===')
        r=await page.evaluate("""()=>{
          bancoMapaGerarOndeRaso();
          return {tela:document.getElementById('screen-simgeral').classList.contains('active'),
                  painelAberto:document.getElementById('treinar-avancado').style.display!=='none',
                  marcado:simGeralConfig.selectedSubIds.has('sE1')};}""")
        print('   %s'%r)
        assert r['tela'] and r['painelAberto'] and r['marcado']
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
