import numpy as np, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
BASE='/tmp/claude-0/-home-user-alja0079/27f91246-efb8-51af-b2c6-c34e8553cf88/'
FD=BASE+'scratchpad/fonts/package/files/inter-latin-%d-normal.woff'
F=lambda w,s: ImageFont.truetype(FD%w,s)
SY=lambda s: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',s)
RED=(255,59,48); BLUE=(10,132,255); GRN=(52,199,89); DK=(20,20,30); GR=(120,120,130); YEL=(255,214,10); ORG=(255,149,0)
SWc,SHc=540,1310   # screen canvas
# ---- geometry of green screen in hand photo
src=Image.open(BASE+'images/127.jpg').convert('RGB'); A=np.array(src).astype(int)
M=(A[...,1]>120)&(A[...,1]>A[...,0]+40)&(A[...,1]>A[...,2]+40)
def fit(ts,vals): p=np.polyfit(ts,vals,1); return p
L=fit(*zip(*[(y,np.nonzero(M[y])[0].min()) for y in range(420,940,10)]))
Rr=fit(*zip(*[(y,np.nonzero(M[y])[0].max()) for y in range(380,560,10)]))
T=fit(*zip(*[(x,np.nonzero(M[:,x])[0].min()) for x in range(300,460,10)]))
Bm=fit(*zip(*[(x,np.nonzero(M[:,x])[0].max()) for x in range(320,500,10)]))
def inter(vline,hline):  # vline x=a*y+b ; hline y=c*x+d
    a,b=vline; c,d=hline; y=(c*b+d)/(1-c*a); return (a*y+b,y)
