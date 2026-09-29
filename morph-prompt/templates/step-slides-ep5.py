from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
Bd=lambda s: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',s)
Rg=lambda s: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',s)
W,H=1080,1920; OUT='scratchpad/ep5/'
YEL=(255,214,10); RED=(255,70,70); BLUE=(10,132,255); NAVY=(14,18,40)
# phone geometry
PX,PY,PW,PH=150,540,780,1300
SX,SY,SW,SH=PX+24,PY+24,PW-48,PH-48
def base(step,title,sub):
    im=Image.new('RGB',(W,H),NAVY); d=ImageDraw.Draw(im)
    for y in range(H):
        t=y/H; d.line([(0,y),(W,y)],fill=(int(14+20*t),int(18+24*t),int(40+50*t)))
    d.rounded_rectangle([W/2-150,215,W/2+150,285],radius=35,fill=YEL)
    d.text((W/2,250),f'STEP {step}',font=Bd(44),fill=NAVY,anchor='mm')
    f=Bd(74)
    while f.getlength(title)>W-180: f=Bd(f.size-2)
    d.text((W/2,330),title,font=f,fill='white',anchor='ma',stroke_width=4,stroke_fill='black')
    d.text((W/2,440),sub,font=Rg(40),fill=(200,210,235),anchor='ma')
    d.rounded_rectangle([PX,PY,PX+PW,PY+PH],radius=90,fill=(18,18,20),outline=(110,110,120),width=6)
    return im,d
def camera_screen(d):
    vy0,vy1=SY+110,SY+SH-290
    LIGHT=(242,242,247)
    d.rounded_rectangle([SX,SY,SX+SW,SY+SH],radius=70,fill=LIGHT)
    d.line([(SX+30,vy1),(SX+SW-30,vy1)],fill=(215,215,222),width=3)
    d.text((SX+SW/2,vy1+45),'PHOTO',font=Bd(34),fill=(214,160,0),anchor='mm')
    d.text((SX+SW/2-190,vy1+45),'VIDEO',font=Rg(30),fill=(120,120,130),anchor='mm')
    d.text((SX+SW/2+200,vy1+45),'PORTRAIT',font=Rg(30),fill=(120,120,130),anchor='mm')
    cx,cy=SX+SW/2,vy1+185
    d.ellipse([cx-78,cy-78,cx+78,cy+78],outline=(60,60,67),width=8); d.ellipse([cx-62,cy-62,cx+62,cy+62],fill='white',outline=(200,200,210),width=2)
    return vy0,vy1
def card(d,vy0,sel=None):
    x0,y0,x1,y1=SX+60,vy0+70,SX+SW-60,vy0+470
    d.rounded_rectangle([x0+10,y0+14,x1+10,y1+14],radius=24,fill=(215,215,225))
    d.rounded_rectangle([x0,y0,x1,y1],radius=24,fill=(255,255,255),outline=(225,225,230),width=2)
    d.text(((x0+x1)/2,y0+50),'GUEST Wi-Fi',font=Bd(46),fill=(40,40,40),anchor='ma')
    d.text(((x0+x1)/2,y0+130),'Network: CafeGuest',font=Rg(38),fill=(40,40,40),anchor='ma')
    d.text(((x0+x1)/2,y0+210),'Password:',font=Rg(38),fill=(40,40,40),anchor='ma')
    pw='Sunny#2026'; f=Bd(62); tx=(x0+x1)/2; ty=y0+285
    if sel:
        w=f.getlength(pw); bx0,bx1=tx-w/2-8,tx+w/2+8
        d.rectangle([bx0,ty-6,bx1,ty+76],fill=(150,190,255))
        d.line([(bx0,ty-6),(bx0,ty+76)],fill=BLUE,width=6); d.line([(bx1,ty-6),(bx1,ty+76)],fill=BLUE,width=6)
        d.ellipse([bx0-16,ty-36,bx0+16,ty-4],fill=BLUE); d.ellipse([bx1-16,ty+74,bx1+16,ty+106],fill=BLUE)
    d.text((tx,ty),pw,font=f,fill=(40,40,40),anchor='ma')
    return (x0,y0,x1,y1),(tx,ty+35)
