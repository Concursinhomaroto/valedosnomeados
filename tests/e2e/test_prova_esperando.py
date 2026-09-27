# -*- coding: utf-8 -*-
# Prova NUNCA FEITA nao e historico: e trabalho marcado, esperando. Ela estava sendo
# despejada junto com as velhas — a pessoa engavetava uma prova de 120 pra fazer no
# sabado e ela sumia sozinha antes do sabado. Agora o despejo escolhe: sai sempre a mais
# antiga ENTRE AS JA FEITAS, e nunca uma que voce ainda nao abriu.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page
from test_acervo import seed, QS

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)
        await page.evaluate("()=>{showScreen('provas');return true;}")

        print('=== A) o defeito: prova esperando era despejada pelo teto ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          // 2 nunca feitas, as MAIS ANTIGAS da lista
          ['E1','E2'].forEach(t=>provaGuardarLote(
            QS('kEnf','Enfermagem','💉','sE1','Choque septico',8,t),{formato:'certoerrado'}));
          // e PROVAS_MAX feitas por cima
          for(let i=0;i<PROVAS_MAX;i++){
            const id=provaGuardarLote(QS('kSus','Saúde Pública','⚕️','sS1','Lei 8080',4,'F'+i),
                                      {formato:'certoerrado'});
            provaAchar(id).tentativas=[{data:new Date().toISOString(),
              respostas:['C','C','C','C'],acertos:4,tempoGastoSec:60}];
          }
          provasAparar();
          const esperando=db.provas.filter(p=>!provaFoiFeita(p));
          return {total:db.provas.length, teto:PROVAS_MAX,
                  esperandoNaLista:esperando.length,
                  quais:esperando.map(p=>p.questoes[0].questao.slice(0,2)),
                  arquivadas:db.provasArquivo.length,
                  arquivadasFeitas:db.provasArquivo.every(a=>(a.tentativas||[]).length>0)};}""")
        print('   lista: %s (teto %s) · provas esperando que sobreviveram: %s %s'
              %(r['total'],r['teto'],r['esperandoNaLista'],r['quais']))
        print('   arquivadas: %s · todas elas já tinham sido feitas: %s'
              %(r['arquivadas'],r['arquivadasFeitas']))
        assert r['esperandoNaLista']==2, 'prova nunca feita foi despejada de novo'
        assert sorted(r['quais'])==['E1','E2']
        assert r['arquivadas']==2 and r['arquivadasFeitas']
        print('   as 2 engavetadas ficaram; saíram 2 já feitas, as mais antigas')
        print('   OK\n')

        print('=== B) sai sempre a mais antiga entre as feitas ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          for(let i=0;i<PROVAS_MAX+3;i++){
            const id=provaGuardarLote(QS('kEnf','Enfermagem','💉','sE1','Choque septico',4,'T'+i),
                                      {formato:'certoerrado'});
            provaAchar(id).tentativas=[{data:new Date().toISOString(),
              respostas:['C','C','C','C'],acertos:4,tempoGastoSec:60}];
          }
          provasAparar();
          const saiu=db.provasArquivo.map(a=>a.num).sort((x,y)=>x-y);
          const ficou=db.provas.map(p=>p.num).sort((x,y)=>x-y);
          return {saiu, primeiraQueFicou:ficou[0], total:db.provas.length};}""")
        print('   saíram os números %s · a menor que ficou é a %s'
              %(r['saiu'],r['primeiraQueFicou']))
        assert len(r['saiu'])==3 and max(r['saiu'])<r['primeiraQueFicou']
        print('   ordem respeitada: as 3 mais antigas')
        print('   OK\n')

        print('=== C) so restam esperando: ninguem sai, e ele avisa ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          for(let i=0;i<PROVAS_MAX+5;i++)provaGuardarLote(
            QS('kEnf','Enfermagem','💉','sE1','Choque septico',4,'N'+i),{formato:'certoerrado'});
          let avisos=[]; const t=window.toast; window.toast=(m)=>avisos.push(m);
          provasAparar();
          window.toast=t;
          return {total:db.provas.length, teto:PROVAS_MAX,
                  arquivadas:db.provasArquivo.length,
                  avisou:avisos.some(a=>/ainda não fez/.test(a)),
                  aviso:avisos.join(' | ')};}""")
        print('   %s provas esperando com teto %s → arquivadas: %s'
              %(r['total'],r['teto'],r['arquivadas']))
        print('   avisou: "%s"'%r['aviso'][:130])
        assert r['total']==r['teto']+5 and r['arquivadas']==0 and r['avisou']
        print('   passou do teto e não comeu nada — avisou em vez de apagar')
        print('   OK\n')

        print('=== D) restaurar traz a prova de volta ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kPt','Português','📖','sP1','Crase',12,'R');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          provaAchar(id).nome='A que sumiu';
          acervoGuardarProva(provaAchar(id)); provaArquivar(provaAchar(id));
          db.provas=[];
          const antes={lista:db.provas.length, arq:db.provasArquivo.length};
          provaRestaurar(id);
          const p=provaAchar(id);
          return {antes, lista:db.provas.length, arq:db.provasArquivo.length,
                  nome:p?p.nome:null, itens:p?p.questoes.length:0,
                  temEnunciado:!!(p&&p.questoes[0].questao),
                  nuncaFeita:p?!provaFoiFeita(p):null,
                  daPraFazer:/provaRefazer\\('"""+"""/.test(provasGuardadasHTML())};}""")
        print('   antes: %s na lista, %s arquivadas'%(r['antes']['lista'],r['antes']['arq']))
        print('   depois de restaurar: %s na lista, %s arquivadas'%(r['lista'],r['arq']))
        print('   "%s" com %s itens, com enunciado: %s'%(r['nome'],r['itens'],r['temEnunciado']))
        assert r['lista']==1 and r['arq']==0 and r['itens']==12
        assert r['nome']=='A que sumiu' and r['temEnunciado'] and r['nuncaFeita']
        print('   volta como estava: nunca feita, pronta pra fazer')
        print('   OK\n')

        print('=== E) restaurar duas vezes nao duplica ===')
        r=await page.evaluate("""()=>{
          const id=db.provas[0].id;
          let aviso=''; const t=window.toast; window.toast=(m)=>{aviso=m;};
          provaRestaurar(id);
          window.toast=t;
          return {lista:db.provas.filter(p=>p.id===id).length, aviso};}""")
        print('   na lista: %s · aviso: "%s"'%(r['lista'],r['aviso']))
        assert r['lista']==1 and 'já está na lista' in r['aviso']
        print('   OK\n')

        print('=== F) o botao Restaurar aparece na lista de arquivadas ===')
        r=await page.evaluate("""()=>{
          db.provas=[]; db.provasArquivo=[]; db.acervo=[];
          const id=provaGuardarLote(QS('kEnf','Enfermagem','💉','sE1','Choque septico',5,'B'),
                                    {formato:'certoerrado'});
          acervoGuardarProva(provaAchar(id)); provaArquivar(provaAchar(id));
          db.provas=[];
          provarqAberto=true;
          const h=provasArquivadasHTML();
          return {botao:/provaRestaurar\\('/.test(h),
                  selo:/nunca feita/.test(h),
                  explica:/<b>Restaurar<\\/b> traz a prova de volta/.test(h)};}""")
        print('   botão Restaurar: %s · selo "nunca feita": %s · a tela explica: %s'
              %(r['botao'],r['selo'],r['explica']))
        assert r['botao'] and r['selo'] and r['explica']
        print('   OK\n')

        print('=== G) a regra esta escrita em Minhas Provas ===')
        r=await page.evaluate("""()=>{
          provaGuardarLote(QS('kEnf','Enfermagem','💉','sE1','Choque septico',3,'G'),
                           {formato:'certoerrado'});
          const h=provasGuardadasHTML();
          return {regra:/prova que ainda não foi feita nunca sai da lista/i.test(h)};}""")
        print('   "prova que ainda não foi feita nunca sai da lista": %s'%r['regra'])
        assert r['regra']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
