# Um item da fila apareceu com "??" no lugar do icone do reino. A fila era o unico lugar
# que imprimia k.icon cru — o resto do app ja usava `k.icon||'🏰'`. Mas o `||` nao resolve
# icone CORROMPIDO (U+FFFD nao e vazio), entao precisa de um tratamento proprio.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
SUB={'id':'s1','name':'Teniase','priority':70,'studied':True,'studiedAt':'2026-01-01'}
seed=make_seed({'studyNickname':'Leo',
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'��'},   # corrompido
              {'id':'k2','name':'SUS','icon':''},                       # vazio
              {'id':'k3','name':'Portugues','icon':'📖'}],              # normal
  'topics':{'k1':[{'id':'t1','name':'Parasitologia','subtopics':[SUB]}],
            'k2':[{'id':'t2','name':'Lei','subtopics':[dict(SUB,id='s2',name='8080')]}],
            'k3':[{'id':'t3','name':'Sintaxe','subtopics':[dict(SUB,id='s3',name='Crase')]}]}})
async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        print('=== A) a funcao troca o corrompido e o vazio, e nao mexe no bom ===')
        r=await page.evaluate("()=>['\\uFFFD\\uFFFD','','  ','📖','💊'].map(x=>[JSON.stringify(x),iconeReino(x)])")
        for orig,saida in r: print('   %-14s -> %s'%(orig,saida))
        assert r[0][1]=='🏰' and r[1][1]=='🏰' and r[2][1]=='🏰'
        assert r[3][1]=='📖' and r[4][1]=='💊'
        print('   OK\n')

        print('=== B) a fila nao mostra mais "??" ===')
        r2=await page.evaluate("""()=>{
          const d=n=>{const x=new Date();x.setDate(x.getDate()-n);return x.toISOString().slice(0,10);};
          db.revisions={s1:[{date:d(60),completed:true,quality:4}],
                        s2:[{date:d(60),completed:true,quality:4}],
                        s3:[{date:d(60),completed:true,quality:4}]};
          db.revOrcamentoMin=240;
          filterRevs('fila',document.querySelector('#screen-revisions .filter-row .chip'));
          const t=document.getElementById('revisions-list').textContent;
          return {temFFFD:t.indexOf('\\uFFFD')>=0, temCastelo:t.indexOf('🏰')>=0,
                  temLivro:t.indexOf('📖')>=0};
        }""")
        print('   sobrou algum U+FFFD na tela: %s'%r2['temFFFD'])
        print('   castelo no lugar dos quebrados: %s · icone bom preservado: %s'
              %(r2['temCastelo'],r2['temLivro']))
        assert not r2['temFFFD'] and r2['temCastelo'] and r2['temLivro']
        print('   OK\n')

        print('=== C) o cabecalho da tela de revisao tambem ===')
        r3=await page.evaluate("""async()=>{revAbrirTela('s1');await new Promise(r=>setTimeout(r,200));
          const t=document.getElementById('modal-body').textContent;
          revFecharTela();
          return {temFFFD:t.indexOf('\\uFFFD')>=0,temCastelo:t.indexOf('🏰')>=0};}""")
        print('   U+FFFD: %s · castelo: %s'%(r3['temFFFD'],r3['temCastelo']))
        assert not r3['temFFFD'] and r3['temCastelo']
        print('   OK\n')
        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')
asyncio.run(main())

# ---- D: o icone nao tinha onde ser editado; so dava pra consertar pelo console.
async def editar():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        print('=== D) editar o reino agora conserta o icone ===')
        r=await page.evaluate("""async()=>{
          renameKingdom('k1'); await new Promise(r=>setTimeout(r,150));
          const ic=document.getElementById('rn-kingdom-icon');
          const txt=document.getElementById('modal-body').textContent;
          const pre=ic.value;
          ic.value='💊';
          saveKingdomRename('k1'); await new Promise(r=>setTimeout(r,150));
          const k=db.kingdoms.find(x=>x.id==='k1');
          return {pre,avisou:txt.indexOf('corrompido')>=0,icone:k.icon,nome:k.name};
        }""")
        print('   campo veio preenchido com: %s (nao com "??")'%r['pre'])
        print('   avisou que estava corrompido: %s'%r['avisou'])
        print('   depois de salvar: icon=%s · nome=%s'%(r['icone'],r['nome']))
        assert r['pre']=='🏰' and r['avisou'] and r['icone']=='💊' and r['nome']=='Enfermagem'
        print('   OK\n')
        print('=== E) e o campo nao aceita gravar lixo de volta ===')
        r2=await page.evaluate("""async()=>{
          renameKingdom('k3'); await new Promise(r=>setTimeout(r,120));
          document.getElementById('rn-kingdom-icon').value='\\uFFFD\\uFFFD';
          saveKingdomRename('k3'); await new Promise(r=>setTimeout(r,120));
          return db.kingdoms.find(x=>x.id==='k3').icon;
        }""")
        print('   tentei salvar U+FFFD -> ficou: %s'%r2)
        assert r2=='🏰'
        print('   OK\n')
        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')
asyncio.run(editar())
