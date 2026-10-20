"""Build the lab PDF. Requires reportlab, pypdf, and system DejaVu fonts."""
from pathlib import Path
from math import ceil
from html import escape
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/LPC1768_Beginner_Lab_Guide.pdf'
FONTDIR = Path('/usr/share/fonts/truetype/dejavu')
for name, file in [('Sans','DejaVuSans.ttf'),('Bold','DejaVuSans-Bold.ttf'),('Mono','DejaVuSansMono.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONTDIR / file)))
pdfmetrics.registerFontFamily('Sans', normal='Sans', bold='Bold', italic='Sans', boldItalic='Bold')
W, H = 595.276, 841.89
M, CW = 44, W - 88
NAVY = colors.HexColor('#133449')
TEAL = colors.HexColor('#006D77')
INK = colors.HexColor('#233544')
MUTED = colors.HexColor('#526574')
PALE = colors.HexColor('#EDF5F5')
AMBER = colors.HexColor('#FFF1D9')
LINE = colors.HexColor('#CCD8DE')
RED = colors.HexColor('#A33028')
BODY = ParagraphStyle('body', fontName='Sans', fontSize=10, leading=14.5, textColor=INK)
CELL = ParagraphStyle('cell', parent=BODY, fontSize=9.1, leading=12.5)
SMALL = ParagraphStyle('small', parent=BODY, fontSize=8.6, leading=12)
HEAD = ParagraphStyle('head', parent=BODY, fontName='Bold', fontSize=14, leading=18, textColor=NAVY)
WHITE = ParagraphStyle('white', parent=CELL, fontName='Bold', textColor=colors.white)
TITLE = ParagraphStyle('title', parent=BODY, fontName='Bold', fontSize=23, leading=29, textColor=NAVY)
source = (ROOT / 'main.c').read_text()
code_lines = source.splitlines()
CODE_PER_PAGE = 50
TOTAL = 16 + ceil(len(code_lines) / CODE_PER_PAGE)
buffer = BytesIO()
c = canvas.Canvas(buffer, pagesize=(W,H), pageCompression=1)
c.setTitle('LPC1768 + HC-SR04: Beginner Lab Guide')
c.setAuthor('Ultrasonic Collision Warning System project')
c.setSubject('Beginner wiring, electrical checks, Keil, Flash Magic, expected output, and complete firmware')
y = 0
page = 0


def p(text, style=BODY, after=9, x=M, width=CW):
    global y
    para = Paragraph(text, style)
    _, h = para.wrap(width, H)
    assert y - h >= 57, f'Page {page} paragraph overflow: {text[:60]} at {y-h}'
    para.drawOn(c,x,y-h)
    y -= h + after


def start(kicker, title, subtitle=None):
    global y, page
    page += 1
    c.bookmarkPage(f'page-{page}')
    c.addOutlineEntry(f'{page}. {kicker.title()}', f'page-{page}', level=0)
    c.setFillColor(NAVY); c.rect(0,H-27,W,27,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont('Bold',8)
    c.drawString(M,H-18,'LPC1768 + HC-SR04  /  BEGINNER LAB GUIDE')
    c.setFillColor(TEAL); c.setFont('Bold',9)
    c.drawString(M,H-57,kicker.upper())
    y = H-71
    p(title, TITLE, after=10)
    if subtitle: p(subtitle, SMALL, after=16)


def finish():
    assert y >= 45, f'Page {page} content crossed footer: {y}'
    c.setStrokeColor(LINE); c.line(M,43,W-M,43)
    c.setFillColor(MUTED); c.setFont('Sans',8)
    c.drawString(M,29,'ALS-SDA-ARMCTXM3-01 | Bench prototype | Follow pages in order')
    c.drawRightString(W-M,29,f'{page} / {TOTAL}')
    c.showPage()


def h(text):
    global y
    y -= 3
    p(text, HEAD, after=7)


def steps(items):
    for i, text in enumerate(items,1):
        p(f'<b>{i}.</b> {text}', after=8)


def note(title, text, warning=False):
    global y
    para=Paragraph(f'<b>{title}</b><br/>{text}', BODY)
    _,hh=para.wrap(CW-24,H)
    hh += 22
    assert y-hh >= 57, f'Note overflow p{page}'
    c.setFillColor(AMBER if warning else PALE)
    c.roundRect(M,y-hh,CW,hh,5,fill=1,stroke=0)
    para.drawOn(c,M+12,y-hh+11)
    y -= hh+12


def table(headers, rows, widths=None, font=CELL):
    global y
    widths = widths or [CW/len(headers)]*len(headers)
    data=[[Paragraph(escape(str(v)),WHITE) for v in headers]]
    data += [[Paragraph(str(v),font) for v in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),NAVY),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#F1F5F7'),colors.white]),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
        ('LINEBELOW',(0,-1),(-1,-1),.6,LINE)
    ]))
    _,hh=t.wrap(CW,H)
    assert y-hh >= 57, f'Table overflow p{page} bottom {y-hh}'
    t.drawOn(c,M,y-hh)
    y -= hh+12


def diagram(height, draw):
    global y
    assert y-height >= 57
    c.setFillColor(colors.HexColor('#F6F9FA')); c.setStrokeColor(LINE)
    c.roundRect(M,y-height,CW,height,6,fill=1,stroke=1)
    c.saveState(); c.translate(M,y-height); draw(); c.restoreState()
    y -= height+12


