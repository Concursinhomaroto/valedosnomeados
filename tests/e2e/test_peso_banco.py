# Achado 04: o historico de simulado parava de carregar peso morto no banco.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SUB='s1'; TOPIC='t1'; KING='k1'

def seed():
    return make_seed({'studyNickname':'R','studyCharacter':'ash',
        'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
        'topics':{KING:[{'id':TOPIC,'name':'Sepse','icon':'⚔️','subtopics':[
            {'id':SUB,'name':'Choque séptico','priority':100,'studied':True}]}]}})

MONTA = '''(id)=>{
  const alts=['A','B','C','D','E'].map(l=>({letra:l,
    texto:'Alternativa '+l+': conduta descrita com o detalhamento que uma questão de banca costuma ter.'}));
  const q=(i,acertou)=>({
    questao:'Em um paciente com choque séptico refratário a volume, qual a conduta inicial ('+i+')?',
    alternativas:alts.map(a=>({...a})), correta:'A',
    explicacao:'A noradrenalina é o vasopressor de primeira escolha quando a PAM não se sustenta após a reposição inicial.',
    userAnswer:acertou?'A':'B', formato:'multipla'});
  // 10 questões, 8 certas e 2 erradas (índices 1 e 7 são erradas)
  const questoes=[]; for(let i=0;i<10;i++) questoes.push(q(i, i!==1 && i!==7));
  const s=simFindSub(id);
  s.simHistorico=[{id:'h1',data:new Date().toISOString(),quantidade:10,acertos:8,erros:2,
                   questoes,formato:'multipla',nivel:'dificil'}];
  s.simStats={tentativas:1,questoesTotal:10,acertosTotal:8,porFormato:{multipla:{tentativas:1,questoes:10,acertos:8}}};
  const antes=JSON.stringify(db).length;
  const depois=JSON.stringify(sanitizeForFirebase(db)).length;
  const hist=JSON.stringify(s.simHistorico).length;
  const histDepois=JSON.stringify(sanitizeForFirebase(db).kingdoms?0:0)&&
    JSON.stringify(enxugarHistoricos(JSON.parse(JSON.stringify(db))).topics[k0()][0].subtopics[0].simHistorico).length;
  return {antes,depois,hist,histDepois};
}'''

MEDE = '''(id)=>{
  const copia=sanitizeForFirebase(db);
  const s=simFindSub(id);
  const histAntes=JSON.stringify(s.simHistorico).length;
  const kid=db.kingdoms[0].id;
  const histDepois=JSON.stringify(copia.topics[kid][0].subtopics[0].simHistorico).length;
  return {dbAntes:JSON.stringify(db).length, dbDepois:JSON.stringify(copia).length,
          histAntes, histDepois,
          qs:copia.topics[kid][0].subtopics[0].simHistorico[0].questoes.map((q,i)=>({
            i, temAlts:!!q.alternativas, temExpl:!!q.explicacao, errada:q.userAnswer!==q.correta}))};
}'''

BANCO = '''()=>{
  const b=getErrorBank();
  return b.map(x=>({q:x.questao.slice(-6), idx:x.qIdx, alts:(x.alternativas||[]).length,
                    temExpl:!!x.explicacao, correta:x.correta, resp:x.userAnswer}));
}'''

FLAGS = '''(id)=>{
  // marca a errada do indice 7 como revisada e a certa do indice 3 como problematica,
  // depois faz o ciclo de gravacao/leitura e confere se cairam no lugar certo
  toggleErroRevisado(id,'h1',7);
  toggleQuestaoProblematica(id,'h1',3);
  const copia=sanitizeForFirebase(db);
  const kid=db.kingdoms[0].id;
  const qs=copia.topics[kid][0].subtopics[0].simHistorico[0].questoes;
  return {revisadaEm:qs.map((q,i)=>q.revisado?i:null).filter(i=>i!==null),
          problematicaEm:qs.map((q,i)=>q.problematico?i:null).filter(i=>i!==null),
          statsDepois:simFindSub(id).simStats};
}'''

async def main():
    async with async_playwright() as pw:
        browser,page,errors=await setup_page(pw, seed())
        try:
            await page.evaluate(MONTA.replace("const histDepois=JSON.stringify(sanitizeForFirebase(db).kingdoms?0:0)&&\n    JSON.stringify(enxugarHistoricos(JSON.parse(JSON.stringify(db))).topics[k0()][0].subtopics[0].simHistorico).length;","const histDepois=0;"), SUB)
            m=await page.evaluate(MEDE, SUB)
            corte=100-round(m['histDepois']/m['histAntes']*100)
            print('=== peso do histórico (1 simulado de 10 questões, 8 certas) ===')
            print(f"  histórico gravado antes : {m['histAntes']:,} bytes")
            print(f"  histórico gravado agora : {m['histDepois']:,} bytes   (-{corte}%)")
            print(f"  banco inteiro           : {m['dbAntes']:,} → {m['dbDepois']:,} bytes")
            for q in m['qs']:
                marca='errada' if q['errada'] else 'certa '
                print(f"    q{q['i']} {marca} alternativas={str(q['temAlts']):<5} explicacao={q['temExpl']}")
            assert all(q['temAlts'] and q['temExpl'] for q in m['qs'] if q['errada']), 'errada perdeu dado'
            assert not any(q['temAlts'] or q['temExpl'] for q in m['qs'] if not q['errada']), 'certa manteve peso'
            assert corte>=50, f'só cortou {corte}%'

            print('\n=== Banco de Erros continua completo ===')
            for b in await page.evaluate(BANCO):
                print(f"  índice {b['idx']}: {b['alts']} alternativas, explicação={b['temExpl']}, gabarito {b['correta']} / respondeu {b['resp']}")
            banco=await page.evaluate(BANCO)
            assert len(banco)==2, banco
            assert [b['idx'] for b in banco]==[1,7], [b['idx'] for b in banco]
            assert all(b['alts']==5 and b['temExpl'] for b in banco), banco

            print('\n=== índices e marcações sobrevivem à gravação ===')
            f=await page.evaluate(FLAGS, SUB)
            print(f"  revisada no índice   : {f['revisadaEm']}")
            print(f"  problemática no índice: {f['problematicaEm']}")
            print(f"  simStats             : {f['statsDepois']}")
            assert f['revisadaEm']==[7], f['revisadaEm']
            assert f['problematicaEm']==[3], f['problematicaEm']
            assert f['statsDepois']['questoesTotal']==9 and f['statsDepois']['acertosTotal']==7, f['statsDepois']
            # marcar como problematica tem que descontar tambem no recorte por formato,
            # senao o total e a separacao passam a contar coisas diferentes
            pf=f['statsDepois']['porFormato']['multipla']
            print(f"  porFormato           : {pf}")
            assert pf['questoes']==9 and pf['acertos']==7, pf

            assert not real_errors(errors), real_errors(errors)
            print('\nOK — histórico enxuto, Banco de Erros intacto e índices preservados')
        finally:
            await browser.close()
asyncio.run(main())
