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

# 入浴時間リスト
times = []
times.append(datetime.datetime.strptime('17:00', "%H:%M"))
while times[-1] < datetime.datetime.strptime('22:50', "%H:%M"):
    times.append(times[-1] + datetime.timedelta(minutes=25))
i=0
while i < len(times):
    times[i] = times[i].strftime("%H:%M")
    i += 1

@app.route("/", methods=["GET", "POST"])
def hello():
    return render_template("index.html", Error=0)

@app.route("/reserve", methods=["GET", "POST"])
def login_manager():
    # ユーザ変数取得
    print(request)
    userid = request.form["userid"]
    userpassword = request.form["password"]
    # ----------------------------------------------------------
    # DB接続
    # 
    # ----------------------------------------------------------1433
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+password)
    cursor = cnxn.cursor()

    # DBからパスワード取得
    sql = "SELECT userpassword FROM users WHERE userid = ?"
    cursor.execute(sql, userid)
    result = cursor.fetchone()
    # パスワード認証
    i = 0
    while i<10:
        userpassword = hashlib.sha256(userpassword.encode()).hexdigest()
        i += 1
    if userid is "" or userpassword is "":
        return render_template("index.html", Error=1)
    elif result[0] != userpassword:
        return render_template("index.html", Error=2)
    
    # initialize variable
    now = datetime.datetime.now()
    today = now.strftime("%Y_%m_%d")

    # ----------------------------------------------------------
    # 現時点の予約時間帯あたりの予約者数を取得
    # Get Today's number of RESERVATION.
    # ----------------------------------------------------------
    #
    #    |---------------------|-------------|
    #    |       date          | reserve_cnt |
    #    |---------------------|-------------|
    # Ex.| 2020-07-14 17:30:00 |      3      | 
    #    |---------------------|-------------|
    # Ex.| 2020-07-14 17:55:00 |      1      | 
    #    |---------------------|-------------|
    #    ～～～～～～～～～～～～～～～～～～～
    #
    # Note: only "today" argment for sql command must not escape. Koreha Siyou Desu.
    get_today_cnt = "SELECT date, count(userid) As reserve_cnt FROM reserve " \
                  + "WHERE bath_type = ? " \
                  + "group by date HAVING date LIKE '"+today+"%'" \
                  + "order by date asc;"
    print(get_today_cnt)
    
    # SMALL
    reservation_small = cursor.execute(get_today_cnt, 0).fetchall()# [('2020_07_141990-01-01 20:20:00',4), ...]
    reservation_small = np.array(reservation_small).T.tolist()# [['2020_07_141990-01-01 20:20:00', ... ], ['4', ... ]]
    print(reservation_small)

    # LARGE
    reservation_large = cursor.execute(get_today_cnt, 1).fetchall() # [('2020_07_141990-01-01 20:20:00',4), ...]
    reservation_large = np.array(reservation_large).T.tolist()# [['2020_07_141990-01-01 20:20:00', ... ], ['4', ... ]]
    print(reservation_large)

    # ----------------------------------------------------------
    # 新規予約か、予約更新かをチェック
    # 
    # ----------------------------------------------------------
    sql = "SELECT bath_type, date FROM reserve WHERE userid=? AND date LIKE ?;"
    cursor.execute(sql, userid, today+'%')

    result = cursor.fetchone() or ["",""]
    reserved = (result == None)
    bath_type = result[0]
    bath_time = str(result[1])[11:]
    
    # ----------------------------------------------------------
    # DB切断
    # 
    # ----------------------------------------------------------
    cursor.close()
    cnxn.close()

    # ----------------------------------------------------------
    # Generate Responce
    # 
    # ----------------------------------------------------------
    session['userid'] = userid
    session['login_flag'] = True
    session['reserved'] = reserved
    # dic = {'userid':userid, 'login_flag':True, 'reserved':reserved}
    # responce.set_cookie('cookie', value = json.dumps(dic))
    return make_response(
        render_template("reserve.html",
            today=now.strftime("%m/%d") ,
            userid=userid,
            times=times,
            times_len=len(times),
            reservation_small=reservation_small[1],
            reservation_large=reservation_large[1],
            bath_type=bath_type,
            bath_time=bath_time
        )
    )

@app.route("/reserve_resister", methods=["GET", "POST"])
def reserve_register():
    # ユーザ変数取得
    userid = session['userid']
    desired_time = request.form["desired_time"]
    now = datetime.datetime.now()
    today = now.strftime("%Y_%m_%d ")
    bath_type = int(desired_time)//100
    desired_time = now.strftime("%Y_%m_%d ") + times[int(desired_time)%100]
    # DB接続
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+password)
    cursor = cnxn.cursor()
    # パスワード認証
    # i = 0
    # while i<10:
    #     userpassword = hashlib.sha256(userpassword.encode()).hexdigest()
    #     i += 1
    # セッション認証
    if session['login_flag']:
        if session['reserved']:
            # DBの予約を更新
            sql = "UPDATE reserve SET bath_type=?, date=? WHERE userid=? AND date LIKE ?"
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
    return render_template("reserve_success.html", desired_time=desired_time, userid=userid)
    
@app.route("/user_regist_form", methods=["GET", "POST"])
def user_regist_form():
    return render_template("user_regist_form.html")

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
        return render_template("user_regist_form.html", Error=2)
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
    return render_template("user_regist_success.html")

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)