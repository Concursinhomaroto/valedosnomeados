# -*- coding: utf-8 -*-
# montarChaveQ (o ENDERECO usado no arquivo de provas) e normalizeForDedup(questao).slice(0,120)
# — sem o formato. Dois itens certo/errado da Cebraspe costumam compartilhar um enunciado
# longo e divergir so na clausula final, e os 120 primeiros caracteres saem identicos. A
# questao que chegava depois era tratada como repeticao da primeira e sumia, sem aviso.
#
# acervoChave2 e a IDENTIDADE de verdade: hash do enunciado INTEIRO (backupHash, ja usado
# no diff do backup) mais o formato. So decide "e a mesma questao" nos tres lugares que
# tomam essa decisao (guardar no acervo, unir copias no boot, montar o pool) — o arquivo
# de provas continua ENDERECANDO por montarChaveQ, sem mudar de definicao.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page
from test_acervo import seed, QS

# 120+ caracteres identicos, diverge so no final — exatamente o caso real do prompt.
COMUM = ('De acordo com a Lei 8.080/1990, compete ao SUS a execução de ações de '
         'vigilância sanitária, epidemiológica e de saúde do trabalhador')
A = COMUM + ', sendo vedado ao gestor delegar tal competência a terceiros sem previsão legal expressa.'
B = COMUM + ', sendo permitido ao gestor delegar tal competência mediante convênio formal, nos termos da lei.'