def label(x,y,text,size=9,bold=False,color=INK):
    c.setFont('Bold' if bold else 'Sans',size); c.setFillColor(color)
    c.drawString(x,y,text)


def box(x,y,w,hh,title,sub=None):
    c.setFillColor(colors.white); c.setStrokeColor(TEAL)
    c.roundRect(x,y,w,hh,5,fill=1,stroke=1)
    label(x+10,y+hh-20,title,10,True)
    if sub: label(x+10,y+12,sub,8)


def wire(points,color=TEAL,width=1.7):
    c.setStrokeColor(color); c.setLineWidth(width)
    path=c.beginPath(); path.moveTo(*points[0])
    for pt in points[1:]: path.lineTo(*pt)
    c.drawPath(path)


def dot(x,y,color=TEAL):
    c.setFillColor(color);c.circle(x,y,3,fill=1,stroke=0)


# 1
start('Read first', 'From loose parts\nto a working lab demo'.replace('\n','<br/>'), 'One guide for the exact LPC1768 trainer, three-resistor echo divider, LCD, and buzzer in your supplied references.')
p('You do <b>not</b> paste code into the board. You save <b>main.c</b> in a Keil project, build a <b>.hex</b> file, send that file to the board with <b>Flash Magic</b>, then put the board in <b>RUN</b> mode.')
def overview():
    for xx,title,sub in [(16,'CONNECT','Power OFF'),(143,'BUILD','Keil on PC'),(270,'FLASH','Send HEX'),(397,'RUN','LCD + buzzer')]:
        box(xx,30,96,66,title,sub)
    for xx in [112,239,366]: wire([(xx+2,63),(xx+25,63)]); label(xx+15,68,'>',10,True)
    label(16,112,'The four stages you will complete',11,True)
diagram(143,overview)
note('Two checks need the instructor', 'Have lab staff identify the physical CN6 pin numbers and confirm the supply / divider pulse voltage. The supplied documents do not establish the physical pin-1 location on your particular board.', True)
table(['Pages','What you do'],[
('2-3','Learn the parts and locate the labelled board connectors.'),
('4-6','Build the divider and connect every sensor, LCD, and buzzer wire.'),
('7-9','Set jumpers, connect the PC, and build the Keil project.'),
('10-12','Check supplies, program the board, and verify ECHO before connecting P2.1.'),
('13-16','Get output, test states, solve common problems, and use the final checklist.'),
(f'17-{TOTAL}','Complete main.c listing; an exact main.c copy is also embedded in the PDF.')],[70,CW-70])
p('Use this only as a bench prototype. Neither this firmware nor these exact connections have been tested on your physical kit. Do not use this project for real vehicle collision protection.',SMALL)
finish()

# 2
start('Step 01 / Prepare', 'Put these items on the bench', 'Do not turn on the kit yet. You will work with power disconnected through the wiring steps.')
table(['Item','What to look for / quantity'],[
('Trainer board','ALS-SDA-ARMCTXM3-01, LPC1768 piggyback already installed, 12 MHz crystal.'),
('Sensor','One HC-SR04 with VCC, TRIG, ECHO, GND printed beside its pins.'),
('Breadboard','One conventional board with numbered rows and side power rails.'),
('Resistors','Two 1 kΩ (R1/R2) and one 2.2 kΩ (R3). Confirm values with an unpowered resistance test.'),
('Jumper wires','At least eight jumpers plus spares: seven mandatory leads on page 6, with extras for rail bridging if needed.'),
('Ribbon cables','Two straight-through 10-pin FRC cables, usually supplied with the kit.'),
('PC and software','Lab Windows PC with Keil µVision, LPC1768 device support, Flash Magic, and USB-serial driver.'),
('Serial and power','Lab USB-to-serial adapter, grey RS232 cable, and separate lab 5 V power cable.'),
('Test equipment','Multimeter; instructor-operated oscilloscope or suitable analyzer for the ECHO high pulse.'),
('If CN6 is recessed','Compatible 26-pin IDC breakout. Do not wedge loose wires into contacts that do not fit.')],[125,CW-125])
h('Words you will see')
table(['Word','Plain meaning'],[
('GPIO / P2.0','A microcontroller signal. P2.0 means port 2, bit 0; it is not a connector number.'),
('CN6 pin 1','A physical contact on the connector labelled CN6 on the board.'),
('GND / VCC','Common electrical reference / sensor positive supply.'),
('Jumper short / open','Plastic cap joins the specified pins / the pins are not joined.'),
('FRC ribbon / HEX','Flat cable with multi-pin ends / compiled program file that Flash Magic sends to the board.')],[125,CW-125])
finish()

# 3
start('Step 02 / Locate', 'Find the labels before the pins', 'This diagram is a connection map. It is not a photo, a board placement drawing, or a physical pin-orientation guide.')
def boardmap():
    box(15,19,235,174,'ALS LPC1768 BOARD','Find these exact printed labels')
    for yy,txt in [(158,'CN6: sensor / divider'),(135,'CND: LCD GPIO'),(112,'CNAD: LCD block'),(89,'CNA: buzzer GPIO'),(66,'CNA5: buzzer block')]: label(29,yy,txt,10)
    box(275,119,215,65,'CN9: SERIAL','Left female DB9 in supplied notes')
    box(275,30,215,65,'CN8: POWER','Right male DB9 in supplied notes')
    wire([(250,151),(275,151)]); wire([(250,62),(275,62)])
