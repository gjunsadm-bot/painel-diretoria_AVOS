"""Replica a aba 'Fluxo grupo' (e a DRE derivada dela) para qualquer seleção de empreendimento."""
import datetime, re
from pyxlsb import open_workbook

low = lambda s: str(s or '').strip().lower()
def xdate(v):
    return datetime.date(1899,12,30)+datetime.timedelta(days=int(v)) if isinstance(v,(int,float)) else None

# colunas da Fluxo grupo (cabeçalho da linha 4) na ordem D..W, exceto F/G/H calculadas
COLS = [('receita','Receita'),('distrato','Distrato'),('impostos','Impostos'),('terreno','Terreno (compra)'),('aprovacao','Aprovação'),('obra','Obra'),
        ('comissao','Comissão Avos'),('marketing','Marketing + Plantão Vendas'),('adm','Administrativo'),('taxa','Taxa administrativa'),('fin','Financeiro'),
        ('aporte_cap','Aporte de capital'),('aporte_soc','Aporte de Sócio'),('retirada','Retirada Sócios'),('lucro_grupo','Lucro grupo'),('lucro_terc','Lucro a Terceiros')]
CUSTOS = ['impostos','terreno','aprovacao','obra','comissao','marketing','adm','taxa']
OPCOES = ['BELLEVIE','VILLA NOAH','Todos Bambuzal','VICTÓRIA GARDEN','AVOS','HIRAIWA','UNA','NELSON E MARCELO','Todos']
INICIO = datetime.date(2019,1,1); FIM = datetime.date(2042,2,1); PROJ = datetime.date(2026,11,1)

def meses():
    d=INICIO; out=[]
    while d<=FIM: out.append(d); d=datetime.date(d.year+(d.month==12),d.month%12+1,1)
    return out

class Base:
    def __init__(self, path):
        self.base=[]; self.rec=[]; self.prev=[]; self.part={}; self.lista=[]; self.ind=[]
        with open_workbook(path) as wb:
            with wb.get_sheet('BASE PASSADO') as sh:
                for i,row in enumerate(sh.rows()):
                    if i==0: continue
                    v=[c.v for c in row]+[None]*22
                    d=xdate(v[2])
                    if d and isinstance(v[8],(int,float)): self.base.append((d,float(v[8]),low(v[19]),low(v[16]),low(v[20])))
            with wb.get_sheet('basecontasareceber') as sh:
                for i,row in enumerate(sh.rows()):
                    if i==0: continue
                    v=[c.v for c in row]+[None]*25
                    d=xdate(v[11])
                    if d and low(v[20])=='a vencer' and isinstance(v[19],(int,float)): self.rec.append((d,float(v[19]),low(v[1]),low(v[23])))
            with wb.get_sheet('previsão obra bambuzal') as sh:
                for row in sh.rows():
                    v=[c.v for c in row]+[None]*5; d=xdate(v[0])
                    if d and isinstance(v[1],(int,float)) and low(v[2])=='todos bambuzal': self.prev.append((d,low(v[3]),float(v[1])))
            with wb.get_sheet('lista depara') as sh:
                for i,row in enumerate(sh.rows()):
                    v=[c.v for c in row]+[None]*14
                    if i==0: continue
                    if 1<=i<=13 and v[0]: self.lista.append((str(v[0]),str(v[1])))
                    if v[4] and v[5]: self.ind.append((low(v[4]),low(v[5]),v[6] if isinstance(v[6],(int,float)) else 0.0))
                    if 2<=i<=9 and v[9]: self.part[str(v[9]).strip().upper()]=(v[10],str(v[11] or ''))
        self.individuais=[low(a) for a,_ in self.lista[:12]]
        self.grupos_rec={r[3] for r in self.rec}

    def pct_avos(self, sel):
        p=self.part.get(sel.upper())
        if p and isinstance(p[0],(int,float)): return float(p[0])
        if sel=='Todos Bambuzal':
            vals=[float(v) for v,e in self.part.values() if isinstance(v,(int,float)) and e.upper()=='BAMBUZAL']
            return sum(vals)/len(vals) if vals else None
        if sel=='Todos': return None
        return 1.0

    def fluxo(self, sel):
        s=low(sel)
        if sel=='Todos': fb=lambda r: True
        elif s in self.individuais: fb=lambda r: r[3]==s
        else: fb=lambda r: r[4]==s
        if sel=='Todos': fr=lambda r: True
        elif s in self.grupos_rec: fr=lambda r: r[3]==s
        else: fr=lambda r: r[2]==s
        agg={}
        for d,val,cat,_,_ in filter(fb,self.base): k=(d.year,d.month,cat); agg[k]=agg.get(k,0)+val
        av={}
        for d,val,_,_ in filter(fr,self.rec): k=(d.year,d.month); av[k]=av.get(k,0)+val
        pv={}
        if sel in ('Todos','Todos Bambuzal'):
            for d,c,val in self.prev:
                if c=='obra': k=(d.year,d.month); pv[k]=pv.get(k,0)+val
        pct=self.pct_avos(sel)
        out=[]; saldo=0
        for d in meses():
            m={'m':d.strftime('%Y-%m')}
            for k,cat in COLS: m[k]=agg.get((d.year,d.month,low(cat)),0.0)
            m['avencer']=av.get((d.year,d.month),0.0)
            if d>=PROJ: m['impostos']=-m['avencer']*0.04
            m['obra']+=-pv.get((d.year,d.month),0.0)
            m['receitas']=m['receita']+m['distrato']+m['avencer']           # col G
            m['avos']=m['receitas']*pct if pct is not None else None         # col H
            m['custos']=sum(m[k] for k in CUSTOS)                             # col Q
            m['socios']=m['aporte_cap']+m['aporte_soc']+m['retirada']+m['lucro_grupo']+m['lucro_terc']  # col X
            m['geracao']=m['receitas']+m['custos']+m['fin']+m['socios']      # col Y
            saldo+=m['geracao']; m['saldo']=saldo; out.append(m)
        return out, pct

