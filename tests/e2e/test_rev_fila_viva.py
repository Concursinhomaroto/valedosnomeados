# Dois acertos finais:
#  - concluir (pela fila OU pela tela de revisao) tem que tirar o assunto da lista na hora
#    e subir o proximo; antes so atualizava quando voce saia e voltava da tela.
#  - "Assuntos que mais erro em questoes" ocupava o topo da tela toda visita; virou aba.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
RESUMO={'texto':'CAMPO DE ATUACAO: texto.','geradoEm':'2026-08-01T10:00:00Z','origem':'web'}
SUBS=[{'id':'s%d'%i,'name':'Assunto %d'%i,'priority':70,'studied':True,
       'studiedAt':'2026-01-01','resumo':RESUMO} for i in range(1,9)]
seed=make_seed({'studyNickname':'Leo','kingdoms':[{'id':'k1','name':'Enf','icon':'🏥'}],
  'topics':{'k1':[{'id':'t1','name':'T','subtopics':SUBS}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.evaluate("""()=>{
          db.revisions={}; db.revOrcamentoMin=60; db.revCustoMin=20;   // 3 por dia
          SUB_IDS=['s1','s2','s3','s4','s5','s6','s7','s8'];
          SUB_IDS.forEach((id,i)=>{const d=new Date();d.setDate(d.getDate()-(300-i*10));
            db.revisions[id]=[{date:d.toISOString().slice(0,10),completed:true,quality:4}];});
          filterRevs('fila',document.querySelector('#screen-revisions .filter-row .chip'));
        }""")
        nomes=lambda: page.evaluate("()=>[].map.call(document.querySelectorAll('#revisions-list .rev-name'),e=>e.textContent)")

        print('=== A) concluir PELA FILA troca o item na hora ===')
        antes=await nomes()
        print('   fila: %s'%antes)
        await page.evaluate("()=>revConcluirDaFila(document.querySelector('#revisions-list .rev-name').textContent&&'s1',4)")
        await page.wait_for_timeout(250)
        depois=await nomes()
        print('   depois de "Revisei" no primeiro: %s'%depois)
        assert len(antes)==3 and len(depois)==3, (antes,depois)
        assert antes[0] not in depois, (antes,depois)
        assert depois[-1] not in antes, 'o proximo da fila tem que subir'
        print('   OK — saiu um, entrou outro, sem sair da tela\n')

        print('=== B) concluir PELA TELA DE REVISAO tambem ===')
        antes2=await nomes()
        r=await page.evaluate("""async()=>{
          const alvo=revCandidatos()[0].sub.id;
          revAbrirTela(alvo); await new Promise(r=>setTimeout(r,200));
          revTelaResponder(alvo,4); await new Promise(r=>setTimeout(r,250));
          return {alvo,modalAberto:document.getElementById('modal').classList.contains('open')};
        }""")
        depois2=await nomes()
        print('   fila antes:  %s'%antes2)
        print('   fila depois: %s  (modal fechou: %s)'%(depois2,not r['modalAberto']))
        assert antes2[0] not in depois2, (antes2,depois2)
        assert len(depois2)==3 and not r['modalAberto']
        print('   OK\n')

        print('=== C) "Preciso ver de novo" e "Dominado" tambem tiram da lista ===')
        a3=await nomes()
        await page.evaluate("()=>revConcluirDaFila(revCandidatos()[0].sub.id,1)")
        await page.wait_for_timeout(200)
        b3=await nomes()
        await page.evaluate("()=>revDominar(revCandidatos()[0].sub.id,true)")
        await page.wait_for_timeout(200)
        c3=await nomes()
        print('   apos "Preciso ver de novo": %s'%b3)
        print('   apos "Dominado":            %s'%c3)
        assert a3[0] not in b3 and b3[0] not in c3
        print('   OK\n')

        print('=== D) a caixa de erros virou aba, ao lado de "Todas" ===')
        r4=await page.evaluate("""()=>{
          const tela=document.getElementById('screen-revisions');
          const chips=[].map.call(tela.querySelectorAll('.filter-row .chip'),e=>e.textContent.trim());
          const caixa=document.getElementById('err-assuntos-card');
          const linha=tela.querySelector('.filter-row');
          const depoisDosChips=!!(linha.compareDocumentPosition(caixa)&Node.DOCUMENT_POSITION_FOLLOWING);
          const naFila={caixa:caixa.style.display,lista:document.getElementById('revisions-list').style.display};
          const chipErro=[].find.call(tela.querySelectorAll('.filter-row .chip'),e=>e.textContent.indexOf('Mais erro')>=0);
          chipErro.click();
          document.getElementById('err-assunto-input').value='Regencia verbal';
          addErroAssunto();
          return {chips,depoisDosChips,naFila,
                  naAba:{caixa:caixa.style.display,lista:document.getElementById('revisions-list').style.display},
                  registrados:(db.erroAssuntos||[]).length,
                  txt:document.getElementById('err-assuntos-list').textContent.replace(/\\s+/g,' ').slice(0,60)};
        }""")
        print('   abas: %s'%r4['chips'])
        print('   caixa esta DEPOIS dos chips no HTML: %s'%r4['depoisDosChips'])
        print('   na Fila  -> caixa "%s" / lista "%s"'%(r4['naFila']['caixa'],r4['naFila']['lista']))
        print('   na aba   -> caixa "%s" / lista "%s"'%(r4['naAba']['caixa'],r4['naAba']['lista']))
        print('   registrar erro na aba: %d -> %s'%(r4['registrados'],r4['txt']))
        assert r4['depoisDosChips'] and any('Mais erro' in c for c in r4['chips'])
        assert r4['naFila']['caixa']=='none' and r4['naAba']['caixa']!='none'
        assert r4['naAba']['lista']=='none' and r4['registrados']==1 and 'Regencia' in r4['txt']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
