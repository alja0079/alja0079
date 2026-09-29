from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
Bd=lambda s: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',s)
Rg=lambda s: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',s)
W,H=1080,1920; OUT='scratchpad/ep4/'
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
# STEP 2
im,d=base(2,'Tap the yellow button','Bottom-right corner')
vy0,vy1=camera_screen(d); card(d,vy0); bx,by=ytext_btn(d,vy1,glow=True)
arrow(d,bx-360,by+10,bx-85,by+10)
label(d,bx-520,by+10,'TAP THIS',size=50)
im.save(OUT+'step2.png')
# STEP 3
im,d=base(3,'Press on the password','Drag the blue dots to fit')
vy0,vy1=camera_screen(d); _,(tx,ty)=card(d,vy0,sel=True); ytext_btn(d,vy1)
d.ellipse([tx+95,ty+5,tx+155,ty+65],outline='white',width=7)
arrow(d,tx-60,ty+300,tx+95,ty+80)
label(d,tx-120,ty+330,'PRESS HERE',size=46)
im.save(OUT+'step3.png')
# STEP 4 (menu)
im,d=base(4,'Tap "Copy"','Or "Copy All" for everything')
vy0,vy1=camera_screen(d); (x0,y0,x1,y1),(tx,ty)=card(d,vy0,sel=True); ytext_btn(d,vy1)
my=ty-150; mx0=x0+10
d.rounded_rectangle([mx0,my-55,mx0+620,my+55],radius=22,fill=(40,40,44))
items=[('Copy',150),('Select All',230),('Look Up',210)]; cx=mx0
for i,(t,w) in enumerate(items):
    d.text((cx+w/2,my),t,font=Rg(36),fill='white',anchor='mm'); cx+=w
    if i<2: d.line([(cx,my-40),(cx,my+40)],fill=(80,80,85),width=3)
d.ellipse([mx0-5,my-65,mx0+155,my+65],outline=RED,width=9)
arrow(d,mx0+15,my+400,mx0+40,my+72,w=14)
label(d,mx0+200,my+450,'TAP COPY',size=48)
# copy all pill
ca_y=vy1-60; d.rounded_rectangle([SX+40,ca_y-45,SX+310,ca_y+45],radius=45,fill=(40,40,44)); d.text((SX+175,ca_y),'Copy All',font=Rg(34),fill='white',anchor='mm')
im.save(OUT+'step4.png')
# STEP 5 paste
im,d=base(5,'Paste it anywhere','Wi-Fi, Notes, Messages')
d.rounded_rectangle([SX,SY,SX+SW,SY+SH],radius=70,fill=(242,242,247))
d.text((SX+SW/2,SY+120),'Enter Password',font=Bd(44),fill=(20,20,30),anchor='mm')
d.text((SX+SW/2,SY+180),'for "CafeGuest"',font=Rg(34),fill=(110,110,120),anchor='mm')
fy=SY+300; d.rounded_rectangle([SX+50,fy,SX+SW-50,fy+110],radius=18,fill='white',outline=(200,200,210),width=3)
d.text((SX+80,fy+55),'Sunny#2026',font=Rg(46),fill=(20,20,30),anchor='lm')
d.rounded_rectangle([SX+80,fy-95,SX+260,fy-15],radius=16,fill=(40,40,44)); d.text((SX+170,fy-55),'Paste',font=Rg(34),fill='white',anchor='mm')
d.ellipse([SX+SW/2-80,fy+220,SX+SW/2+80,fy+380],fill=(46,204,113)); d.text((SX+SW/2,fy+300),'✓',font=Bd(100),fill='white',anchor='mm')
d.text((SX+SW/2,fy+450),'No typing!',font=Bd(60),fill=(46,160,90),anchor='mm')
im.save(OUT+'step5.png')
# contact sheet
sheet=Image.new('RGB',(5*324+6*20,576+40),(0,0,0))
for i in range(5): sheet.paste(Image.open(OUT+f'step{i+1}.png').resize((324,576)),(20+i*344,20))
sheet.save(OUT+'sheet.jpg')