def ytext_btn(d,vy1,glow=False):
    bx,by=SX+SW-150,vy1-150
    if glow: d.ellipse([bx-26,by-26,bx+126,by+126],outline=RED,width=10)
    d.ellipse([bx,by,bx+100,by+100],fill=YEL)
    # icon: corner brackets + lines
    c=(0,0,0); m=24
    for (ax,ay,sx,sy) in [(bx+m,by+m,1,1),(bx+100-m,by+m,-1,1),(bx+m,by+100-m,1,-1),(bx+100-m,by+100-m,-1,-1)]:
        d.line([(ax,ay),(ax+14*sx,ay)],fill=c,width=5); d.line([(ax,ay),(ax,ay+14*sy)],fill=c,width=5)
    for i,l in enumerate([36,28,36]): d.line([(bx+50-l/2,by+38+i*12),(bx+50+l/2,by+38+i*12)],fill=c,width=5)
    return bx+50,by+50
def arrow(d,x0,y0,x1,y1,col=RED,w=16):
    d.line([(x0,y0),(x1,y1)],fill=col,width=w)
    a=math.atan2(y1-y0,x1-x0); L=55
    d.polygon([(x1,y1),(x1-L*math.cos(a-0.45),y1-L*math.sin(a-0.45)),(x1-L*math.cos(a+0.45),y1-L*math.sin(a+0.45))],fill=col)
def label(d,x,y,txt,col=RED,anchor='mm',size=44):
    f=Bd(size); w=f.getlength(txt)
    if anchor=='mm': x0=x-w/2-28
    elif anchor=='lm': x0=x
    else: x0=x-w-56
    d.rounded_rectangle([x0,y-44,x0+w+56,y+44],radius=44,fill=col)
    d.text((x0+28+w/2,y),txt,font=f,fill='white',anchor='mm')
def finger(d,x,y):
    d.ellipse([x-60,y-60,x+60,y+60],outline='white',width=8); d.ellipse([x-38,y-38,x+38,y+38],fill=(255,255,255))
# STEP 1
im,d=base(1,'Open your Camera','Point it at any text')
vy0,vy1=camera_screen(d); (x0,y0,x1,y1),_=card(d,vy0)
for (ax,ay,sx,sy) in [(x0-20,y0-20,1,1),(x1+20,y0-20,-1,1),(x0-20,y1+20,1,-1),(x1+20,y1+20,-1,-1)]:
    d.line([(ax,ay),(ax+70*sx,ay)],fill=YEL,width=12); d.line([(ax,ay),(ax,ay+70*sy)],fill=YEL,width=12)
label(d,W/2,y1+120,'Sign, menu, box, receipt…',col=(60,70,110),size=36)
im.save(OUT+'step1.png')
LIGHT=(242,242,247); DK=(20,20,30); GR=(120,120,130)
def screen(title=None):
    d.rounded_rectangle([SX,SY,SX+SW,SY+SH],radius=70,fill=LIGHT)
    if title: d.text((SX+50,SY+110),title,font=Bd(52),fill=DK,anchor='lm')
def row(y,txt,icon=None,sub=None,chev=True,hl=False):
    x0,x1=SX+40,SX+SW-40
    d.rounded_rectangle([x0,y,x1,y+110],radius=22,fill='white',outline=(225,225,230),width=2)
    tx=x0+40
    if icon: d.rounded_rectangle([x0+30,y+27,x0+86,y+83],radius=14,fill=icon); tx=x0+110
    d.text((tx,y+(38 if sub else 55)),txt,font=Rg(38),fill=DK,anchor='lm')
    if sub: d.text((tx,y+80),sub,font=Rg(28),fill=GR,anchor='lm')
    if chev: d.text((x1-40,y+55),'›',font=Rg(60),fill=(190,190,200),anchor='mm')
    if hl: d.rounded_rectangle([x0-12,y-12,x1+12,y+122],radius=30,outline=RED,width=9)
    return y+55
