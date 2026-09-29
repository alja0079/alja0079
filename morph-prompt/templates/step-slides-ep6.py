from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
Bd=lambda s: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',s)
Rg=lambda s: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',s)
W,H=1080,1920; OUT='scratchpad/ep6/'
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
LIGHT=(242,242,247); DK=(20,20,30); GR=(120,120,130); GRN=(52,199,89)
def screen(title=None):
    d.rounded_rectangle([SX,SY,SX+SW,SY+SH],radius=70,fill=LIGHT)
    if title: d.text((SX+50,SY+110),title,font=Bd(52),fill=DK,anchor='lm')
def rec_icon(cx,cy,r=48,glow=False):
    if glow: d.ellipse([cx-r-22,cy-r-22,cx+r+22,cy+r+22],outline=RED,width=10)
    d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=(225,225,232))
    for i,h in enumerate([18,34,50,34,18]):
        x=cx-28+i*14; d.line([(x,cy-h/2),(x,cy+h/2)],fill=DK,width=7)
def callscreen(buttons=True):
    screen()
    d.text((SX+SW/2,SY+440),'Support Line',font=Bd(56),fill=DK,anchor='mm')
    d.text((SX+SW/2,SY+510),'04:12',font=Rg(40),fill=GR,anchor='mm')
    labels=['speaker','video','mute','add','end','keypad'] if buttons else ['','','','','end','']
    for i,l in enumerate(labels):
        if not l: continue
        cx=SX+SW/2+(i%3-1)*210; cy=SY+760+(i//3)*230
        col=(255,59,48) if l=='end' else (225,225,232)
        d.ellipse([cx-75,cy-75,cx+75,cy+75],fill=col)
        d.text((cx,cy+110),l,font=Rg(30),fill=GR,anchor='mm')
    d.text((SX+SW/2+0,SY+760+230),'✆',font=Bd(60),fill='white',anchor='mm')
# STEP 1
im,d=base(1,'Tap the record button','Top-left of the call screen')
callscreen(); rec_icon(SX+110,SY+110,glow=True)
arrow(d,SX+330,SY+290,SX+175,SY+165); label(d,SX+430,SY+320,'TAP THIS',size=50)
im.save(OUT+'step1.png')
# STEP 2
im,d=base(2,'Everyone is told','Only record with permission')
callscreen(buttons=False)
d.rounded_rectangle([SX+40,SY+60,SX+SW-40,SY+170],radius=55,fill=(255,59,48))
d.ellipse([SX+80,SY+95,SX+120,SY+135],fill='white')
d.text((SX+150,SY+115),'Recording  00:08',font=Bd(40),fill='white',anchor='lm')
by=SY+580; d.rounded_rectangle([SX+60,by,SX+SW-60,by+150],radius=30,fill='white',outline=(210,210,220),width=3)
d.text((SX+SW/2,by+75),'"This call will be recorded."',font=Bd(38),fill=DK,anchor='mm')
label(d,W/2,by+240,'BOTH PEOPLE HEAR IT',size=44)
im.save(OUT+'step2.png')
# STEP 3
im,d=base(3,'After the call, open Notes','Look for "Call Recordings"')
screen('Folders')
rows=['All iCloud','Notes','Call Recordings','Recipes']
for i,r in enumerate(rows):
    yy=SY+200+i*140
    d.rounded_rectangle([SX+40,yy,SX+SW-40,yy+115],radius=22,fill='white',outline=(225,225,230),width=2)
    d.rounded_rectangle([SX+75,yy+32,SX+125,yy+82],radius=10,fill=(255,204,0))
    d.text((SX+155,yy+57),r,font=Rg(40),fill=DK,anchor='lm'); d.text((SX+SW-80,yy+57),'›',font=Rg(60),fill=(190,190,200),anchor='mm')
    if r=='Call Recordings':
        d.rounded_rectangle([SX+28,yy-12,SX+SW-28,yy+127],radius=30,outline=RED,width=9); ty=yy
arrow(d,W/2,ty+450,W/2,ty+150); label(d,W/2,ty+510,'TAP THIS',size=50)
im.save(OUT+'step3.png')
# STEP 4 payoff
im,d=base(4,'Your call, written out!','Search it, copy it, keep it')
screen()
d.text((SX+50,SY+100),'Support Line call',font=Bd(46),fill=DK,anchor='lm')
py=SY+160; d.rounded_rectangle([SX+40,py,SX+SW-40,py+110],radius=24,fill='white',outline=(225,225,230),width=2)
d.polygon([(SX+85,py+30),(SX+85,py+80),(SX+125,py+55)],fill=BLUE)
import random; random.seed(3)
for i in range(34):
    x=SX+160+i*14; h=random.randint(12,60); d.line([(x,py+55-h/2),(x,py+55+h/2)],fill=(160,170,190),width=6)
lines=[('Agent','Your refund of $84 is approved.'),('You','When will it arrive?'),('Agent','In 5 business days.'),('You','What is my case number?'),('Agent','It is 44721.')]
yy=py+160
for who,t in lines:
    d.text((SX+60,yy),who,font=Bd(32),fill=BLUE if who=='Agent' else (46,160,90),anchor='la')
    d.text((SX+60,yy+42),t,font=Rg(36),fill=DK,anchor='la'); yy+=120
d.rounded_rectangle([SX+40,yy+10,SX+SW-40,yy+130],radius=24,fill=(255,249,219),outline=(240,210,90),width=3)
d.text((SX+70,yy+42),'Summary',font=Bd(30),fill=(150,110,0),anchor='la')
d.text((SX+70,yy+82),'$84 refund, 5 days, case 44721',font=Rg(32),fill=DK,anchor='la')
im.save(OUT+'step4.png')