diagram(211,boardmap)
table(['Locate','How you identify it'],[
('CN6','26-pin NIFC boxed header. Do not confuse with CND (10-pin), CN5 (JTAG), or CN7 (trace).'),
('CN6 pins 1 / 2 / 25 / 26','Ask staff to confirm physical numbering from the kit drawing / pin-1 marker. Mark nearby tape.'),
('CND + CNAD','Two separate 10-pin connectors; the LCD ribbon will join them.'),
('CNA + CNA5','Two separate 10-pin connectors; the buzzer ribbon will join them. CNA1 is the LED block.'),
('JP1, JP2, JP3, JP5, JP6, JP16','Find the small jumper caps by their printed labels. Do not move unlabelled caps.'),
('SW21 / SW1 / POT3','Two-position programming DIP switch / reset button / LCD contrast adjustment.')],[127,CW-127])
note('Do not guess pin orientation', 'A generic 2 x 13 drawing cannot tell you which end is pin 1 on this board. If you cannot securely identify and reach pins 1, 2, 25, 26, stop and ask the instructor. Use connector labels, not left/right alone.',True)
finish()

# 4
start('Step 03 / Breadboard', 'Understand the connected holes', 'All component placement below uses the A-E half of the breadboard. Rows 10, 15, and 20 are examples you can label with tape.')
def breadlearn():
    for j,l in enumerate('ABCDE'): label(60+j*29,171,l,10,True)
    for j,l in enumerate('FGHIJ'): label(292+j*29,171,l,10,True)
    for yy,num in [(137,10),(94,15),(51,20)]:
        label(20,yy-3,str(num),10,True)
        for startx in [64,296]:
            c.setStrokeColor(LINE);c.setLineWidth(8);c.line(startx,yy,startx+116,yy)
            for j in range(5):
                c.setFillColor(colors.white);c.setStrokeColor(MUTED);c.circle(startx+j*29,yy,4,fill=1,stroke=1)
    label(211,110,'gap',9,True)
    label(54,18,'Same row: A-B-C-D-E connected',9,True)
    label(291,18,'F-J is a separate strip',9,True)
diagram(195,breadlearn)
steps([
'Find the row numbers and letters on your breadboard. Check continuity with the kit unpowered if the layout differs.',
'Use rows <b>10, 15, and 20 on A-E</b>. Different numbered rows must be electrically separate.',
'Find the side rails. Mark the intended rail <b>+5 V</b> and the other <b>GND</b>. Check for breaks halfway along a rail. Use the same continuous section for this circuit.',
'Confirm two resistors measure 1 kΩ and one measures 2.2 kΩ. Resistors have no positive/negative orientation.',
'If the sensor is plugged directly into holes, place each of its four pins in a different numbered row. For this guide, connecting its labelled pins with wires is easier.'
])
note('Common beginner mistake', 'A resistor between A10 and E10 has both ends on the same electrical strip, so it is bypassed. R1 must go between rows 10 and 15, not two holes in row 10.',True)
finish()

# 5
start('Step 04 / Divider', 'Install all three resistors', 'Board OFF and power cable unplugged. This circuit reduces the sensor ECHO pulse before it reaches the microcontroller.')
def divider():
    label(16,231,'Circuit (logical)',10,True)
    label(279,231,'Exact hole placement: A-E',10,True)
    x=67
    label(17,208,'ECHO',9,True)
    wire([(x,214),(x,196)])
    c.setFillColor(colors.HexColor('#F2DFC0'));c.setStrokeColor(MUTED)
    c.rect(x-18,169,36,27,fill=1,stroke=1);label(x-14,179,'R1',9,True)
    label(110,179,'1 kΩ',9)
    wire([(x,169),(x,148)]);dot(x,148)
    label(110,145,'A: 3.81 V',9,True,RED)
    wire([(x,148),(x,127)])
    c.setFillColor(colors.HexColor('#F2DFC0'));c.setStrokeColor(MUTED)
    c.rect(x-18,100,36,27,fill=1,stroke=1);label(x-14,110,'R2',9,True)
    label(110,110,'1 kΩ',9)
    wire([(x,100),(x,79)]);dot(x,79)
    wire([(x,79),(204,79)]);label(110,89,'B: 2.62 V',9,True,TEAL)
    label(136,65,'To CN6 pin 2',9,True)
    wire([(x,79),(x,58)])
    c.setFillColor(colors.HexColor('#F2DFC0'));c.setStrokeColor(MUTED)
    c.rect(x-18,31,36,27,fill=1,stroke=1);label(x-14,41,'R3',9,True)
    label(110,41,'2.2 kΩ',9)
    wire([(x,31),(x,16),(100,16)]);label(110,13,'GND',9,True)
    c.setStrokeColor(LINE);c.line(254,14,254,241)
    for j,l in enumerate('ABCDE'): label(297+j*33,205,l,9,True)
    for yy,num in [(190,10),(125,15),(60,20)]:
        label(270,yy-3,str(num),9,True)
        c.setStrokeColor(LINE);c.setLineWidth(7);c.line(300,yy,432,yy)
        for j in range(5):
            c.setFillColor(colors.white);c.setStrokeColor(MUTED);c.setLineWidth(1)
            c.circle(300+j*33,yy,3.4,fill=1,stroke=1)
    def rvertical(xx,top,bot,txt,labelx):
        wire([(xx,top),(xx,bot)],TEAL,1.5)
        c.setFillColor(colors.HexColor('#F2DFC0'));c.setStrokeColor(MUTED)
        c.rect(xx-5,(top+bot)/2-13,10,26,fill=1,stroke=1)
        label(labelx,(top+bot)/2-3,txt,8,True)
    rvertical(300,190,125,'R1',313)
    rvertical(333,125,60,'R2',346)
    wire([(366,60),(366,17),(473,17)])
    c.setFillColor(colors.HexColor('#F2DFC0'));c.setStrokeColor(MUTED)
    c.rect(361,25,10,24,fill=1,stroke=1)
    label(380,31,'R3 2.2k -> GND',8,True)
    wire([(333,190),(333,197),(474,197)])
    label(375,218,'Sensor ECHO',8,True)
    wire([(399,60),(484,60)])
    label(399,73,'D20 -> CN6 pin 2',8,True,TEAL)
