// Parser de caderno de prova Cebraspe (certo/errado) — ainda NAO esta no app.
// Guardado aqui porque foi validado contra a prova real e o proximo passo e porta-lo
// pra dentro de app/index.html, na tela de "Colar prova pronta".
//
// Validado contra o caderno da SESAU/AL (Enfermeiro):
//   120/120 itens, 25/25 grupos de comando, os dois textos de apoio capturados,
//   gabarito de 50 lido com os anulados (24 e 25) reconhecidos, e a trava de
//   contagem recusando 120 itens contra 50 gabaritos e aceitando 50 contra 50.
//
// O texto do caderno NAO esta no repositorio de proposito: o repo e servido como
// site publico (CNAME valedosnomeados.com.br) e o caderno e da banca.
//
// Falta pra fechar: a UI (anexar PDF, conferir o que foi achado, colar gabarito,
// escolher o assunto de cada grupo) e o gabarito dos itens 51 a 120.

// ---- parser de caderno de prova (Cebraspe certo/errado) ----
const CAD_LIXO=[
  /CEBRASPE\s*\|/i,            // cabecalho de pagina
  /^\d{6}_\d\w*$/,             // codigo do caderno
  /^--\s*CONHECIMENTOS/i,      // divisor de secao
  /^Espa[çc]o livre$/i,
  /^\s*$/
];
function cadLimpar(texto){
  return String(texto||'').replace(/\r\n?/g,'\n').split('\n')
    .map(l=>l.replace(/ /g,' ').trim())
    .filter(l=>!CAD_LIXO.some(re=>re.test(l)));
}
// O numero em inicio de linha SO vale se for o proximo esperado. E isso que impede
// "1900", "8.080/1990" e ate "30 anos" (que abre linha no item 11) de virarem item.
function cadAcharItens(linhas,primeiro){
  const marcas=[];
  let esperado=primeiro;
  for(let i=0;i<linhas.length;i++){
    const m=linhas[i].match(/^(\d{1,3})\s+(\S.*)$/);
    if(m&&parseInt(m[1],10)===esperado){
      marcas.push({num:esperado,linha:i,resto:m[2]});
      esperado++;
    }
  }
  return marcas;
}
// A banca SEMPRE quebra o caderno em dois arquivos (gerais e especificos), e a
// numeracao continua entre eles: o segundo abre no 51, ou em qualquer outro numero.
// Entao o inicio nao pode ser chutado — e o numero que abre a sequencia mais longa.
function cadPrimeiroNumero(linhas){
  const cands=[];
  for(let i=0;i<Math.min(linhas.length,80);i++){
    const m=linhas[i].match(/^(\d{1,3})\s+\S/);
    if(m){const n=parseInt(m[1],10); if(n>=1&&n<=300&&cands.indexOf(n)<0)cands.push(n);}
  }
  let melhor=null;
  cands.forEach(c=>{
    const n=cadAcharItens(linhas,c).length;
    if(n>=3&&(!melhor||n>melhor.n||(n===melhor.n&&c<melhor.cand)))melhor={cand:c,n};
  });
  return melhor?melhor.cand:(cands[0]||1);
}
// O comando e o bloco que antecede um grupo de itens e sempre contem "julgue".
// Corta o rabo do item anterior no ponto final que precede o inicio desse bloco.
const CAD_RE_JULGUE=/\bjulgue\b|\bjulgada\b|\bjulgar\b/i;
// "Lei n.º 8.080/1990" tem tres pontos que NAO terminam frase. Sem proteger isso, o
// corte de frases picava o comando no meio e o grupo saia errado — foi o que juntou
// 31-38 num grupo so e cortou o comando da Lei 8.080 em "080/1990".
const CAD_MASCARA='\u0001';
function cadProtegerPontos(t){
  return t
    .replace(/(\d)\.(?=\d)/g,'$1'+CAD_MASCARA)                 // 8.080  5.247  2.500
    .replace(/\bn\.(?=[ºo°\s])/gi,'n'+CAD_MASCARA)              // n.º  n.o
    .replace(/\b(art|arts|inc|al|par|pag|fl|Dr|Dra|Sr|Sra|Prof)\./gi,'$1'+CAD_MASCARA)
    .replace(/(\d)\.(ª|º|a\b|o\b)/gi,'$1'+CAD_MASCARA+'$2');   // 1.ª dose  3.º dia
}
function cadDesprotegerPontos(t){return t.split(CAD_MASCARA).join('.');}
function cadSepararComando(bloco){
  // bloco = texto do item anterior + (talvez) o comando do proximo grupo
  if(!CAD_RE_JULGUE.test(bloco))return{item:bloco,comando:''};
  // frases, mantendo o terminador
  const prot=cadProtegerPontos(bloco);
  const frases=(prot.match(/[^.!?]+[.!?]+(?:\s|$)|[^.!?]+$/g)||[prot]).map(cadDesprotegerPontos);
  let iJulgue=-1;
  for(let i=frases.length-1;i>=0;i--){ if(CAD_RE_JULGUE.test(frases[i])){iJulgue=i;break;} }
  if(iJulgue<0)return{item:bloco,comando:''};
  // o comando pode ter frases de contexto antes da que diz "julgue"; elas vao junto
  // ate encontrar o fim do item anterior. Sem marca de paragrafo no texto extraido,
  // o corte fica na frase do "julgue" e nas anteriores que ainda cabem no bloco do
  // comando (ate 3), desde que o item anterior nao fique vazio.
  // A frase de contexto so vem junto quando a frase do "julgue" APONTA PRA TRAS
  // ("A respeito desse tema...", "Com base nesses protocolos...", "Acerca dessas
  // infracoes..."). Sem esse gatilho, puxar a frase anterior rouba a ultima frase do
  // item anterior — foi o que aconteceu com o item 18, que ficava vazio porque o texto
  // dele inteiro virava comando do grupo seguinte.
  const APONTA=/\b(dess[ea]s?|ness[ea]s?|desse tema|tais|referid[oa]s?|tal tema)\b/i;
  let ini=iJulgue;
  if(APONTA.test(frases[iJulgue])&&iJulgue>0
     &&frases.slice(iJulgue-1).join('').trim().length<=900)ini=iJulgue-1;
  return{item:frases.slice(0,ini).join('').trim(),comando:frases.slice(ini).join('').trim()};
}
// Um bloco "Texto CG1A1-I ..." e material de apoio de um grupo inteiro de itens — sem
// ele os itens de portugues nao podem ser respondidos.
const CAD_RE_TEXTO=/^Texto\s+[A-Z0-9][\w.\-]*$/;
function cadSepararApoio(linhas){
  for(let i=0;i<linhas.length;i++){
    if(CAD_RE_TEXTO.test(linhas[i].trim())){
      return{antes:linhas.slice(0,i),apoio:linhas.slice(i)};
    }
  }
  return{antes:linhas,apoio:[]};
}
function cadernoParse(texto){
  const linhas=cadLimpar(texto);
  const primeiro=cadPrimeiroNumero(linhas);
  const marcas=cadAcharItens(linhas,primeiro);
  if(!marcas.length)return{itens:[],grupos:[],faltando:[],primeiro,aviso:'Nenhum item encontrado.'};
  const preambulo=linhas.slice(0,marcas[0].linha).join('\n');
  const itens=[];
  for(let k=0;k<marcas.length;k++){
    const m=marcas[k];
    const fim=(k+1<marcas.length)?marcas[k+1].linha:linhas.length;
    const cru=[m.resto].concat(linhas.slice(m.linha+1,fim));
    const {antes,apoio}=cadSepararApoio(cru);
    const bruto=antes.join(' ').replace(/\s+/g,' ').trim();
    const {item,comando}=cadSepararComando(bruto);
    let apoioTxt='',comandoFinal=comando;
    if(apoio.length){
      const sep=cadSepararComando(apoio.join(' ').replace(/\s+/g,' ').trim());
      apoioTxt=sep.item; comandoFinal=sep.comando||comando;
    }
    itens.push({num:m.num,texto:item,comandoDepois:comandoFinal,apoioDepois:apoioTxt});
  }
  // o comando que veio ANTES do item 1 esta no preambulo
  const preLinhas=linhas.slice(0,marcas[0].linha);
  const preSep=cadSepararApoio(preLinhas);
  const preBloco=(preSep.apoio.length?preSep.apoio:preLinhas).join(' ').replace(/\s+/g,' ');
  const preFull=cadSepararComando(preBloco);
  const preComando=preFull.comando;
  const preApoio=preSep.apoio.length?preFull.item:'';
  // monta os grupos: um comando abre um grupo, que vai ate o proximo comando
  const grupos=[];
  let atual={comando:preComando,apoio:preApoio,itens:[]};
  itens.forEach(it=>{
    atual.itens.push(it.num);
    if(it.comandoDepois){grupos.push(atual);atual={comando:it.comandoDepois,apoio:it.apoioDepois||'',itens:[]};}
  });
  if(atual.itens.length)grupos.push(atual);
  const faltando=[];
  for(let n=primeiro;n<primeiro+marcas.length;n++){
    if(!itens.some(i=>i.num===n))faltando.push(n);
  }
  return{itens,grupos,faltando,primeiro};
}
// ---- gabarito ----
function gabaritoParse(txt,letras){
  const perm=new Set((letras||'CEX').split(''));
  const soLetras=String(txt||'').toUpperCase().replace(/[^A-Z]/g,'');
  if(soLetras.length&&[...soLetras].every(c=>perm.has(c)))return soLetras.split('');
  // tem palavra no meio: fica so com as letras isoladas
  return String(txt||'').toUpperCase().split(/[^A-Z]+/)
    .filter(t=>t.length===1&&perm.has(t));
}
module.exports={cadernoParse,gabaritoParse};