def _irr(fl):
    npv=lambda r: sum(f/(1+r)**i for i,f in enumerate(fl))
    lo,hi=-0.99,1.0
    try:
        if npv(lo)*npv(hi)>0: return None
    except ZeroDivisionError: return None
    for _ in range(200):
        mid=(lo+hi)/2
        if npv(lo)*npv(mid)<=0: hi=mid
        else: lo=mid
    return mid

def dre(B, sel):
    fl,pct=B.fluxo(sel)
    anos=list(range(2019,2027))+['2027+ (previsão)']
    yr=lambda m: int(m['m'][:4]) if int(m['m'][:4])<=2026 else '2027+ (previsão)'
    def by(key): return [sum(m[key] for m in fl if yr(m)==a)/1000 for a in anos]
    rb=by('receitas'); dis=by('distrato'); com=by('comissao'); imp=by('impostos')
    rl=[a+b+c for a,b,c in zip(rb,com,imp)]
    ob,te,ap,mk,ad,tx=by('obra'),by('terreno'),by('aprovacao'),by('marketing'),by('adm'),by('taxa')
    ro=[a+b+c+d+e+f+g for a,b,c,d,e,f,g in zip(rl,ob,te,ap,mk,ad,tx)]
    fi=by('fin'); fa=[a+b for a,b in zip(ro,fi)]
    apo=[a+b for a,b in zip(by('aporte_cap'),by('aporte_soc'))]; ret=by('retirada'); lt=by('lucro_terc'); lg=by('lucro_grupo')
    gl=[a+b+c+d+e for a,b,c,d,e in zip(fa,apo,ret,lt,lg)]
    ini=[];fin_=[];s=0
    for g in gl: ini.append(s); s+=g; fin_.append(s)
    mg=[(o/r if r else 0) for o,r in zip(ro,rb)]
    T=sum; R=T(rb)
    L=[('Receita bruta de vendas (receitas + a vencer)',rb),('(−) Distratos (já incluso na receita)',dis),('(−) Comissões de vendas',com),('(−) Impostos',imp),
       ('(=) Receita líquida',rl),('(−) Obras e infraestrutura',ob),('(−) Terreno (compra)',te),('(−) Aprovação de projetos',ap),('(−) Marketing e plantão de vendas',mk),
       ('(−) Administrativo',ad),('(±) Taxa de administração',tx),('(=) Resultado operacional',ro),('Margem operacional',mg),('(±) Resultado financeiro',fi),
       ('(=) Fluxo antes dos sócios',fa),('(+) Aportes de terceiro',apo),('(−) Retirada de sócios',ret),('(−) Lucro distribuído a terceiros',lt),
       ('(±) Lucro grupo (intercompany)',lg),('(=) Geração de caixa líquida',gl),('Saldo de caixa inicial',ini),('Saldo de caixa final',fin_)]
    linhas=[]
    for lab,arr in L:
        tot=T(arr)
        if lab=='Margem operacional': tot=T(ro)/R if R else 0
        elif lab=='Saldo de caixa inicial': tot=0
        elif lab=='Saldo de caixa final': tot=fin_[-1]
        linhas.append(dict(lin=lab,tot=tot,pct=(tot/R if R and lab not in ('Margem operacional','Saldo de caixa inicial') else None),anos=arr))
    C=lambda lab: next(l['tot'] for l in linhas if l['lin'].startswith(lab))
    # indicadores (lista depara)
    grp=[low(a) for a,b in B.lista if low(b)==low(sel)]
    alvo=grp if grp else [low(sel)]
    if low(sel) not in alvo: alvo.append(low(sel))
    gi=lambda pat: sum(v for g,i,v in B.ind if g in alvo and i.startswith(pat.lower()))
    A10,A11,L12,L13=gi('Área líquida vendável Empreendimento'),gi('Área líquida vendável AVOS'),gi('Qdade de lotes Empreendimento'),gi('Qdade de lotes AVOS')
    dv=lambda a,b: a/b if b else 0
    C10=C('Receita bruta')*1000; C11=C('(−) Distratos')*1000; C15=C('(−) Obras')*1000
    preco=dv(C10+C11,L13); precom2=dv(preco*L13,A11)
    custo=C15; fa_t=C('(=) Fluxo antes')*1000
    # fluxo mensal antes dos sócios 2019-01..2026-12 (como na planilha: G+Q+R)
    mm=[m for m in fl if m['m']<='2026-12']; ms=[m['receitas']+m['custos']+m['fin'] for m in mm]
    acc=[];s=0
    for v in ms: s+=v; acc.append(s)
    expo=min(0,min(acc)) if acc else 0; r=_irr(ms)
    ind=[('PRODUTO',None),('Área líquida vendável – empreendimento (m²)',('n',A10)),('Área líquida vendável – AVOS (m²)',('n',A11)),('Lotes – empreendimento',('n',L12)),('Lotes – AVOS',('n',L13)),
      ('Tamanho médio do lote (m²)',('n',dv(A10,L12))),('Preço médio do lote – AVOS',('r',preco)),('Preço médio do m² – AVOS',('r',precom2)),
      ('CUSTO DE OBRA',None),('Custo de obra – empreendimento (100%)',('r',custo)),('Custo de obra por m² vendável',('r',dv(custo,A10))),('Custo de obra por lote – AVOS',('r',dv(custo,L13))),
      ('Custo de obra / VGV',('p',dv(custo,C10))),('VGV / custo de obra',('x',dv(C10,custo))),
      ('RENTABILIDADE',None),('Margem bruta (receita líq. − obra) / receita',('p',dv(C('(=) Receita líquida')+C('(−) Obras'),R))),('Margem operacional (EBITDA caixa)',('p',dv(C('(=) Resultado operacional'),R))),
      ('Margem antes dos sócios',('p',dv(C('(=) Fluxo antes'),R))),('Lucro por lote – AVOS',('r',dv(fa_t,L13))),('Lucro por m² vendável – AVOS',('r',dv(fa_t,A11))),
      ('EXPOSIÇÃO E RETORNO',None),('Meses com saldo acumulado negativo',('i',sum(1 for a in acc if a<0))),('Exposição máxima de caixa',('r',expo)),
      ('Lucro sobre exposição máxima',('p',dv(fa_t,-expo))),('TIR anualizada (fluxo antes dos sócios)',('p',(1+r)**12-1) if r is not None else ('t','n/a')),
      ('VPL a 1% a.m.',('r',sum(v/1.01**(i+1) for i,v in enumerate(ms))))]
    return dict(linhas=linhas,anos=anos,ind=[[a,b] for a,b in ind],saldo=[[m['m'],a] for m,a in zip(mm,acc)],pct=pct,
                avos_total=(sum(m['avos'] for m in fl) if pct is not None else None))