# STEP 1 search
im,d=base(1,'Search "Safety Check"','Open Settings, type it at the top')
screen('Settings')
d.rounded_rectangle([SX+40,SY+180,SX+SW-40,SY+270],radius=22,fill=(226,226,232))
d.ellipse([SX+70,SY+208,SX+98,SY+236],outline=GR,width=4); d.line([(SX+95,SY+233),(SX+108,SY+246)],fill=GR,width=5)
d.text((SX+125,SY+225),'Safety Check',font=Rg(40),fill=DK,anchor='lm')
d.rounded_rectangle([SX+40,SY+176,SX+SW-40,SY+274],radius=26,outline=RED,width=8)
y=row(SY+330,'Safety Check',icon=(52,120,246),sub='Privacy & Security',hl=True)
arrow(d,W/2+40,SY+700,W/2-20,y+75); label(d,W/2+60,SY+760,'TAP THIS',size=50)
im.save(OUT+'step1.png')
# STEP 2 manage
im,d=base(2,'Tap "Manage Sharing"','Red Quick Exit hides it fast')
screen()
d.rounded_rectangle([SX+SW-230,SY+60,SX+SW-40,SY+130],radius=35,fill=(255,59,48)); d.text((SX+SW-135,SY+95),'Quick Exit',font=Bd(30),fill='white',anchor='mm')
d.text((SX+SW/2,SY+260),'Safety Check',font=Bd(56),fill=DK,anchor='mm')
d.text((SX+SW/2,SY+330),'See who has access to',font=Rg(34),fill=GR,anchor='mm')
d.text((SX+SW/2,SY+375),'your location and photos',font=Rg(34),fill=GR,anchor='mm')
y=row(SY+470,'Emergency Reset',chev=True)
y=row(SY+620,'Manage Sharing & Access',hl=True)
arrow(d,W/2,SY+1000,W/2-40,y+80); label(d,W/2,SY+1060,'TAP THIS',size=50)
im.save(OUT+'step2.png')
# STEP 3 people list
im,d=base(3,'See who can see you','Remove anyone you don\'t trust')
screen('Sharing With')
people=[('Sam','Location · Photos',(255,149,0)),('Mom','Location',(52,199,89)),('Old Roommate','Location · Notes',(175,82,222))]
for i,(n,s,c) in enumerate(people):
    yy=SY+200+i*150
    d.rounded_rectangle([SX+40,yy,SX+SW-40,yy+125],radius=22,fill='white',outline=(225,225,230),width=2)
    d.ellipse([SX+70,yy+22,SX+150,yy+102],fill=c); d.text((SX+110,yy+62),n[0],font=Bd(40),fill='white',anchor='mm')
    d.text((SX+175,yy+42),n,font=Rg(38),fill=DK,anchor='lm'); d.text((SX+175,yy+88),s,font=Rg(28),fill=GR,anchor='lm')
    d.ellipse([SX+SW-110,yy+37,SX+SW-60,yy+87],outline=(190,190,200),width=4)
    if i==2:
        d.ellipse([SX+SW-110,yy+37,SX+SW-60,yy+87],fill=BLUE); d.text((SX+SW-85,yy+62),'✓',font=Bd(30),fill='white',anchor='mm')
        d.rounded_rectangle([SX+28,yy-12,SX+SW-28,yy+137],radius=30,outline=RED,width=9)
by=SY+SH-230
d.rounded_rectangle([SX+60,by,SX+SW-60,by+110],radius=26,fill=BLUE); d.text((SX+SW/2,by+55),'Stop Sharing',font=Bd(42),fill='white',anchor='mm')
arrow(d,W/2,by-170,W/2,by-15); label(d,W/2,by-230,'THEN TAP',size=46)
im.save(OUT+'step3.png')
# STEP 4 it goes further
im,d=base(4,'It goes even further','Checks apps, devices and account security')
screen('Safety Check')
items=[('People','Who you share with',(255,149,0)),('Apps','Location, camera, photos',(10,132,255)),('Devices','Phones and iPads signed in',(52,199,89)),('Account Security','Passcode and Apple Account',(175,82,222))]
for i,(n,s,c) in enumerate(items):
    yy=SY+200+i*170
    d.rounded_rectangle([SX+40,yy,SX+SW-40,yy+140],radius=22,fill='white',outline=(225,225,230),width=2)
    d.rounded_rectangle([SX+70,yy+35,SX+140,yy+105],radius=16,fill=c)
    d.text((SX+170,yy+50),n,font=Bd(40),fill=DK,anchor='lm'); d.text((SX+170,yy+98),s,font=Rg(30),fill=GR,anchor='lm')
    d.ellipse([SX+SW-120,yy+42,SX+SW-64,yy+98],fill=(52,199,89)); d.text((SX+SW-92,yy+70),'✓',font=Bd(34),fill='white',anchor='mm')
d.text((SX+SW/2,SY+SH-170),'All in one place',font=Bd(50),fill=(46,160,90),anchor='mm')
im.save(OUT+'step4.png')
