For Window ความต้องการระบบ window 10, python 3.10.0
การ set up project
ให้ติดตั้ง python 3.10.0 ที่เครื่องก่อน
ขณะติดตั้งห้ามติ๊กเลือก add path ให้ติดตั้งแบบ default ทั่วไป
เริ่ม init project ที่ root folder
python -m venv .venv
VS Code จะเลือก interpreter อัติโนมัติ

./.venv/Scripts/python.exe      (Windows)

./.venv/bin/python              (WSL / Linux)

ติดตั้ง python 3.10 env
py -3.10 -m venv .venv

ใน CMD
.\.venv\Scripts\activate
หลังจาก activate แล้ว prompt จะเปลี่ยนเป็น: (.venv) D:\ML\pom_rl_ive>
python -m pip install --upgrade pip
pip install -r requirements.txt

library ใน venv:
python -c "import sys, numpy, pandas; print(sys.version); print(numpy.__version__); print(pandas.__version__)"

ใน VS Code:

1. กด Ctrl+Shift+P

2. พิมพ์ Python: Select Interpreter

3. เลือก: Enter interpreter path เช่น
D:\Nodejs_Project\face_qscan\.venv\Scripts\python.exe


การ setup xprinter
1. ให้ติดตั้ง driver POS printer ก่อนแล้วทำการทดสอบพิมพ์ 
2. หากยังพิมพ์ไม่ได้ให้ติดตั้ง Xprinter


การ setup window task
1. สร้าง Task sleep เวลา 12:05 น.

ใน Task Scheduler: เลือก Create Basic Task
Name ใส่: Face Queue Sleep
หากต้องการเฉพาะวันจันทร์–ศุกร์ ให้เลือก Trigger เป็น Weekly แล้วเลือก Monday ถึง Friday แทน Daily
กำหนดเวลา 12:05:00
Action เลือก Start a program
กด Browse แล้วเลือก sleep_pc.bat
เลือก Run whether user is logged on 


2.  สร้าง Task ปลุกเครื่อง 04:50 น.
ใน Task Scheduler: เลือก Create Task
Name ใส่: Face Queue Awake
Trigger เป็น Weekly แล้วเลือก Monday ถึง Friday แทน Daily
กำหนดเวลา 04:50:00
Action เลือก Start a program
กด Browse แล้วเลือก start_face_qscan.bat
ตรง Start in (optional) ใส่ตำแหน่งโฟลเดอร์โปรเจกต์ เช่น: D:\Nodejs_Project\face_qscan
Conditions : Wake the computer to run this task
หากเป็น Notebook และต้องการให้ทำงานแม้ใช้แบตเตอรี่ ให้เอาติ๊กออกจาก:
Start the task only if the computer is on AC power
เลือก Run whether user is logged on 

3. เปิด Wake Timer ใน Windows

หากเครื่องไม่ตื่นตามเวลา ให้ตรวจสอบดังนี้:

เปิด Control Panel
เข้า Power Options
เลือก Change plan settings
เลือก Change advanced power settings
เปิดหัวข้อ Sleep
เปิด Allow wake timers
ตั้งเป็น Enable
กด OK

4. ทดสอบก่อนใช้งานจริง

ทดสอบ Sleep:

หา Task ชื่อ Face Queue Sleep
คลิกขวา
เลือก Run
เครื่องควรเข้า Sleep

ทดสอบการปลุก แนะนำแก้เวลา Task Face Queue Wake ให้เป็นอีกประมาณ 3–5 นาทีข้างหน้า จากนั้นสั่งเครื่อง Sleep และรอดูว่าเครื่องตื่นและเปิดโปรเจกต์หรือไม่


For Linux