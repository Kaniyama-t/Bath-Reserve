from flask import *
import datetime
import hashlib
import pyodbc
import random
import json
from my_server_setting import server, database, username, password, driver 

import numpy as np

app = Flask(__name__)
app.secret_key = str(random.randrange(9999999999999999))
app.jinja_env.add_extension('jinja2.ext.loopcontrols')

# session['*']が外部から操作されないよう対策
cookie_secure = True
app.config.update(
    SESSION_COOKIE_SECURE=cookie_secure,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

# Cookieの保存期間
cookie_maxAge = 60 * 60 * 24 * 90

# 入浴時間リスト
# 七宝寮
times_cloisonne = []
times_cloisonne.append(datetime.datetime.strptime('17:00', "%H:%M"))
while times_cloisonne[-1] < datetime.datetime.strptime('22:50', "%H:%M"):
    times_cloisonne.append(times_cloisonne[-1] + datetime.timedelta(minutes=25))
i=0
while i < len(times_cloisonne):
    times_cloisonne[i] = times_cloisonne[i].strftime("%H:%M")
    i += 1
# 紫雲寮
times_purple = []
times_purple.append(datetime.datetime.strptime('17:00', "%H:%M"))
while times_purple[-1] < datetime.datetime.strptime('20:45', "%H:%M"):
    times_purple.append(times_purple[-1] + datetime.timedelta(minutes=45))
times_purple.append(times_purple[-1] + datetime.timedelta(minutes=15))
while times_purple[-1] < datetime.datetime.strptime('22:30', "%H:%M"):
    times_purple.append(times_purple[-1] + datetime.timedelta(minutes=45))
times_purple.append(times_purple[-1] + datetime.timedelta(minutes=30))
i=0
while i < len(times_purple):
    times_purple[i] = times_purple[i].strftime("%H:%M")
    i += 1

# --------------------------------
# モバイル版仕様
# １．初回アクセス
# 　古いバージョンのUIが表示されます
# 
# ２．新・旧UI表示の仕組み
# 　すべてのmake_responce関数において，sessionの"TemplateRootPath"に指定されたディレクトリ直下のテンプレートを読み込むようにする．
# 
# ３．新・旧UI切替の仕組み
# 　POSTかGETでui=ver2を入れると，before_request関数でsessionの値が書き換わり新しいバージョンに切り替わる．
# --------------------------------
# モバイル版対応コードここから
# --------------------------------

# POSTかGETのすべてのリクエストが処理される前に実行
def before_request():
    # *******************************************************
    # Login Session & Auto Login
    if ('login_flag' not in session):
        session['login_flag'] = False
    # *******************************************************
    # UI切替トリガ
    # --- 初回アクセス --------------------------------------
    if ('TemplateRootPath' not in request.cookies):
        SwitchUI = 'default'
    # --- 前回のUI設定を復元 --------------------------------
    elif ('TemplateRootPath' not in session):
        session['TemplateRootPath'] = request.cookies['TemplateRootPath']
        SwitchUI = None
    # --- 変更指定があったら(GET) ---------------------------
    elif (request.method == 'GET') and (request.args.get('ui',default=None)):
        SwitchUI = request.args.get('ui')
    # --- 変更指定があったら(POST) --------------------------
    elif (request.method == 'POST') and ('ui' in request.form):
        SwitchUI = request.form['ui']
    # --- 変更なし ------------------------------------------
    else:
        SwitchUI = None

    # *******************************************************
    # UI切替
    # --- 新バージョン --------------------------------------
    if SwitchUI == 'ver2':
        session['TemplateRootPath'] = 'mobile/'
        session['switchUI'] = True
    # elif modeq == 'ver3':
    #     pass
    # ...
    # --- デフォルト ----------------------------------------
    elif SwitchUI:
        session['TemplateRootPath'] = ''
    # --- 変更なし ------------------------------------------
    else:
        pass

def after_request(responce):
    responce.set_cookie("TemplateRootPath",session['TemplateRootPath'],max_age=cookie_maxAge,secure=cookie_secure,httponly=True)
    return responce
    

app.before_request(before_request)
app.after_request(after_request)
# --------------------------------
# モバイル版対応コードここまで
# --------------------------------

# ログインページへの遷移
@app.route("/", methods=["GET", "POST"])
def hello():
    if ('autologin_userid' in request.cookies) and ('autologin_userpassword' in request.cookies):
        return redirect('/reserve')

    return render_template(session['TemplateRootPath'] + "index.html", Error=0)

# 予約入力画面への遷移
@app.route("/reserve", methods=["GET", "POST"])
def login_manager():
    # ----------------------------------------------------------
    # DB接続
    # 
    # ----------------------------------------------------------1433
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+password)
    cursor = cnxn.cursor()

    # ----------------------------------------------------------
    # ログイン処理
    # 
    # ----------------------------------------------------------1433
    # ※ログイン済みの場合はこの処理を飛ばして予約状況取得へ行きます．
    # bug fixed     : /reserve決め打ちしてアクセスした時に400エラー発生を修正
    # security fixed: パス登録をしていなくてもログインできる点を防止 
    if (not session['login_flag']):
        # ちゃんとuseridとpasswordに値が入っていて，未登録ユーザじゃないなら
        if ('userid' in request.form) and ('password' in request.form) and (request.form["userid"]) and (request.form["password"]):
            userid = request.form["userid"]
            userpassword = request.form["password"]
            autosave = ('save_authentification' in request.form)
        elif ('autologin_userid' in request.cookies) and ('autologin_userpassword' in request.cookies):
            userid = request.cookies.get('autologin_userid',type=str)
            userpassword = request.cookies.get('autologin_userpassword',type=str)
            autosave = True
        else:
            # お前...さてはログイン情報入れずにリクエストしたやろ...
            return render_template(session['TemplateRootPath'] + "index.html", Error=1)

        sql = "SELECT userpassword FROM users WHERE userid = ?"
        cursor.execute(sql, userid)
        result = cursor.fetchone()
        # パスワード認証
        i = 0
        hashedpass = userpassword
        while i<10:
            hashedpass = hashlib.sha256(hashedpass.encode()).hexdigest()
            i += 1
            
        # パスワードによる認証結果の分岐
        # --- 成功 --------------------------------------------------------------
        if result[0] == hashedpass:
            session['userid'] = userid
            session['login_flag'] = True

            responce = redirect('/reserve') # /reserveページで更新した際に「フォームの内容を再度送信しますか？」と表示されるのを回避
            # 自動ログインの登録
            if autosave:
                responce.set_cookie("autologin_userid",userid,max_age=cookie_maxAge,secure=cookie_secure,httponly=True)
                responce.set_cookie("autologin_userpassword",userpassword,max_age=cookie_maxAge,secure=cookie_secure,httponly=True)
            
            return responce
        # --- 失敗 --------------------------------------------------------------
        else:
            session['userid'] = ''
            session['login_flag'] = False
            responce = make_response(
                render_template(session['TemplateRootPath'] + "index.html", Error=2)
            )
            responce.set_cookie("autologin_userid",'',expires=0)
            responce.set_cookie("autologin_userpassword",'',expires=0)
            return responce
            
    else:
        userid = session['userid']

    # ----------------------------------------------------------
    # 寮取得
    # 
    # ----------------------------------------------------------
    sql = "SELECT dormitory_type FROM users WHERE userid = ?"
    cursor.execute(sql, userid)
    result = cursor.fetchone()
    dormitory_type = result[0]

    # ----------------------------------------------------------
    # DBから時間帯あたりの予約者数を取得
    # 
    # ----------------------------------------------------------
    # initialize variable
    now = datetime.datetime.now()
    today = now.strftime("%Y_%m_%d ")
    # 七宝寮 or 紫雲寮
    sql = "SELECT "
    i = 0
    while i < len(times_cloisonne)-1:
        sql = sql + "SUM(CASE WHEN date = '" + today + times_cloisonne[i] + "' THEN 1 ELSE 0 END), "
        i += 1
    sql_small = sql[:-2] +" FROM reserve WHERE bath_type = 0;"
    sql_large = sql[:-2] +" FROM reserve WHERE bath_type = 1;"
    cursor.execute(sql_small)
    reservation_small = cursor.fetchone()
    cursor.execute(sql_large)
    reservation_large = cursor.fetchone()
    sql = "SELECT "
    i = 0
    while i < len(times_purple)-1:
        sql = sql + "SUM(CASE WHEN date = '" + today + times_purple[i] + "' THEN 1 ELSE 0 END), "
        i += 1
        if i == 5:
            i += 1
    print(sql)
    sql_purple = sql[:-2] +"FROM reserve WHERE bath_type = 2"
    cursor.execute(sql_purple)
    reservation_purple = cursor.fetchone()
    print(reservation_purple)
    print(times_purple[5])
    print(len(times_purple))
    # ----------------------------------------------------------
    # 既存の自身の予約を確認
    # 
    # ----------------------------------------------------------
    sql = "SELECT bath_type, date FROM reserve WHERE userid=? AND date LIKE ?;"
    cursor.execute(sql, userid, today+"%")
    
    result = cursor.fetchone()
    reserved = (result != None)

    result = result or ['','']
    bath_type = result[0]
    bath_time = str(result[1])[11:]
    print(bath_time)

    # ----------------------------------------------------------
    # DB切断
    # 
    # ----------------------------------------------------------
    cursor.close()
    cnxn.close()

    # ----------------------------------------------------------
    # ページ・レスポンスの作成
    # 
    # ----------------------------------------------------------
    session['reserved'] = reserved
    session['dormitory_type'] = dormitory_type
    if dormitory_type == 0:
        responce = make_response(render_template(session['TemplateRootPath'] + "reserve.html",today=now.strftime("%m/%d") ,userid=userid, times=times_cloisonne, times_len=len(times_cloisonne), reservation_small=reservation_small, reservation_large=reservation_large, reservation_purple=reservation_purple,bath_type=bath_type, bath_time=bath_time, dormitory_type=dormitory_type))
        return responce
    elif dormitory_type == 1:
        responce = make_response(render_template(session['TemplateRootPath'] + "reserve.html",today=now.strftime("%m/%d") ,userid=userid, times=times_purple, times_len=len(times_purple), reservation_small=reservation_small, reservation_large=reservation_large, reservation_purple=reservation_purple, bath_type=bath_type, bath_time=bath_time, dormitory_type=dormitory_type))
        return responce