def todas(path):
    B=Base(path)
    dados={o:dre(B,o) for o in OPCOES}
    anos=dados['Todos']['anos']
    for o in OPCOES: dados[o]['anos']=None
    # receita avos por linha do Painel executivo (seleção individual = mesma regra da Fluxo grupo)
    emps=['BELLEVIE','VILLA NOAH','KOA','ALOHI','KALA','NALU','BAMBUZAL','VICTÓRIA GARDEN','HIRAIWA','UNA','NELSON E MARCELO','AVOS']
    avos={}
    def linha(fl,p):
        T=lambda k: sum(m[k] for m in fl)
        rec=T('receitas'); cus=T('custos')
        return dict(pct=p,avos=(T('avos') if p is not None else None),receita=T('receita'),distrato=T('distrato'),avencer=T('avencer'),receitas=rec,custos=cus,
                    resultado=rec+cus,margem=((rec+cus)/rec if rec>0 else None),fin=T('fin'),aportes=T('aporte_cap')+T('aporte_soc'),retirada=T('retirada'),
                    lucro_grupo=T('lucro_grupo'),lucro_terc=T('lucro_terc'),distrib=T('lucro_grupo')+T('lucro_terc'),socios=T('socios'),geracao=T('geracao'))
    for e in emps:
        fl,p=B.fluxo(e); avos[e]=linha(fl,p)
    flT,_=B.fluxo('Todos'); avos['Total do grupo']=linha(flT,None)
    flt,_=B.fluxo('Todos')
    return {'opcoes':OPCOES,'anos':anos,'dados':dados}, avos, flt, {k:v[0] for k,v in B.part.items()}