diagram(253,divider)
table(['Place','Exact two endpoints','What it does'],[
('R1 = 1 kΩ','A10 to A15','ECHO input to Node A'),
('R2 = 1 kΩ','B15 to B20','Node A to Node B'),
('R3 = 2.2 kΩ','C20 to the GND rail','Node B to ground')],[85,175,CW-260])
p('The A/B/C letters simply select different holes on the same strip. Row 15 joins A15 to B15. Row 20 joins B20, C20, and D20.')
note('The only ECHO output for the MCU is Node B', 'The future P2.1 lead must come from <b>D20 / row 20</b>. Do not use row 15 (Node A) or the sensor ECHO pin directly. At 5 V input, Node B = 5 x 2.2 / 4.2 = about 2.62 V.',True)
finish()

# 6
start('Step 05 / All sensor wires', 'Connect the sensor and rails', 'Keep power disconnected. Prepare W1-W7 below; W8 is an optional extension. Two ends deliberately remain disconnected until the electrical checks.')
table(['Wire','From','To','Initial state'],[
('W1','CN6 pin 26','Breadboard GND rail','Connect'),
('W2','HC-SR04 GND','Same GND rail','Connect'),
('W3','CN6 pin 25','Breadboard +5 V rail','Connect; JP1 short later'),
('W4','HC-SR04 VCC','Same +5 V rail','Leave sensor VCC end loose'),
('W5','HC-SR04 TRIG','CN6 pin 1 / P2.0','Connect directly'),
('W6','HC-SR04 ECHO','B10 / row 10','Connect to R1 input'),
('W7','D20 / Node B','CN6 pin 2 / P2.1','Leave CN6 pin 2 end loose'),
('W8','R3 ground end, if not already in rail','GND rail','Only if needed; direct resistor-to-rail placement needs no extra wire')],[43,127,155,CW-325])
p('There are <b>seven mandatory jumper wires (W1-W7)</b> in this arrangement. W8 is optional if R3 reaches the ground rail directly; take at least eight jumpers plus spares. Keep loose ends isolated so they cannot touch other contacts.')
def connections():
    box(14,24,165,150,'HC-SR04')
    box(310,24,182,150,'BOARD / DIVIDER')
    pairs=[('VCC','+5 V rail (W4 loose)',124),('TRIG','CN6 pin 1',95),('ECHO','B10 -> resistors',66),('GND','GND rail',37)]
    for a,b,yy in pairs:
        label(27,yy,a,10,True);wire([(178,yy+3),(310,yy+3)])
        label(322,yy,b,9)
    label(16,8,'Use the sensor PCB labels; this is not a physical pin-order picture.',8)
diagram(189,connections)
note('Check sensor labels, not a memorized view', 'The reference photos show VCC/TRIG/ECHO/GND from top to bottom with front transducers facing you and pins on the left; the rear view reverses that order. A rotated module changes the view. The printed labels win.')
finish()

# 7
start('Step 06 / Output peripherals', 'Add the two ribbon cables', 'Board OFF. Use whole straight-through FRC ribbons, with pin 1 aligned at each end. No individual LCD signal wires are needed.')
def ribbons():
    box(15,121,112,45,'CND');box(341,121,150,45,'CNAD','16 x 2 LCD')
    box(15,41,112,45,'CNA');box(341,41,150,45,'CNA5','Onboard buzzer')
    for yy in [141,61]:
        for dy in [-5,0,5]:wire([(127,yy+dy),(341,yy+dy)],TEAL,.8)
    label(172,159,'Ribbon 1: pin 1 to pin 1',9,True)
    label(172,79,'Ribbon 2: pin 1 to pin 1',9,True)
    label(15,17,'Logical map only - header positions on your kit may differ.',8)
diagram(185,ribbons)
table(['Action','Exactly what to do'],[
('LCD ribbon','CND -> CNAD. Short JP16 and JP5. Leave graphic LCD connections unused.'),
('LCD contrast','After final power-on, gently adjust POT3 if text is invisible. Use a screwdriver and no pressure; do not force or exceed the lab limit.'),
('Buzzer ribbon','CNA -> CNA5. The buzzer is P0.11, through ribbon contact 8 and the existing onboard driver.'),
('Keep unused','Motor and relay loads, LED ribbon CNA->CNA1, seven-segment ribbons, and graphic LCD. Do not try to use these together on CNA.'),
('Polarity check','Ask staff to confirm the buzzer active level with their example. Default BUZZ_ACTIVE_HIGH=1; if active low, use 0, rebuild, and reflash.')],[106,CW-106])
table(['LCD ribbon contact','GPIO','LCD function'],[
('1 / 2 / 3 / 4','P0.23 / P0.24 / P0.25 / P0.26','D4 / D5 / D6 / D7'),
('5 / 6','P0.27 / P0.28','RS / EN')],[150,195,CW-345])
p('These mappings are derived from the source tables for a 1:1 ribbon. LCD power/contrast is onboard; add no separate LCD 5 V lead. R/W is not MCU-controlled; use the kit wiring as provided.',SMALL)
finish()