TL,TR,BR,BL=inter(L,T),inter(Rr,T),inter(Rr,Bm),inter(L,Bm)
QUAD=[TL,TR,BR,BL]
def homog(srcp,dstp):
    Am=[];bv=[]
    for (x,y),(u,v) in zip(srcp,dstp):
        Am+= [[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]; bv+=[u,v]
    return np.append(np.linalg.solve(np.array(Am,float),np.array(bv,float)),1).reshape(3,3)
SCR=[(0,0),(SWc,0),(SWc,SHc),(0,SHc)]
Hs2p=homog(SCR,QUAD)        # screen -> photo
Hp2s=np.linalg.inv(Hs2p)
S=1080/736; OY=int((1312*S-1920)/2)
def to_final(sx,sy):
    v=Hs2p@[sx,sy,1]; x,y=v[0]/v[2],v[1]/v[2]; return (x*S, y*S-OY)
def compose(screen, pill, title, sub, callouts=()):
    c=list(Hp2s.flatten()[:8]/Hp2s[2,2])
    warped=screen.convert('RGB').transform(src.size,Image.PERSPECTIVE,c,Image.BICUBIC)
    mk=Image.fromarray((M*255).astype('uint8')).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    ph=src.copy(); ph.paste(warped,(0,0),mk)
    big=ph.resize((1080,round(1312*S)),Image.LANCZOS).crop((0,OY,1080,OY+1920))
    # top gradient for title
    g=Image.new('L',(1080,1920),0); gd=ImageDraw.Draw(g)
    for y in range(0,620): gd.line([(0,y),(1080,y)],fill=int(250*(1-y/620)**0.9))
    big=Image.composite(Image.new('RGB',big.size,(10,14,34)),big,g)
    d=ImageDraw.Draw(big)
    f=F(800,40); w=f.getlength(pill)
    d.rounded_rectangle([540-w/2-34,205,540+w/2+34,265],radius=30,fill=YEL); d.text((540,235),pill,font=f,fill=(14,18,40),anchor='mm')
    fs=78
    while F(800,fs).getlength(title)>900: fs-=2
    d.text((540,290),title,font=F(800,fs),fill='white',anchor='ma',stroke_width=3,stroke_fill=(0,0,0))
    d.text((543,395),sub,font=F(600,40),fill=(0,0,0),anchor='ma'); d.text((540,392),sub,font=F(600,40),fill=(225,230,245),anchor='ma')
    for (sx,sy),(lx,ly),txt in callouts:
        tx,ty=to_final(sx,sy)
        fl=F(800,42); w=fl.getlength(txt); lx=max(lx,w/2+28+95); lx=min(lx,1080-w/2-28-95)
        ang=math.atan2(ty-ly,tx-lx); ex,ey=tx-26*math.cos(ang),ty-26*math.sin(ang)
        d.line([(lx,ly),(ex,ey)],fill=RED,width=12)
        Lh=40; d.polygon([(tx,ty),(ex-Lh*math.cos(ang-0.5)+26*math.cos(ang),ey-Lh*math.sin(ang-0.5)+26*math.sin(ang)),(ex-Lh*math.cos(ang+0.5)+26*math.cos(ang),ey-Lh*math.sin(ang+0.5)+26*math.sin(ang))],fill=RED)
        fl=F(800,42); w=fl.getlength(txt); lx=max(lx,w/2+28+95); lx=min(lx,1080-w/2-28-95)
        ang=math.atan2(ty-ly,tx-lx); ex,ey=tx-26*math.cos(ang),ty-26*math.sin(ang)
        d.rounded_rectangle([lx-w/2-28,ly-40,lx+w/2+28,ly+40],radius=40,fill=RED,outline='white',width=4)
        d.text((lx,ly),txt,font=fl,fill='white',anchor='mm')
    return big
# ---- cartoon map crop
def mapimg():
    m=Image.open(BASE+'images/126.jpg').convert('RGB').crop((0,0,265,646))
    return m.resize((SWc,SHc),Image.LANCZOS)
def status(d,dark=False):
    c='white' if dark else DK
    d.text((95,62),'9:41',font=F(600,34),fill=c,anchor='lm')
REG={'A':(0,0,265,646),'B':(475,0,736,640),'C':(0,690,255,1312),'D':(470,640,736,1312)}
def mapreg(k,dim=0):
    m=Image.open(BASE+'images/126.jpg').convert('RGB').crop(REG[k]).resize((SWc,SHc),Image.LANCZOS)
    if dim: m=Image.blend(m,Image.new('RGB',m.size,(0,0,0)),dim)
    return m
def sheet(d,y0):
    d.rounded_rectangle([0,y0,SWc,SHc+60],radius=46,fill='white')
    d.rounded_rectangle([SWc/2-40,y0+16,SWc/2+40,y0+24],radius=4,fill=(210,210,215))
def row(d,y,txt,col=DK,icon=None,hl=False,right=None,sub=None,h=96):
    d.rounded_rectangle([30,y,SWc-30,y+h],radius=22,fill=(244,244,247))
    tx=60
    if icon: d.ellipse([52,y+h/2-26,104,y+h/2+26],fill=icon[0]); d.text((78,y+h/2),icon[1],font=SY(28),fill='white',anchor='mm'); tx=124
    if sub: d.text((tx,y+h/2-16),txt,font=F(600,34),fill=col,anchor='lm'); d.text((tx,y+h/2+22),sub,font=F(400,26),fill=GR,anchor='lm')
    else: d.text((tx,y+h/2),txt,font=F(600,34),fill=col,anchor='lm')
    if right: d.text((SWc-60,y+h/2),right,font=SY(36),fill=BLUE,anchor='rm')
    if hl: d.rounded_rectangle([20,y-10,SWc-20,y+h+10],radius=30,outline=RED,width=8)
def puck(d,x,y):
    d.ellipse([x-26,y-26,x+26,y+26],fill='white'); d.ellipse([x-19,y-19,x+19,y+19],fill=BLUE)
    d.polygon([(x,y-12),(x+9,y+9),(x,y+4),(x-9,y+9)],fill='white')
def route(d,pts):
    d.line(pts,fill='white',width=28,joint='curve'); d.line(pts,fill=BLUE,width=17,joint='curve')
def pin(d,x,y):
    d.ellipse([x-30,y-30,x+30,y+30],fill=RED,outline='white',width=7)
def msgs(title_name):
    sc=Image.new('RGB',(SWc,SHc),'white'); d=ImageDraw.Draw(sc); status(d)
    d.ellipse([SWc/2-44,110,SWc/2+44,198],fill=(120,130,150)); d.text((SWc/2,154),title_name[0],font=F(800,44),fill='white',anchor='mm')
    d.text((SWc/2,232),title_name,font=F(600,28),fill=DK,anchor='mm')
    d.line([(0,272),(SWc,272)],fill=(225,225,230),width=2)
    return sc,d
def bubble(sc,d,y,lines,fill=(233,233,238),icon=None,mapk=None):
    x0,x1=30,SWc-80; h=34+len(lines)*46+(190 if mapk else 0)
    d.rounded_rectangle([x0,y,x1,y+h],radius=30,fill=fill)
    yy=y+18
    if mapk:
        mp=Image.open(BASE+'images/126.jpg').convert('RGB').crop(REG[mapk]).crop((0,0,265,150)).resize((x1-x0-24,176))
        mk=Image.new('L',mp.size,0); ImageDraw.Draw(mk).rounded_rectangle([0,0,mp.size[0]-1,mp.size[1]-1],radius=20,fill=255)
        sc.paste(mp,(x0+12,y+12),mk); yy=y+200
    tx=x0+26
    if icon: d.ellipse([x0+20,yy+4,x0+64,yy+48],fill=icon[0]); d.text((x0+42,yy+26),icon[1],font=SY(26),fill='white',anchor='mm'); tx=x0+80
    for i,l in enumerate(lines): d.text((tx,yy+8+i*46),l,font=F(700 if i==0 else 400,32),fill=DK,anchor='la')
    return y+h