# 予約の実行，予約完了画面への遷移
@app.route("/reserve_resister", methods=["GET", "POST"])
def reserve_register():
    # ユーザ変数取得
    userid = session['userid']
    desired_time = request.form["desired_time"]
    now = datetime.datetime.now()
    today = now.strftime("%Y_%m_%d ")
    bath_type = int(desired_time)//100
    # desired_time = now.strftime("%Y_%m_%d ") + times[int(desired_time)%100]
    if session['dormitory_type'] == 0:
        desired_time = now.strftime("%Y_%m_%d ") + times_cloisonne[int(desired_time)%100]
    elif session['dormitory_type'] == 1:
        desired_time = now.strftime("%Y_%m_%d ") + times_purple[int(desired_time)%100]
    # DB接続
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+password)
    cursor = cnxn.cursor()
    # セッション認証
    if session['login_flag']:
        # 予約状況再確認
        sql = "SELECT SUM(CASE WHEN date = ? THEN 1 ELSE 0 END) FROM reserve WHERE bath_type=?;"
        cursor.execute(sql, desired_time, bath_type)
        result = cursor.fetchone()
        result[0] = result[0] or 0
        print(result)
        if (result[0] >= 9 and bath_type == 1) or (result[0] >= 4 and bath_type == 0) or (result[0] >= 6 and bath_type == 2):
            return render_template("index.html", Error=3)
        if session['reserved']:
            # DBの予約を更新
            sql = "UPDATE reserve SET bath_type=?, date=? WHERE userid=? AND date LIKE ?;"
            cursor.execute(sql, str(bath_type), desired_time, session['userid'], today+"%")
            cnxn.commit()
        else:
            # DBに予約登録
            sql = "INSERT INTO reserve VALUES(?, ?, ?)"
            cursor.execute(sql, session["userid"], str(bath_type), desired_time)
            cnxn.commit()
    else:
        render_template("index.html", Error=3)
    # DB切断
    cursor.close()
    cnxn.close()
    #返却処理
    session.pop('userid', None)
    session.pop('login_flag', None)
    session.pop('reserved', None)
    session.pop('dormitory_type', None)
    return render_template(session['TemplateRootPath'] + "reserve_success.html", desired_time=desired_time, userid=userid, autologin=('autologin_userid' in request.cookies))
    