# 8
start('Step 07 / Jumpers and cables', 'Set up the programming position', 'A jumper cap is SHORT when it joins the specified pins. OPEN means those pins are not joined. Ask staff if the label or cap orientation is unclear.')
table(['Item','FLASH position now','RUN position later'],[
('JP1','SHORT','SHORT: supplies sensor rail'),
('JP2','OPEN','OPEN for this UART setup'),
('JP3','SHORT: enter ISP','OPEN before run reset/power-on'),
('JP5','SHORT','SHORT: LCD D7 path'),
('JP6','SHORT','SHORT: normal 3.3 V board supply'),
('JP16','SHORT','SHORT: select 16 x 2 LCD'),
('SW21 (both DIP positions)','ON','OFF per supplied normal/UART0 run procedure')],[112,192,CW-304])
p('Leave all unrelated jumper groups in their existing lab-approved configuration. Do not remove the LPC1768 piggyback. <b>SW1 is RESET</b>; <b>SW21</b> is the programming handshake switch.')
h('Connect the PC and power cables, still with power off')
steps([
'Plug the lab USB-to-serial adapter into the PC. Connect its serial end to the lab grey RS232 cross cable.',
'Connect the grey serial cable to <b>CN9: left female DB9</b> in the supplied board notes. Read the CN9 label to confirm.',
'Connect the separate lab-supplied power cable to <b>CN8: right male DB9</b>. Keep the power source switched off for now.',
'On Windows, open <b>Device Manager -> Ports (COM &amp; LPT)</b>. Note the USB-serial port, for example COM4. Your number may differ.',
'Close serial terminals that could hold that COM port open. Keep W4 sensor VCC and W7 CN6 pin 2 disconnected.'
])
note('These DB9 connectors are not interchangeable', 'CN9 uses RS232 levels via the onboard MAX3232. Do not plug a TTL UART device into CN9. Use only the lab power lead for CN8; a serial cable is not a power supply.',True)
finish()

# 9
start('Step 08 / Keil on the PC', 'Save code, build, find the HEX', 'The board can remain OFF for this entire page. Best route: use a copy of the instructor-approved LPC1768 project that already builds on this kit.')
steps([
'Get the repository files on the PC. Copy the lab template project to a new folder such as <b>CollisionWarning</b>, then open its <b>.uvproj / .uvprojx</b> file in Keil.',
'Remove or exclude the template\'s old application file containing <b>int main(...)</b> from the build. Keep its startup file and <b>system_LPC17xx.c</b>. There must be only one application main function.',
'Copy this repository\'s <b>main.c</b> into that folder. In Keil\'s Project pane, right-click the source group -> <b>Add Existing Files to Group</b> -> choose main.c -> Add -> Close. It is fine to paste the complete listing into a new file and save it as main.c instead; do not include PDF line numbers.',
'Confirm target <b>NXP LPC1768</b> and board crystal <b>12.0 MHz</b>. Confirm the kit startup, CMSIS header <b>LPC17xx.h</b>, and system clock file are included. Leave <b>ENABLE_UART 0</b> for the first demo.',
'Open <b>Project -> Options for Target -> Output</b>; tick <b>Create HEX File</b>. For older lab profiles, the supplied settings list IROM1 start 0x0 / size 0x8000 and IRAM1 start 0x10000000 / size 0x8000. Use the instructor\'s approved profile; these are not the chip\'s full memory sizes.',
'Choose <b>Project -> Build Target</b> (commonly F7). Read Build Output. Continue only with <b>0 errors</b> and a created HEX file. Ask staff about warnings. An unused TTC warning with UART disabled does not prove hardware success or failure.',
'Find the generated <b>.hex</b> file in the configured output folder, often Objects. Record its full path and check its modification time. This is what you will select in Flash Magic, not main.c.'
])
note('If you have no lab template', 'Project -> New µVision Project -> choose LPC1768. Use device support/startup selected by your Keil version and the kit\'s matching system file. In newer versions this may be through Manage Run-Time Environment. Ask staff to confirm this first build; the repository does not supply those vendor files.')
p('The startup normally calls SystemInit() before main(). This program calls SystemCoreClockUpdate() in timer_init(). Do not add a second SystemInit() or rewrite PLL settings blindly. The 12 MHz crystal setting is not necessarily the CPU clock. Leave optional UART off: the source\'s 3 MHz core profile does not produce exact 9600 baud with the current divider.',SMALL)
finish()

