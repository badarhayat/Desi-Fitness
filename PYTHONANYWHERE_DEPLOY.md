PythonAnywhere Deployment (badarniazi)

1) Open a Bash console on PythonAnywhere.

2) Clone your repo into home:
   cd ~
   git clone https://github.com/badarhayat/Desi-Fitness.git
   cd Desi-Fitness

3) Create and activate virtualenv (Python 3.10 example):
   mkvirtualenv --python=/usr/bin/python3.10 desifitness-env
   workon desifitness-env

4) Install dependencies:
   pip install --upgrade pip
   pip install -r requirements.txt

5) In PythonAnywhere dashboard:
   - Go to Web tab
   - Add a new web app (Manual configuration, Python 3.10)
   - Set virtualenv path to: /home/badarniazi/.virtualenvs/desifitness-env
   - Set source code path to: /home/badarniazi/Desi-Fitness

6) Edit WSGI file in Web tab and replace contents with:

   import sys
      path = '/home/badarniazi/Desi-Fitness'
   if path not in sys.path:
       sys.path.insert(0, path)

   from app import app as application

7) Static files mapping (Web tab):
   URL: /static/
   Directory: /home/badarniazi/Desi-Fitness/static/

8) Click Reload on Web tab.

9) Visit your app URL:
   https://badarniazi.pythonanywhere.com

Troubleshooting:
- If app fails, check error log in Web tab.
- If dependencies fail to build, install a compatible Python version in step 3.
- If page loads but styles/images are missing, re-check /static/ mapping.