def prova(qs,tag):
    return {'questoes':[{'questao':q,'correta':'C','formato':'certoerrado','subId':'sE1',
             'subName':'Choque septico','kingdomId':'kEnf','kingdomName':'Enfermagem',
             'kingdomIcon':'💉'} for q in qs],'tentativas':[]}

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)

        print('=== A) mesmo prefixo de 120 chars, o COMEÇO é idêntico (confirma o cenário) ===')
        r=await page.evaluate("""(args)=>{
          const [a,b]=args;
          return {enderecoIgual:montarChaveQ({questao:a})===montarChaveQ({questao:b}),
                  identidadeDiferente:acervoChave2({questao:a,formato:'certoerrado'})
                                     !==acervoChave2({questao:b,formato:'certoerrado'}),
                  prefixo120:a.slice(0,120)===b.slice(0,120)};}""",[A,B])
        print('   os 120 primeiros chars batem: %s'%r['prefixo120'])
        print('   montarChaveQ (endereço) colide: %s · acervoChave2 (identidade) diferencia: %s'
              %(r['enderecoIgual'],r['identidadeDiferente']))
        assert r['prefixo120'] and r['enderecoIgual'] and r['identidadeDiferente']
        print('   OK\n')

        print('=== B) as duas sobrevivem no banco — antes, a 2ª sumia dentro da 1ª ===')
        r=await page.evaluate("""(args)=>{
          const [pa,pb]=args;
          db.acervo=[];
          const n1=acervoGuardarProva(pa);
          const n2=acervoGuardarProva(pb);
          return {n1,n2,total:db.acervo.length,
                  textos:db.acervo.map(q=>q.questao.slice(-30))};}""",
          [prova([A],'x'),prova([B],'x')])
        print('   guardei A (%s nova) e B (%s nova) → banco tem %s'%(r['n1'],r['n2'],r['total']))
        for t in r['textos']: print('   ...%s'%t)
        assert r['n1']==1 and r['n2']==1 and r['total']==2
        print('   as duas ficaram — nenhuma engoliu a outra')
        print('   OK\n')

        print('=== C) a MESMA questão, de novo, continua sendo UMA só (não superdividiu) ===')
        r=await page.evaluate("""(args)=>{
          const [pa]=args;
          const antes=db.acervo.length;
          const novas=acervoGuardarProva(pa);   // A de novo, texto idêntico
          return {antes,depois:db.acervo.length,novas};}""",[prova([A],'x')])
        print('   guardei A de novo → %s novas (banco: %s → %s)'
              %(r['novas'],r['antes'],r['depois']))
        assert r['novas']==0 and r['depois']==r['antes']
        print('   OK\n')

        print('=== D) migração: item antigo sem _chaveForte ganha um, sem duplicar nem mudar ao repetir ===')
        r=await page.evaluate("""async(args)=>{
          const [a,b]=args;
          // simula cache de ANTES desta versao: sem _chaveForte
          db.acervo=[{questao:a,correta:'C',formato:'certoerrado',subId:'sE1',kingdomId:'kEnf'},
                     {questao:b,correta:'C',formato:'certoerrado',subId:'sE1',kingdomId:'kEnf'}];
          window.__root.users.TEST_UID_LEO.vdn_acervo=db.acervo;
          const n1=await acervoCarregar();
          const chaves1=db.acervo.map(q=>q._chaveForte);
          const n2=await acervoCarregar();          // abre o app de novo
          const chaves2=db.acervo.map(q=>q._chaveForte);
          return {n1,n2,chaves1,chaves2,
                  todasPreenchidas:chaves1.every(Boolean),
                  estavel:JSON.stringify(chaves1)===JSON.stringify(chaves2),
                  semRepetir:new Set(chaves1).size===2};}""",[A,B])
        print('   1º load: %s itens, chaves: preenchidas=%s, sem repetir=%s'
              %(r['n1'],r['todasPreenchidas'],r['semRepetir']))
        print('   2º load: %s itens · chave estável entre loads: %s'%(r['n2'],r['estavel']))
        assert r['n1']==2 and r['n2']==2 and r['todasPreenchidas'] and r['semRepetir']
        assert r['estavel']
        print('   OK\n')

        print('=== E) acervoUnir junta nuvem+local+registro sem duplicar, mesmo com item sem chave ===')
        r=await page.evaluate("""(args)=>{
          const [a,b]=args;
          const semChave=q=>({questao:q,correta:'C',formato:'certoerrado',subId:'sE1',kingdomId:'kEnf'});
          const comChave=q=>({...semChave(q),_chaveForte:acervoChave2(semChave(q))});
          const nuvem=[comChave(a)], local=[semChave(a),comChave(b)], registro=[semChave(b)];
          const u=acervoUnir(nuvem,local,registro);
          return {total:u.length,
                  temA:u.some(q=>q.questao===a), temB:u.some(q=>q.questao===b)};}""",[A,B])
        print('   nuvem+local+registro com A e B em formatos mistos → %s no total'%r['total'])
        assert r['total']==2 and r['temA'] and r['temB']
        print('   OK\n')

        print('=== F) montarAcervo não confunde as duas no pool ===')
        r=await page.evaluate("""(args)=>{
          const [pa,pb]=args;
          db.provas=[]; db.provasArquivo=[];
          const ida=provaGuardarLote(pa.questoes,{formato:'certoerrado'});
          const idb=provaGuardarLote(pb.questoes,{formato:'certoerrado'});
          provaAchar(ida).tentativas=[{respostas:['C'],acertos:1,tempoGastoSec:10}];   // acertou A
          provaAchar(idb).tentativas=[{respostas:['E'],acertos:0,tempoGastoSec:10}];   // errou B
          const pool=montarAcervo();
          const doA=pool.find(x=>x.q.questao===args[0].questoes[0].questao);
          const doB=pool.find(x=>x.q.questao===args[1].questoes[0].questao);
          return {total:pool.length,
                  aErrou:doA&&doA.errou, bErrou:doB&&doB.errou};}""",
          [prova([A],'x'),prova([B],'x')])
        print('   pool: %s itens · A errou=%s (acertei) · B errou=%s (errei)'
              %(r['total'],r['aErrou'],r['bErrou']))
        assert r['total']==2 and r['aErrou']==False and r['bErrou']==True
        print('   se a chave antiga estivesse em uso, as duas virariam UMA linha confusa no pool')
        print('   OK\n')

        print('=== G) arquivadas com prefixo colidente resolvem CADA UMA o texto certo ===')
        r=await page.evaluate("""(args)=>{
          const [pa,pb]=args;
          db.provas=[]; db.provasArquivo=[]; db.acervo=[];
          acervoGuardarProva(pa); acervoGuardarProva(pb);   // as duas no banco
          const provaComB={id:'pcolidente',num:1,criadaEm:new Date().toISOString(),
            formato:'certoerrado',questoes:pb.questoes,
            tentativas:[{data:new Date().toISOString(),respostas:['E'],acertos:0,tempoGastoSec:5}]};
          provaArquivar(provaComB);
          const remontada=provaDoArquivo('pcolidente');
          return {itens:remontada?remontada.questoes.length:0,
                  textoCerto:remontada&&remontada.questoes[0].questao===args[1].questoes[0].questao,
                  temChaves2:!!(db.provasArquivo[0].chaves2||[]).length};}""",
          [prova([A],'x'),prova([B],'x')])
        print('   arquivou a prova que tem B (colide com A no endereço) · chaves2 gravado: %s'
              %r['temChaves2'])
        print('   remontou %s item(ns) · texto é o de B (o certo): %s'%(r['itens'],r['textoCerto']))
        assert r['itens']==1 and r['textoCerto'] and r['temChaves2']
        print('   sem a desambiguação, isso podia voltar com o texto de A por engano')
        print('   OK\n')

        print('=== H) prova arquivada ANTES desta versão (sem chaves2) continua resolvendo ===')
        r=await page.evaluate("""(args)=>{
          const [pa]=args;
          db.provas=[]; db.provasArquivo=[]; db.acervo=[];
          acervoGuardarProva(pa);
          // simula um arquivo gravado pela versao anterior: sem chaves2
          db.provasArquivo=[{id:'legado',num:1,criadaEm:new Date().toISOString(),
            formato:'certoerrado',nome:'',origem:'ia',treino:false,limiteSec:0,
            chaves:[montarChaveQ(pa.questoes[0])],
            marcacoes:{},
            tentativas:[{data:new Date().toISOString(),respostas:['C'],acertos:1,tempoGastoSec:5}]}];
          const remontada=provaDoArquivo('legado');
          return {itens:remontada?remontada.questoes.length:0,
                  texto:remontada&&remontada.questoes[0].questao===args[0].questoes[0].questao};}""",
          [prova([A],'x')])
        print('   arquivo legado (sem chaves2) → remontou %s item(ns), texto certo: %s'
              %(r['itens'],r['texto']))
        assert r['itens']==1 and r['texto']
        print('   nenhuma prova já arquivada quebra com esta mudança')
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