# 10
start('Step 09 / First power-on', 'Check power before sensor VCC', 'You are checking the power rails only. W4 (sensor VCC) and W7 (Node B to CN6 pin 2) must still be disconnected and isolated.')
steps([
'With power off, ask staff to inspect resistor placement, CN6 numbering, ribbons, programming jumpers, and the separate serial/power cables.',
'Ask staff to operate the multimeter on <b>DC volts</b>, with its black probe on GND. Never use resistance/continuity mode on a powered kit, and never place a meter in current mode across a supply.',
'Switch on the lab board supply. With JP6 short, verify the power rails using the table below. Avoid letting probe tips bridge adjacent pins.',
'If the readings are wrong, or anything heats/smells, switch off immediately. Do not connect sensor VCC or P2.1. Have staff investigate.',
'When supplies are correct, switch the board <b>OFF</b>. Keep the sensor VCC lead and P2.1 lead loose for the first flash. Proceed to page 11.'
])
table(['Measurement','Expected nominal result','Who checks'],[
('TP1 to TP3 (GND)','About +5 V','Lab staff / supervised measurement'),
('TP2 to TP3 (GND)','About +3.3 V','Lab staff / supervised measurement'),
('CN6 pin 25 to pin 26','About +5 V with JP1 short','Lab staff confirms pin orientation first'),
('Breadboard +5 V rail to GND rail','About +5 V','Confirms W3/W1 rail routing')],[205,135,CW-340])
note('A staged first power-on is intentional', 'You have not yet connected the sensor supply or the MCU ECHO input. This prevents a rail mistake reaching the sensor/input before the basic power check. Do not skip directly from wiring to a full powered demo.',True)
p('The reference describes removing JP6 before first assembling a piggyback board. That is a staff commissioning procedure for an unassembled kit. For this already assembled lab kit, keep JP6 short and do not remove the piggyback.',SMALL)
finish()

# 11
start('Step 10 / Flash Magic', 'Send the built program to the kit', 'Board OFF while selecting the HEX and changing cables/jumpers. Sensor VCC and P2.1 are still disconnected for this first programming stage.')
table(['Flash Magic field','Set / select'],[
('Device / interface','LPC1768 / None (ISP), as named in the supplied lab notes'),
('COM port','Your Device Manager port, not an assumed COM1'),
('Baud / oscillator','Lab-supported 115200 baud; crystal 12 MHz'),
('Erase / verify','Erase blocks used by HEX before programming; verify after programming'),
('HEX file','The newly built main.c application HEX from page 9'),
('Advanced -> Hardware Config','DTR/RTS control RST/ISP; keep RTS asserted while COM is open'),
('Hardware timing','T1 = 50 ms; T2 = 100 ms, from supplied notes')],[155,CW-155])
steps([
'Confirm <b>JP2 open, JP3 short, JP6 short, SW21 both ON</b>. Keep JP1/JP5/JP16 short for the completed wiring.',
'After selecting the HEX with the kit off, power the kit on. Click <b>Start</b> in Flash Magic. Wait for erase, program, and verification to finish; read the success/error messages.',
'If unsuccessful, do not keep changing wires under power. Use the communication checks on page 15. The supplied lab sheet recommends High Speed Communications at 115200, while the ALS manual differs; use the lab-supported setting or try 9600/7200.',
'After successful verification, disconnect/close Flash Magic\'s serial session. Switch the board off. You will now change to RUN on page 12.'
])
note('Do not erase it afterward', 'The sequence is <b>erase -> program -> verify -> run</b>. Erasing after a successful download removes the application. The source\'s phrase about clearing flash after each download must not be followed literally.',True)
p('Flash Magic success means the program was transferred, not that sensor readings, timing, or physical wiring have been validated. Its ISP baud is separate from the optional application UART setting.',SMALL)
finish()

# 12
start('Step 11 / Verify ECHO', 'Test the divider before P2.1', 'A lab instructor must check the ECHO high pulse. Keep W7 disconnected from CN6 pin 2 until the pulse check passes.')
steps([
'With power <b>OFF</b>, <b>open JP3</b> and set <b>SW21 both OFF</b> using the lab run procedure. Leave JP1/JP5/JP6/JP16 short and JP2 open.',
'Connect <b>W4: HC-SR04 VCC to the verified +5 V rail</b>. Check sensor GND, TRIG, ECHO-to-R1, and all three resistors. Keep the CN6 pin 2 end of W7 loose and isolated.',
'Place a flat target about <b>50 cm</b> in front of the sensor. Power on/reset. The flashed firmware now generates trigger pulses automatically even though its ECHO input is disconnected.',
'Ask staff to measure <b>Node B / row 20 relative to GND during an ECHO high</b>, using the instrument correctly. Expected peak is about <b>2.62 V</b> for a 5 V ECHO. Check it stays within the supplied 3.3 V limit for the intended input.',
'If no pulse is seen, first verify the program is running, P2.0 TRIG pulses, sensor power/ground, and target alignment. An idle multimeter reading of 0 V is <b>not</b> proof of correct division.',
'After staff confirm the pulse is safe, switch power <b>OFF</b>. Connect <b>W7 from D20 / Node B to CN6 pin 2 / P2.1</b>. Check it does not touch adjacent contacts.',
'Now power on/reset again. This is the first full sensor-to-MCU run. Continue to page 13.'
])
note('SENSOR ERROR is expected during the disconnected-input test', 'The MCU cannot receive ECHO while W7 is loose. The LCD may show SENSOR ERROR / CHECK HC-SR04. Do not move W7 under power to try to clear it. Switch off, finish the validated connection, and restart.',True)
p('If the buzzer is unexpectedly on during SENSOR ERROR, switch off and check its active polarity with staff. The program intends to silence it in that state; the board\'s actual active level must match BUZZ_ACTIVE_HIGH.',SMALL)
finish()