# ユーザー登録への遷移
@app.route("/user_regist_form", methods=["GET", "POST"])
def user_regist_form():
    return render_template(session['TemplateRootPath'] + "user_regist_form.html")

# ユーザー登録の実行，登録完了画面への遷移
@app.route("/user_register", methods=["GET","POST"])
def user_resister():
    # ユーザ変数取得
    userid = request.form["userid"]
    userpassword = request.form["password"]
    # DB接続
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+password)
    cursor = cnxn.cursor()
    # DBに学籍番号の存在を問い合わせ
    sql = "SELECT userid FROM users WHERE userid=?"
    cursor.execute(sql, userid)
    result = cursor.fetchone()
    if(result == None):
        return render_template("user_regist_form.html", Error=1)
    # DBにパスワードがすでに登録されているかを確認
    sql = "SELECT userpassword FROM users WHERE userid=?"
    cursor.execute(sql, userid)
    result = cursor.fetchone()
    if(result[0] != ""):
        return render_template(session['TemplateRootPath'] + "user_regist_form.html", Error=2)
    # パスワードストレッチング
    i = 0
    while i<10:
        userpassword = hashlib.sha256(userpassword.encode()).hexdigest()
        i += 1
    # DBにパスワードを登録
    sql = "UPDATE users SET userpassword=? WHERE userid=?"
    cursor.execute(sql, userpassword, userid)
    cnxn.commit()
    # DB切断
    cursor.close()
    cnxn.close()
    # 返却処理
    return render_template(session['TemplateRootPath'] + "user_regist_success.html")

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session['login_flag'] = False
    session['userid'] = False
    responce = redirect('/')
    responce.set_cookie("autologin_userid",'',expires=0)
    responce.set_cookie("autologin_userpassword",'',expires=0)
    return responce

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)