# 13
start('Step 12 / First output', 'Read the LCD and hear the alarm', 'Use a flat book, board, or cardboard target facing the two transducers. Measure distance from the front of the sensor to the target.')
steps([
'Confirm RUN settings: <b>JP3 open, SW21 off</b>. All seven mandatory sensor wires are now connected. Power on; the firmware starts automatically. You do not need to press a PC Run button.',
'Keep a target at about <b>100 cm</b>. Wait for at least three valid readings and allow about one second for filtering/motion estimates to settle.',
'If the LCD is blank, adjust <b>POT3</b> gently within the lab\'s limit. If still blank, power off before inspecting CND->CNAD, JP16, and JP5.',
'Check that D roughly follows the target distance. Keep the target still: V should tend toward 0 and W toward 50.',
'Move to about <b>40 cm</b>, hold still, then to about <b>15 cm</b>. You should see WARNING, then CRITICAL with buzzer, assuming valid measurements and correct polarity.'
])
def lcd():
    c.setFillColor(colors.HexColor('#C9DEA1'));c.setStrokeColor(NAVY)
    c.roundRect(56,24,395,78,5,fill=1,stroke=1)
    c.setFont('Mono',17);c.setFillColor(NAVY)
    c.drawString(79,73,'D:100cm V:  0')
    c.drawString(79,44,'SAFE     W: 50')
    label(56,118,'Illustrative stationary-target display',10,True)
diagram(139,lcd)
table(['Readout','Meaning'],[
('D','Filtered distance in centimeters; it may lag briefly after moving the target.'),
('V','Estimated closing velocity in cm/s. Moving away is displayed as zero closing velocity.'),
('W','Current warning boundary in cm, normally 50 at rest and up to 150 for approach.'),
('State','SAFE / WARNING / CRITICAL. Only CRITICAL commands the buzzer on.'),
('SENSOR ERROR','Three invalid readings cause a fault; three consecutive valid readings recover it. Startup also requires three valid readings.')],[105,CW-105])
finish()

# 14
start('Step 13 / Demonstrate', 'Run these tests in order', 'These are expected software behaviors to verify on the bench, not measured results. Keep hands and objects clear of connectors while powered.')
table(['Test','What you do','Expected behavior'],[
('1. Stationary safe','Hold a flat target at 100 cm for a few seconds.','D near 100; V settles near 0; W near 50; SAFE; buzzer off.'),
('2. Warning','Move target to 40 cm and hold it.','After filtering settles: WARNING, W near 50; buzzer off.'),
('3. Critical','Move target to 15 cm, keeping it in the beam.','CRITICAL; buzzer on after a valid close reading, once startup recovery has completed.'),
('4. Clear critical','Move from 15 cm to 30 cm and hold.','Critical holds until filtered D exceeds 25 cm; then normally WARNING at 30 cm.'),
('5. Clear warning','Move from 40 cm to 60 cm and hold.','At settled W=50, WARNING clears only above 55 cm; then SAFE.'),
('6. Adaptive response','Approach slowly, then faster, from a valid distance such as 100 cm.','V becomes positive; W can rise, giving a larger warning boundary. A reading of 50 cm/s gives W=75 cm.'),
('7. Missing echo','Power off. Disconnect W7 at CN6 pin 2 and isolate it. Power on.','SENSOR ERROR remains; startup cannot recover without valid samples. Buzzer is intended off.'),
('8. Recovery','Power off, reconnect W7, power on with target at 100 cm.','Three consecutive valid readings permit normal classification.')],[77,202,CW-279])
p('For a running-fault demonstration, a powered W7 disconnection is not part of this beginner procedure. Out-of-range/no-reflection conditions can also produce invalid readings. Never rewire a live input just to test the counter.',SMALL)
note('Limits of what you can conclude', 'The valid range is configured as 2-400 cm, not a guarantee on all surfaces. The filter uses five readings; one or two invalid readings can leave old values visible. A missing reflection can mean no suitable target, not necessarily a broken sensor.')
finish()

# 15
start('If something does not work', 'Find the failing stage first', 'Switch off before every wiring, cable, or jumper change. Keep a note of the exact error message; do not change several things at once.')
table(['Problem','Check in this order'],[
('No power / no LED','Lab power source -> CN8 power cable -> JP6 short -> supervised TP1/TP2/GND measurements.'),
('Failed to open COM','Device Manager COM number -> driver/adapter recognized -> close serial terminal -> correct COM selected in Flash Magic.'),
('Failed to autobaud','CN9 serial cable -> JP2 open / JP3 short / SW21 on -> lab high-speed setting -> 115200, then supported lower baud (9600/7200).'),
('Still cannot communicate','Power off -> change USB port -> recheck new COM number. Lab replacement order: USB cable, RS232 cable, power supply, then kit.'),
('LPC17xx.h missing','Install/select LPC1768 device/CMSIS support and use the lab template include paths. Do not remove the include to hide the error.'),
('SystemInit or SystemCoreClock unresolved','Missing/mismatched kit startup or system_LPC17xx.c. Ask staff to restore the correct project files.'),
('Duplicate main / duplicate symbols','Old demo main.c still included, or startup/system files included twice. Exclude duplicates from the build.'),
('HEX flashed but nothing runs','Correct HEX timestamp -> JP3 open / SW21 off -> reset -> board supplies -> clock/startup match.'),
('LCD blank / blocks only','POT3 contrast -> power off -> CND->CNAD -> JP16 and JP5 short -> complete firmware and clock/timing.'),
('SENSOR ERROR persists','Flat target/alignment -> power off -> sensor labels/5 V/GND -> W5 TRIG -> divider and W7 at Node B -> staff checks pulses.'),
('Buzzer silent in CRITICAL','State really CRITICAL -> power off -> CNA->CNA5 -> staff polarity test -> correct BUZZ_ACTIVE_HIGH -> rebuild and reflash.'),
('Motor/relay acts / anything heats','Power off immediately; disconnect unused loads and ask staff to inspect CNA5 and the loaded program.')],[151,CW-151],font=SMALL)
p('Optional UART: keep ENABLE_UART=0 until the core clock and divider are validated. The source\'s 3 MHz core profile makes the current integer divider produce about 11,719 baud, not the intended 9600. Serial logging is not required for the LCD/buzzer demo.',SMALL)
finish()

# 16
start('Keep this page beside the board', 'Final connection and run checklist', 'Read the wire numbers together with page 6. This page is a recap; it does not replace the staged voltage checks on pages 10-12.')
table(['Check','Final connection / setting'],[
('[ ] Sensor supply','CN6 pin 25 -> +5 V rail -> sensor VCC; JP1 short.'),
('[ ] Common ground','CN6 pin 26 -> GND rail -> sensor GND and R3 ground end.'),
('[ ] Trigger','CN6 pin 1 / P2.0 -> sensor TRIG.'),
('[ ] ECHO input','Sensor ECHO -> B10; R1 A10-A15; R2 B15-B20; R3 C20-GND.'),
('[ ] ECHO output','D20 / Node B -> CN6 pin 2 / P2.1 only after safe-pulse check.'),
('[ ] LCD','CND -> CNAD ribbon, pin 1 aligned; JP5 and JP16 short; POT3 adjusted.'),
('[ ] Buzzer','CNA -> CNA5 ribbon, pin 1 aligned; loads disconnected; polarity checked.'),
('[ ] PC / power','Serial -> CN9; lab power -> CN8. JP6 short.'),
('[ ] RUN state','JP2 open; JP3 open; SW21 both off; JP1/JP5/JP6/JP16 short.'),
('[ ] Program','Correct main.c built with LPC1768 startup/system; HEX programmed and verified.'),
('[ ] Output','100 cm SAFE; 40 cm WARNING; 15 cm CRITICAL + buzzer; test with flat target.')],[109,CW-109])
h('Code and source trail')
p('The next five pages contain the <b>complete current main.c</b>. Prefer the repository file to avoid PDF copying mistakes. For offline use, an exact main.c file is also attached <i>inside this PDF</i>; in a desktop PDF reader, look for the Attachments / paperclip panel and save it to your Keil project folder. Browser PDF viewers may not expose attachments.',SMALL)
p('Repository: <link href="https://github.com/ayatinkering/Ultrasonic-Collision-Warning-System" color="#006D77">github.com/ayatinkering/Ultrasonic-Collision-Warning-System</link><br/>Guide based on supplied main.c, README.md, docs/design-notes.md, the ALS board pin-and-wiring reference, and LPC1768_HCSR04_Complete_Connection_Manual_REVISED.pdf (sections A-Q). Physical pin-1 orientation, adapter fit, supplies, and board performance remain for lab verification.',SMALL)
p('The supplied references cite the ALS user manual and MIT Manipal sheets. They disagree about some Flash Magic settings and contain pin-table uncertainties. This guide uses only the project\'s confirmed numbered signal assignments and flags the physical checks instead of inventing a board photograph. LCD/buzzer mappings assume a straight 1:1 ribbon. Do not copy unrelated peripheral-demo jumper settings into this build.',SMALL)
finish()

# Complete selectable code appendix, without altered code.
for chunk in range(ceil(len(code_lines)/CODE_PER_PAGE)):
    first = chunk*CODE_PER_PAGE
    lines = code_lines[first:first+CODE_PER_PAGE]
    start(f'Firmware appendix / {chunk+1} of {ceil(len(code_lines)/CODE_PER_PAGE)}', 'Complete main.c', f'Lines {first+1}-{first+len(lines)}. Copy only code, not the grey line numbers. The embedded main.c attachment preserves exact bytes.')
    c.setFillColor(colors.HexColor('#F3F6F8'))
    c.roundRect(M,y-590,CW,590,5,fill=1,stroke=0)
    yy=y-18
    for offset,line in enumerate(lines):
        c.setFont('Mono',7.5);c.setFillColor(MUTED)
        c.drawRightString(M+27,yy,str(first+offset+1))
        c.setFillColor(INK)
        assert pdfmetrics.stringWidth(line,'Mono',7.5) < CW-49, (first+offset+1,len(line))
        c.drawString(M+38,yy,line)
        yy-=11.2
    y-=605
    finish()
assert page == TOTAL, (page,TOTAL)
c.save()
writer=PdfWriter()
writer.clone_document_from_reader(PdfReader(BytesIO(buffer.getvalue())))
writer.add_attachment('main.c',(ROOT/'main.c').read_bytes())
writer.add_metadata({'/Title':'LPC1768 + HC-SR04: Beginner Lab Guide','/Author':'Ultrasonic Collision Warning System project'})
OUT.parent.mkdir(parents=True,exist_ok=True)
with OUT.open('wb') as f: writer.write(f)
print(f'Created {OUT} ({page} pages, embedded main.c).')
